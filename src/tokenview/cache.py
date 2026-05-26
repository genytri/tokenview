"""On-disk cache for parsed `claude plugin details` results."""

from __future__ import annotations

import json
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any

from tokenview.models import Plugin, PluginComponent


class PluginCache:
    """JSON-backed cache with per-entry TTL.

    File format:
        { "<plugin_id>": { "fetched_at": <unix_ts>, "plugin": <serialized Plugin> } }
    """

    def __init__(self, path: Path, ttl_seconds: float = 3600.0) -> None:
        self._path = path
        self._ttl = ttl_seconds
        self._data: dict[str, dict[str, Any]] = {}
        self._load()

    def _load(self) -> None:
        if not self._path.exists():
            return
        try:
            self._data = json.loads(self._path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            self._data = {}

    def _flush(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(self._data), encoding="utf-8")

    def get(self, plugin_id: str) -> Plugin | None:
        entry = self._data.get(plugin_id)
        if not entry:
            return None
        if time.time() - entry["fetched_at"] > self._ttl:
            return None
        raw = entry["plugin"]
        return Plugin(
            name=raw["name"],
            marketplace=raw["marketplace"],
            version=raw["version"],
            always_on_tokens=raw["always_on_tokens"],
            components=[PluginComponent(**c) for c in raw["components"]],
        )

    def set(self, plugin_id: str, plugin: Plugin) -> None:
        self._data[plugin_id] = {
            "fetched_at": time.time(),
            "plugin": asdict(plugin),
        }
        self._flush()
