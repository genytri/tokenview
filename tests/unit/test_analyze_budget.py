"""Tests for tokenview.analyze.budget."""

from __future__ import annotations

from pathlib import Path

from tokenview.analyze.budget import compute_budget
from tokenview.models import Plugin, PluginComponent
from tokenview.sources.jsonl import parse_session


def _plugin(name: str, always_on: int) -> Plugin:
    return Plugin(
        name=name,
        marketplace="m",
        version="1",
        always_on_tokens=always_on,
        components=[
            PluginComponent(
                name=name,
                type="skill",
                always_on_tokens=always_on,
                on_invoke_tokens=0,
            )
        ],
    )


def test_budget_first_turn_anchors_base(fixtures_dir: Path) -> None:
    session = parse_session(fixtures_dir / "session_minimal.jsonl")
    plugins = [_plugin("truth-serum", 240), _plugin("superpowers", 500)]
    breakdown = compute_budget(
        session=session,
        plugins=plugins,
        mcp_servers=[],
        claude_md_tokens=300,
    )

    assert breakdown.plugins_always_on == 740
    assert breakdown.mcp_tool_definitions == 0
    assert breakdown.claude_md_loaded == 300
    first = session.turns[0]
    assert breakdown.total_observed == first.usage.total_input
    accounted = (
        breakdown.claude_code_base
        + breakdown.plugins_always_on
        + breakdown.mcp_tool_definitions
        + breakdown.claude_md_loaded
        + breakdown.conversation_so_far
    )
    assert accounted + breakdown.residual == breakdown.total_observed
    assert 0.0 <= breakdown.cache_read_ratio <= 1.0
