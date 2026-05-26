"""Combined Watch layout: Budget on top, Timeline + Components below."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel

from tokenview.analyze.timeline import TimelineRow
from tokenview.models import BudgetBreakdown, ComponentUsage
from tokenview.render.budget_view import render_budget
from tokenview.render.components_view import render_components
from tokenview.render.timeline_view import render_timeline


def _render_to_panel(fn: Callable[..., None], **kwargs: Any) -> Panel:
    buf = Console(record=True, width=80, force_terminal=False, color_system=None)
    fn(console=buf, **kwargs)
    return Panel(buf.export_text(clear=False))


def build_watch_layout(
    *,
    session_id: str,
    breakdown: BudgetBreakdown,
    timeline: list[TimelineRow],
    components: list[ComponentUsage],
    session_total: int,
) -> Layout:
    layout = Layout(name="root")
    layout.split_column(Layout(name="top", size=14), Layout(name="bottom"))
    layout["bottom"].split_row(Layout(name="left"), Layout(name="right"))

    layout["top"].update(
        _render_to_panel(render_budget, breakdown=breakdown, session_id=session_id)
    )
    layout["bottom"]["left"].update(_render_to_panel(render_timeline, rows=timeline, last=5))
    layout["bottom"]["right"].update(
        _render_to_panel(render_components, rows=components, top=5, session_total=session_total)
    )
    return layout
