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


def test_budget_floor_anchors_base_latest_turn_anchors_total(
    fixtures_dir: Path,
) -> None:
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

    latest = session.turns[-1]
    assert breakdown.total_observed == latest.usage.total_input

    # base = min(non-zero total_input across turns) - overhead.
    overhead = breakdown.plugins_always_on + breakdown.claude_md_loaded
    non_zero = [t.usage.total_input for t in session.turns if t.usage.total_input > 0]
    assert breakdown.claude_code_base == max(0, min(non_zero) - overhead)

    accounted = (
        breakdown.claude_code_base
        + breakdown.plugins_always_on
        + breakdown.mcp_tool_definitions
        + breakdown.claude_md_loaded
        + breakdown.conversation_so_far
    )
    assert accounted + breakdown.residual == breakdown.total_observed
    assert 0.0 <= breakdown.cache_read_ratio <= 1.0


def test_budget_conversation_grows_across_turns(fixtures_dir: Path) -> None:
    """Multi-turn session: latest turn's input > first turn's → conversation > 0."""
    session = parse_session(fixtures_dir / "session_minimal.jsonl")
    first = session.turns[0]
    latest = session.turns[-1]
    if latest.usage.total_input <= first.usage.total_input:
        # The fixture has identical-or-shrinking inputs in some scenarios; in
        # that case there's nothing to assert here. Skip when this happens so
        # the assertion below is meaningful when it runs.
        return

    breakdown = compute_budget(session=session, plugins=[], mcp_servers=[], claude_md_tokens=0)
    growth = latest.usage.total_input - first.usage.total_input
    assert breakdown.conversation_so_far >= growth - 1  # tolerate rounding


def test_budget_cache_reset_does_not_hide_conversation() -> None:
    """If the cache is reset mid-session and the floor of total_input drops,
    base must follow the floor — otherwise conversation gets erroneously
    pegged at 0 even when there are clearly more turns piling up."""
    from datetime import datetime, timezone

    from tokenview.analyze.budget import compute_budget
    from tokenview.models import Session, TurnRecord, UsageRecord

    ts = datetime(2026, 5, 26, tzinfo=timezone.utc)

    def _turn(idx: int, total_input: int) -> TurnRecord:
        # Encode the requested total_input via cache_read so the property
        # `total_input` matches without inventing other fields.
        return TurnRecord(
            index=idx,
            timestamp=ts,
            usage=UsageRecord(
                input_tokens=0,
                output_tokens=0,
                cache_read_input_tokens=total_input,
                cache_creation_input_tokens=0,
            ),
        )

    # Turn 0 large, turn 1 small (cache reset), then growing back up.
    session = Session(
        session_id="s",
        project_path="p",
        started_at=ts,
        turns=[
            _turn(0, 38_797),
            _turn(1, 31_170),  # ← floor: cache was reset here
            _turn(2, 35_285),
            _turn(3, 38_214),  # latest: above the floor → real conversation
        ],
    )

    breakdown = compute_budget(session=session, plugins=[], mcp_servers=[], claude_md_tokens=0)
    # base = floor - overhead(0) = 31_170. Conversation = 38_214 - 31_170 = 7_044.
    assert breakdown.claude_code_base == 31_170
    assert breakdown.conversation_so_far == 7_044
    assert breakdown.residual == 0
