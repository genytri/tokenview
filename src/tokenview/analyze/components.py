"""Aggregate per-component usage across a session."""

from __future__ import annotations

from collections import defaultdict

from tokenview.models import ComponentType, ComponentUsage, Plugin, Session


def aggregate_components(session: Session, plugins: list[Plugin]) -> list[ComponentUsage]:
    """Aggregate invocations across a session and attribute estimated tokens.

    Attribution = invocations * manifest on-invoke cost. Components without a
    matching manifest entry get an `estimated_tokens` of 0 and are still listed
    so the user sees the invocation count.
    """
    cost: dict[tuple[str, str], int] = {}
    for p in plugins:
        for c in p.components:
            cost[(p.name, c.name)] = c.on_invoke_tokens

    counts: dict[tuple[str | None, str], int] = defaultdict(int)
    types: dict[tuple[str | None, str], ComponentType] = {}
    for turn in session.turns:
        for inv in turn.invocations:
            key = (inv.plugin, inv.component)
            counts[key] += 1
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
                estimated_tokens=per_invoke * n,
            )
        )
    rows.sort(key=lambda r: r.estimated_tokens, reverse=True)
    return rows
