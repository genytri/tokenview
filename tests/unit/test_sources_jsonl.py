"""Tests for tokenview.sources.jsonl."""

from __future__ import annotations

from pathlib import Path

import pytest

from tokenview.sources.jsonl import _classify_tool, parse_session


def test_parse_session_minimal(fixtures_dir: Path) -> None:
    session = parse_session(fixtures_dir / "session_minimal.jsonl")

    assert session.session_id == "sess-min-1"
    assert len(session.turns) == 2  # only assistant turns counted

    t0 = session.turns[0]
    assert t0.usage.input_tokens == 12
    assert t0.usage.output_tokens == 50
    assert t0.usage.cache_read_input_tokens == 1000
    assert t0.usage.cache_creation_input_tokens == 500
    assert len(t0.invocations) == 1
    inv = t0.invocations[0]
    assert inv.plugin == "truth-serum"
    assert inv.component == "verify"
    assert inv.component_type == "skill"
    assert inv.turn_index == 0

    t1 = session.turns[1]
    assert t1.usage.total == 2003 + 20  # 2000 + 3 + 0 input + 20 output
    assert t1.invocations == []

    assert session.total_tokens == t0.usage.total + t1.usage.total


@pytest.mark.parametrize(
    ("name", "inp", "expected"),
    [
        ("Skill", {"skill": "truth-serum:verify"}, ("truth-serum", "verify", "skill")),
        ("Skill", {"skill": "init"}, (None, "init", "skill")),
        ("Agent", {"subagent_type": "plug:auditor"}, ("plug", "auditor", "agent")),
        ("Agent", {}, (None, "general-purpose", "agent")),
        ("mcp__filesystem__read_file", {}, (None, "filesystem", "mcp")),
        (
            "mcp__plugin_chrome-devtools-mcp_chrome-devtools__click",
            {},
            ("chrome-devtools-mcp", "chrome-devtools", "mcp"),
        ),
        (
            "mcp__plugin_context7_context7__query-docs",
            {},
            ("context7", "context7", "mcp"),
        ),
        ("Bash", {}, (None, "Bash", "tool")),
    ],
)
def test_classify_tool(
    name: str,
    inp: dict[str, str],
    expected: tuple[str | None, str, str],
) -> None:
    assert _classify_tool(name, inp) == expected


def test_parse_session_skips_malformed_lines(tmp_path: Path) -> None:
    """A single corrupted line should not abort parsing."""
    f = tmp_path / "session.jsonl"
    user_line = (
        '{"type":"user","timestamp":"2026-05-26T10:00:00.000Z",'
        '"sessionId":"x","message":{"role":"user","content":"hi"}}'
    )
    assistant_line = (
        '{"type":"assistant","timestamp":"2026-05-26T10:00:01.000Z",'
        '"sessionId":"x","message":{"role":"assistant",'
        '"content":[{"type":"text","text":"ok"}],'
        '"usage":{"input_tokens":1,"output_tokens":2,'
        '"cache_read_input_tokens":0,"cache_creation_input_tokens":0}}}'
    )
    f.write_text(user_line + "\n" + "this is not json at all\n" + assistant_line + "\n")
    session = parse_session(f)
    assert session.session_id == "x"
    assert len(session.turns) == 1


def test_parse_session_empty_file_raises(tmp_path: Path) -> None:
    f = tmp_path / "empty.jsonl"
    f.write_text("")
    with pytest.raises(ValueError, match="Empty or invalid session file"):
        parse_session(f)


def test_parse_session_no_session_id_raises(tmp_path: Path) -> None:
    """Lines without sessionId leave started_at unset -> ValueError."""
    f = tmp_path / "weird.jsonl"
    f.write_text('{"type":"user","timestamp":"2026-05-26T10:00:00.000Z"}\n')
    with pytest.raises(ValueError, match="Empty or invalid session file"):
        parse_session(f)
