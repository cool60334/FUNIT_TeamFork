from __future__ import annotations

from pathlib import Path
from typing import Any, Dict
import json


def _get_base_dir() -> Path:
    return Path(__file__).resolve().parent.parent


def load_system_config() -> Dict[str, Any]:
    base_dir = _get_base_dir()
    path = base_dir / "config" / "system.json"
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def get_max_retries(default: int = 2) -> int:
    config = load_system_config()
    return int(config.get("api_defaults", {}).get("max_retries", default))
