"""Tests for the correction log."""

from __future__ import annotations

from pathlib import Path

import pytest

import agent_learn as al


def test_normalise_collapses_case_and_punctuation() -> None:
    assert al.normalise("  Don't  use   print()! ") == "don t use print"


def test_log_assigns_ids_and_keys(log_file: Path, at) -> None:
    a = al.add_correction(log_file, "Use loguru, not print", project="ord", now=at.hour(1))
    b = al.add_correction(log_file, "Use LOGURU not print!", now=at.hour(2))
    assert (a.id, b.id) == (1, 2)
    assert a.key == b.key
    assert a.project == "ord"


def test_tag_overrides_text_key(log_file: Path, at) -> None:
    a = al.add_correction(log_file, "one wording", tag="Logging", now=at.hour(1))
    b = al.add_correction(log_file, "totally different", tag="logging", now=at.hour(2))
    assert a.key == b.key == "logging"


def test_empty_text_rejected(log_file: Path) -> None:
    with pytest.raises(ValueError, match="empty"):
        al.add_correction(log_file, "   ")


def test_repeat_rate(log_file: Path, at) -> None:
    assert al.repeat_rate([]) is None
    for hour, text in enumerate(["a rule", "b rule", "a rule", "a rule"], start=1):
        al.add_correction(log_file, text, now=at.hour(hour))
    corrections, _ = al.load(log_file)
    assert al.repeat_rate(corrections) == 0.5


def test_promotion_and_recurrence(log_file: Path, at) -> None:
    al.add_correction(log_file, "use click", now=at.hour(1))
    al.add_correction(log_file, "use click", now=at.hour(2))
    al.add_promotion(log_file, 1, "user-claude-md", "~/.claude/CLAUDE.md", now=at.hour(3))
    al.add_correction(log_file, "use click", now=at.hour(4))
    al.add_correction(log_file, "other thing", now=at.hour(5))
    corrections, promotions = al.load(log_file)
    items = {g.key: g for g in al.groups(corrections, promotions)}
    assert items["use click"].count == 3
    assert items["use click"].after_promotion == 1
    assert items["use click"].promoted_to == "user-claude-md"
    assert items["other thing"].promoted_at is None
    status = al.format_status(corrections, promotions)
    assert "promoted_but_recurring 1" in status
    assert "recurring after user-claude-md: use click (1x)" in status


def test_first_promotion_wins(log_file: Path, at) -> None:
    al.add_correction(log_file, "x", now=at.hour(1))
    al.add_promotion(log_file, 1, "rule", now=at.hour(5))
    al.add_promotion(log_file, 1, "hook", now=at.hour(3))
    corrections, promotions = al.load(log_file)
    assert al.groups(corrections, promotions)[0].promoted_to == "hook"


def test_promotion_validation(log_file: Path) -> None:
    al.add_correction(log_file, "x")
    with pytest.raises(ValueError, match="target"):
        al.add_promotion(log_file, 1, "nowhere")
    with pytest.raises(ValueError, match="no correction"):
        al.add_promotion(log_file, 9, "rule")


def test_load_missing_and_bad_lines(tmp_path: Path) -> None:
    assert al.load(tmp_path / "nope.jsonl") == ([], [])
    path = tmp_path / "f.jsonl"
    path.write_text('junk\n{"type": "other"}\n{"type": "correction"}\n[1]\n')
    assert al.load(path) == ([], [])


def test_list_open_hides_promoted(log_file: Path, at) -> None:
    al.add_correction(log_file, "keep me", now=at.hour(1))
    al.add_correction(log_file, "done", now=at.hour(2))
    al.add_promotion(log_file, 2, "skill", now=at.hour(3))
    corrections, promotions = al.load(log_file)
    items = al.groups(corrections, promotions)
    assert "done" in al.format_list(items, only_open=False)
    open_text = al.format_list(items, only_open=True)
    assert "keep me" in open_text
    assert "done" not in open_text


def test_status_with_empty_log() -> None:
    assert al.format_status([], []).startswith("corrections 0")
    assert "repeat_rate n/a" in al.format_status([], [])


def test_main_flow(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    env = {"AGENT_LEARN_DIR": str(tmp_path / "d"), "AGENT_PROJECT": "ord"}
    assert al.main(["log", "Use", "pytest", "fixtures", "--tag", "tests"], env, tmp_path) == 0
    assert "logged 1 [tests]" in capsys.readouterr().out
    assert al.main(["promote", "1", "--to", "rule", "--ref", ".claude/rules/tests.md"], env, tmp_path) == 0
    assert al.main(["list"], env, tmp_path) == 0
    assert "rule\ttests" in capsys.readouterr().out
    assert al.main(["status"], env, tmp_path) == 0
    assert "corrections 1" in capsys.readouterr().out
    rows = (tmp_path / "d" / "corrections.jsonl").read_text()
    assert '"project": "ord"' in rows


def test_main_errors(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    env = {"AGENT_LEARN_DIR": str(tmp_path / "d")}
    assert al.main(["promote", "5", "--to", "rule"], env, tmp_path) == 1
    assert "no correction" in capsys.readouterr().err
    assert al.main(["promote", "1", "--to", "bogus"], env, tmp_path) == 2
    assert al.main([], env, tmp_path) == 2
    assert al.main(["log", " "], env, tmp_path) == 1


def test_default_log_path(tmp_path: Path) -> None:
    assert al.log_path({}, tmp_path) == tmp_path / ".agent-learning" / "corrections.jsonl"
