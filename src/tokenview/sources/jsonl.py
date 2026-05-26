"""Parse a Claude Code session JSONL file into a Session dataclass."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import cast

from tokenview.models import ComponentType, Invocation, Session, TurnRecord, UsageRecord


def _parse_ts(s: str) -> datetime:
    # JSONL timestamps look like "2026-05-26T10:00:00.000Z"
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def _extract_invocations(content: list[dict[str, object]], turn_index: int) -> list[Invocation]:
    invs: list[Invocation] = []
    for block in content:
        if block.get("type") != "tool_use":
            continue
        name = str(block.get("name", ""))
        inp_raw = block.get("input") or {}
        inp = cast(dict[str, object], inp_raw)
        plugin, component, ctype = _classify_tool(name, inp)
        invs.append(
            Invocation(
                plugin=plugin,
                component=component,
                component_type=ctype,
                turn_index=turn_index,
            )
        )
    return invs


def _classify_tool(name: str, inp: dict[str, object]) -> tuple[str | None, str, ComponentType]:
    """Map a tool_use block to (plugin, component, type)."""
    if name == "Skill":
        skill = str(inp.get("skill", ""))
        if ":" in skill:
            plugin, component = skill.split(":", 1)
            return plugin, component, "skill"
        return None, skill, "skill"
    if name == "Agent":
        subtype = str(inp.get("subagent_type", "general-purpose"))
        if ":" in subtype:
            plugin, component = subtype.split(":", 1)
            return plugin, component, "agent"
        return None, subtype, "agent"
    if name.startswith("mcp__"):
        parts = name.split("__")
        # Forms observed in real session JSONL:
        #   mcp__plugin_<plugin>_<server>__<tool>  (literal "plugin_" prefix, plugin-namespaced)
        #   mcp__<server>__<tool>                  (user-level MCP server, no plugin)
        if len(parts) >= 3:
            middle = parts[1]
            if middle.startswith("plugin_"):
                rest = middle[len("plugin_") :]
                # rsplit on the last underscore: plugin name is leftmost, server name is one token
                plugin_name, _, server_name = rest.rpartition("_")
                if plugin_name:
                    return plugin_name, server_name, "mcp"
                # Fallback: malformed "plugin_" prefix with no underscore after it
                return None, rest, "mcp"
            # No "plugin_" prefix → middle IS the server name, no plugin attribution
            return None, middle, "mcp"
        return None, name, "mcp"
    return None, name, "tool"


def parse_session(path: Path) -> Session:
    """Parse a Claude Code session JSONL into a Session."""
    session_id = ""
    project_path = ""
    started_at: datetime | None = None
    turns: list[TurnRecord] = []
    turn_index = 0

    with path.open("r", encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.strip()
            if not line:
                continue
            try:
                event = cast(dict[str, object], json.loads(line))
            except json.JSONDecodeError:
                continue
            if not session_id and event.get("sessionId"):
                session_id = str(event["sessionId"])
                project_path = str(path.parent.name)
            if started_at is None and event.get("timestamp"):
                started_at = _parse_ts(str(event["timestamp"]))
            if event.get("type") != "assistant":
                continue
            msg = cast(dict[str, object], event.get("message") or {})
            usage_raw = cast(dict[str, object], msg.get("usage") or {})
            usage = UsageRecord(
                input_tokens=int(cast(int, usage_raw.get("input_tokens", 0))),
                output_tokens=int(cast(int, usage_raw.get("output_tokens", 0))),
                cache_read_input_tokens=int(cast(int, usage_raw.get("cache_read_input_tokens", 0))),
                cache_creation_input_tokens=int(
                    cast(int, usage_raw.get("cache_creation_input_tokens", 0))
                ),
            )
            content = cast(list[dict[str, object]], msg.get("content") or [])
            invocations = _extract_invocations(content, turn_index)
            turns.append(
                TurnRecord(
                    index=turn_index,
                    timestamp=_parse_ts(str(event["timestamp"])),
                    usage=usage,
                    invocations=invocations,
                )
            )
            turn_index += 1

    if not session_id or started_at is None:
        raise ValueError(f"Empty or invalid session file: {path}")

    return Session(
        session_id=session_id,
        project_path=project_path,
        started_at=started_at,
        turns=turns,
    )
