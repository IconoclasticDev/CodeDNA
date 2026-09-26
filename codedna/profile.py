"""Historical profile construction and input hygiene."""

from __future__ import annotations

import hashlib
import math
import statistics
import uuid
from dataclasses import asdict

from .features import ALL_FEATURES, FEATURE_GROUPS, FeatureExtractionError, FileFeatures, extract_features
from .semantic import mean_vector

MIN_PROFILE_FILES = 10
RECOMMENDED_PROFILE_FILES = 10
MAX_FILES = 100
MAX_SOURCE_BYTES = 1_000_000


def _validate_file(raw: dict) -> tuple[str, str]:
    name = str(raw.get("name", "unnamed.py"))
    content = raw.get("content", "")
    if not name.lower().endswith(".py"):
        raise FeatureExtractionError("Only Python (.py) files are supported.")
    if not isinstance(content, str):
        raise FeatureExtractionError("File content must be text.")
    if len(content.encode("utf-8", errors="ignore")) > MAX_SOURCE_BYTES:
        raise FeatureExtractionError("File exceeds the 1 MB analysis limit.")
    return name, content


def extract_file_set(raw_files: list[dict]) -> tuple[list[FileFeatures], list[dict], int]:
    accepted: list[FileFeatures] = []
    skipped: list[dict] = []
    hashes: set[str] = set()
    duplicate_count = 0
    for raw in raw_files[:MAX_FILES]:
        try:
            name, content = _validate_file(raw)
            digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
            if digest in hashes:
                duplicate_count += 1
                continue
            hashes.add(digest)
            accepted.append(extract_features(name, content))
        except FeatureExtractionError as exc:
            skipped.append({"name": str(raw.get("name", "unnamed")), "reason": str(exc)})
    if len(raw_files) > MAX_FILES:
        skipped.append({"name": "repository", "reason": f"Only the first {MAX_FILES} files were considered."})
    return accepted, skipped, duplicate_count


def _stats(files: list[FileFeatures]) -> dict[str, dict[str, float]]:
    result: dict[str, dict[str, float]] = {}
    for feature in ALL_FEATURES:
        values = [item.features[feature] for item in files]
        result[feature] = {
            "mean": statistics.fmean(values),
            "std": statistics.stdev(values) if len(values) > 1 else 0.0,
            "median": statistics.median(values),
            "min": min(values),
            "max": max(values),
        }
    return result


def _stability(stats: dict[str, dict[str, float]], group: str) -> float:
    scores = []
    for feature in FEATURE_GROUPS[group]:
        mean = abs(stats[feature]["mean"])
        std = stats[feature]["std"]
        scores.append(1.0 / (1.0 + std / max(mean, 0.25)))
    return 100.0 * statistics.fmean(scores)


def build_profile(name: str, raw_files: list[dict], *, minimum_files: int = MIN_PROFILE_FILES) -> dict:
    files, skipped, duplicates = extract_file_set(raw_files)
    if len(files) < minimum_files:
        detail = f" First issue: {skipped[0]['reason']}" if skipped else ""
        raise ValueError(
            f"At least {minimum_files} valid, distinct Python files are required; received {len(files)}.{detail}"
        )
    stats = _stats(files)
    representations = {item.representation_name for item in files}
    if len(representations) != 1:
        raise ValueError("All historical files must use the same representation provider.")
    representation_name = representations.pop()
    group_stability = {group: round(_stability(stats, group), 1) for group in FEATURE_GROUPS}
    warnings = []
    if len(files) < RECOMMENDED_PROFILE_FILES:
        warnings.append(
            f"This profile uses {len(files)} files. Use at least {RECOMMENDED_PROFILE_FILES} for stronger confidence."
        )
    stable = sorted(
        ALL_FEATURES,
        key=lambda feature: stats[feature]["std"] / max(abs(stats[feature]["mean"]), 0.25),
    )[:3]
    return {
        "id": uuid.uuid4().hex[:12],
        "name": name.strip() or "Developer",
        "status": "ready",
        "files_analyzed": len(files),
        "files_skipped": len(skipped),
        "duplicates_removed": duplicates,
        "functions_analyzed": sum(item.functions for item in files),
        "lines_analyzed": sum(item.lines for item in files),
        "confidence": "moderate" if len(files) < RECOMMENDED_PROFILE_FILES else "strong",
        "warnings": warnings,
        "skipped": skipped,
        "stats": stats,
        "semantic_centroid": mean_vector([item.semantic_vector for item in files]),
        "group_stability": group_stability,
        "stable_features": stable,
        "source_files": [asdict(item) for item in files],
        "semantic_status": representation_name,
        "representation_name": representation_name,
        "schema_version": "0.2.0",
    }
