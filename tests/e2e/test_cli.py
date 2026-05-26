"""End-to-end CLI tests (subprocess invocations)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

FIXTURES = Path(__file__).parent.parent / "fixtures"


def _run_cli(
    *args: str, env_extra: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    import os

    env = os.environ.copy()
    env["TOKENVIEW_OFFLINE"] = "1"
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        [sys.executable, "-m", "tokenview", *args],
        capture_output=True,
        text=True,
        env=env,
    )


def test_cli_budget_runs_on_fixture() -> None:
    result = _run_cli("budget", "--session-file", str(FIXTURES / "session_minimal.jsonl"))
    assert result.returncode == 0, result.stderr
    assert "Token budget" in result.stdout


def test_cli_components_runs() -> None:
    result = _run_cli("components", "--session-file", str(FIXTURES / "session_minimal.jsonl"))
    assert result.returncode == 0, result.stderr
    assert "Top" in result.stdout


def test_cli_timeline_runs() -> None:
    result = _run_cli("timeline", "--session-file", str(FIXTURES / "session_minimal.jsonl"))
    assert result.returncode == 0, result.stderr
    assert "Per-turn" in result.stdout
