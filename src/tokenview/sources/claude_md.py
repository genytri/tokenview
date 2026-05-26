"""Walk CLAUDE.md files from a directory upward and count their tokens."""

from __future__ import annotations

from collections.abc import Iterator
from functools import lru_cache
from pathlib import Path

import tiktoken


@lru_cache(maxsize=1)
def _encoder() -> tiktoken.Encoding:
    # cl100k_base is the closest stable approximation of Anthropic's tokenizer
    return tiktoken.get_encoding("cl100k_base")


def count_markdown_tokens(path: Path) -> int:
    return len(_encoder().encode(path.read_text(encoding="utf-8")))


def walk_claude_md_files(start: Path, *, stop_at: Path | None = None) -> Iterator[Path]:
    """Yield CLAUDE.md files walking upward from `start` until `stop_at` (inclusive).

    If `stop_at` is None, walk to filesystem root.
    """
    cur = start.resolve()
    stop = stop_at.resolve() if stop_at else None
    while True:
        candidate = cur / "CLAUDE.md"
        if candidate.is_file():
            yield candidate
        if stop is not None and cur == stop:
            return
        if cur.parent == cur:
            return
        cur = cur.parent
