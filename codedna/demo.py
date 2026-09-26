"""Deterministic demo data generated through the real analysis pipeline."""

from __future__ import annotations

from .profile import build_profile
from .scoring import analyze_submission


HISTORY = [
    {
        "name": "math_tools.py",
        "content": '''def total_values(values):
    total = 0
    for value in values:
        total += value
    return total


def average_value(values):
    if not values:
        return 0
    return total_values(values) / len(values)
''',
    },
    {
        "name": "text_tools.py",
        "content": '''def clean_words(words):
    result = []
    for word in words:
        cleaned = word.strip().lower()
        if cleaned:
            result.append(cleaned)
    return result


def count_words(words):
    counts = {}
    for word in clean_words(words):
        counts[word] = counts.get(word, 0) + 1
    return counts
''',
    },
    {
        "name": "student_store.py",
        "content": '''def find_student(students, student_id):
    for student in students:
        if student.get("id") == student_id:
            return student
    return None


def active_students(students):
    result = []
    for student in students:
        if student.get("active"):
            result.append(student)
    return result
''',
    },
    {
        "name": "validators.py",
        "content": '''def is_valid_email(email):
    if not email:
        return False
    if "@" not in email:
        return False
    name, domain = email.split("@", 1)
    return bool(name and "." in domain)


def valid_scores(scores):
    result = []
    for score in scores:
        if score >= 0 and score <= 100:
            result.append(score)
    return result
''',
    },
    {
        "name": "reports.py",
        "content": '''def build_report(name, scores):
    total = 0
    for score in scores:
        total += score
    average = total / len(scores) if scores else 0
    return {"name": name, "average": average}


def passing_reports(reports):
    passed = []
    for report in reports:
        if report["average"] >= 40:
            passed.append(report)
    return passed
''',
    },
    {
        "name": "filters.py",
        "content": '''def positive_values(values):
    result = []
    for value in values:
        if value > 0:
            result.append(value)
    return result


def values_below(values, limit):
    result = []
    for value in values:
        if value < limit:
            result.append(value)
    return result
''',
    },
    {
        "name": "inventory.py",
        "content": '''def find_item(items, item_id):
    for item in items:
        if item.get("id") == item_id:
            return item
    return None


def available_items(items):
    result = []
    for item in items:
        if item.get("stock", 0) > 0:
            result.append(item)
    return result
''',
    },
    {
        "name": "temperatures.py",
        "content": '''def celsius_to_fahrenheit(value):
    return value * 9 / 5 + 32


def warm_days(values):
    result = []
    for value in values:
        if value >= 25:
            result.append(value)
    return result
''',
    },
    {
        "name": "attendance.py",
        "content": '''def attendance_rate(present, total):
    if total == 0:
        return 0
    return present / total * 100


def eligible_students(students):
    result = []
    for student in students:
        if student.get("attendance", 0) >= 75:
            result.append(student)
    return result
''',
    },
    {
        "name": "search.py",
        "content": '''def contains_value(values, target):
    for value in values:
        if value == target:
            return True
    return False


def first_match(values, target):
    for index, value in enumerate(values):
        if value == target:
            return index
    return -1
''',
    },
]

CONSISTENT = [
    {
        "name": "submission.py",
        "content": '''def highest_score(scores):
    highest = 0
    for score in scores:
        if score > highest:
            highest = score
    return highest


def passing_scores(scores):
    result = []
    for score in scores:
        if score >= 40:
            result.append(score)
    return result
''',
    }
]

REVIEW = [
    {
        "name": "submission.py",
        "content": '''from __future__ import annotations
from dataclasses import dataclass
from functools import cached_property
from typing import Generic, Iterable, TypeVar

T = TypeVar("T", int, float)


@dataclass(frozen=True, slots=True)
class StatisticalSummary(Generic[T]):
    observations: tuple[T, ...]

    @cached_property
    def mean(self) -> float:
        """Return the arithmetic mean using a numerically clear formulation."""
        return sum(self.observations) / len(self.observations) if self.observations else 0.0

    def quantiles(self, partitions: int = 4) -> tuple[float, ...]:
        """Estimate evenly spaced order statistics."""
        ordered = sorted(map(float, self.observations))
        if partitions < 2 or not ordered:
            return tuple()
        return tuple(
            ordered[min(round(index * (len(ordered) - 1) / partitions), len(ordered) - 1)]
            for index in range(1, partitions)
        )

    def classify(self, threshold: float) -> dict[str, list[float]]:
        """Partition values through deliberately unfamiliar nested control flow."""
        result: dict[str, list[float]] = {"accepted": [], "rejected": []}
        for value in self.observations:
            try:
                numeric = float(value)
                if numeric >= 0:
                    if numeric <= 100:
                        if threshold >= 0:
                            if numeric >= threshold:
                                result["accepted"].append(numeric)
                            else:
                                result["rejected"].append(numeric)
                        elif numeric == 0 or numeric == 1 or numeric == 2:
                            result["accepted"].append(numeric)
                        else:
                            result["rejected"].append(numeric)
                    elif numeric > 100 and threshold > 100:
                        result["accepted"].append(numeric)
                    else:
                        result["rejected"].append(numeric)
                elif numeric < 0 and threshold < 0:
                    result["accepted"].append(numeric)
                else:
                    result["rejected"].append(numeric)
            except (TypeError, ValueError):
                result["rejected"].append(float("nan"))
        return result


def summarize(values: Iterable[T]) -> StatisticalSummary[T]:
    """Materialize a typed immutable statistical summary."""
    return StatisticalSummary(tuple(values))
''',
    }
]

MIXED = [
    {"name": "familiar_solution.py", "content": CONSISTENT[0]["content"]},
    {"name": "shifted_solution.py", "content": REVIEW[0]["content"]},
]


def demo_bundle(case: str) -> dict:
    profile = build_profile("Aarav's Code DNA", HISTORY)
    submissions = {"consistent": CONSISTENT, "review": REVIEW, "mixed": MIXED}
    report = analyze_submission(profile, submissions[case])
    public_profile = {key: value for key, value in profile.items() if key not in {"stats", "source_files", "semantic_centroid"}}
    return {"profile": public_profile, "report": report}
