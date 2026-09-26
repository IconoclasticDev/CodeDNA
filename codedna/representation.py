"""Representation-provider selection and compatibility metadata."""

from __future__ import annotations

import os

from .codebert import CodeBERTUnavailable, dependency_status, codebert_vector
from .semantic import ast_token_vector

AST_PROVIDER = "ast-token-hash-v1"
CODEBERT_PROVIDER = "codebert-frozen-v1"


class RepresentationUnavailable(RuntimeError):
    pass


def configured_provider() -> str:
    value = os.environ.get("CODEDNA_REPRESENTATION", "ast-token-hash").strip().lower()
    return CODEBERT_PROVIDER if value == "codebert" else AST_PROVIDER


def provider_status() -> dict:
    configured = configured_provider()
    if configured == CODEBERT_PROVIDER:
        status = dependency_status()
        return {"configured": configured, **status}
    return {"configured": configured, "available": True, "reason": None, "model": None}


def representation_vector(source: str) -> tuple[list[float], str]:
    provider = configured_provider()
    if provider == CODEBERT_PROVIDER:
        try:
            return codebert_vector(source), provider
        except CodeBERTUnavailable as exc:
            raise RepresentationUnavailable(str(exc)) from exc
    return ast_token_vector(source), provider
