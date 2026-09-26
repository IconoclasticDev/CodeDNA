"""Safe local ZIP and allow-listed public GitHub repository ingestion."""

from __future__ import annotations

import base64
import binascii
import io
import json
import re
import urllib.error
import urllib.request
import zipfile
from pathlib import PurePosixPath
from urllib.parse import quote

MAX_ARCHIVE_BYTES = 25_000_000
MAX_UNCOMPRESSED_BYTES = 50_000_000
MAX_ARCHIVE_MEMBERS = 2_000
MAX_PYTHON_FILES = 100
GITHUB_RE = re.compile(r"^https://github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+?)(?:\.git)?/?$")
GITHUB_REF_RE = re.compile(r"^[A-Za-z0-9._/-]{1,100}$")
EXCLUDED_PARTS = {
    ".git", ".venv", "venv", "env", "site-packages", "node_modules", "vendor",
    "dist", "build", "generated", "migrations", "__pycache__", "coverage", "third_party",
}


class IngestionError(ValueError):
    pass


def _safe_member(name: str) -> bool:
    path = PurePosixPath(name.replace("\\", "/"))
    return not path.is_absolute() and ".." not in path.parts and not any(part in EXCLUDED_PARTS for part in path.parts)


def python_files_from_zip(data: bytes) -> tuple[list[dict], dict]:
    if len(data) > MAX_ARCHIVE_BYTES:
        raise IngestionError("The ZIP exceeds the 25 MB compressed limit.")
    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile as exc:
        raise IngestionError("The uploaded archive is not a valid ZIP file.") from exc
    members = archive.infolist()
    if len(members) > MAX_ARCHIVE_MEMBERS:
        raise IngestionError("The ZIP contains too many entries.")
    if sum(member.file_size for member in members) > MAX_UNCOMPRESSED_BYTES:
        raise IngestionError("The ZIP exceeds the 50 MB extracted-size limit.")

    files: list[dict] = []
    unsafe = excluded = unreadable = 0
    for member in members:
        if member.is_dir():
            continue
        if not _safe_member(member.filename):
            unsafe += 1
            continue
        if not member.filename.lower().endswith(".py"):
            excluded += 1
            continue
        # Unix symlink marker in the high file-mode bits.
        if (member.external_attr >> 16) & 0o170000 == 0o120000:
            unsafe += 1
            continue
        if member.file_size > 1_000_000:
            excluded += 1
            continue
        try:
            content = archive.read(member).decode("utf-8")
        except (UnicodeDecodeError, RuntimeError, zipfile.BadZipFile):
            unreadable += 1
            continue
        files.append({"name": member.filename, "content": content})
        if len(files) >= MAX_PYTHON_FILES:
            break
    if not files:
        raise IngestionError("The ZIP contains no eligible UTF-8 Python files.")
    return files, {"archive_entries": len(members), "unsafe_skipped": unsafe, "non_python_skipped": excluded, "unreadable_skipped": unreadable}


def python_files_from_base64(value: str) -> tuple[list[dict], dict]:
    try:
        data = base64.b64decode(value, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise IngestionError("The archive payload is not valid base64.") from exc
    return python_files_from_zip(data)


def _github_json(url: str, timeout: int, max_bytes: int = 10_000_000) -> dict:
    request = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json", "User-Agent": "CodeDNA-Hackathon/0.3"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload = response.read(max_bytes + 1)
    if len(payload) > max_bytes:
        raise IngestionError("GitHub returned more repository metadata than the safety limit allows.")
    return json.loads(payload)


def _github_raw_text(owner: str, repository: str, commit_sha: str, path: str, timeout: int) -> str:
    encoded_path = quote(path, safe="/")
    raw_url = f"https://raw.githubusercontent.com/{owner}/{repository}/{commit_sha}/{encoded_path}"
    request = urllib.request.Request(raw_url, headers={"User-Agent": "CodeDNA-Hackathon/0.3"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        content_length = int(response.headers.get("Content-Length", "0") or 0)
        if content_length > 1_000_000:
            raise IngestionError("A repository file exceeds the 1 MB analysis limit.")
        data = response.read(1_000_001)
    if len(data) > 1_000_000:
        raise IngestionError("A repository file exceeds the 1 MB analysis limit.")
    return data.decode("utf-8")


def github_repository_files(url: str, timeout: int = 15, ref: str | None = None) -> tuple[list[dict], dict]:
    match = GITHUB_RE.fullmatch(url.strip())
    if not match:
        raise IngestionError("Use a public GitHub repository URL such as https://github.com/owner/repository.")
    owner, repository = match.groups()
    repository = repository.removesuffix(".git")
    api_url = f"https://api.github.com/repos/{owner}/{repository}"
    try:
        metadata = _github_json(api_url, timeout)
        selected_ref = ref or metadata.get("default_branch", "main")
        if not GITHUB_REF_RE.fullmatch(selected_ref) or ".." in selected_ref:
            raise IngestionError("The requested Git reference is invalid.")
        commit = _github_json(f"{api_url}/commits/{quote(selected_ref, safe='')}", timeout)
        commit_sha = str(commit.get("sha", ""))
        if not re.fullmatch(r"[0-9a-fA-F]{40}", commit_sha):
            raise IngestionError("GitHub did not return a valid commit for the repository.")
        tree_sha = str(commit.get("commit", {}).get("tree", {}).get("sha", ""))
        if not re.fullmatch(r"[0-9a-fA-F]{40}", tree_sha):
            raise IngestionError("GitHub did not return a valid tree for the repository.")
        tree = _github_json(f"{api_url}/git/trees/{tree_sha}?recursive=1", timeout)
        entries = tree.get("tree") or []
        files: list[dict] = []
        unsafe = unreadable = oversized = 0
        eligible = []
        for entry in entries:
            path = str(entry.get("path", ""))
            if entry.get("type") != "blob" or not path.lower().endswith(".py"):
                continue
            if not _safe_member(path):
                unsafe += 1
                continue
            if int(entry.get("size", 0) or 0) > 1_000_000:
                oversized += 1
                continue
            eligible.append(path)
        for path in sorted(eligible)[:MAX_PYTHON_FILES]:
            try:
                content = _github_raw_text(owner, repository, commit_sha, path, timeout)
            except (UnicodeDecodeError, IngestionError, urllib.error.URLError, TimeoutError):
                unreadable += 1
                continue
            files.append({"name": f"{repository}-{commit_sha[:12]}/{path}", "content": content})
        if not files:
            raise IngestionError("The repository contains no eligible UTF-8 Python files.")
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            raise IngestionError("The repository is private, unavailable, or does not exist. Upload a ZIP instead.") from exc
        if exc.code == 403:
            raise IngestionError("GitHub refused the request or rate-limited access. Upload a ZIP instead.") from exc
        raise IngestionError(f"GitHub returned HTTP {exc.code}. Upload a ZIP instead.") from exc
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise IngestionError("GitHub could not be reached. Upload a ZIP or use cached demo data.") from exc
    stats = {
        "repository": f"{owner}/{repository}",
        "requested_ref": selected_ref,
        "commit_sha": commit_sha,
        "tree_entries": len(entries),
        "tree_truncated": bool(tree.get("truncated")),
        "eligible_python_files": len(eligible),
        "selected_python_files": len(files),
        "unsafe_skipped": unsafe,
        "non_python_skipped": max(0, len(entries) - len(eligible)),
        "unreadable_skipped": unreadable + oversized,
    }
    return files, stats


def collect_payload_files(payload: dict) -> tuple[list[dict], list[dict]]:
    files = list(payload.get("files") or [])
    sources: list[dict] = []
    archive = payload.get("archive_base64")
    if archive:
        archive_files, stats = python_files_from_base64(str(archive))
        files.extend(archive_files)
        sources.append({"type": "zip", **stats})
    for url in payload.get("repository_urls") or []:
        repository_files, stats = github_repository_files(str(url))
        files.extend(repository_files)
        sources.append({"type": "github", **stats})
    if not files:
        raise IngestionError("Provide Python files, a ZIP archive, or a public GitHub repository URL.")
    return files, sources

