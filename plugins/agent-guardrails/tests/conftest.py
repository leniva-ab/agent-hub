"""Shared fixtures for the guard hook tests."""

from __future__ import annotations

import json
import sys
from collections.abc import Callable
from pathlib import Path

import pytest

# The hook is a plain script, not an installed package, so make it importable at collection time.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))


@pytest.fixture
def event() -> Callable[..., str]:
    """Build a PreToolUse event as JSON text."""

    def _make(command: str, tool: str = "Bash", cwd: str = "/work/repo") -> str:
        return json.dumps({"tool_name": tool, "tool_input": {"command": command}, "cwd": cwd})

    return _make
