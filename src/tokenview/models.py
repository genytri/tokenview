"""Core data models for tokenview."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal


@dataclass(frozen=True)
class UsageRecord:
    """Token usage from a single assistant turn (mirrors JSONL `message.usage`)."""

    input_tokens: int
    output_tokens: int
    cache_read_input_tokens: int
    cache_creation_input_tokens: int

    @property
    def total_input(self) -> int:
        return self.input_tokens + self.cache_read_input_tokens + self.cache_creation_input_tokens

    @property
    def total(self) -> int:
        return self.total_input + self.output_tokens


ComponentType = Literal["skill", "agent", "tool", "mcp"]


@dataclass(frozen=True)
class Invocation:
    """A skill, agent, or tool invocation observed in a session turn."""

    plugin: str | None
    component: str
    component_type: ComponentType
    turn_index: int


@dataclass(frozen=True)
class TurnRecord:
    """One assistant turn from a session."""

    index: int
    timestamp: datetime
    usage: UsageRecord
    invocations: list[Invocation] = field(default_factory=list)


@dataclass(frozen=True)
class Session:
    """A full Claude Code session parsed from a JSONL file."""

    session_id: str
    project_path: str
    started_at: datetime
    turns: list[TurnRecord]

    @property
    def total_tokens(self) -> int:
        return sum(t.usage.total for t in self.turns)


PluginComponentType = Literal["skill", "agent", "hook", "mcp", "lsp"]


@dataclass(frozen=True)
class PluginComponent:
    """A single component declared by a plugin (skill, agent, MCP server, etc.)."""

    name: str
    type: PluginComponentType
    always_on_tokens: int
    on_invoke_tokens: int  # 0 for hooks (no model context cost)


@dataclass(frozen=True)
class Plugin:
    """A Claude Code plugin and its declared cost structure."""

    name: str
    marketplace: str
    version: str
    always_on_tokens: int
    components: list[PluginComponent]


@dataclass(frozen=True)
class BudgetBreakdown:
    """Categorical breakdown of session input tokens (mutually exclusive)."""

    claude_code_base: int  # estimated
    plugins_always_on: int  # exact
    mcp_tool_definitions: int  # estimated
    claude_md_loaded: int  # ≈ exact (tiktoken)
    conversation_so_far: int  # exact
    residual: int  # observed - sum(above)
    total_observed: int
    cache_read_ratio: float  # 0.0 - 1.0


@dataclass(frozen=True)
class ComponentUsage:
    """Aggregated per-component usage in a session."""

    plugin: str | None
    component: str
    component_type: ComponentType
    invocations: int
    estimated_tokens: int
