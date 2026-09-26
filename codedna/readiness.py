"""Release and judging readiness checks for the CodeDNA prototype."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from .demo import demo_bundle
from .fusion import MODEL_PATH, load_default_model
from .representation import configured_provider, provider_status

ROOT = Path(__file__).resolve().parent.parent
RESULTS_PATH = ROOT / "work" / "evaluation" / "results.json"
DATASET_PATH = ROOT / "work" / "dataset"
SOURCE_MANIFEST_PATH = ROOT / "work" / "evaluation" / "resolved_sources.csv"
REQUIRED_DOCS = ("README.md", "ARCHITECTURE.md", "MODEL_CARD.md", "EVALUATION.md", "DEMO.md")


def readiness_report() -> dict:
    representation = provider_status()
    model = load_default_model()
    model_compatible = bool(model and model.representation == configured_provider())
    evaluation = None
    if RESULTS_PATH.is_file():
        try:
            evaluation = json.loads(RESULTS_PATH.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            evaluation = None
    dataset_authors = len([path for path in DATASET_PATH.iterdir() if path.is_dir()]) if DATASET_PATH.is_dir() else 0
    permission_authors: set[str] = set()
    if SOURCE_MANIFEST_PATH.is_file():
        try:
            with SOURCE_MANIFEST_PATH.open(newline="", encoding="utf-8-sig") as stream:
                for row in csv.DictReader(stream):
                    if (row.get("license_or_permission") or "").strip() and (row.get("commit_sha") or "").strip():
                        permission_authors.add((row.get("author_id") or "").strip())
        except (OSError, csv.Error):
            permission_authors = set()
    try:
        consistent = demo_bundle("consistent")["report"]
        review = demo_bundle("review")["report"]
        separation = consistent["score"] - review["score"]
        demo_ready = separation >= 15.0 and review["verdict"] == "Review Recommended"
        demo_detail = {
            "familiar_score": consistent["score"],
            "familiar_verdict": consistent["verdict"],
            "anomaly_score": review["score"],
            "anomaly_verdict": review["verdict"],
            "separation": round(separation, 1),
            "minimum_separation": 15.0,
        }
    except Exception as exc:
        demo_ready = False
        demo_detail = {"error": str(exc)}
    missing_docs = [name for name in REQUIRED_DOCS if not (ROOT / name).is_file()]
    gates = {
        "core_analysis": {"passed": representation["available"], "detail": representation},
        "deterministic_demo": {"passed": demo_ready, "detail": demo_detail},
        "documentation": {"passed": not missing_docs, "detail": {"missing": missing_docs}},
        "real_dataset": {
            "passed": dataset_authors >= 4 and len(permission_authors) >= 4,
            "detail": {
                "authors_found": dataset_authors,
                "permission_backed_authors": len(permission_authors),
                "minimum": 4,
                "source_manifest": str(SOURCE_MANIFEST_PATH),
            },
        },
        "held_out_evaluation": {"passed": evaluation is not None, "detail": {"results_path": str(RESULTS_PATH)}},
        "trained_fusion": {
            "passed": model_compatible,
            "detail": {
                "artifact_present": MODEL_PATH.is_file(),
                "compatible": model_compatible,
                "active_representation": configured_provider(),
                "model_representation": model.representation if model else None,
            },
        },
    }
    demo_complete = all(gates[name]["passed"] for name in ("core_analysis", "deterministic_demo", "documentation"))
    evidence_complete = all(gates[name]["passed"] for name in ("real_dataset", "held_out_evaluation", "trained_fusion"))
    if demo_complete and evidence_complete:
        status = "competition_ready"
    elif demo_complete:
        status = "demo_ready_awaiting_real_evaluation"
    else:
        status = "not_demo_ready"
    return {
        "status": status,
        "demo_ready": demo_complete,
        "excellent_tier_evidence_ready": evidence_complete,
        "gates": gates,
        "evaluation_summary": (
            {
                "dataset": evaluation.get("dataset", {}),
                "selected_fusion": evaluation.get("evaluation", {}).get("selected_fusion"),
                "metrics": {
                    **evaluation.get("evaluation", {}).get("summary", {}).get("full_fusion", {}),
                    "calibrated_false_positive_rate": evaluation.get("evaluation", {}).get("calibrated_operating_point", {}).get("false_positive_rate"),
                    "calibrated_recall": evaluation.get("evaluation", {}).get("calibrated_operating_point", {}).get("recall"),
                    "uncertain_rate": evaluation.get("evaluation", {}).get("calibrated_operating_point", {}).get("uncertain_rate"),
                },
                "limitation": evaluation.get("limitation"),
            }
            if evaluation
            else None
        ),
        "next_action": (
            "Run collection, audit and training with the completed real-data manifest."
            if demo_complete and not evidence_complete
            else "Resolve failed readiness gates."
            if not demo_complete
            else "Rehearse the five-minute demo and freeze the release."
        ),
    }


def main() -> None:
    print(json.dumps(readiness_report(), indent=2))


if __name__ == "__main__":
    main()




