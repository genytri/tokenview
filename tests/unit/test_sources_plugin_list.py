"""Tests for tokenview.sources.plugin_list."""

from __future__ import annotations

from pathlib import Path

from tokenview.sources.plugin_list import parse_list_output


def test_parse_list_only_enabled(fixtures_dir: Path) -> None:
    text = (fixtures_dir / "plugin_list.txt").read_text()
    ids = parse_list_output(text)
    assert ids == [
        "truth-serum@truth-serum-marketplace",
        "context7@claude-plugins-official",
    ]
