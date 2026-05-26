"""CLI entry point with argparse subcommand dispatch."""

from __future__ import annotations

import argparse
import os
from collections.abc import Callable
from pathlib import Path

from rich.console import Console

from tokenview import __version__
from tokenview.analyze.budget import compute_budget
from tokenview.analyze.components import aggregate_components
from tokenview.analyze.timeline import build_timeline
from tokenview.cache import PluginCache
from tokenview.models import Plugin, Session
from tokenview.render.budget_view import render_budget
from tokenview.render.components_view import render_components
from tokenview.render.timeline_view import render_timeline
from tokenview.sources.claude_md import count_markdown_tokens, walk_claude_md_files
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


def _decode_project_root(encoded: str) -> Path | None:
    """Decode the original CWD from a Claude Code session's project dirname.

    Sessions live under ``~/.claude/projects/<encoded-cwd>/<id>.jsonl`` where
    ``<encoded-cwd>`` has ``/`` *and* ``.`` both replaced by ``-``. The encoding
    is ambiguous (a ``-`` could mean either), so we try the most likely
    decodings and validate against the filesystem.
    """
    if not encoded or not encoded.startswith("-"):
        return None
    # Path #1: try the home-prefix shortcut. We know the user's home dir, so
    # if the encoded form starts with `-<home-encoded>-`, the remaining tail
    # decodes cleanly as ``home / tail-as-path``.
    home = Path.home()
    home_encoded = "-" + str(home).replace(".", "-").lstrip("/").replace("/", "-")
    if encoded.startswith(home_encoded + "-"):
        tail = encoded[len(home_encoded) :].lstrip("-").replace("-", "/")
        candidate = home / tail
        if candidate.exists():
            return candidate
    # Path #2: pure path interpretation (every `-` becomes `/`).
    candidate = Path("/" + encoded[1:].replace("-", "/"))
    if candidate.exists():
        return candidate
    return None


def _load_claude_md_tokens(start: Path | None = None) -> int:
    """Sum tiktoken count of CLAUDE.md files walked from start up to filesystem root."""
    base = (start or Path.cwd()).resolve()
    total = 0
    for path in walk_claude_md_files(base):
        try:
            total += count_markdown_tokens(path)
        except OSError:
            continue
    return total


def _mcp_servers_from_plugins(plugins: list[Plugin]) -> list[str]:
    """Collect the MCP server names this user's plugins expose.

    The session JSONL's tool invocations encode the same names (e.g.
    ``mcp__plugin_chrome-devtools-mcp_chrome-devtools__click``), but driving
    the budget from plugin manifests means we count MCP overhead even when
    the user hasn't invoked any MCP tool *yet* this session — the cost is
    paid regardless of usage.
    """
    return [c.name for p in plugins for c in p.components if c.type == "mcp"]


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
    project_root = _decode_project_root(session.project_path)
    breakdown = compute_budget(
        session=session,
        plugins=plugins,
        mcp_servers=_mcp_servers_from_plugins(plugins),
        claude_md_tokens=_load_claude_md_tokens(start=project_root),
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
    from tokenview.watch import resolve_session_path, run_watch

    plugins = _load_plugins(_is_offline())
    target = resolve_session_path(args.session_file, args.session)
    project_root = _decode_project_root(target.parent.name)
    return int(
        run_watch(
            session_file=str(target),
            session_id=None,
            plugins=plugins,
            mcp_servers=_mcp_servers_from_plugins(plugins),
            claude_md_tokens=_load_claude_md_tokens(start=project_root),
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
    # "billable token-events" is honest: each turn's input is billed
    # independently even when most of it was served from cache, so the sum
    # counts the same physical tokens once per turn they were re-read.
    console.print(f"Last {args.days} days: {sessions} sessions, {total:,} billable token-events")
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tokenview",
        description="Visibility into Claude Code token consumption.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"tokenview {__version__}",
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
