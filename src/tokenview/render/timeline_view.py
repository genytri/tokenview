"""Render the Timeline view."""

from __future__ import annotations

from rich.console import Console
from rich.table import Table
from rich.text import Text

from tokenview.analyze.timeline import TimelineRow

_BAR_FILL = "█"  # FULL BLOCK
_SPIKE_MARK = "⚡"  # HIGH VOLTAGE SIGN


def _bar(value: int, max_value: int, width: int = 20) -> str:
    if max_value <= 0:
        return ""
    n = round(value / max_value * width)
    return _BAR_FILL * n


def render_timeline(*, console: Console, rows: list[TimelineRow], last: int) -> None:
    shown = rows[-last:]
    max_total = max((r.total for r in shown), default=1)

    table = Table(
        title=f"Per-turn (last {len(shown)})",
        show_header=True,
        header_style="bold",
    )
    table.add_column("T", justify="right")
    table.add_column("Bar")
    table.add_column("Total", justify="right")
    table.add_column("Cum", justify="right")
    table.add_column("Spike", justify="center")

    for r in shown:
        bar = _bar(r.total, max_total)
        spike = _SPIKE_MARK if r.is_spike else ""
        table.add_row(
            f"T{r.turn_index:02d}",
            bar,
            f"{r.total:>6,}",
            f"{r.cumulative:>7,}",
            spike,
        )
    console.print(table)
    console.print(Text("Bars scaled to the largest turn in window.", style="dim italic"))
