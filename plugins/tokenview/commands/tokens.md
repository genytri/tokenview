---
name: tokens
description: Show a breakdown of where Claude Code tokens are consumed in the current session (budget, components, timeline).
---

# /tokens

Inspect token consumption of the current Claude Code session.

The `tokenview` CLI must be installed locally. If it is not, install it once:

```bash
pipx install tokenview
```

Run the requested view (default: budget):

```bash
tokenview "$@"
```

Examples:

```bash
tokenview budget                    # composition of current session
tokenview components --top 5        # heaviest 5 components
tokenview timeline --last 10        # last 10 turns
tokenview watch                     # live dashboard (Ctrl+C to stop)
```

If you want to compare with a specific session, pass `--session <id-prefix>` or `--session-file <path>`.
