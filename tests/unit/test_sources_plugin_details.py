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


def test_parse_unfamiliar_format_returns_zeros_gracefully() -> None:
    """If `claude plugin details` ever changes its output format, the parser
    must degrade quietly — return a Plugin with zero tokens and an empty
    component list — rather than raising. Anyone seeing the surprising zeros
    can then investigate the format drift.
    """
    text = (
        "totally-unknown-plugin 9.9\n"
        "  some description on the wrong line\n"
        "  no projected token cost section at all\n"
    )
    plugin = parse_details_output(text, marketplace="m")
    assert plugin.name == "totally-unknown-plugin"
    assert plugin.always_on_tokens == 0
    assert plugin.components == []
