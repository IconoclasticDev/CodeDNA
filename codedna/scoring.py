"""Profile comparison, consistency scoring, and explanations."""

from __future__ import annotations

import ast
import math
import statistics
import textwrap

from .features import FEATURE_GROUPS, FeatureExtractionError, extract_features
from .profile import extract_file_set
from .semantic import cosine_similarity, mean_vector

FEATURE_LABELS = {
    "snake_case_ratio": "Snake-case identifier use",
    "camel_case_ratio": "Camel-case identifier use",
    "identifier_length_mean": "Average identifier length",
    "identifier_diversity": "Identifier diversity",
    "comment_density": "Comment density",
    "docstring_density": "Docstring density",
    "type_hint_ratio": "Type annotation use",
    "blank_line_density": "Blank-line density",
    "parameters_per_function": "Parameters per function",
    "imports_per_100_loc": "Import density",
    "function_length_mean": "Average function length",
    "literal_density": "Literal density",
    "ast_depth_mean": "Average AST depth",
    "ast_depth_max": "Maximum AST depth",
    "nesting_depth_max": "Maximum nesting",
    "cyclomatic_mean": "Average cyclomatic complexity",
    "cyclomatic_max": "Maximum cyclomatic complexity",
    "logical_loc": "Logical lines of code",
    "function_complexity_mean": "Function complexity",
    "high_complexity_ratio": "High-complexity function rate",
}


def _submission_means(files) -> dict[str, float]:
    keys = files[0].features.keys()
    return {key: statistics.fmean(item.features[key] for item in files) for key in keys}


def _feature_distance(value: float, mean: float, std: float) -> float:
    scale = max(std, abs(mean) * 0.15, 0.10)
    return abs(value - mean) / scale


def _group_similarity(profile: dict, values: dict[str, float], group: str) -> float:
    distances = [
        min(_feature_distance(values[name], profile["stats"][name]["mean"], profile["stats"][name]["std"]), 6.0)
        for name in FEATURE_GROUPS[group]
    ]
    robust_distance = statistics.median(distances) if distances else 6.0
    return max(0.0, min(1.0, math.exp(-0.48 * robust_distance)))


def _comparison_from_features(profile: dict, files) -> tuple[list[float], dict[str, float]]:
    values = _submission_means(files)
    lexical = _group_similarity(profile, values, "lexical")
    structural = _group_similarity(profile, values, "structural")
    complexity = _group_similarity(profile, values, "complexity")
    semantic_raw = cosine_similarity(profile.get("semantic_centroid", []), mean_vector([item.semantic_vector for item in files]))
    semantic = (semantic_raw + 1.0) / 2.0
    gap = lexical - statistics.fmean([structural, complexity, semantic])
    return [lexical, structural, complexity, semantic, gap], values


def _function_review_map(profile: dict, raw_files: list[dict], *, limit: int = 12) -> tuple[list[dict], int]:
    """Rank functions by engineered deviation without changing the trained score."""
    candidates: list[dict] = []
    seen: set[tuple[str, int]] = set()
    for raw in raw_files[:100]:
        name = str(raw.get("name", "unnamed.py"))
        source = raw.get("content", "")
        if not name.lower().endswith(".py") or not isinstance(source, str) or not source.strip():
            continue
        try:
            tree = ast.parse(source, filename=name)
        except (SyntaxError, ValueError):
            continue
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            key = (name, node.lineno)
            if key in seen:
                continue
            seen.add(key)
            segment = ast.get_source_segment(source, node)
            if not segment:
                continue
            try:
                item = extract_features(
                    f"{name}::{node.name}", textwrap.dedent(segment), include_representation=False
                )
            except FeatureExtractionError:
                continue
            group_deviations: dict[str, float] = {}
            strongest_feature = None
            strongest_distance = -1.0
            for group in ("lexical", "structural", "complexity"):
                distances = []
                for feature in FEATURE_GROUPS[group]:
                    baseline = profile["stats"][feature]
                    distance = min(
                        _feature_distance(item.features[feature], baseline["mean"], baseline["std"]), 6.0
                    )
                    distances.append(distance)
                    if distance > strongest_distance:
                        strongest_distance = distance
                        strongest_feature = feature
                median_distance = statistics.median(distances) if distances else 0.0
                group_deviations[group] = round(
                    100.0 * (1.0 - math.exp(-0.48 * median_distance)), 1
                )
            deviation_index = statistics.fmean(group_deviations.values())
            candidates.append(
                {
                    "file": name,
                    "function": node.name,
                    "line_start": node.lineno,
                    "line_end": getattr(node, "end_lineno", node.lineno),
                    "lines": max(1, getattr(node, "end_lineno", node.lineno) - node.lineno + 1),
                    "deviation_index": round(deviation_index, 1),
                    "signals": group_deviations,
                    "strongest_feature": FEATURE_LABELS.get(
                        strongest_feature, str(strongest_feature).replace("_", " ").title()
                    ),
                }
            )
    candidates.sort(key=lambda item: (-item["deviation_index"], item["file"], item["line_start"]))
    return candidates[:limit], len(candidates)


def _score_inputs(inputs: list[float], model, representation_name: str) -> tuple[float, str, dict]:
    lexical, structural, complexity, semantic, _ = inputs
    if model and model.representation == representation_name:
        score = 100.0 * model.predict_probability(inputs)
        model_meta = {"name": model.name, "trained": True, "semantic_available": True}
        consistent_threshold = 100.0 * model.thresholds.get("consistent", 0.70)
        review_threshold = 100.0 * model.thresholds.get("review", 0.40)
    else:
        score = 100.0 * (0.25 * lexical + 0.30 * structural + 0.22 * complexity + 0.23 * semantic)
        model_meta = {
            "name": "deterministic-baseline-v2",
            "trained": False,
            "semantic_available": True,
            "trained_model_compatible": model is None or model.representation == representation_name,
        }
        consistent_threshold = 70.0
        review_threshold = 55.0
    if score >= consistent_threshold:
        verdict = "Consistent"
    elif score >= review_threshold:
        verdict = "Uncertain"
    else:
        verdict = "Review Recommended"
    return score, verdict, model_meta


def comparison_features(profile: dict, raw_files: list[dict]) -> tuple[list[float], dict]:
    files, skipped, duplicates = extract_file_set(raw_files)
    if not files:
        detail = f" First issue: {skipped[0]['reason']}" if skipped else ""
        raise ValueError(f"No valid, distinct Python files could be analyzed.{detail}")
    representation_names = {item.representation_name for item in files}
    expected_representation = profile.get("representation_name", profile.get("semantic_status"))
    if representation_names != {expected_representation}:
        actual = ", ".join(sorted(representation_names))
        raise ValueError(
            f"Profile representation '{expected_representation}' is incompatible with submission representation '{actual}'. "
            "Rebuild the profile with the active provider."
        )
    inputs, values = _comparison_from_features(profile, files)
    context = {"files": files, "skipped": skipped, "duplicates": duplicates, "values": values}
    return inputs, context


def analyze_submission(profile: dict, raw_files: list[dict]) -> dict:
    inputs, context = comparison_features(profile, raw_files)
    lexical, structural, complexity, semantic, gap = inputs
    files, skipped, duplicates, values = context["files"], context["skipped"], context["duplicates"], context["values"]
    try:
        from .fusion import load_default_model
        model = load_default_model()
    except (ImportError, OSError, ValueError):
        model = None
    representation_name = profile.get("representation_name", "unknown")
    score, verdict, model_meta = _score_inputs(inputs, model, representation_name)

    deviations = []
    for feature, value in values.items():
        baseline = profile["stats"][feature]
        raw_std = baseline["std"]
        stabilizer = max(abs(baseline["mean"]) * 0.10, 0.05)
        scale = max(raw_std, stabilizer)
        deviation = (value - baseline["mean"]) / scale
        display_deviation = max(-9.9, min(9.9, deviation))
        deviations.append(
            {
                "feature": feature,
                "label": FEATURE_LABELS.get(feature, feature.replace("_", " ").title()),
                "historical": round(baseline["mean"], 3),
                "submission": round(value, 3),
                "deviation_score": round(display_deviation, 2),
                "raw_deviation_score": round(deviation, 4),
                "deviation_capped": abs(deviation) > 9.9,
                "scale_method": "historical standard deviation" if raw_std >= stabilizer else "stabilized low-variance scale",
                "direction": "higher" if deviation > 0 else "lower",
            }
        )
    deviations.sort(key=lambda item: abs(item["raw_deviation_score"]), reverse=True)
    warnings = []
    if gap > 0.10:
        warnings.append(
            "Surface naming is more similar than deeper structural behaviour. Review the highlighted deviations."
        )
    warnings.extend(item["reason"] for item in skipped[:3])
    file_breakdown = []
    if len(files) > 1:
        for item in files:
            file_inputs, _ = _comparison_from_features(profile, [item])
            file_score, file_verdict, _ = _score_inputs(file_inputs, model, representation_name)
            file_breakdown.append(
                {
                    "name": item.name,
                    "score": round(file_score, 1),
                    "verdict": file_verdict,
                    "components": {
                        "lexical": round(100 * file_inputs[0], 1),
                        "structural": round(100 * file_inputs[1], 1),
                        "complexity": round(100 * file_inputs[2], 1),
                        "semantic": round(100 * file_inputs[3], 1),
                    },
                    "surface_structure_gap": round(100 * file_inputs[4], 1),
                }
            )
        file_breakdown.sort(key=lambda item: (item["score"], item["name"]))
    function_breakdown, function_breakdown_total = _function_review_map(profile, raw_files)
    return {
        "profile_id": profile["id"],
        "profile_name": profile["name"],
        "score": round(score, 1),
        "verdict": verdict,
        "components": {
            "lexical": round(100 * lexical, 1),
            "structural": round(100 * structural, 1),
            "complexity": round(100 * complexity, 1),
            "semantic": round(100 * semantic, 1),
        },
        "surface_structure_gap": round(100 * gap, 1),
        "top_deviations": deviations[:5],
        "file_breakdown": file_breakdown[:12],
        "file_breakdown_total": len(file_breakdown),
        "function_breakdown": function_breakdown,
        "function_breakdown_total": function_breakdown_total,
        "coverage": {
            "files_analyzed": len(files),
            "files_skipped": len(skipped),
            "duplicates_removed": duplicates,
        },
        "warnings": warnings,
        "model": model_meta,
        "representation": profile.get("representation_name", "unknown"),
        "notice": (
            "This score measures behavioural deviation from the supplied history. "
            "It does not establish AI use, plagiarism, or misconduct. Human review is required."
        ),
    }
