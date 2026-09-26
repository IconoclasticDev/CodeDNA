"""Dependency-free Python source feature extraction."""

from __future__ import annotations

import ast
import io
import keyword
import math
import re
import tokenize
from collections import Counter
from dataclasses import dataclass
from typing import Iterable

from .representation import RepresentationUnavailable, representation_vector


FEATURE_GROUPS = {
    "lexical": (
        "snake_case_ratio",
        "camel_case_ratio",
        "identifier_length_mean",
        "identifier_diversity",
        "comment_density",
        "docstring_density",
        "type_hint_ratio",
        "blank_line_density",
        "parameters_per_function",
        "imports_per_100_loc",
        "function_length_mean",
        "literal_density",
    ),
    "structural": (
        "if_per_100_nodes",
        "for_per_100_nodes",
        "while_per_100_nodes",
        "try_per_100_nodes",
        "with_per_100_nodes",
        "function_per_100_nodes",
        "class_per_100_nodes",
        "lambda_per_100_nodes",
        "comprehension_per_100_nodes",
        "return_per_100_nodes",
        "call_per_100_nodes",
        "ast_depth_mean",
        "ast_depth_max",
        "nesting_depth_max",
    ),
    "complexity": (
        "cyclomatic_mean",
        "cyclomatic_max",
        "logical_loc",
        "function_complexity_mean",
        "high_complexity_ratio",
    ),
}

ALL_FEATURES = tuple(name for group in FEATURE_GROUPS.values() for name in group)


class FeatureExtractionError(ValueError):
    """Raised when a source file cannot be safely analysed."""


@dataclass(frozen=True)
class FileFeatures:
    name: str
    features: dict[str, float]
    lines: int
    functions: int
    semantic_vector: list[float]
    representation_name: str


def _safe_ratio(numerator: float, denominator: float) -> float:
    return float(numerator) / denominator if denominator else 0.0


def _mean(values: Iterable[float]) -> float:
    values = list(values)
    return sum(values) / len(values) if values else 0.0


def _node_depths(tree: ast.AST) -> list[int]:
    depths: list[int] = []
    stack = [(tree, 1)]
    while stack:
        node, depth = stack.pop()
        depths.append(depth)
        stack.extend((child, depth + 1) for child in ast.iter_child_nodes(node))
    return depths


def _max_nesting(tree: ast.AST) -> int:
    nesting_types = (ast.If, ast.For, ast.AsyncFor, ast.While, ast.Try, ast.With, ast.AsyncWith)

    def visit(node: ast.AST, depth: int) -> int:
        next_depth = depth + 1 if isinstance(node, nesting_types) else depth
        child_depths = [visit(child, next_depth) for child in ast.iter_child_nodes(node)]
        return max([next_depth, *child_depths])

    return visit(tree, 0)


def _complexity(node: ast.AST) -> int:
    decision_types = (ast.If, ast.For, ast.AsyncFor, ast.While, ast.ExceptHandler, ast.IfExp, ast.comprehension)
    score = 1
    for child in ast.walk(node):
        if isinstance(child, decision_types):
            score += 1
        elif isinstance(child, ast.BoolOp):
            score += max(1, len(child.values) - 1)
        elif isinstance(child, ast.Match):
            score += len(child.cases)
    return score


def extract_features(name: str, source: str, *, include_representation: bool = True) -> FileFeatures:
    """Extract normalized behavioural signals from one Python source file."""
    if not isinstance(source, str) or not source.strip():
        raise FeatureExtractionError("The file is empty.")
    if "\x00" in source:
        raise FeatureExtractionError("The file appears to be binary.")
    try:
        tree = ast.parse(source, filename=name)
    except (SyntaxError, ValueError) as exc:
        raise FeatureExtractionError(f"Python syntax could not be parsed: {exc.msg if isinstance(exc, SyntaxError) else exc}") from exc

    lines = source.splitlines()
    logical_loc = sum(1 for line in lines if line.strip() and not line.lstrip().startswith("#"))
    blank_lines = sum(1 for line in lines if not line.strip())
    comments = 0
    literal_count = 0
    identifiers: list[str] = []
    try:
        tokens = tokenize.generate_tokens(io.StringIO(source).readline)
        for token in tokens:
            if token.type == tokenize.COMMENT:
                comments += 1
            elif token.type == tokenize.NAME and not keyword.iskeyword(token.string):
                identifiers.append(token.string)
            elif token.type in (tokenize.STRING, tokenize.NUMBER):
                literal_count += 1
    except (tokenize.TokenError, IndentationError) as exc:
        raise FeatureExtractionError(f"Python tokens could not be parsed: {exc}") from exc

    functions = [node for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))]
    classes = [node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
    node_counts = Counter(type(node).__name__ for node in ast.walk(tree))
    node_total = sum(node_counts.values())
    docstrings = sum(
        1 for node in [tree, *functions, *classes] if ast.get_docstring(node, clean=False) is not None
    )
    annotations = sum(
        int(arg.annotation is not None)
        for fn in functions
        for arg in [*fn.args.posonlyargs, *fn.args.args, *fn.args.kwonlyargs]
    ) + sum(int(fn.returns is not None) for fn in functions)
    arg_count = sum(
        len(fn.args.posonlyargs) + len(fn.args.args) + len(fn.args.kwonlyargs)
        for fn in functions
    )
    possible_annotations = arg_count + len(functions)
    function_lengths = [
        max(1, getattr(fn, "end_lineno", fn.lineno) - fn.lineno + 1) for fn in functions
    ]
    snake = sum(bool(re.fullmatch(r"[a-z_][a-z0-9_]*", value)) and "_" in value for value in identifiers)
    camel = sum(bool(re.fullmatch(r"[a-z]+(?:[A-Z][a-zA-Z0-9]*)+", value)) for value in identifiers)
    import_count = node_counts["Import"] + node_counts["ImportFrom"]
    depths = _node_depths(tree)
    function_complexities = [_complexity(fn) for fn in functions]
    module_complexity = _complexity(tree)
    complexities = function_complexities or [module_complexity]

    def per_nodes(kind: str) -> float:
        return 100.0 * _safe_ratio(node_counts[kind], node_total)

    comprehension_count = sum(
        node_counts[kind] for kind in ("ListComp", "SetComp", "DictComp", "GeneratorExp")
    )
    feature_values = {
        "snake_case_ratio": _safe_ratio(snake, len(identifiers)),
        "camel_case_ratio": _safe_ratio(camel, len(identifiers)),
        "identifier_length_mean": _mean(map(len, identifiers)),
        "identifier_diversity": _safe_ratio(len(set(identifiers)), len(identifiers)),
        "comment_density": _safe_ratio(comments, max(logical_loc, 1)),
        "docstring_density": _safe_ratio(docstrings, max(len(functions) + len(classes) + 1, 1)),
        "type_hint_ratio": _safe_ratio(annotations, possible_annotations),
        "blank_line_density": _safe_ratio(blank_lines, max(len(lines), 1)),
        "parameters_per_function": _safe_ratio(arg_count, len(functions)),
        "imports_per_100_loc": 100.0 * _safe_ratio(import_count, max(logical_loc, 1)),
        "function_length_mean": _mean(function_lengths),
        "literal_density": _safe_ratio(literal_count, max(logical_loc, 1)),
        "if_per_100_nodes": per_nodes("If"),
        "for_per_100_nodes": per_nodes("For") + per_nodes("AsyncFor"),
        "while_per_100_nodes": per_nodes("While"),
        "try_per_100_nodes": per_nodes("Try"),
        "with_per_100_nodes": per_nodes("With") + per_nodes("AsyncWith"),
        "function_per_100_nodes": 100.0 * _safe_ratio(len(functions), node_total),
        "class_per_100_nodes": 100.0 * _safe_ratio(len(classes), node_total),
        "lambda_per_100_nodes": per_nodes("Lambda"),
        "comprehension_per_100_nodes": 100.0 * _safe_ratio(comprehension_count, node_total),
        "return_per_100_nodes": per_nodes("Return"),
        "call_per_100_nodes": per_nodes("Call"),
        "ast_depth_mean": _mean(depths),
        "ast_depth_max": float(max(depths, default=0)),
        "nesting_depth_max": float(_max_nesting(tree)),
        "cyclomatic_mean": _mean(complexities),
        "cyclomatic_max": float(max(complexities, default=1)),
        "logical_loc": float(logical_loc),
        "function_complexity_mean": _mean(function_complexities),
        "high_complexity_ratio": _safe_ratio(sum(value > 10 for value in function_complexities), len(function_complexities)),
    }
    if include_representation:
        try:
            representation, representation_name = representation_vector(source)
        except RepresentationUnavailable as exc:
            raise FeatureExtractionError(str(exc)) from exc
    else:
        representation, representation_name = [], "engineered-explainability-v1"
    return FileFeatures(
        name=name,
        features=feature_values,
        lines=len(lines),
        functions=len(functions),
        semantic_vector=representation,
        representation_name=representation_name,
    )
