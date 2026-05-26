"""Live watch loop: continuous, animated, always-moving dashboard.

The loop builds a single :class:`rich.layout.Layout` skeleton once and then
mutates its named slots in place every frame. Rich's auto-refresh thread
repaints at a steady 10 Hz, so there is exactly **one** screen wipe per
frame (no double-paint, no stroboscopic flashing).

Per frame we:

  1. Cheaply re-stat the session file. If the mtime moved, re-parse and push
     new measurements into the :class:`AnimRegistry` as targets.
  2. Ease every animated value one step toward its target.
  3. Update the four named regions of the persistent Layout.

The header carries a spinner and a clock so motion is always visible, even
when the JSONL hasn't changed in a while.
"""

from __future__ import annotations

import contextlib
import time
from pathlib import Path

from rich.console import Console
from rich.layout import Layout
from rich.live import Live

from tokenview.analyze.budget import compute_budget
from tokenview.analyze.components import aggregate_components
from tokenview.analyze.timeline import TimelineRow, build_timeline
from tokenview.models import BudgetBreakdown, ComponentUsage, Plugin, Session
from tokenview.render._animation import AnimRegistry
from tokenview.render.watch_view import (
    build_layout_skeleton,
    render_budget_panel,
    render_components_panel,
    render_header_line,
    render_timeline_panel,
)
from tokenview.sources.jsonl import parse_session

# 10 Hz repaint matches what htop/less feel like and stays well within
# typical terminal redraw budgets. The animation easing factor is tuned so
# values settle in ~10 frames (~1 second).
_TARGET_FPS = 10
_FRAME_SECONDS = 1.0 / _TARGET_FPS


def resolve_session_path(session_file: str | None, session_id: str | None) -> Path:
    if session_file:
        return Path(session_file).resolve()
    projects = Path.home() / ".claude" / "projects"
    if session_id:
        matches = list(projects.rglob(f"{session_id}*.jsonl"))
        if not matches:
            raise SystemExit(f"Session id '{session_id}' not found")
        return matches[0].resolve()
    files = list(projects.rglob("*.jsonl"))
    if not files:
        raise SystemExit("No Claude Code sessions found.")
    return max(files, key=lambda p: p.stat().st_mtime).resolve()


def _sync_targets(anim: AnimRegistry, breakdown: BudgetBreakdown) -> None:
    anim.get("base").set_target(breakdown.claude_code_base)
    anim.get("plugins").set_target(breakdown.plugins_always_on)
    anim.get("mcp").set_target(breakdown.mcp_tool_definitions)
    anim.get("claude_md").set_target(breakdown.claude_md_loaded)
    anim.get("conv").set_target(breakdown.conversation_so_far)
    anim.get("residual").set_target(breakdown.residual)
    anim.get("total").set_target(breakdown.total_observed)
    anim.get("cache_ratio").set_target(breakdown.cache_read_ratio)


def _update_layout(
    layout: Layout,
    *,
    session_id: str,
    breakdown: BudgetBreakdown | None,
    timeline: list[TimelineRow],
    components: list[ComponentUsage],
    anim: AnimRegistry,
    frame: int,
    last_change_frame: int,
    width: int,
    redraw_budget: bool,
    redraw_data_panels: bool,
) -> None:
    full_width = max(40, width - 2)
    half_width = max(30, (full_width // 2) - 2)
    session_total = breakdown.total_observed if breakdown else 0

    # Header always — spinner + clock change every frame, but it's one row,
    # so rich's per-cell diff sends only a handful of bytes per tick.
    layout["header"].update(
        render_header_line(
            session_id=session_id,
            frame=frame,
            last_change_frame=last_change_frame,
            fps=_TARGET_FPS,
        )
    )
    if redraw_budget:
        layout["budget"].update(
            render_budget_panel(breakdown=breakdown, anim=anim, width=full_width)
        )
    if redraw_data_panels:
        layout["bottom"]["left"].update(render_timeline_panel(timeline=timeline, width=half_width))
        layout["bottom"]["right"].update(
            render_components_panel(
                components=components, session_total=session_total, width=half_width
            )
        )


def run_watch(
    *,
    session_file: str | None,
    session_id: str | None,
    plugins: list[Plugin],
    mcp_servers: list[str],
    claude_md_tokens: int,
    console: Console,
) -> int:
    target = resolve_session_path(session_file, session_id)
    anim = AnimRegistry()
    last_mtime = 0.0
    last_change_frame = 0
    cached_session: Session | None = None
    cached_breakdown: BudgetBreakdown | None = None
    cached_timeline: list[TimelineRow] = []
    cached_components: list[ComponentUsage] = []

    # Build the persistent Layout skeleton once. Per-frame work only mutates
    # the renderables inside its named slots; rich diffs them against the
    # previously-painted frame and only repaints what changed.
    layout = build_layout_skeleton()

    # auto_refresh=True lets rich's internal thread paint at refresh_per_second
    # without us calling refresh() explicitly. One paint per tick, no doubles.
    with Live(
        layout,
        console=console,
        screen=True,
        refresh_per_second=_TARGET_FPS,
        auto_refresh=True,
        transient=False,
    ):
        frame = 0
        try:
            while True:
                start = time.monotonic()
                try:
                    mtime = target.stat().st_mtime
                except FileNotFoundError:
                    mtime = last_mtime

                data_changed = False
                if mtime > last_mtime:
                    # ValueError happens when the file exists but is still
                    # being initialised. Keep showing the last good snapshot
                    # and retry on the next frame.
                    with contextlib.suppress(ValueError):
                        cached_session = parse_session(target)
                    if cached_session is not None and cached_session.turns:
                        cached_breakdown = compute_budget(
                            session=cached_session,
                            plugins=plugins,
                            mcp_servers=mcp_servers,
                            claude_md_tokens=claude_md_tokens,
                        )
                        cached_timeline = build_timeline(cached_session)
                        cached_components = aggregate_components(cached_session, plugins)
                        _sync_targets(anim, cached_breakdown)
                        last_change_frame = frame
                        data_changed = True
                    last_mtime = mtime

                anim_moved = anim.tick()

                # Header always updates (spinner + clock change every frame).
                # Other regions only re-render when something actually changed
                # in them — that's what keeps a quiet screen quiet.
                fresh_window = (frame - last_change_frame) < 16  # ~1.5s
                _update_layout(
                    layout,
                    session_id=(cached_session.session_id[:8] if cached_session else "—"),
                    breakdown=cached_breakdown,
                    timeline=cached_timeline,
                    components=cached_components,
                    anim=anim,
                    frame=frame,
                    last_change_frame=last_change_frame,
                    width=console.size.width,
                    redraw_budget=anim_moved or data_changed or fresh_window,
                    redraw_data_panels=data_changed,
                )

                frame += 1
                elapsed = time.monotonic() - start
                time.sleep(max(0.0, _FRAME_SECONDS - elapsed))
        except KeyboardInterrupt:
            return 0
