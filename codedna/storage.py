"""Small atomic JSON profile store for the hackathon prototype."""

from __future__ import annotations

import json
import os
import tempfile
import threading
from pathlib import Path

STORE_DIR = (
    Path(tempfile.gettempdir()) / "codedna" / "profiles"
    if os.environ.get("VERCEL")
    else Path(__file__).resolve().parent.parent / "work" / "runtime" / "profiles"
)
LOCK = threading.Lock()


def save_profile(profile: dict) -> None:
    STORE_DIR.mkdir(parents=True, exist_ok=True)
    target = STORE_DIR / f"{profile['id']}.json"
    with LOCK:
        handle, temporary = tempfile.mkstemp(prefix="profile-", suffix=".json", dir=STORE_DIR)
        try:
            with os.fdopen(handle, "w", encoding="utf-8") as stream:
                json.dump(profile, stream, separators=(",", ":"))
            os.replace(temporary, target)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)


def load_profile(profile_id: str) -> dict | None:
    if not profile_id.isalnum() or len(profile_id) > 32:
        return None
    target = STORE_DIR / f"{profile_id}.json"
    if not target.is_file():
        return None
    try:
        return json.loads(target.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None

