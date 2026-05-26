"""Aggregate per-component usage across a session."""

from __future__ import annotations

from collections import defaultdict

from tokenview.models import ComponentType, ComponentUsage, Plugin, Session


def aggregate_components(session: Session, plugins: list[Plugin]) -> list[ComponentUsage]:
    """Aggregate invocations across a session and attribute estimated tokens.

    Per-invocation cost vs session residency
    ----------------------------------------
    The naive estimate ``invocations * on_invoke_cost`` only captures the
    moment a component is called. But a component's output stays in the
    conversation context for every subsequent turn until the session ends
    (or the context is compacted) — so the real session contribution is
    closer to ``sum_invocations(cost * turns_after_this_invocation)``.

    Concretely, an invocation at turn T in a session of N turns contributes
    its on-invoke cost ``(N - T)`` more times after the initial call. We
    sum that residency across every invocation of a component.
    """
    cost: dict[tuple[str, str], int] = {}
    for p in plugins:
        for c in p.components:
            cost[(p.name, c.name)] = c.on_invoke_tokens

    n_turns = len(session.turns)
    counts: dict[tuple[str | None, str], int] = defaultdict(int)
    residency_sum: dict[tuple[str | None, str], int] = defaultdict(int)
    types: dict[tuple[str | None, str], ComponentType] = {}
    for turn in session.turns:
        for inv in turn.invocations:
            key = (inv.plugin, inv.component)
            counts[key] += 1
            # Residency for this invocation: this turn plus every later turn.
            residency_sum[key] += max(1, n_turns - inv.turn_index)
            types[key] = inv.component_type

    rows: list[ComponentUsage] = []
    for (plugin, component), n in counts.items():
        per_invoke = 0
        if plugin is not None:
            per_invoke = cost.get((plugin, component), 0)
        rows.append(
            ComponentUsage(
                plugin=plugin,
                component=component,
                component_type=types[(plugin, component)],
                invocations=n,
                estimated_tokens=per_invoke * residency_sum[(plugin, component)],
            )
        )
    rows.sort(key=lambda r: r.estimated_tokens, reverse=True)
    return rows
