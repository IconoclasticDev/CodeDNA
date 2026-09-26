"""Audit a multi-author dataset before model training."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

from .features import FeatureExtractionError, extract_features
from .ingest import EXCLUDED_PARTS


def audit_dataset(root: Path) -> tuple[list[dict], dict]:
    if not root.is_dir():
        raise ValueError(f"Dataset directory does not exist: {root}")
    rows: list[dict] = []
    digest_owners: dict[str, set[str]] = defaultdict(set)
    for author_dir in sorted(path for path in root.iterdir() if path.is_dir()):
        author = author_dir.name
        for path in sorted(author_dir.rglob("*.py")):
            relative = path.relative_to(root).as_posix()
            status = "eligible"
            reason = ""
            content = ""
            if any(part in EXCLUDED_PARTS for part in path.parts):
                status, reason = "excluded", "excluded directory"
                content = ""
            else:
                try:
                    content = path.read_text(encoding="utf-8")
                    if len(content.encode("utf-8")) > 1_000_000:
                        status, reason = "excluded", "larger than 1 MB"
                    else:
                        extract_features(path.name, content)
                except UnicodeDecodeError:
                    content = ""
                    status, reason = "invalid", "not UTF-8 text"
                except (OSError, FeatureExtractionError) as exc:
                    status, reason = "invalid", str(exc)
            digest = hashlib.sha256(content.encode("utf-8")).hexdigest() if content else ""
            if digest:
                digest_owners[digest].add(author)
            rows.append(
                {
                    "author_id": author,
                    "file": relative,
                    "sha256": digest,
                    "logical_lines": sum(1 for line in content.splitlines() if line.strip()),
                    "bytes": len(content.encode("utf-8")),
                    "status": status,
                    "reason": reason,
                    "cross_author_duplicate": False,
                }
            )

    cross_author = {digest for digest, owners in digest_owners.items() if len(owners) > 1}
    for row in rows:
        if row["sha256"] in cross_author:
            row["cross_author_duplicate"] = True
            if row["status"] == "eligible":
                row["status"] = "duplicate"
                row["reason"] = "identical content appears under multiple authors"

    status_counts = Counter(row["status"] for row in rows)
    eligible_by_author = Counter(row["author_id"] for row in rows if row["status"] == "eligible")
    summary = {
        "authors_found": len({row["author_id"] for row in rows}),
        "files_found": len(rows),
        "status_counts": dict(status_counts),
        "eligible_files_by_author": dict(sorted(eligible_by_author.items())),
        "cross_author_duplicate_hashes": len(cross_author),
        "authors_ready_for_training": sum(count >= 6 for count in eligible_by_author.values()),
        "training_ready": len(eligible_by_author) >= 4 and all(count >= 6 for count in eligible_by_author.values()),
        "required_external_metadata": ["source repository", "commit/snapshot", "license or contributor permission", "collection notes"],
    }
    return rows, summary


def write_audit(root: Path, output_dir: Path) -> dict:
    rows, summary = audit_dataset(root)
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / "file_audit.csv"
    with manifest_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]) if rows else ["author_id", "file", "status", "reason"])
        writer.writeheader()
        writer.writerows(rows)
    summary_path = output_dir / "audit_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return {**summary, "manifest": str(manifest_path), "summary": str(summary_path)}


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit CodeDNA training data for validity and leakage risks.")
    parser.add_argument("dataset", type=Path)
    parser.add_argument("--output", type=Path, default=Path("work/evaluation/audit"))
    args = parser.parse_args()
    print(json.dumps(write_audit(args.dataset, args.output), indent=2))


if __name__ == "__main__":
    main()
