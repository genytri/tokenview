"""Per-frame easing helpers used by the live watch view.

The watch loop runs at a fixed FPS and calls :meth:`AnimRegistry.tick` once
per frame. Each :class:`Animated` value eases exponentially toward its target,
which turns hard cuts ("12,300 → 14,800") into a smooth visual ramp instead of
a sudden snap.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Animated:
    current: float = 0.0
    target: float = 0.0

    def set_target(self, value: float) -> None:
        self.target = float(value)

    def tick(self, factor: float = 0.18) -> bool:
        """Step toward target. Returns True if the value moved this tick.

        Lets callers skip redrawing a region whose underlying values are
        completely settled — that's what keeps the steady-state frame to
        just the spinner + clock update.
        """
        if self.current == self.target:
            return False
        delta = self.target - self.current
        if abs(delta) < 0.5:
            self.current = self.target
            return True
        self.current += delta * factor
        return True


@dataclass
class AnimRegistry:
    values: dict[str, Animated] = field(default_factory=dict)

    def get(self, key: str) -> Animated:
        if key not in self.values:
            self.values[key] = Animated()
        return self.values[key]

    def tick(self, factor: float = 0.18) -> bool:
        """Returns True if any tracked value moved this tick."""
        moved = False
        for v in self.values.values():
            if v.tick(factor):
                moved = True
        return moved
