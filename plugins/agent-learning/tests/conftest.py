"""Shared fixtures for the agent-learn tests."""

from __future__ import annotations

import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))


@pytest.fixture
def log_file(tmp_path: Path) -> Path:
    """A log file path in a temp folder that does not exist yet."""
    return tmp_path / "learn" / "corrections.jsonl"


@pytest.fixture
def at() -> "type[_Clock]":
    """Build timestamps one hour apart on a fixed day."""
    return _Clock


class _Clock:
    """Deterministic timestamps."""

    @staticmethod
    def hour(n: int) -> datetime:
        """Return the fixed day at hour n."""
        return datetime(2026, 11, 12, n, 0, 0, tzinfo=UTC)
