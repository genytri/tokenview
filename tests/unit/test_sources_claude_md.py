"""Tests for tokenview.sources.claude_md."""

from __future__ import annotations

from pathlib import Path

from tokenview.sources.claude_md import count_markdown_tokens, walk_claude_md_files


def test_count_returns_positive(fixtures_dir: Path) -> None:
    n = count_markdown_tokens(fixtures_dir / "claude_md_sample.md")
    assert n > 0
    assert n < 50  # sanity bound — small fixture


def test_walk_finds_files_up_to_root(tmp_path: Path) -> None:
    (tmp_path / "CLAUDE.md").write_text("# root\n")
    sub = tmp_path / "sub" / "nested"
    sub.mkdir(parents=True)
    (sub.parent / "CLAUDE.md").write_text("# sub\n")
    found = list(walk_claude_md_files(sub, stop_at=tmp_path))
    rel = sorted(p.relative_to(tmp_path).as_posix() for p in found)
    assert rel == ["CLAUDE.md", "sub/CLAUDE.md"]
