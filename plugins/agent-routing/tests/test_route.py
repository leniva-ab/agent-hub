"""Tests for the routing hook and audit."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

import agent_route


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("---\nname: a\nmodel: haiku\n---\nbody", "haiku"),
        ('---\nname: a\nmodel: "claude-sonnet-5-5"\n---\n', "claude-sonnet-5-5"),
        ("---\nname: a\nmodel: inherit\n---\n", None),
        ("---\nname: a\n---\nmodel: opus\n", None),
        ("no frontmatter\nmodel: opus\n", None),
        ("---\nname: a\nmodel: opus\n", None),
    ],
)
def test_pinned_model(text: str, expected: str | None) -> None:
    assert agent_route.pinned_model(text) == expected


def test_denies_unpinned_general_purpose(event: Callable[..., str], home: Path) -> None:
    code = agent_route.run_hook(event("general-purpose"), environ={}, home=home)
    assert code == 2


def test_denies_call_with_no_type(event: Callable[..., str], home: Path) -> None:
    assert agent_route.run_hook(event(), environ={}, home=home) == 2


def test_allows_explicit_model(event: Callable[..., str], home: Path) -> None:
    assert agent_route.run_hook(event("general-purpose", model="haiku"), environ={}, home=home) == 0


def test_inherit_value_does_not_count(event: Callable[..., str], home: Path) -> None:
    assert agent_route.run_hook(event("general-purpose", model="inherit"), environ={}, home=home) == 2


def test_allows_agent_that_pins_model(
    event: Callable[..., str], home: Path, write_agent: Callable[[Path, str, str | None], Path]
) -> None:
    write_agent(home / ".claude" / "agents", "verifier", "sonnet")
    assert agent_route.run_hook(event("verifier"), environ={}, home=home) == 0


def test_agent_that_inherits_is_denied(
    event: Callable[..., str], home: Path, write_agent: Callable[[Path, str, str | None], Path]
) -> None:
    write_agent(home / ".claude" / "agents", "loose", None)
    assert agent_route.run_hook(event("loose"), environ={}, home=home) == 2


def test_plugin_prefix_resolves_installed_plugin_agent(
    event: Callable[..., str], home: Path, write_agent: Callable[[Path, str, str | None], Path]
) -> None:
    write_agent(home / ".claude" / "plugins" / "cache" / "x" / "agent-core" / "agents", "researcher", "sonnet")
    assert agent_route.run_hook(event("agent-core:researcher"), environ={}, home=home) == 0


def test_project_agent_resolves_from_cwd(
    event: Callable[..., str],
    home: Path,
    tmp_path: Path,
    write_agent: Callable[[Path, str, str | None], Path],
) -> None:
    project = tmp_path / "proj"
    write_agent(project / ".claude" / "agents", "mine", "haiku")
    assert agent_route.run_hook(event("mine", cwd=str(project)), environ={}, home=home) == 0


def test_extra_dirs_env(
    event: Callable[..., str],
    home: Path,
    tmp_path: Path,
    write_agent: Callable[[Path, str, str | None], Path],
) -> None:
    extra = tmp_path / "extra"
    write_agent(extra, "shared", "opus")
    env = {agent_route.EXTRA_DIRS_ENV: str(extra)}
    assert agent_route.run_hook(event("shared"), environ=env, home=home) == 0


def test_allow_inherit_list(event: Callable[..., str], home: Path) -> None:
    env = {agent_route.ALLOW_INHERIT_ENV: "Explore, Plan"}
    assert agent_route.run_hook(event("Explore"), environ=env, home=home) == 0
    assert agent_route.run_hook(event("general-purpose"), environ=env, home=home) == 2


def test_kill_switch(event: Callable[..., str], home: Path) -> None:
    assert agent_route.run_hook(event("general-purpose"), environ={agent_route.DISABLE_ENV: "1"}, home=home) == 0


def test_other_tools_pass(event: Callable[..., str], home: Path) -> None:
    assert agent_route.run_hook(event("x", tool="Bash"), environ={}, home=home) == 0


@pytest.mark.parametrize("text", ["", "not json", "[1, 2]", '"str"'])
def test_garbage_input_is_allowed(text: str, home: Path) -> None:
    assert agent_route.run_hook(text, environ={}, home=home) == 0


def test_non_dict_tool_input_is_denied(home: Path) -> None:
    text = '{"tool_name": "Agent", "tool_input": "oops"}'
    assert agent_route.run_hook(text, environ={}, home=home) == 2


def test_denial_message_names_the_fix(
    event: Callable[..., str], home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    agent_route.run_hook(event("general-purpose"), environ={}, home=home)
    err = capsys.readouterr().err
    assert "explicit model" in err
    assert "general-purpose" in err


def test_audit_lists_and_strict_fails_on_inherit(
    home: Path,
    tmp_path: Path,
    write_agent: Callable[[Path, str, str | None], Path],
    capsys: pytest.CaptureFixture[str],
) -> None:
    write_agent(home / ".claude" / "agents", "a", "haiku")
    write_agent(home / ".claude" / "agents", "b", None)
    assert agent_route.run_audit(False, str(tmp_path), {}, home) == 0
    out = capsys.readouterr().out
    assert "a\thaiku" in out
    assert "b\t(inherits)" in out
    assert agent_route.run_audit(True, str(tmp_path), {}, home) == 1


def test_audit_strict_passes_when_all_pinned(
    home: Path, tmp_path: Path, write_agent: Callable[[Path, str, str | None], Path]
) -> None:
    write_agent(home / ".claude" / "agents", "a", "haiku")
    assert agent_route.run_audit(True, str(tmp_path), {}, home) == 0


def test_main_usage_and_hook(
    event: Callable[..., str], capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch, home: Path
) -> None:
    assert agent_route.main([]) == 64
    assert "usage" in capsys.readouterr().err
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.delenv(agent_route.DISABLE_ENV, raising=False)
    assert agent_route.main(["hook"], stdin_text=event("general-purpose", model="haiku")) == 0
