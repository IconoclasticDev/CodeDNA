"""Lightweight structural-token representation for offline semantic comparison.

This is an honest local fallback, not CodeBERT. It hashes AST token n-grams into
a fixed vector so the pipeline can exercise a fourth independent representation
without downloading or executing a neural model.
"""

from __future__ import annotations

import ast
import hashlib
import math

VECTOR_SIZE = 128


def ast_token_vector(source: str) -> list[float]:
    tree = ast.parse(source)
    tokens: list[str] = []
    edges: list[str] = []

    def visit(node: ast.AST, parent: str = "ROOT", depth: int = 0) -> None:
        token = type(node).__name__
        if isinstance(node, ast.BinOp):
            token += f":{type(node.op).__name__}"
        elif isinstance(node, ast.BoolOp):
            token += f":{type(node.op).__name__}"
        elif isinstance(node, ast.Compare):
            token += ":" + ",".join(type(op).__name__ for op in node.ops)
        elif isinstance(node, ast.Call):
            token += f":argc{len(node.args)}"
        tokens.append(f"d{min(depth, 8)}:{token}")
        edges.append(f"{parent}>{token}")
        for child in ast.iter_child_nodes(node):
            visit(child, token, depth + 1)

    visit(tree)

    vector = [0.0] * VECTOR_SIZE
    grams = tokens + edges + [f"seq:{a}>{b}" for a, b in zip(tokens, tokens[1:])]
    for gram in grams:
        digest = hashlib.blake2b(gram.encode("utf-8"), digest_size=8).digest()
        bucket = int.from_bytes(digest, "big") % VECTOR_SIZE
        sign = 1.0 if digest[0] & 1 else -1.0
        vector[bucket] += sign
    norm = math.sqrt(sum(value * value for value in vector))
    return [value / norm for value in vector] if norm else vector


def mean_vector(vectors: list[list[float]]) -> list[float]:
    if not vectors:
        return [0.0] * VECTOR_SIZE
    vector = [sum(values) / len(vectors) for values in zip(*vectors)]
    norm = math.sqrt(sum(value * value for value in vector))
    return [value / norm for value in vector] if norm else vector


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right:
        return 0.0
    dot = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if not left_norm or not right_norm:
        return 0.0
    return max(-1.0, min(1.0, dot / (left_norm * right_norm)))
