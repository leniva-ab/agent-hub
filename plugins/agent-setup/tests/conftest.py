"""Shared fixtures for the agent-versions tests."""

from __future__ import annotations

import json
import sys
from collections.abc import Callable
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

type Outputs = dict[str, str | None]


@pytest.fixture
def data() -> dict:
    """Return the shipped versions file."""
    return json.loads((Path(__file__).resolve().parents[1] / "data" / "versions.json").read_text())


@pytest.fixture
def data_file(tmp_path: Path, data: dict) -> Path:
    """Write the shipped data to a temp file."""
    path = tmp_path / "versions.json"
    path.write_text(json.dumps(data))
    return path


@pytest.fixture
def good_outputs() -> Outputs:
    """Command outputs where every tool meets its target."""
    return {
        "git --version": "git version 2.55.0\n",
        "gh --version": "gh version 2.103.3 (2026-10-01)\n",
        "gh extension list": "gh stack\tgithub/gh-stack\tv0.2.1\n",
        "claude --version": "2.1.322 (Claude Code)\n",
        "copilot version": "GitHub Copilot CLI 1.0.96\n",
        "python3 --version": "Python 3.15.2\n",
    }


@pytest.fixture
def fake_runner() -> Callable[[Outputs], Callable[[list[str]], str | None]]:
    """Build a runner that returns canned output per command."""
    return lambda outputs: (lambda command: outputs.get(" ".join(command)))


@pytest.fixture
def everything_installed() -> Callable[[str], str | None]:
    """A PATH lookup that finds every program."""
    return lambda name: f"/usr/bin/{name}"
