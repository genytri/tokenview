# tokenview

Visibility into Claude Code token consumption per session — see where your tokens go, identify the heavy hitters, optimize your setup.

## Why

Two users running the same Claude Code prompt can see very different token counts. The difference comes from installed plugins, MCP servers, `CLAUDE.md` files, conversation history, and base prompt size — but Claude Code does not expose this breakdown anywhere. `tokenview` reads your session JSONL and your `claude plugin details` output to give you a clear picture.

## Install

```bash
pipx install tokenview
```

## Commands

| Command | Shows |
|---|---|
| `tokenview budget` | Composition of the current session's input tokens (base, plugins, MCP, CLAUDE.md, conversation, residual). |
| `tokenview components --top N` | Top N skills/agents/MCP tools by estimated invocation cost. |
| `tokenview timeline --last N` | Per-turn input/cache/output bars, with spike flagging. |
| `tokenview watch` | Combined live dashboard (refreshes when JSONL changes). |
| `tokenview summary --days N` | Aggregate tokens across the last N days. |
| `tokenview plugins` | Static always-on cost of installed plugins. |

By default, every command reads the **latest** session under `~/.claude/projects/`. Use `--session <id-prefix>` or `--session-file <path>` to target a specific session.

## Honest about what is measured

| Metric | Source | Precision |
|---|---|---|
| Session totals, per-turn usage, cache split | JSONL `message.usage` | Exact |
| Per-plugin always-on cost | `claude plugin details` | Exact (as declared) |
| Invocation counts | JSONL `tool_use` blocks | Exact |
| CLAUDE.md size | `tiktoken cl100k_base` | ≈ exact |
| MCP tool definition size | Hardcoded table | Estimate ⚠ |
| Per-component token attribution | `invocations × manifest_on_invoke_cost` | Estimate ⚠ |

`tokenview` does **not** try to compute financial cost — use [`ccusage`](https://github.com/ryoppippi/ccusage) for that.

## Plugin install (Claude Code)

```bash
claude plugin marketplace add genytri/tokenview
claude plugin install tokenview@tokenview-marketplace
```

Then use `/tokens` inside any Claude Code session.

## Development

```bash
git clone https://github.com/genytri/tokenview
cd tokenview
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest
ruff check src tests
mypy src
```

## License

MIT.
