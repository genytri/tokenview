"""Tests for tokenview.models."""

from __future__ import annotations

import dataclasses
from datetime import datetime, timezone

import pytest

from tokenview.models import (
    Invocation,
    Session,
    TurnRecord,
    UsageRecord,
)


def test_usage_record_totals() -> None:
    u = UsageRecord(
        input_tokens=10,
        output_tokens=200,
        cache_read_input_tokens=5000,
        cache_creation_input_tokens=1000,
    )
    assert u.total_input == 6010
    assert u.total == 6210


def test_session_total_sums_turns() -> None:
    u1 = UsageRecord(1, 10, 100, 0)
    u2 = UsageRecord(2, 20, 200, 0)
    s = Session(
        session_id="abc",
        project_path="/x",
        started_at=datetime(2026, 5, 26, tzinfo=timezone.utc),
        turns=[
            TurnRecord(
                index=0,
                timestamp=datetime(2026, 5, 26, tzinfo=timezone.utc),
                usage=u1,
                invocations=[],
            ),
            TurnRecord(
                index=1,
                timestamp=datetime(2026, 5, 26, tzinfo=timezone.utc),
                usage=u2,
                invocations=[],
            ),
        ],
    )
    assert s.total_tokens == u1.total + u2.total


def test_invocation_frozen() -> None:
    inv = Invocation(
        plugin="truth-serum",
        component="lie-detector",
        component_type="skill",
        turn_index=2,
    )
    with pytest.raises(dataclasses.FrozenInstanceError):
        inv.turn_index = 99  # type: ignore[misc]
