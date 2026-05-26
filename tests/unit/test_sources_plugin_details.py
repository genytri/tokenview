"""Tests for tokenview.sources.plugin_details."""

from __future__ import annotations

from pathlib import Path

from tokenview.sources.plugin_details import parse_details_output


def test_parse_truth_serum_details(fixtures_dir: Path) -> None:
    text = (fixtures_dir / "plugin_details_truth_serum.txt").read_text()
    plugin = parse_details_output(text, marketplace="truth-serum-marketplace")

    assert plugin.name == "truth-serum"
    assert plugin.version == "0.6.1"
    assert plugin.marketplace == "truth-serum-marketplace"
    assert plugin.always_on_tokens == 243

    by_name = {c.name: c for c in plugin.components}
    assert by_name["lie-detector"].always_on_tokens == 240
    assert by_name["lie-detector"].on_invoke_tokens == 1600
    assert by_name["lie-detector"].type == "skill"

    assert by_name["auditor"].on_invoke_tokens == 2400
    assert by_name["auditor"].type == "agent"

    # Hooks excluded — no model context cost
    assert "UserPromptSubmit" not in by_name


def test_parse_versionless_header(fixtures_dir: Path) -> None:
    """Plugins whose first line has only a name (no version) should still parse."""
    text = (fixtures_dir / "plugin_details_versionless.txt").read_text()
    plugin = parse_details_output(text, marketplace="claude-plugins-official")
    assert plugin.name == "context7"
    assert plugin.version == "unknown"  # default when not present
    assert plugin.always_on_tokens == 120
