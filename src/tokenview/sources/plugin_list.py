"""Parse output of `claude plugin list`."""

from __future__ import annotations

import re
import subprocess

# Use unicode escape sequences for the Claude CLI's ornament characters so
# we don't trigger ruff RUF001 ("ambiguous unicode in string") on the
# heavy right-pointing angle that visually resembles `>`.
_BULLET = "\u276f"  # HEAVY RIGHT-POINTING ANGLE QUOTATION MARK ORNAMENT
_CHECK = "\u2714"  # HEAVY CHECK MARK
_CROSS = "\u2718"  # HEAVY BALLOT X

_ENTRY_RE = re.compile(rf"^\s*{_BULLET}\s+(?P<id>\S+@\S+)\s*$")
_STATUS_RE = re.compile(rf"^\s*Status:\s+(?P<sym>[{_CHECK}{_CROSS}])")


def parse_list_output(text: str) -> list[str]:
    """Return the list of enabled plugin IDs (`name@marketplace`)."""
    lines = text.splitlines()
    out: list[str] = []
    pending: str | None = None
    for line in lines:
        m = _ENTRY_RE.match(line)
        if m:
            pending = m.group("id")
            continue
        s = _STATUS_RE.match(line)
        if s and pending:
            if s.group("sym") == _CHECK:
                out.append(pending)
            pending = None
    return out


def fetch_enabled_plugin_ids() -> list[str]:
    """Run `claude plugin list` and return enabled plugin IDs."""
    result = subprocess.run(
        ["claude", "plugin", "list"],
        capture_output=True,
        text=True,
        check=True,
    )
    return parse_list_output(result.stdout)
