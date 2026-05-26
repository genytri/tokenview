"""Renderables for the live watch dashboard.

The watch loop in :mod:`tokenview.watch` builds the Layout skeleton once and
calls one of these per-region renderers each frame. Keeping them as small
pure functions lets rich's diff renderer reuse what didn't change and only
repaint what did.

Layout shape::

    ┌──── header (1 row, ticks every frame) ────┐
    │  budget panel — animated bars             │
    ├──────────────────┬───────────────────────┤
    │  timeline (top5) │  components (top5)    │
    └──────────────────┴───────────────────────┘

The budget bars ease toward their targets with 1/8-cell sub-pixel precision
via :class:`AnimRegistry`. The header carries a spinner + clock that change
every frame so the screen is never completely still.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from rich.align import Align
from rich.console import Console, RenderableType
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from tokenview.analyze.timeline import TimelineRow
from tokenview.models import BudgetBreakdown, ComponentUsage
from tokenview.render._animation import AnimRegistry
from tokenview.render.components_view import render_components
from tokenview.render.timeline_view import render_timeline

_ESTIMATE_MARK = "⚠"  # WARNING SIGN
_FULL_BLOCK = "█"
# 0..7 → trailing-partial-cell at 0/8..7/8 of a cell width.
_PARTIAL_BLOCKS = (None, "▏", "▎", "▍", "▌", "▋", "▊", "▉")
_EMPTY_DOT = "·"
_SPINNER = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"

_BUDGET_ROWS: list[tuple[str, str, str, bool]] = [
    ("base", "Claude Code base", "yellow", True),
    ("plugins", "Plugins always-on", "magenta", False),
    ("mcp", "MCP tool defs", "cyan", True),
    ("claude_md", "CLAUDE.md loaded", "green", False),
    ("conv", "Conversation", "blue", False),
    ("residual", "Residual", "red", True),
]


def build_layout_skeleton() -> Layout:
    """The persistent layout the watch loop mutates every frame."""
    layout = Layout(name="root")
    layout.split_column(
        Layout(name="header", size=1),
        Layout(name="budget", size=12),
        Layout(name="bottom"),
    )
    layout["bottom"].split_row(Layout(name="left"), Layout(name="right"))
    return layout


def _smooth_bar(value: float, total: float, width: int) -> str:
    """Horizontal bar with 1/8-cell precision.

    Plain full-block bars snap from N to N+1 cells once the underlying value
    crosses an integer boundary, which makes easing look stair-stepped. The
    trailing partial block (▏▎▍▌▋▊▉) adds 8x sub-cell resolution so growth
    looks continuous.
    """
    if total <= 0 or width <= 0:
        return _EMPTY_DOT * max(0, width)
    fraction = max(0.0, min(1.0, value / total))
    raw = fraction * width
    full_cells = int(raw)
    partial_idx = int((raw - full_cells) * 8)
    bar = _FULL_BLOCK * full_cells
    partial = _PARTIAL_BLOCKS[partial_idx] if partial_idx else None
    if partial and full_cells < width:
        bar += partial
        empty = width - full_cells - 1
    else:
        empty = width - full_cells
    return bar + _EMPTY_DOT * max(0, empty)


def _capture(fn: Any, width: int, **kwargs: Any) -> RenderableType:
    buf = Console(record=True, width=width, force_terminal=False, color_system=None)
    fn(console=buf, **kwargs)
    return Text(buf.export_text(clear=False))


def render_header_line(
    *,
    session_id: str,
    frame: int,
    last_change_frame: int,
    fps: int,
) -> RenderableType:
    spinner = _SPINNER[frame % len(_SPINNER)]
    now = datetime.now().strftime("%H:%M:%S")
    seconds_since = max(0, frame - last_change_frame) / fps
    fresh = seconds_since < 1.2
    fresh_label = "● NEW DATA" if fresh else f"last update {seconds_since:5.1f}s ago"
    fresh_style = "bold green" if fresh else "dim"
    return Align.center(
        Text.assemble(
            ("▮ ", "bold cyan"),
            ("tokenview ", "bold"),
            (f"· session {session_id} ", "dim"),
            (f"· {spinner} live ", "magenta"),
            (f"· {now} ", "yellow"),
            ("· ", "dim"),
            (fresh_label, fresh_style),
        )
    )


def render_budget_panel(
    *,
    breakdown: BudgetBreakdown | None,
    anim: AnimRegistry,
    width: int,
) -> RenderableType:
    if breakdown is None:
        return Panel(
            Align.center(Text("waiting for first turn…", style="dim italic")),
            border_style="cyan",
            title="Token budget",
        )

    bar_width = max(12, width - 42)
    total_target = max(1, breakdown.total_observed)

    table = Table.grid(expand=True, padding=(0, 1))
    table.add_column(width=bar_width)
    table.add_column(width=22)
    table.add_column(justify="right")

    for key, label, color, is_est in _BUDGET_ROWS:
        animated_value = anim.get(key).current
        pct = animated_value / total_target
        bar = _smooth_bar(animated_value, total_target, bar_width)
        marker = f" {_ESTIMATE_MARK}" if is_est else "  "
        table.add_row(
            Text(bar, style=color),
            Text(f"{label}{marker}"),
            Text(f"{round(animated_value):>7,}  ({pct * 100:5.1f}%)"),
        )

    total_value = round(anim.get("total").current)
    table.add_row(
        Text(""),
        Text("TOTAL", style="bold"),
        Text(f"{total_value:>7,}", style="bold"),
    )

    cache_pct = anim.get("cache_ratio").current * 100
    footer = Text.assemble(
        (f"Cache: {cache_pct:.0f}% read from cache    ", "dim"),
        (f"{_ESTIMATE_MARK} = estimate. Real may differ by ±20%.", "dim italic"),
    )
    return Panel(table, title="Token budget", subtitle=footer, border_style="cyan")


def render_timeline_panel(*, timeline: list[TimelineRow], width: int) -> RenderableType:
    if not timeline:
        return Panel(
            Align.center(Text("no turns yet", style="dim italic")),
            title="Timeline",
        )
    return Panel(_capture(render_timeline, width, rows=timeline, last=5))


def render_components_panel(
    *,
    components: list[ComponentUsage],
    session_total: int,
    width: int,
) -> RenderableType:
    if not components:
        return Panel(
            Align.center(Text("no components yet", style="dim italic")),
            title="Components",
        )
    return Panel(
        _capture(
            render_components,
            width,
            rows=components,
            top=5,
            session_total=session_total,
        )
    )
