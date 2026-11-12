"""Tests for the token hygiene helpers."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

import pytest

import agent_tokens

type WhichFactory = Callable[[set[str]], Callable[[str], str | None]]
type RunFactory = Callable[[dict[str, str]], Callable[[list[str]], str | None]]


def _status(checks: list[agent_tokens.Check]) -> dict[str, str]:
    return {c.name: c.status for c in checks}


def test_doctor_reports_missing_as_optional(fake_which: WhichFactory, fake_run: RunFactory, home: Path) -> None:
    checks = agent_tokens.doctor(fake_which(set()), fake_run({}), {}, home)
    assert _status(checks) == {"tokf": "missing", "sem": "missing"}


def test_doctor_ok_with_versions(fake_which: WhichFactory, fake_run: RunFactory, home: Path) -> None:
    run = fake_run({"tokf": "tokf 0.2.1\n", "sem": "sem 0.5.0\n"})
    checks = agent_tokens.doctor(fake_which({"tokf", "sem"}), run, {}, home)
    status = _status(checks)
    assert status["tokf"] == "ok"
    assert status["sem"] == "ok"
    assert status["tokf hook"] == "info"


def test_doctor_detects_gnu_parallel_sem(fake_which: WhichFactory, fake_run: RunFactory, home: Path) -> None:
    run = fake_run({"sem": "GNU parallel 20240122\nCopyright\n"})
    checks = agent_tokens.doctor(fake_which({"sem"}), run, {}, home)
    assert _status(checks)["sem"] == "warn"


def test_doctor_finds_hook_in_settings(fake_which: WhichFactory, fake_run: RunFactory, home: Path) -> None:
    (home / ".claude").mkdir()
    (home / ".claude" / "settings.json").write_text('{"hooks": {"x": "tokf hook handle"}}')
    checks = agent_tokens.doctor(fake_which({"tokf"}), fake_run({"tokf": "tokf 1\n"}), {}, home)
    assert _status(checks)["tokf hook"] == "ok"


def test_doctor_warns_when_tool_search_off(fake_which: WhichFactory, fake_run: RunFactory, home: Path) -> None:
    checks = agent_tokens.doctor(fake_which(set()), fake_run({}), {"ENABLE_TOOL_SEARCH": "False"}, home)
    assert _status(checks)["ENABLE_TOOL_SEARCH"] == "warn"


def test_doctor_unknown_version_still_ok(fake_which: WhichFactory, fake_run: RunFactory, home: Path) -> None:
    checks = agent_tokens.doctor(fake_which({"tokf"}), fake_run({}), {}, home)
    assert "version unknown" in checks[0].detail


def test_audit_flags_long_claude_md(project: Path, home: Path) -> None:
    (project / "CLAUDE.md").write_text("x\n" * 201)
    (home / ".claude").mkdir()
    (home / ".claude" / "CLAUDE.md").write_text("x\n" * 10)
    status = _status(agent_tokens.audit(project, home))
    assert status[str(project / "CLAUDE.md")] == "warn"
    assert status[str(home / ".claude" / "CLAUDE.md")] == "ok"


def test_audit_flags_unscoped_rules(project: Path, home: Path) -> None:
    rules = project / ".claude" / "rules"
    rules.mkdir(parents=True)
    (rules / "scoped.md").write_text("---\npaths:\n  - src/**\n---\nbody\n")
    (rules / "loose.md").write_text("---\nname: x\n---\nbody\n")
    (rules / "bare.md").write_text("no frontmatter\n")
    status = _status(agent_tokens.audit(project, home))
    assert status[str(rules / "scoped.md")] == "ok"
    assert status[str(rules / "loose.md")] == "warn"
    assert status[str(rules / "bare.md")] == "warn"


def test_audit_empty_project(project: Path, home: Path) -> None:
    assert agent_tokens.audit(project, home) == []


def test_raw_dir_precedence(home: Path) -> None:
    assert agent_tokens.raw_dir({"AGENT_TOKENS_RAW_DIR": "/a"}, home) == Path("/a")
    assert agent_tokens.raw_dir({"AGENT_RUNS_DIR": "/r"}, home) == Path("/r/raw")
    assert agent_tokens.raw_dir({}, home) == home / ".agent-runs" / "raw"


def test_run_raw_keeps_full_output_and_exit_code(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    now = datetime(2026, 11, 12, 1, 2, 3, tzinfo=UTC)
    code, path = agent_tokens.run_raw(
        ["python3", "-c", "import sys; print('out'); print('err', file=sys.stderr); sys.exit(3)"], tmp_path / "raw", now
    )
    assert code == 3
    assert capsys.readouterr().out == "out\nerr\n"
    text = path.read_text()
    assert "out\nerr\n" in text
    assert text.rstrip().endswith("[exit 3]")
    assert path.name.startswith("20261112-010203-")


def test_run_raw_missing_program(tmp_path: Path) -> None:
    code, path = agent_tokens.run_raw(["definitely-not-a-program-xyz"], tmp_path)
    assert code == 127
    assert "cannot run" in path.read_text()


def test_main_raw_and_usage(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("AGENT_TOKENS_RAW_DIR", str(tmp_path / "keep"))
    assert agent_tokens.main(["raw", "--", "python3", "-c", "print('hi')"]) == 0
    captured = capsys.readouterr()
    assert captured.out == "hi\n"
    assert "raw: " in captured.err
    assert agent_tokens.main(["raw"]) == 64
    assert agent_tokens.main(["raw", "--dir", str(tmp_path / "d"), "--", "python3", "-c", "pass"]) == 0
    assert any((tmp_path / "d").iterdir())
    assert agent_tokens.main([]) == 64


def test_main_audit_strict(project: Path, monkeypatch: pytest.MonkeyPatch, home: Path) -> None:
    monkeypatch.setenv("HOME", str(home))
    (project / "CLAUDE.md").write_text("x\n" * 300)
    assert agent_tokens.main(["audit", str(project)]) == 0
    assert agent_tokens.main(["audit", str(project), "--strict"]) == 1


def test_main_doctor_runs(monkeypatch: pytest.MonkeyPatch, home: Path, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("PATH", "/nonexistent")
    monkeypatch.delenv("ENABLE_TOOL_SEARCH", raising=False)
    assert agent_tokens.main(["doctor"]) == 0
    assert "tokf" in capsys.readouterr().out
