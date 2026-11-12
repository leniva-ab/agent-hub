"""Tests for agent-state."""

from __future__ import annotations

import json

import pytest

import agent_state as s


def test_init_creates_queued_run(isolated_env, clock) -> None:
    run_id, state = s.init_run("ord", "review", "PR-231", clock)
    assert run_id == "ord-review-PR231-20261110-0930"
    assert (isolated_env / "ord" / run_id / "state.json").is_file()
    assert state["state"] == "queued" and state["updated"] == "2026-11-10T09:30:00Z"


@pytest.mark.parametrize(("project", "kind"), [("ORD", "review"), ("o", "review"), ("ord", "deploy"), ("bil", "review")])
def test_init_rejects_bad_input_and_wrong_project(project, kind, clock) -> None:
    with pytest.raises(ValueError):
        s.init_run(project, kind, "X", clock)


def test_update_writes_state_log_and_agents(clock, runner) -> None:
    run_id, _ = s.init_run("ord", "review", "PR-231", clock)
    state = s.update_run(run_id, state="running", stage="validate 2/3", round_=2, progress=0.5, agents=["security=running", "validator=done:3 kept"], runner=runner, clock=clock)
    assert state["round"] == 2 and state["agents"][1] == {"role": "validator", "state": "done", "note": "3 kept"}
    assert (s.run_path(run_id) / "log.txt").read_text() == "2026-11-10T09:30:00Z running validate 2/3\n"
    s.update_run(run_id, agents=["security=done"], runner=runner, clock=clock)
    assert s.read_state(run_id)["agents"][0]["state"] == "done"
    assert not (s.run_path(run_id) / "state.json.tmp").exists()


def test_no_cmux_calls_without_workspace(clock, runner, calls) -> None:
    run_id, _ = s.init_run("ord", "build", "P-1", clock)
    s.update_run(run_id, state="running", runner=runner, clock=clock)
    assert calls == []


def test_cmux_projection_and_notify(clock, runner, calls) -> None:
    run_id, _ = s.init_run("ord", "review", "PR-231", clock)
    s.update_run(run_id, state="waiting_human", stage="approve", progress=0.9, next_action="approve 7 comments", workspace="ws1", runner=runner, clock=clock)
    flat = [" ".join(c) for c in calls]
    assert "cmux set-status state waiting_human --workspace ws1 --color #ff9f0a" in flat
    assert "cmux set-status next approve 7 comments --workspace ws1" in flat
    assert any(c.startswith("cmux set-progress 0.9") for c in flat)
    assert any(c.startswith("cmux notify --title ord review PR-231") for c in flat)


def test_running_does_not_notify(clock, runner, calls) -> None:
    run_id, _ = s.init_run("ord", "review", "PR-1", clock)
    s.update_run(run_id, state="running", workspace="ws1", runner=runner, clock=clock)
    assert not any(c[1] == "notify" for c in calls)


def test_cmux_failure_does_not_break_the_run(clock) -> None:
    run_id, _ = s.init_run("ord", "review", "PR-1", clock)
    s.update_run(run_id, state="done", workspace="ws1", runner=lambda c: False, clock=clock)
    assert s.read_state(run_id)["state"] == "done"


def test_workspace_from_env(monkeypatch, clock, runner, calls) -> None:
    monkeypatch.setenv("CMUX_WORKSPACE_ID", "envws")
    run_id, _ = s.init_run("ord", "review", "PR-1", clock)
    s.update_run(run_id, state="running", runner=runner, clock=clock)
    assert ["--workspace", "envws"] == calls[0][4:6]


@pytest.mark.parametrize("kwargs", [{"state": "nope"}, {"progress": 1.5}, {"agents": ["x"]}, {"agents": ["x=weird"]}])
def test_update_rejects_invalid_values(kwargs, clock, runner) -> None:
    run_id, _ = s.init_run("ord", "review", "PR-1", clock)
    with pytest.raises(ValueError):
        s.update_run(run_id, runner=runner, clock=clock, **kwargs)


def test_next_none_clears(clock, runner) -> None:
    run_id, _ = s.init_run("ord", "review", "PR-1", clock)
    s.update_run(run_id, next_action="do x", runner=runner, clock=clock)
    assert s.update_run(run_id, next_action="none", runner=runner, clock=clock)["next_human_action"] is None


def test_cli_round_trip(capsys, runner) -> None:
    assert s.main(["init", "--project", "ord", "--kind", "verify", "--ref", "P-9"], runner) == 0
    run_id = capsys.readouterr().out.strip()
    assert s.main(["set", run_id, "--state", "blocked", "--next", "start db"], runner) == 0
    assert s.main(["show", run_id], runner) == 0
    assert json.loads(capsys.readouterr().out)["state"] == "blocked"
    assert s.main(["set", "ord-x-y-1", "--state", "done"], runner) == 2
    assert s.main(["set", run_id, "--state", "bogus"], runner) == 2
