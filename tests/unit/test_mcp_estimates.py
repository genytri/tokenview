"""Tests for tokenview.sources.mcp_estimates."""

from __future__ import annotations

from tokenview.sources.mcp_estimates import (
    DEFAULT_MCP_TOKENS,
    estimate_mcp_tokens,
)


def test_known_server_returns_table_value() -> None:
    assert estimate_mcp_tokens("chrome-devtools-mcp") == 6000


def test_unknown_server_returns_default() -> None:
    assert estimate_mcp_tokens("totally-fictional-server") == DEFAULT_MCP_TOKENS
