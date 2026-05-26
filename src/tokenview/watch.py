"""Live watch loop: re-render combined layout whenever the session JSONL changes."""

from __future__ import annotations

import threading
import time
from pathlib import Path

from rich.console import Console
from rich.live import Live
from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from tokenview.analyze.budget import compute_budget
from tokenview.analyze.components import aggregate_components
from tokenview.analyze.timeline import build_timeline
from tokenview.models import Plugin
from tokenview.render.watch_view import build_watch_layout
from tokenview.sources.jsonl import parse_session


class _Trigger(FileSystemEventHandler):
    def __init__(self, target: Path, event: threading.Event) -> None:
        self._target = target.resolve()
        self._event = event

    def on_modified(self, event: FileSystemEvent) -> None:
        src = event.src_path
        if isinstance(src, bytes):
            src = src.decode()
        if Path(src).resolve() == self._target:
            self._event.set()


def _resolve_session_path(session_file: str | None, session_id: str | None) -> Path:
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


def run_watch(
    *,
    session_file: str | None,
    session_id: str | None,
    plugins: list[Plugin],
    claude_md_tokens: int,
    console: Console,
) -> int:
    target = _resolve_session_path(session_file, session_id)
    refresh = threading.Event()
    refresh.set()  # render once immediately

    observer = Observer()
    observer.schedule(_Trigger(target, refresh), str(target.parent), recursive=False)
    observer.start()

    try:
        with Live(console=console, screen=False, refresh_per_second=4) as live:
            while True:
                refresh.wait()
                refresh.clear()
                session = parse_session(target)
                if not session.turns:
                    time.sleep(0.2)
                    continue
                breakdown = compute_budget(
                    session=session,
                    plugins=plugins,
                    mcp_servers=[],
                    claude_md_tokens=claude_md_tokens,
                )
                timeline = build_timeline(session)
                components = aggregate_components(session, plugins)
                live.update(
                    build_watch_layout(
                        session_id=session.session_id[:8],
                        breakdown=breakdown,
                        timeline=timeline,
                        components=components,
                        session_total=session.total_tokens,
                    )
                )
    except KeyboardInterrupt:
        return 0
    finally:
        observer.stop()
        observer.join()
