"""Tests for tokenview.cache."""

from __future__ import annotations

import time
from pathlib import Path

from tokenview.cache import PluginCache
from tokenview.models import Plugin, PluginComponent


def _make_plugin(name: str) -> Plugin:
    return Plugin(
        name=name,
        marketplace="m",
        version="1",
        always_on_tokens=100,
        components=[
            PluginComponent(
                name="c",
                type="skill",
                always_on_tokens=100,
                on_invoke_tokens=500,
            )
        ],
    )


def test_cache_round_trip(tmp_path: Path) -> None:
    cache = PluginCache(path=tmp_path / "plugins.json", ttl_seconds=60)
    p = _make_plugin("x")
    cache.set("x@m", p)
    assert cache.get("x@m") == p


def test_cache_expires_after_ttl(tmp_path: Path) -> None:
    cache = PluginCache(path=tmp_path / "plugins.json", ttl_seconds=0.05)
    cache.set("x@m", _make_plugin("x"))
    time.sleep(0.1)
    assert cache.get("x@m") is None


def test_cache_persists_across_instances(tmp_path: Path) -> None:
    cache_path = tmp_path / "plugins.json"
    cache_a = PluginCache(path=cache_path, ttl_seconds=60)
    cache_a.set("y@m", _make_plugin("y"))
    cache_b = PluginCache(path=cache_path, ttl_seconds=60)
    assert cache_b.get("y@m") is not None
