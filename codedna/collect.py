"""Permission-aware, commit-pinned public GitHub dataset collector."""

from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path, PurePosixPath

from .ingest import github_repository_files

AUTHOR_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


def collect_sources(source_csv: Path, dataset_dir: Path, resolved_manifest: Path) -> dict:
    if not source_csv.is_file():
        raise ValueError(f"Source manifest does not exist: {source_csv}")
    with source_csv.open(newline="", encoding="utf-8-sig") as stream:
        rows = list(csv.DictReader(stream))
    required = {"author_id", "repository", "license_or_permission"}
    if not rows or not required.issubset(rows[0]):
        raise ValueError(f"Source manifest must contain: {', '.join(sorted(required))}.")

    resolved = []
    total_files = 0
    for row in rows:
        author = (row.get("author_id") or "").strip()
        repository_url = (row.get("repository") or "").strip()
        permission = (row.get("license_or_permission") or "").strip()
        requested_ref = (row.get("ref") or row.get("commit_or_snapshot") or "").strip() or None
        if not AUTHOR_RE.fullmatch(author):
            raise ValueError(f"Invalid author_id: {author!r}.")
        if not permission:
            raise ValueError(f"Missing license or permission note for author {author}.")
        files, stats = github_repository_files(repository_url, ref=requested_ref)
        repository_name = stats["repository"].split("/", 1)[1]
        target_root = dataset_dir / author / repository_name
        written = 0
        for item in files:
            path = PurePosixPath(item["name"])
            relative_parts = path.parts[1:] if len(path.parts) > 1 else path.parts
            relative = Path(*relative_parts)
            target = (target_root / relative).resolve()
            target.relative_to(target_root.resolve())
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(item["content"], encoding="utf-8")
            written += 1
        total_files += written
        resolved.append(
            {
                "author_id": author,
                "repository": repository_url,
                "commit_sha": stats["commit_sha"],
                "license_or_permission": permission,
                "eligible_files": written,
                "excluded_files": stats["non_python_skipped"] + stats["unreadable_skipped"] + stats["unsafe_skipped"],
                "collection_notes": (row.get("collection_notes") or "").strip(),
            }
        )

    resolved_manifest.parent.mkdir(parents=True, exist_ok=True)
    with resolved_manifest.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(resolved[0]))
        writer.writeheader()
        writer.writerows(resolved)
    return {
        "repositories": len(resolved),
        "authors": len({row["author_id"] for row in resolved}),
        "files": total_files,
        "dataset_directory": str(dataset_dir),
        "resolved_manifest": str(resolved_manifest),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect commit-pinned public repositories for CodeDNA training.")
    parser.add_argument("sources", type=Path, help="CSV containing author_id, repository and license_or_permission.")
    parser.add_argument("--dataset", type=Path, default=Path("work/dataset"))
    parser.add_argument("--manifest", type=Path, default=Path("work/evaluation/resolved_sources.csv"))
    args = parser.parse_args()
    print(json.dumps(collect_sources(args.sources, args.dataset, args.manifest), indent=2))


if __name__ == "__main__":
    main()

