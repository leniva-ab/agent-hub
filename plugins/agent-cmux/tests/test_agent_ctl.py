"""Tests for agent-ctl."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import agent_ctl as c
import agent_state as s

NOW = datetime(2026, 11, 10, 11, 30, tzinfo=UTC)


def make(project, kind, ref, state, minutes_ago, monkeypatch, nxt=None):
    monkeypatch.setenv("AGENT_PROJECT", project)
    when = NOW - timedelta(minutes=minutes_ago)
    run_id, _ = s.init_run(project, kind, ref, lambda: when)
    s.update_run(run_id, state=state, stage="st", next_action=nxt, clock=lambda: when, runner=lambda x: True)


def test_orders_by_urgency_then_age(monkeypatch) -> None:
    make("bil", "build", "P-88", "running", 41, monkeypatch)
    make("ord", "review", "PR-231", "waiting_human", 12, monkeypatch, "approve 7 comments")
    make("inv", "verify", "P-12", "blocked", 60, monkeypatch, "start staging db")
    make("ord", "build", "P-1", "done", 5, monkeypatch)
    lines = c.render(c.load_runs(), NOW).splitlines()
    assert [row.split()[3] for row in lines[1:]] == ["waiting_human", "blocked", "running", "done"]
    assert "approve 7 comments" in lines[1] and "12m" in lines[1] and "1h" in lines[2]


def test_filters_and_empty(monkeypatch, capsys) -> None:
    assert c.main(["status"]) == 0 and capsys.readouterr().out.strip() == "no runs"
    make("ord", "review", "A", "done", 1, monkeypatch)
    make("bil", "review", "B", "running", 1, monkeypatch)
    c.main(["status", "--project", "ord", "--hide-done"])
    assert capsys.readouterr().out.strip() == "no runs"
    c.main(["status", "--json"])
    assert capsys.readouterr().out.count('"run_id"') == 2


def test_corrupt_state_is_skipped(monkeypatch, isolated_env) -> None:
    make("ord", "review", "A", "running", 1, monkeypatch)
    bad = isolated_env / "ord" / "ord-bad-1"
    bad.mkdir()
    (bad / "state.json").write_text("{nope")
    assert len(c.load_runs()) == 1


def test_age_units() -> None:
    f = lambda sec: c.age((NOW - timedelta(seconds=sec)).strftime("%Y-%m-%dT%H:%M:%SZ"), NOW)  # noqa: E731
    assert (f(30), f(120), f(7200), f(200000)) == ("30s", "2m", "2h", "2d")
