"""Leakage-aware dataset pairing, grouped evaluation, and fusion training CLI."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
from pathlib import Path

import numpy as np

from .fusion import MODEL_PATH, FusionModel, MLPFusionModel, train_logistic, train_mlp
from .profile import build_profile
from .reporting import write_benchmark_artifacts
from .representation import configured_provider
from .scoring import comparison_features


def load_dataset(root: Path) -> dict[str, list[dict]]:
    authors: dict[str, list[dict]] = {}
    hashes: set[str] = set()
    for author_dir in sorted(path for path in root.iterdir() if path.is_dir()):
        files = []
        for path in sorted(author_dir.rglob("*.py")):
            try:
                content = path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
            if digest in hashes:
                continue
            hashes.add(digest)
            files.append({"name": path.name, "content": content})
        if len(files) >= 6:
            authors[author_dir.name] = files
    if len(authors) < 4:
        raise ValueError("Evaluation requires at least four author directories with six valid Python files each.")
    return authors


def build_pairs(authors: dict[str, list[dict]], seed: int = 42) -> list[dict]:
    rng = random.Random(seed)
    names = sorted(authors)
    profiles = {}
    queries = {}
    for name in names:
        shuffled = list(authors[name])
        rng.shuffle(shuffled)
        split = max(3, int(len(shuffled) * 0.7))
        # Evaluation fixtures may be smaller than the product's ten-file
        # enrollment gate. Three enrollment files remain the statistical floor.
        profiles[name] = build_profile(name, shuffled[:split], minimum_files=3)
        queries[name] = shuffled[split:]

    pairs = []
    for name in names:
        for query in queries[name]:
            features, _ = comparison_features(profiles[name], [query])
            pairs.append({"claimed_author": name, "query_author": name, "label": 1, "features": features})
        other_queries = [(other, query) for other in names if other != name for query in queries[other]]
        rng.shuffle(other_queries)
        for query_author, query in other_queries[: len(queries[name])]:
            features, _ = comparison_features(profiles[name], [query])
            pairs.append({"claimed_author": name, "query_author": query_author, "label": 0, "features": features})
    return pairs


def _auc(labels: np.ndarray, scores: np.ndarray) -> float:
    positives = scores[labels == 1]
    negatives = scores[labels == 0]
    if not len(positives) or not len(negatives):
        return 0.0
    wins = sum(float(pos > neg) + 0.5 * float(pos == neg) for pos in positives for neg in negatives)
    return wins / (len(positives) * len(negatives))


def metrics(labels: np.ndarray, scores: np.ndarray, threshold: float = 0.5) -> dict[str, float]:
    predicted = scores >= threshold
    positive = labels == 1
    tp = int(np.sum(predicted & positive))
    fp = int(np.sum(predicted & ~positive))
    fn = int(np.sum(~predicted & positive))
    tn = int(np.sum(~predicted & ~positive))
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "roc_auc": round(_auc(labels, scores), 4),
        "f1": round(f1, 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "false_positive_rate": round(fp / (fp + tn), 4) if fp + tn else 0.0,
        "tp": tp, "fp": fp, "fn": fn, "tn": tn,
        "brier_score": round(float(np.mean((scores - labels) ** 2)), 4),
    }


def calibrate_verdict_thresholds(labels: np.ndarray, scores: np.ndarray, target_error: float = 0.10) -> dict:
    """Create an uncertainty band from out-of-fold genuine and impostor scores."""
    genuine = np.sort(scores[labels == 1])
    impostor = np.sort(scores[labels == 0])
    if not len(genuine) or not len(impostor):
        raise ValueError("Threshold calibration requires both genuine and impostor predictions.")
    # Bound the two harmful outcomes independently. A review threshold at the
    # lower genuine tail limits genuine code sent directly to review. A
    # consistency threshold at the upper impostor tail limits impostor code
    # called consistent. Overlap becomes uncertainty instead of a forced call.
    review_candidate = float(np.quantile(genuine, target_error, method="lower"))
    consistent_candidate = float(np.quantile(impostor, 1.0 - target_error, method="higher"))
    if review_candidate < consistent_candidate:
        review, consistent = review_candidate, consistent_candidate
    else:
        midpoint = (review_candidate + consistent_candidate) / 2.0
        review = midpoint - 0.025
        consistent = midpoint + 0.025
    review = max(0.05, min(review, 0.90))
    consistent = max(review + 0.05, min(consistent, 0.95))
    return {
        "review": round(review, 4),
        "consistent": round(consistent, 4),
        "target_error": target_error,
        "observed_false_review_rate": round(float(np.mean(genuine < review)), 4),
        "observed_impostor_consistent_rate": round(float(np.mean(impostor >= consistent)), 4),
        "uncertain_band_width": round(consistent - review, 4),
    }


def grouped_evaluation(pairs: list[dict], folds: int = 4) -> dict:
    authors = sorted({pair["claimed_author"] for pair in pairs})
    fold_count = min(folds, len(authors))
    fold_authors = [authors[index::fold_count] for index in range(fold_count)]
    systems = {"semantic_only": [], "engineered_only": [], "full_fusion_logistic": [], "full_fusion_mlp": []}
    fold_details = []
    out_of_fold_labels: list[int] = []
    out_of_fold_scores: dict[str, list[float]] = {"full_fusion_logistic": [], "full_fusion_mlp": []}
    for held_out in fold_authors:
        train_pairs = [
            pair for pair in pairs
            if pair["claimed_author"] not in held_out and pair["query_author"] not in held_out
        ]
        test_pairs = [pair for pair in pairs if pair["claimed_author"] in held_out]
        x_train = np.asarray([pair["features"] for pair in train_pairs], dtype=float)
        y_train = np.asarray([pair["label"] for pair in train_pairs], dtype=int)
        x_test = np.asarray([pair["features"] for pair in test_pairs], dtype=float)
        y_test = np.asarray([pair["label"] for pair in test_pairs], dtype=int)
        logistic = train_logistic(x_train, y_train)
        mlp = train_mlp(x_train, y_train)
        logistic_scores = np.asarray([logistic.predict_probability(row.tolist()) for row in x_test])
        mlp_scores = np.asarray([mlp.predict_probability(row.tolist()) for row in x_test])
        out_of_fold_labels.extend(y_test.tolist())
        out_of_fold_scores["full_fusion_logistic"].extend(logistic_scores.tolist())
        out_of_fold_scores["full_fusion_mlp"].extend(mlp_scores.tolist())
        semantic_scores = x_test[:, 3]
        engineered_scores = np.average(x_test[:, :3], axis=1, weights=[0.28, 0.40, 0.32])
        detail = {
            "held_out_authors": held_out,
            "train_pairs": len(train_pairs),
            "test_pairs": len(test_pairs),
            "leakage_check": "held-out authors absent from claimed_author and query_author in training pairs",
        }
        for name, scores in (
            ("semantic_only", semantic_scores),
            ("engineered_only", engineered_scores),
            ("full_fusion_logistic", logistic_scores),
            ("full_fusion_mlp", mlp_scores),
        ):
            result = metrics(y_test, scores)
            systems[name].append(result)
            detail[name] = result
        fold_details.append(detail)
    summary = {}
    for name, results in systems.items():
        summary[name] = {
            metric: round(float(np.mean([result[metric] for result in results])), 4)
            for metric in ("roc_auc", "f1", "precision", "recall", "false_positive_rate", "brier_score")
        }
        summary[name]["f1_std"] = round(float(np.std([result["f1"] for result in results])), 4)
        summary[name]["roc_auc_std"] = round(float(np.std([result["roc_auc"] for result in results])), 4)
    challenger_names = ("full_fusion_logistic", "full_fusion_mlp")
    selected = max(challenger_names, key=lambda name: (summary[name]["f1"], -summary[name]["brier_score"]))
    summary["full_fusion"] = dict(summary[selected])
    oof_labels = np.asarray(out_of_fold_labels, dtype=int)
    selected_oof_scores = np.asarray(out_of_fold_scores[selected], dtype=float)
    calibrated = calibrate_verdict_thresholds(oof_labels, selected_oof_scores)
    operating = metrics(oof_labels, selected_oof_scores, threshold=calibrated["consistent"])
    operating["threshold"] = calibrated["consistent"]
    operating["uncertain_rate"] = round(
        float(np.mean((selected_oof_scores >= calibrated["review"]) & (selected_oof_scores < calibrated["consistent"]))), 4
    )
    return {
        "protocol": "grouped by claimed author",
        "folds": fold_details,
        "summary": summary,
        "selected_fusion": selected,
        "selection_rule": "highest mean held-out F1; lower Brier score breaks ties",
        "full_fusion_out_of_fold": metrics(oof_labels, selected_oof_scores),
        "calibrated_operating_point": operating,
        "calibrated_thresholds": calibrated,
    }


def run(dataset: Path, output: Path, model_path: Path = MODEL_PATH) -> dict:
    authors = load_dataset(dataset)
    pairs = build_pairs(authors)
    evaluation = grouped_evaluation(pairs)
    features = np.asarray([pair["features"] for pair in pairs], dtype=float)
    labels = np.asarray([pair["label"] for pair in pairs], dtype=int)
    model = train_mlp(features, labels) if evaluation["selected_fusion"] == "full_fusion_mlp" else train_logistic(features, labels)
    model.representation = configured_provider()
    model.thresholds = {
        "consistent": evaluation["calibrated_thresholds"]["consistent"],
        "review": evaluation["calibrated_thresholds"]["review"],
    }
    model.save(model_path)
    result = {
        "dataset": {"authors": len(authors), "files": sum(map(len, authors.values())), "pairs": len(pairs)},
        "feature_order": ["lexical", "structural", "complexity", "ast_token_representation", "surface_structure_gap"],
        "evaluation": evaluation,
        "model_path": str(model_path),
        "limitation": "Prototype-scale evaluation; broader longitudinal validation is required before institutional use.",
    }
    result["artifacts"] = write_benchmark_artifacts(result, output.parent)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Train and evaluate the CodeDNA fusion model.")
    parser.add_argument("dataset", type=Path, help="Directory containing one subdirectory per author.")
    parser.add_argument("--output", type=Path, default=Path("work/evaluation/results.json"))
    args = parser.parse_args()
    print(json.dumps(run(args.dataset, args.output), indent=2))


if __name__ == "__main__":
    main()

