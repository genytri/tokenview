"""Build a per-turn timeline series."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from tokenview.models import Session


@dataclass(frozen=True)
class TimelineRow:
    turn_index: int
    timestamp: datetime
    input_new: int
    cache_read: int
    cache_write: int
    output: int
    total: int
    cumulative: int
    is_spike: bool  # >2x median(total) over the session


def build_timeline(session: Session) -> list[TimelineRow]:
    totals = [t.usage.total for t in session.turns]
    median = sorted(totals)[len(totals) // 2] if totals else 0
    rows: list[TimelineRow] = []
    cumulative = 0
    for t in session.turns:
        u = t.usage
        total = u.total
        cumulative += total
        rows.append(
            TimelineRow(
                turn_index=t.index,
                timestamp=t.timestamp,
                input_new=u.input_tokens,
                cache_read=u.cache_read_input_tokens,
                cache_write=u.cache_creation_input_tokens,
                output=u.output_tokens,
                total=total,
                cumulative=cumulative,
                is_spike=median > 0 and total > 2 * median,
            )
        )
    return rows
