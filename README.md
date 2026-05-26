# tokenview

> Visibility into Claude Code token consumption per session — see where your tokens go, identify the heavy hitters, optimize your setup.

[![CI](https://github.com/genytri/tokenview/actions/workflows/ci.yml/badge.svg)](https://github.com/genytri/tokenview/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/tokenview)](https://pypi.org/project/tokenview/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/pypi/pyversions/tokenview)](https://pypi.org/project/tokenview/)

---

## Why this exists

Two developers running the **exact same prompt** in Claude Code can see wildly different token counts. The difference comes from:

- Which **plugins** are installed (each adds always-on tokens to the system prompt)
- Which **MCP servers** are configured (each ships tool definitions in the context)
- The size of the **`CLAUDE.md` files** auto-loaded from the working directory upward
- The **conversation history** so far
- The Claude Code **base prompt** itself

Claude Code does not expose this breakdown anywhere. You see a single `input_tokens` number per turn and have no way to attribute it. **`tokenview` reads your session JSONL files and your `claude plugin details` output to give you the breakdown.**

## Install

```bash
pipx install tokenview
```

Requires Python 3.10+. Works on macOS and Linux. The `claude` CLI must be available on PATH for the `--plugins` data source — without it, `tokenview` still works in `TOKENVIEW_OFFLINE=1` mode using just JSONL data.

## Quick start

```bash
tokenview budget                          # composition of the latest session
tokenview components --top 5              # 5 heaviest skills/agents/MCP tools
tokenview timeline --last 20              # last 20 turns with spike flagging
tokenview watch                           # live dashboard (Ctrl+C to stop)
tokenview summary --days 7                # multi-session aggregate
tokenview plugins                         # static cost of installed plugins
```

By default every command reads the **most recently modified** session under `~/.claude/projects/`. Override with:

```bash
tokenview budget --session b0dbc3d0           # prefix match against session id
tokenview budget --session-file path/to/.jsonl # explicit file
```

## Sample output

### `tokenview budget`

```
╭──────────────────────── Token budget — session b0dbc3d0 ────────────────────────╮
│ █████···················      Claude Code base ⚠            20,000  ( 22.5%)   │
│ ██······················      Plugins always-on              8,650  (  9.7%)   │
│ ████████················      MCP tool defs ⚠               28,100  ( 31.6%)   │
│ ████····················      CLAUDE.md loaded              14,200  ( 16.0%)   │
│ ███·····················      Conversation                  10,800  ( 12.1%)   │
│ ██······················      Residual ⚠                     7,250  (  8.1%)   │
│                               TOTAL                                   89,000   │
╰──────  Cache: 68% read from cache    ⚠ = estimate. Real may differ by ±20%.  ──╯
```

### `tokenview components --top 5`

```
                        Top 5 components this session
┏━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━┳━━━━━━━┳━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━┓
┃ Plugin          ┃ Component     ┃ Type  ┃ Invs ┃ Est tokens ⚠ ┃ % session ┃
┡━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━╇━━━━━━━╇━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━┩
│ superpowers     │ brainstorming │ skill │    1 │        3,200 │     25.6% │
│ truth-serum     │ lie-detector  │ skill │    3 │        4,800 │     38.4% │
│ chrome-devtools │ navigate_page │ mcp   │    2 │          420 │      3.4% │
└─────────────────┴───────────────┴───────┴──────┴──────────────┴───────────┘
```

### `tokenview timeline --last 3`

```
                    Per-turn (last 3)
┏━━━━━┳━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━┳━━━━━━━┓
┃   T ┃ Bar                  ┃  Total ┃     Cum ┃ Spike ┃
┡━━━━━╇━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━╇━━━━━━━┩
│ T00 │ ███                  │  1,562 │   1,562 │       │
│ T01 │ ████                 │  2,023 │   3,585 │       │
│ T02 │ ████████████████████ │ 10,488 │  14,073 │  ⚡   │
└─────┴──────────────────────┴────────┴─────────┴───────┘
```

### `tokenview plugins`

```
   723 tok  superpowers@claude-plugins-official (v5.1.0)
   651 tok  chrome-devtools-mcp@claude-plugins-official (v1.0.1)
   507 tok  mcp-server-dev@claude-plugins-official (vunknown)
   243 tok  truth-serum@truth-serum-marketplace (v0.6.1)
   ...
```

## Honest about what is measured

`tokenview` distinguishes **exact** numbers from **estimates**. Every estimate is marked with ⚠ in the rendered output.

| Metric | Source | Precision |
|---|---|---|
| Session totals, per-turn usage, cache split | JSONL `message.usage` | **Exact** (Anthropic's number) |
| Per-plugin always-on cost | `claude plugin details` | **Exact** (as declared in manifest) |
| Invocation counts of skills / agents / MCP tools | JSONL `tool_use` blocks | **Exact** |
| CLAUDE.md size in tokens | `tiktoken cl100k_base` | **≈ Exact** (cl100k is very close to Anthropic's tokenizer) |
| MCP tool definition size | Hardcoded per-server table | **Estimate** ⚠ |
| Per-component token attribution | `invocations × manifest_on_invoke_cost` | **Estimate** ⚠ |
| Claude Code base prompt size | Anchored by first-turn residual | **Derived** ⚠ |

### What `tokenview` will NOT tell you

- **Cost in dollars.** Use [`ccusage`](https://github.com/ryoppippi/ccusage) for that — it tracks $$ via the Anthropic API itself.
- **"Plugin X cost Y tokens in that specific API call."** Context is mathematically unified at API level — once a plugin's prompt is in the system prompt, the API call's `input_tokens` count is shared, and you cannot attribute it back per-plugin with pixel-perfect accuracy. We approximate by `count × declared_cost`, marked as estimate.

## How it works

```
~/.claude/projects/<encoded-cwd>/<session-id>.jsonl
                │
                ▼
       ┌─────────────────┐         ┌─────────────────────┐
       │ JSONL parser    │         │ claude plugin       │
       │ (sources/jsonl) │         │ details parser      │
       └────────┬────────┘         └──────────┬──────────┘
                │                             │
                ▼                             ▼
       ┌──────────────────────────────────────────┐
       │ Analyzers (budget / components / timeline)│
       └──────────────┬───────────────────────────┘
                      ▼
                ┌──────────┐
                │ rich UI  │
                └──────────┘
```

**Persistence:** parsed plugin manifests are cached at `~/.cache/tokenview/plugins.json` with a 1-hour TTL to avoid repeatedly shelling out to `claude plugin details` for every command.

**Walking CLAUDE.md:** `tokenview budget` walks upward from the current working directory looking for `CLAUDE.md` files (the same algorithm Claude Code uses to auto-load them) and counts their tokens with `tiktoken`.

## Plugin install (Claude Code)

```bash
claude plugin marketplace add genytri/tokenview
claude plugin install tokenview@tokenview-marketplace
```

Then in any Claude Code session:

```
/tokens budget
/tokens components --top 5
/tokens watch
```

The `/tokens` slash command is a thin wrapper around the CLI — `pipx install tokenview` is still required on the host.

## Environment variables

| Variable | Effect |
|---|---|
| `TOKENVIEW_OFFLINE=1` | Skip shelling out to `claude plugin details` / `claude plugin list`. Useful in CI and for `--session-file` testing. |

## Development

```bash
git clone https://github.com/genytri/tokenview
cd tokenview
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# Run gates
pytest -v --cov=tokenview --cov-report=term-missing
ruff check src tests
ruff format --check src tests
mypy src
```

**TDD discipline:** every analyzer and parser ships with fixture-based tests. No mocks of the Anthropic SDK — fixtures are real (or realistic) JSONL and `claude plugin details` captures. See `tests/fixtures/` for the test corpus.

## Roadmap (v0.2+)

These are explicitly out of scope for `0.1.0` but tracked for future versions:

- **Diff mode** — `tokenview export > my.json` + `tokenview diff a.json b.json` to compare two users' setups.
- **VSCode extension** — webview wrapping the same data with live updates and clickable plugin entries.
- **OpenTelemetry ingestion** — read OTEL exports for users running Claude Code with telemetry exporters.
- **`tokenview optimize`** — suggestions to disable rarely-invoked plugins to reclaim always-on budget.
- **`tokenview alerts`** — threshold-based notifications (e.g. "session crossed 200k tokens").
- **Better MCP tool definition estimates** — auto-discovery via `claude mcp list` instead of the hardcoded table.
- **Richer timeline visualization** — stacked bars showing input_new / cache_read / cache_write / output split per turn.

## Limitations / FAQ

**Q: My `Residual` line is huge. What does that mean?**
A: It is the gap between observed `input_tokens` and the sum of categories `tokenview` can attribute. Common causes: an MCP server whose token cost is not in our hardcoded table; an injected hook output; an unusually large attachment; or estimation drift. The number itself is exact (it is computed by subtraction), only its label is honest about not knowing more.

**Q: Why is `Conversation` always 0 in the Budget view?**
A: The Budget view anchors on the **first turn** of the session, where no conversation history exists yet. This is the only point at which we can solve for `Claude Code base` accurately. Use `tokenview timeline` to see how the conversation grows over subsequent turns.

**Q: My session shows weird MCP tool names like `mcp__plugin_chrome-devtools-mcp_chrome-devtools__click`.**
A: That is Claude Code's actual naming convention for plugin-namespaced MCP tools. `tokenview` parses these into `plugin=chrome-devtools-mcp`, `server=chrome-devtools`, `tool=click`.

**Q: Does `tokenview watch` consume tokens?**
A: No — it only reads your local JSONL files. It does not make any API calls.

## Project history

- **v0.1.0** (2026-05-26) — first public release. CLI with budget/components/timeline/watch/summary/plugins commands, Claude Code plugin packaging, 34 tests, mypy strict + ruff clean.

## Author

[Yassir Ait El Aizzi](https://github.com/genytri) — also the author of [Truth Serum](https://github.com/genytri/Truth-Serum) (multi-language verification of AI-generated code).

## License

MIT. See [LICENSE](LICENSE).
