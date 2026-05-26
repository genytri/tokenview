"""Tests for tokenview.analyze.timeline."""

from __future__ import annotations

from pathlib import Path

from tokenview.analyze.timeline import build_timeline
from tokenview.sources.jsonl import parse_session


def test_timeline_cumulative_matches_total(fixtures_dir: Path) -> None:
    session = parse_session(fixtures_dir / "session_minimal.jsonl")
    rows = build_timeline(session)
    assert len(rows) == 2
    assert rows[0].turn_index == 0
    assert rows[0].cumulative == rows[0].total
    assert rows[1].cumulative == rows[0].total + rows[1].total
    assert rows[-1].cumulative == session.total_tokens
