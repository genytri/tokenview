"""Hardcoded token-cost estimates for known MCP servers.

These are best-effort approximations of the size of the tool schemas an MCP
server exposes in the model context. They are marked as estimates everywhere
they surface in the UI.
"""

from __future__ import annotations

DEFAULT_MCP_TOKENS = 2000

_MCP_TOKEN_TABLE: dict[str, int] = {
    # Keys are server names (i.e. `PluginComponent.name` for type="mcp"),
    # not plugin names — that's what JSONL `mcp__plugin_X_<server>__<tool>`
    # invocations identify and what `_mcp_servers_from_plugins` collects.
    "chrome-devtools": 6000,
    "context7": 1500,
    "filesystem": 1200,
    "github": 4000,
    "postgres": 1800,
    "slack": 3000,
}


def estimate_mcp_tokens(server_name: str) -> int:
    """Return token estimate for a known MCP server, or DEFAULT_MCP_TOKENS."""
    return _MCP_TOKEN_TABLE.get(server_name, DEFAULT_MCP_TOKENS)
