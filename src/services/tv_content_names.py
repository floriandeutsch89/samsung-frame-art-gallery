"""Persistent mapping of TV content_id → {title, created_at} stored in /app/data/content_names.json."""
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

_LOGGER = logging.getLogger(__name__)

_DATA_DIR = Path(
    os.environ.get("THUMBNAILS_DIR", "/app/data/thumbnails" if Path("/.dockerenv").exists() else "data/thumbnails")
).parent
_NAMES_FILE = _DATA_DIR / "content_names.json"


def _load() -> dict:
    try:
        if _NAMES_FILE.exists():
            return json.loads(_NAMES_FILE.read_text())
    except Exception as e:
        _LOGGER.warning(f"Failed to load content names: {e}")
    return {}


def _save(names: dict) -> None:
    try:
        _NAMES_FILE.parent.mkdir(parents=True, exist_ok=True)
        _NAMES_FILE.write_text(json.dumps(names, indent=2))
    except Exception as e:
        _LOGGER.warning(f"Failed to save content names: {e}")


def _coerce(entry) -> dict:
    """Normalise legacy string entries to the current dict format."""
    if isinstance(entry, str):
        return {"title": entry, "created_at": None}
    return entry or {}


def save_name(content_id: str, title: str) -> None:
    if not content_id or not title:
        return
    names = _load()
    existing = _coerce(names.get(content_id))
    names[content_id] = {
        "title": title,
        "created_at": existing.get("created_at") or datetime.now(timezone.utc).isoformat(),
    }
    _save(names)


def delete_name(content_id: str) -> None:
    names = _load()
    if content_id in names:
        del names[content_id]
        _save(names)


def get_all_names() -> dict:
    """Return {content_id: {title, created_at}} with legacy entries normalised."""
    return {cid: _coerce(entry) for cid, entry in _load().items()}
