# tokenview

Visibility into Claude Code token consumption per session — see where your tokens go, identify the heavy hitters, optimize your setup.

## Install

```bash
pipx install tokenview
```

## Quick start

```bash
tokenview budget                 # composition of latest session
tokenview components --top 5     # top 5 token-consuming components
tokenview timeline --last 10     # last 10 turns
tokenview watch                  # live dashboard
tokenview summary --days 7       # weekly aggregate
tokenview plugins                # static cost of installed plugins
```

## Honest about what is measured

`tokenview` distinguishes **exact** numbers (from JSONL `usage`, from `claude plugin details`) from **estimates** (MCP tool definitions, per-component attribution). Every estimated value is marked with ⚠ in the UI and the footer reminds you of the uncertainty.

For financial / $ accuracy, use [`ccusage`](https://github.com/ryoppippi/ccusage) — `tokenview` is about *composition* visibility, not billing.

## License

MIT
