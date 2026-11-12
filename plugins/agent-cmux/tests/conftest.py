"""Shared fixtures for agent-cmux script tests."""

from __future__ import annotations

import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))


@pytest.fixture(autouse=True)
def isolated_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point runs at a temp dir, set the project, and clear cmux variables."""
    runs = tmp_path / "runs"
    monkeypatch.setenv("AGENT_RUNS_DIR", str(runs))
    monkeypatch.setenv("AGENT_PROJECT", "ord")
    monkeypatch.delenv("CMUX_WORKSPACE_ID", raising=False)
    return runs


@pytest.fixture
def clock():
    """A fixed clock at 2026-11-10 09:30 UTC."""
    return lambda: datetime(2026, 11, 10, 9, 30, tzinfo=UTC)


@pytest.fixture
def calls() -> list[list[str]]:
    """Collected cmux commands."""
    return []


@pytest.fixture
def runner(calls):
    """A cmux runner that records commands and succeeds."""
    def run(command: list[str]) -> bool:
        calls.append(command)
        return True
    return run
