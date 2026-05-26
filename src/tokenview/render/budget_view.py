"""Render the Budget view."""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from tokenview.models import BudgetBreakdown

_ESTIMATE_MARK = "⚠"  # WARNING SIGN
_BAR_FILL = "█"  # FULL BLOCK
_BAR_EMPTY = "·"  # MIDDLE DOT


def _bar(percentage: float, width: int = 24) -> str:
    filled = round(percentage * width)
    return _BAR_FILL * filled + _BAR_EMPTY * (width - filled)


def render_budget(*, console: Console, breakdown: BudgetBreakdown, session_id: str) -> None:
    total = max(breakdown.total_observed, 1)

    rows = [
        ("Claude Code base", breakdown.claude_code_base, True),
        ("Plugins always-on", breakdown.plugins_always_on, False),
        ("MCP tool defs", breakdown.mcp_tool_definitions, True),
        ("CLAUDE.md loaded", breakdown.claude_md_loaded, False),
        ("Conversation", breakdown.conversation_so_far, False),
        ("Residual", breakdown.residual, True),
    ]

    table = Table.grid(expand=True, padding=(0, 1))
    table.add_column(width=24)
    table.add_column(width=22, justify="left")
    table.add_column(justify="right")

    for label, value, is_est in rows:
        pct = value / total
        bar = _bar(pct)
        marker = f" {_ESTIMATE_MARK}" if is_est else "  "
        table.add_row(
            bar,
            f"{label}{marker}",
            f"{value:>7,}  ({pct * 100:5.1f}%)",
        )

    table.add_row(
        "",
        Text("TOTAL", style="bold"),
        Text(f"{breakdown.total_observed:>7,}", style="bold"),
    )
    cache_pct = breakdown.cache_read_ratio * 100
    footer = Text.assemble(
        (f"Cache: {cache_pct:.0f}% read from cache    ", "dim"),
        (f"{_ESTIMATE_MARK} = estimate. Real may differ by ±20%.", "dim italic"),
    )

    console.print(Panel(table, title=f"Token budget — session {session_id}", subtitle=footer))
