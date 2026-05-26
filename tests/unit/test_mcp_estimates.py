"""Tests for tokenview.sources.mcp_estimates."""

from __future__ import annotations

from tokenview.sources.mcp_estimates import (
    DEFAULT_MCP_TOKENS,
    estimate_mcp_tokens,
)


def test_known_server_returns_table_value() -> None:
    # Server name (component), not plugin name — matches the keys used by
    # the JSONL classifier and `_mcp_servers_from_plugins`.
    assert estimate_mcp_tokens("chrome-devtools") == 6000


def test_unknown_server_returns_default() -> None:
    assert estimate_mcp_tokens("totally-fictional-server") == DEFAULT_MCP_TOKENS
