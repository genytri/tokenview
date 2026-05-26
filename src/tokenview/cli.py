"""CLI entry point with argparse subcommand dispatch."""

from __future__ import annotations

import argparse
import os
from collections.abc import Callable
from pathlib import Path

from rich.console import Console

from tokenview.analyze.budget import compute_budget
from tokenview.analyze.components import aggregate_components
from tokenview.analyze.timeline import build_timeline
from tokenview.cache import PluginCache
from tokenview.models import Plugin, Session
from tokenview.render.budget_view import render_budget
from tokenview.render.components_view import render_components
from tokenview.render.timeline_view import render_timeline
from tokenview.sources.jsonl import parse_session
from tokenview.sources.plugin_details import fetch_plugin_details
from tokenview.sources.plugin_list import fetch_enabled_plugin_ids

CLAUDE_PROJECTS_DIR = Path.home() / ".claude" / "projects"
CACHE_PATH = Path.home() / ".cache" / "tokenview" / "plugins.json"


def _latest_session_file() -> Path:
    files = list(CLAUDE_PROJECTS_DIR.rglob("*.jsonl"))
    if not files:
        raise SystemExit("No Claude Code sessions found under ~/.claude/projects/")
    return max(files, key=lambda p: p.stat().st_mtime)


def _load_session(session_file: str | None, session_id: str | None) -> Session:
    if session_file:
        return parse_session(Path(session_file))
    if session_id:
        matches = list(CLAUDE_PROJECTS_DIR.rglob(f"{session_id}*.jsonl"))
        if not matches:
            raise SystemExit(f"Session id '{session_id}' not found")
        return parse_session(matches[0])
    return parse_session(_latest_session_file())


def _load_plugins(offline: bool) -> list[Plugin]:
    if offline:
        return []
    cache = PluginCache(path=CACHE_PATH, ttl_seconds=3600)
    plugins: list[Plugin] = []
    for plugin_id in fetch_enabled_plugin_ids():
        cached = cache.get(plugin_id)
        if cached is not None:
            plugins.append(cached)
            continue
        try:
            plugin = fetch_plugin_details(plugin_id)
        except Exception:
            # Best-effort: one bad plugin must not break the whole CLI.
            continue
        cache.set(plugin_id, plugin)
        plugins.append(plugin)
    return plugins


def _is_offline() -> bool:
    return bool(int(os.environ.get("TOKENVIEW_OFFLINE", "0")))


def _cmd_budget(args: argparse.Namespace, console: Console) -> int:
    session = _load_session(args.session_file, args.session)
    plugins = _load_plugins(_is_offline())
    breakdown = compute_budget(
        session=session,
        plugins=plugins,
        mcp_servers=[],
        claude_md_tokens=0,
    )
    render_budget(console=console, breakdown=breakdown, session_id=session.session_id[:8])
    return 0


def _cmd_components(args: argparse.Namespace, console: Console) -> int:
    session = _load_session(args.session_file, args.session)
    plugins = _load_plugins(_is_offline())
    rows = aggregate_components(session, plugins)
    render_components(console=console, rows=rows, top=args.top, session_total=session.total_tokens)
    return 0


def _cmd_timeline(args: argparse.Namespace, console: Console) -> int:
    session = _load_session(args.session_file, args.session)
    rows = build_timeline(session)
    render_timeline(console=console, rows=rows, last=args.last)
    return 0


def _cmd_watch(args: argparse.Namespace, console: Console) -> int:
    # Local import: defers watchdog load and tolerates Task 18 not landed yet.
    from tokenview.watch import run_watch

    plugins = _load_plugins(_is_offline())
    return int(
        run_watch(
            session_file=args.session_file,
            session_id=args.session,
            plugins=plugins,
            console=console,
        )
    )


def _cmd_plugins(args: argparse.Namespace, console: Console) -> int:
    # `args` is required by argparse's set_defaults(func=...) contract.
    del args
    plugins = _load_plugins(offline=False)
    for p in sorted(plugins, key=lambda p: p.always_on_tokens, reverse=True):
        console.print(f"{p.always_on_tokens:>6,} tok  {p.name}@{p.marketplace} (v{p.version})")
    return 0


def _cmd_summary(args: argparse.Namespace, console: Console) -> int:
    from datetime import datetime, timedelta, timezone

    cutoff = datetime.now(timezone.utc) - timedelta(days=args.days)
    total = 0
    sessions = 0
    for jsonl in CLAUDE_PROJECTS_DIR.rglob("*.jsonl"):
        try:
            session = parse_session(jsonl)
        except Exception:
            # Best-effort: skip unparseable sessions, keep aggregating the rest.
            continue
        if session.started_at < cutoff:
            continue
        sessions += 1
        total += session.total_tokens
    console.print(f"Last {args.days} days: {sessions} sessions, {total:,} tokens total")
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tokenview",
        description="Visibility into Claude Code token consumption.",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    def _session_args(p: argparse.ArgumentParser) -> None:
        g = p.add_mutually_exclusive_group()
        g.add_argument("--session", help="Session id (prefix match).")
        g.add_argument("--session-file", help="Direct path to a .jsonl session file.")

    pb = sub.add_parser("budget", help="Composition of session input tokens.")
    _session_args(pb)
    pb.set_defaults(func=_cmd_budget)

    pc = sub.add_parser("components", help="Per-component invocation breakdown.")
    _session_args(pc)
    pc.add_argument("--top", type=int, default=10)
    pc.set_defaults(func=_cmd_components)

    pt = sub.add_parser("timeline", help="Per-turn token series.")
    _session_args(pt)
    pt.add_argument("--last", type=int, default=20)
    pt.set_defaults(func=_cmd_timeline)

    pw = sub.add_parser("watch", help="Live dashboard.")
    _session_args(pw)
    pw.set_defaults(func=_cmd_watch)

    pp = sub.add_parser("plugins", help="Static cost of installed plugins.")
    pp.set_defaults(func=_cmd_plugins)

    ps = sub.add_parser("summary", help="Multi-session aggregate.")
    ps.add_argument("--days", type=int, default=7)
    ps.set_defaults(func=_cmd_summary)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    console = Console()
    func: Callable[[argparse.Namespace, Console], int] = args.func
    return func(args, console)
