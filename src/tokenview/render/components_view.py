"""Render the Components view."""

from __future__ import annotations

from rich.console import Console
from rich.table import Table
from rich.text import Text

from tokenview.models import ComponentUsage

_ESTIMATE_MARK = "\u26a0"  # WARNING SIGN
_EM_DASH = "\u2014"  # EM DASH
_TIMES = "\u00d7"  # MULTIPLICATION SIGN


def render_components(
    *,
    console: Console,
    rows: list[ComponentUsage],
    top: int,
    session_total: int,
) -> None:
    table = Table(
        title=f"Top {top} components this session",
        show_header=True,
        header_style="bold",
    )
    table.add_column("Plugin", style="cyan")
    table.add_column("Component")
    table.add_column("Type")
    table.add_column("Invs", justify="right")
    table.add_column(f"Est tokens {_ESTIMATE_MARK}", justify="right")
    table.add_column("% session", justify="right")

    shown = rows[:top]
    for r in shown:
        pct = (r.estimated_tokens / session_total * 100) if session_total else 0.0
        table.add_row(
            r.plugin or _EM_DASH,
            r.component,
            r.component_type,
            str(r.invocations),
            f"{r.estimated_tokens:>6,}",
            f"{pct:4.1f}%",
        )
    console.print(table)
    console.print(
        Text(f"Estimates = invocations {_TIMES} manifest on-invoke cost.", style="dim italic")
    )
