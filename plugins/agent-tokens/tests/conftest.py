"""Shared fixtures for the agent-tokens tests."""

from __future__ import annotations

import sys
from collections.abc import Callable
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))


@pytest.fixture
def home(tmp_path: Path) -> Path:
    """A fake home directory."""
    path = tmp_path / "home"
    path.mkdir()
    return path


@pytest.fixture
def project(tmp_path: Path) -> Path:
    """A fake project directory."""
    path = tmp_path / "proj"
    path.mkdir()
    return path


@pytest.fixture
def fake_which() -> Callable[[set[str]], Callable[[str], str | None]]:
    """Build a PATH lookup that finds only the named programs."""
    return lambda present: (lambda name: f"/bin/{name}" if name in present else None)


@pytest.fixture
def fake_run() -> Callable[[dict[str, str]], Callable[[list[str]], str | None]]:
    """Build a runner that returns canned output keyed by program name."""
    return lambda outputs: (lambda command: outputs.get(Path(command[0]).name))
