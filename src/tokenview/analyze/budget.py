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
    """Compose a BudgetBreakdown for the current state of the session.

    Two-step solve:

      * ``base + overhead`` is anchored at the **floor** of observed input
        across the whole session — the minimum non-zero ``total_input`` of
        any turn. That's the smallest the session ever was, which is the
        best estimate of "everything that isn't conversation". Earlier
        versions anchored only on the first turn, which broke when the
        cache was reset mid-session (turn 3 of one of my sessions had a
        smaller floor than turn 0, and the algorithm permanently hid the
        17 turns of conversation that followed).
      * ``total_observed`` is the **latest** turn — so Conversation reflects
        the gap between current input and that historical floor.

    Edge cases:

      * Turns with ``total_input == 0`` (malformed/empty assistant events)
        are excluded from the floor calculation so they don't drag base
        down to zero.
      * If overhead exceeds the floor, ``base`` clamps to 0 — we never
        let it go negative.
    """
    if not session.turns:
        raise ValueError("Session has no assistant turns; cannot compute budget.")

    latest = session.turns[-1]
    plugins_always_on = sum(p.always_on_tokens for p in plugins)
    mcp_tool_definitions = sum(estimate_mcp_tokens(s) for s in mcp_servers)
    overhead = plugins_always_on + mcp_tool_definitions + claude_md_tokens

    non_zero_inputs = [t.usage.total_input for t in session.turns if t.usage.total_input > 0]
    # If literally every turn has a zero usage record, fall back to the
    # latest turn's number — even if it's also zero — rather than crashing.
    floor = min(non_zero_inputs) if non_zero_inputs else latest.usage.total_input
    base = max(0, floor - overhead)

    total_observed = latest.usage.total_input
    conversation_so_far = max(0, total_observed - (base + overhead))
    residual = total_observed - (base + overhead + conversation_so_far)

    # Cache hit rate vs *total* input — including uncached `input_tokens`.
    # Dividing by (cache_read + cache_creation) only would over-report
    # "% read from cache" by ignoring the new-input portion.
    cache_read_ratio = (
        latest.usage.cache_read_input_tokens / total_observed if total_observed > 0 else 0.0
    )

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
