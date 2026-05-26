"""Compose a BudgetBreakdown for a session."""

from __future__ import annotations

from tokenview.models import BudgetBreakdown, Plugin, Session
from tokenview.sources.mcp_estimates import estimate_mcp_tokens


def compute_budget(
    *,
    session: Session,
    plugins: list[Plugin],
    mcp_servers: list[str],
    claude_md_tokens: int,
) -> BudgetBreakdown:
    """Compose a BudgetBreakdown anchored on the first turn of the session.

    Anchoring on the first turn lets us solve for the Claude Code base prompt:
        base = observed_input - (plugins_always_on + mcp_defs + claude_md + conversation)
    """
    if not session.turns:
        raise ValueError("Session has no assistant turns; cannot compute budget.")

    first = session.turns[0]
    total_observed = first.usage.total_input
    plugins_always_on = sum(p.always_on_tokens for p in plugins)
    mcp_tool_definitions = sum(estimate_mcp_tokens(s) for s in mcp_servers)
    conversation_so_far = 0

    known = plugins_always_on + mcp_tool_definitions + claude_md_tokens + conversation_so_far
    base = max(0, total_observed - known)
    residual = total_observed - (base + known)

    cache_total = first.usage.cache_read_input_tokens + first.usage.cache_creation_input_tokens
    cache_read_ratio = first.usage.cache_read_input_tokens / cache_total if cache_total > 0 else 0.0

    return BudgetBreakdown(
        claude_code_base=base,
        plugins_always_on=plugins_always_on,
        mcp_tool_definitions=mcp_tool_definitions,
        claude_md_loaded=claude_md_tokens,
        conversation_so_far=conversation_so_far,
        residual=residual,
        total_observed=total_observed,
        cache_read_ratio=cache_read_ratio,
    )
