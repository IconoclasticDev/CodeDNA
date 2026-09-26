"""Build and checksum the complete evaluation evidence pack in one command."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from .audit import write_audit
from .fusion import MODEL_PATH
from .representation import configured_provider
from .train import run as run_training


class EvidenceBuildError(ValueError):
    """Raised when the dataset cannot support the declared evaluation."""


def _file_record(path: Path) -> dict:
    content = path.read_bytes()
    return {
        "path": str(path.resolve()),
        "bytes": len(content),
        "sha256": hashlib.sha256(content).hexdigest(),
    }


def build_evidence_pack(dataset: Path, output_dir: Path, model_path: Path = MODEL_PATH) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    audit = write_audit(dataset, output_dir / "audit")
    if not audit["training_ready"]:
        counts = audit.get("eligible_files_by_author", {})
        raise EvidenceBuildError(
            "Dataset audit failed the training gate: at least four authors need six eligible, "
            f"non-duplicate Python files each. Eligible counts: {counts}."
        )

    results_path = output_dir / "results.json"
    result = run_training(dataset, results_path, model_path)
    artifact_paths = {
        "results": results_path,
        "model": model_path,
        "audit_csv": Path(audit["manifest"]),
        "audit_summary": Path(audit["summary"]),
        **{name: Path(path) for name, path in result["artifacts"].items()},
    }
    missing = [name for name, path in artifact_paths.items() if not path.is_file()]
    if missing:
        raise EvidenceBuildError(f"Evidence build did not create required artifacts: {', '.join(missing)}.")

    manifest = {
        "schema_version": 1,
        "status": "complete",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "dataset": str(dataset.resolve()),
        "representation": configured_provider(),
        "audit": {
            "authors_found": audit["authors_found"],
            "files_found": audit["files_found"],
            "eligible_files_by_author": audit["eligible_files_by_author"],
            "cross_author_duplicate_hashes": audit["cross_author_duplicate_hashes"],
        },
        "evaluation": {
            "protocol": result["evaluation"]["protocol"],
            "selected_fusion": result["evaluation"]["selected_fusion"],
            "summary": result["evaluation"]["summary"],
            "calibrated_operating_point": result["evaluation"]["calibrated_operating_point"],
            "calibrated_thresholds": result["evaluation"]["calibrated_thresholds"],
        },
        "artifacts": {name: _file_record(path) for name, path in artifact_paths.items()},
    }
    manifest_path = output_dir / "evidence_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return {**manifest, "manifest_path": str(manifest_path.resolve())}


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit, train and package CodeDNA evaluation evidence.")
    parser.add_argument("dataset", type=Path, help="Directory containing one subdirectory per author.")
    parser.add_argument("--output", type=Path, default=Path("work/evaluation"))
    parser.add_argument("--model", type=Path, default=MODEL_PATH)
    args = parser.parse_args()
    try:
        print(json.dumps(build_evidence_pack(args.dataset, args.output, args.model), indent=2))
    except EvidenceBuildError as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
