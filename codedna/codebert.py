"""Optional frozen CodeBERT representation with local caching.

The module imports heavy dependencies lazily. CodeDNA remains runnable without
them, and never downloads model weights unless explicitly enabled.
"""

from __future__ import annotations

import ast
import hashlib
import json
import os
import tempfile
from pathlib import Path

MODEL_ID = os.environ.get("CODEDNA_CODEBERT_MODEL", "microsoft/codebert-base")
CACHE_DIR = Path(__file__).resolve().parent.parent / "work" / "cache" / "codebert"
MAX_CHUNKS = 64


class CodeBERTUnavailable(RuntimeError):
    pass


_RUNTIME = None


def dependency_status() -> dict:
    try:
        import torch  # noqa: F401
        import transformers  # noqa: F401
    except ImportError as exc:
        return {"available": False, "reason": f"missing optional dependency: {exc.name}", "model": MODEL_ID}
    return {"available": True, "reason": None, "model": MODEL_ID}


def _chunks(source: str) -> list[str]:
    """Split primarily at top-level function/class boundaries."""
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        raise CodeBERTUnavailable(f"Source could not be parsed for chunking: {exc.msg}") from exc
    lines = source.splitlines()
    chunks: list[str] = []
    covered: set[int] = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            start = max(1, node.lineno)
            end = min(len(lines), getattr(node, "end_lineno", node.lineno))
            chunks.append("\n".join(lines[start - 1 : end]))
            covered.update(range(start, end + 1))
    module_lines = [line for number, line in enumerate(lines, start=1) if number not in covered]
    module_source = "\n".join(module_lines).strip()
    if module_source:
        chunks.insert(0, module_source)
    return [chunk for chunk in chunks if chunk.strip()][:MAX_CHUNKS] or [source]


def _runtime():
    global _RUNTIME
    if _RUNTIME is not None:
        return _RUNTIME
    try:
        import torch
        from transformers import AutoModel, AutoTokenizer
    except ImportError as exc:
        raise CodeBERTUnavailable(
            "CodeBERT requires the optional torch and transformers packages. "
            "Install requirements-codebert.txt or use the ast-token-hash provider."
        ) from exc
    allow_download = os.environ.get("CODEDNA_ALLOW_MODEL_DOWNLOAD") == "1"
    try:
        tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, local_files_only=not allow_download)
        model = AutoModel.from_pretrained(MODEL_ID, local_files_only=not allow_download)
    except Exception as exc:
        mode = "download enabled" if allow_download else "local files only"
        raise CodeBERTUnavailable(f"CodeBERT model '{MODEL_ID}' is unavailable ({mode}).") from exc
    model.eval()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
    _RUNTIME = (torch, tokenizer, model, device)
    return _RUNTIME


def _cache_path(source: str) -> Path:
    key = hashlib.sha256(f"{MODEL_ID}\0{source}".encode("utf-8")).hexdigest()
    return CACHE_DIR / f"{key}.json"


def codebert_vector(source: str) -> list[float]:
    cache = _cache_path(source)
    if cache.is_file():
        try:
            payload = json.loads(cache.read_text(encoding="utf-8"))
            if payload.get("model") == MODEL_ID and isinstance(payload.get("vector"), list):
                return [float(value) for value in payload["vector"]]
        except (OSError, ValueError, json.JSONDecodeError):
            pass

    torch, tokenizer, model, device = _runtime()
    vectors = []
    with torch.no_grad():
        for chunk in _chunks(source):
            encoded = tokenizer(chunk, truncation=True, max_length=512, return_tensors="pt")
            encoded = {key: value.to(device) for key, value in encoded.items()}
            hidden = model(**encoded).last_hidden_state
            mask = encoded["attention_mask"].unsqueeze(-1)
            pooled = (hidden * mask).sum(dim=1) / mask.sum(dim=1).clamp(min=1)
            vectors.append(pooled.squeeze(0).cpu())
    vector = torch.stack(vectors).mean(dim=0)
    vector = vector / vector.norm(p=2).clamp(min=1e-12)
    values = vector.tolist()

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(prefix="codebert-", suffix=".json", dir=CACHE_DIR)
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            json.dump({"model": MODEL_ID, "vector": values}, stream, separators=(",", ":"))
        os.replace(temporary, cache)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return values

