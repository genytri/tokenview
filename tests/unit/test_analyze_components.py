"""Tests for tokenview.analyze.components."""

from __future__ import annotations

from datetime import datetime, timezone

from tokenview.analyze.components import aggregate_components
from tokenview.models import (
    Invocation,
    Plugin,
    PluginComponent,
    Session,
    TurnRecord,
    UsageRecord,
)


def _session() -> Session:
    u = UsageRecord(0, 0, 0, 0)
    ts = datetime(2026, 5, 26, tzinfo=timezone.utc)
    return Session(
        session_id="s",
        project_path="p",
        started_at=ts,
        turns=[
            TurnRecord(
                index=0,
                timestamp=ts,
                usage=u,
                invocations=[
                    Invocation(
                        plugin="truth-serum",
                        component="lie-detector",
                        component_type="skill",
                        turn_index=0,
                    ),
                    Invocation(
                        plugin="truth-serum",
                        component="lie-detector",
                        component_type="skill",
                        turn_index=0,
                    ),
                ],
            ),
            TurnRecord(
                index=1,
                timestamp=ts,
                usage=u,
                invocations=[
                    Invocation(
                        plugin=None,
                        component="Read",
                        component_type="tool",
                        turn_index=1,
                    ),
                ],
            ),
        ],
    )


def test_aggregate_uses_plugin_on_invoke_cost() -> None:
    plugins = [
        Plugin(
            name="truth-serum",
            marketplace="m",
            version="1",
            always_on_tokens=0,
            components=[
                PluginComponent(
                    name="lie-detector",
                    type="skill",
                    always_on_tokens=0,
                    on_invoke_tokens=1600,
                ),
            ],
        ),
    ]
    rows = aggregate_components(_session(), plugins)
    by_key = {(r.plugin, r.component): r for r in rows}
    skill_row = by_key[("truth-serum", "lie-detector")]
    assert skill_row.invocations == 2
    # Residency-aware estimate: 2 invocations both at turn 0 in a 2-turn
    # session - each stays resident for 2 turns - 2 * 2 * 1600 = 6400.
    assert skill_row.estimated_tokens == 6400
    tool_row = by_key[(None, "Read")]
    assert tool_row.invocations == 1
    assert tool_row.estimated_tokens == 0
