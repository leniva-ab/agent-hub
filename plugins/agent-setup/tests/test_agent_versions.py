"""Tests for agent-versions."""

from __future__ import annotations

import json

import pytest

import agent_versions as av


def test_parse_version() -> None:
    assert av.parse_version("git version 2.36") == (2, 36, 0)
    assert av.parse_version("gh version 2.97.0 (x)", r"(\d+\.\d+\.\d+)") == (2, 97, 0)
    assert av.parse_version("nothing") is None


def test_all_ok(data, good_outputs, fake_runner, everything_installed) -> None:
    statuses = av.inspect_tools(data, fake_runner(good_outputs), everything_installed)
    assert {s.status for s in statuses} == {"ok"}
    assert av.problems(statuses, data) == []


@pytest.mark.parametrize(
    ("key", "output", "tool"),
    [
        ("git --version", "git version 2.30.1\n", "git"),
        ("gh --version", "gh version 2.89.0\n", "gh"),
        ("gh extension list", "gh stack\tgithub/gh-stack\tv0.1.0\n", "gh-stack"),
        ("claude --version", "2.0.1 (Claude Code)\n", "claude"),
    ],
)
def test_below_floor_is_a_problem(data, good_outputs, fake_runner, everything_installed, key, output, tool) -> None:
    statuses = av.inspect_tools(data, fake_runner({**good_outputs, key: output}), everything_installed)
    found = av.problems(statuses, data)
    assert len(found) == 1 and found[0].startswith(tool)


def test_below_target_is_not_a_problem(data, good_outputs, fake_runner, everything_installed) -> None:
    outputs = {**good_outputs, "git --version": "git version 2.43.0\n"}
    statuses = av.inspect_tools(data, fake_runner(outputs), everything_installed)
    assert next(s for s in statuses if s.name == "git").status == "below_target"
    assert av.problems(statuses, data) == []


def test_missing_optional_tool_is_skipped(data, good_outputs, fake_runner) -> None:
    only_git = lambda name: "/usr/bin/git" if name == "git" else None  # noqa: E731
    statuses = av.inspect_tools(data, fake_runner(good_outputs), only_git)
    assert av.problems(statuses, data) == []
    assert next(s for s in statuses if s.name == "gh").status == "missing"


def test_missing_required_tool_is_a_problem(data, fake_runner) -> None:
    statuses = av.inspect_tools(data, fake_runner({}), lambda name: None)
    assert any(p.startswith("git is not installed") for p in av.problems(statuses, data))


def test_gh_stack_needs_gh(data, good_outputs, fake_runner) -> None:
    no_gh = lambda name: None if name == "gh" else f"/usr/bin/{name}"  # noqa: E731
    statuses = av.inspect_tools(data, fake_runner(good_outputs), no_gh)
    assert next(s for s in statuses if s.name == "gh-stack").status == "missing"


def test_unreadable_output_is_not_a_problem(data, good_outputs, fake_runner, everything_installed) -> None:
    outputs = {**good_outputs, "gh extension list": "something odd\n"}
    statuses = av.inspect_tools(data, fake_runner(outputs), everything_installed)
    assert next(s for s in statuses if s.name == "gh-stack").status == "unreadable"
    assert av.problems(statuses, data) == []


def test_main_show_prints_table(data_file, good_outputs, fake_runner, everything_installed, capsys) -> None:
    assert av.main(["show"], fake_runner(good_outputs), everything_installed, data_file) == 0
    out = capsys.readouterr().out
    assert out.splitlines()[0].split() == ["TOOL", "INSTALLED", "FLOOR", "TARGET", "STATUS"]
    assert "gh-stack" in out


def test_main_check_exit_codes(data_file, good_outputs, fake_runner, everything_installed, capsys) -> None:
    assert av.main(["check", "--quiet"], fake_runner(good_outputs), everything_installed, data_file) == 0
    bad = {**good_outputs, "git --version": "git version 2.0.0\n"}
    assert av.main(["check", "--quiet"], fake_runner(bad), everything_installed, data_file) == 1
    assert "below the floor" in capsys.readouterr().err


def test_hook_is_silent_when_ok(data_file, good_outputs, fake_runner, everything_installed, capsys) -> None:
    assert av.main(["check", "--hook"], fake_runner(good_outputs), everything_installed, data_file) == 0
    assert capsys.readouterr().out == ""


def test_hook_prints_json_on_problem(data_file, good_outputs, fake_runner, everything_installed, capsys) -> None:
    bad = {**good_outputs, "git --version": "git version 2.0.0\n"}
    assert av.main(["check", "--hook"], fake_runner(bad), everything_installed, data_file) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["hookSpecificOutput"]["hookEventName"] == "SessionStart"
    assert "below the team floor" in out["hookSpecificOutput"]["additionalContext"]


def test_hook_disabled_by_env(monkeypatch, data_file, capsys) -> None:
    monkeypatch.setenv("AGENT_PREFLIGHT_DISABLE", "1")
    assert av.main(["check", "--hook"], data_file=data_file) == 0
    assert capsys.readouterr().out == ""


def test_models(data_file, capsys) -> None:
    assert av.main(["models"], data_file=data_file) == 0
    assert "strongest: alias opus, id claude-opus-5-5" in capsys.readouterr().out


def test_cooldown_one_and_unknown(data_file, capsys) -> None:
    assert av.main(["cooldown", "npm"], data_file=data_file) == 0
    assert "min-release-age=3" in capsys.readouterr().out
    assert av.main(["cooldown", "nope"], data_file=data_file) == 2


def test_cooldown_all_lists_every_manager(data_file, capsys) -> None:
    assert av.main(["cooldown"], data_file=data_file) == 0
    out = capsys.readouterr().out
    assert all(name in out for name in ("npm", "pnpm", "uv", "dependabot", "renovate", "maven"))
