"""Snapshot tests for tokenview render modules."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from rich.console import Console

from tokenview.models import BudgetBreakdown
from tokenview.render.budget_view import render_budget

SNAPSHOT_DIR = Path(__file__).parent / "snapshots"


def _capture(renderable_fn: Callable[..., None], **kwargs: Any) -> str:
    console = Console(record=True, width=80, force_terminal=False, color_system=None)
    renderable_fn(console=console, **kwargs)
    return console.export_text(clear=False)


def test_render_budget_snapshot() -> None:
    bd = BudgetBreakdown(
        claude_code_base=20000,
        plugins_always_on=8650,
        mcp_tool_definitions=28100,
        claude_md_loaded=14200,
        conversation_so_far=10800,
        residual=7250,
        total_observed=89000,
        cache_read_ratio=0.68,
    )
    out = _capture(render_budget, breakdown=bd, session_id="b0dbc3d0")
    SNAPSHOT_DIR.mkdir(exist_ok=True)
    snapshot = SNAPSHOT_DIR / "budget.txt"
    if not snapshot.exists():
        snapshot.write_text(out)
    assert out == snapshot.read_text(), (
        f"Snapshot mismatch. Delete {snapshot} and re-run if intentional."
    )
