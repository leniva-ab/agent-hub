"""Shared fixtures for the routing hook tests."""

from __future__ import annotations

import json
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
def write_agent() -> Callable[[Path, str, str | None], Path]:
    """Write an agent file, with a model line when one is given."""

    def _write(folder: Path, name: str, model: str | None) -> Path:
        folder.mkdir(parents=True, exist_ok=True)
        model_line = f"model: {model}\n" if model is not None else ""
        path = folder / f"{name}.md"
        path.write_text(f"---\nname: {name}\ndescription: test\n{model_line}---\nBody\n")
        return path

    return _write


@pytest.fixture
def event() -> Callable[..., str]:
    """Build a PreToolUse event as JSON text."""

    def _make(subagent_type: str = "", model: str | None = None, tool: str = "Agent", cwd: str = "/work/repo") -> str:
        tool_input: dict[str, str] = {"description": "d", "prompt": "p"}
        if subagent_type:
            tool_input["subagent_type"] = subagent_type
        if model is not None:
            tool_input["model"] = model
        return json.dumps({"tool_name": tool, "tool_input": tool_input, "cwd": cwd})

    return _make
