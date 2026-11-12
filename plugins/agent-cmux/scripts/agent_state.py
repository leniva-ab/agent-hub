"""Own a run's state file and project it to the cmux sidebar.

``state.json`` is the truth. The sidebar is a projection, so a cmux failure never breaks a
run. Writes are atomic (temp file, then rename). One command replaces about five cmux calls
the model would otherwise have to remember.

Commands:
    init  --project P --kind K --ref R   create a run, print its run id
    set   RUN_ID --state S [...]         update state, log the event, update cmux
    show  RUN_ID                         print state.json
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

STATES = ("queued", "running", "waiting_human", "blocked", "failed", "done", "cancelled")
KINDS = ("review", "build", "verify", "research")
AGENT_STATES = ("queued", "running", "done", "failed")
COLORS = {
    "queued": "#8e8e93",
    "running": "#0a84ff",
    "waiting_human": "#ff9f0a",
    "blocked": "#ff453a",
    "failed": "#ff453a",
    "done": "#30d158",
    "cancelled": "#8e8e93",
}
NOTIFY = {"waiting_human", "blocked", "failed"}
type Json = dict[str, Any]
type Runner = Callable[[list[str]], bool]
type Clock = Callable[[], datetime]


def runs_dir() -> Path:
    """Return the root directory of all runs (AGENT_RUNS_DIR or ~/.agent-runs)."""
    return Path(os.environ.get("AGENT_RUNS_DIR") or Path.home() / ".agent-runs")


def run_path(run_id: str) -> Path:
    """Return a run's directory. The project is the first dash-separated part of the id."""
    return runs_dir() / run_id.split("-", 1)[0] / run_id


def now() -> datetime:
    """Current UTC time."""
    return datetime.now(UTC)


def stamp(moment: datetime) -> str:
    """Format a time as ISO 8601 UTC with seconds."""
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ")


def cmux_run(command: list[str]) -> bool:
    """Run a cmux command, returning False on any failure (the file stays the truth)."""
    try:
        return subprocess.run(command, capture_output=True, timeout=5, check=False).returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def write_state(directory: Path, state: Json) -> None:
    """Atomically write state.json."""
    directory.mkdir(parents=True, exist_ok=True)
    temp = directory / "state.json.tmp"
    temp.write_text(json.dumps(state, indent=2))
    temp.replace(directory / "state.json")


def read_state(run_id: str) -> Json:
    """Read a run's state, raising FileNotFoundError when it does not exist."""
    state: Json = json.loads((run_path(run_id) / "state.json").read_text())
    return state


def new_run_id(project: str, kind: str, ref: str, moment: datetime) -> str:
    """Build ``<project>-<kind>-<ref>-<yyyymmdd-hhmm>`` with a filesystem-safe ref."""
    safe = "".join(c if c.isalnum() else "" for c in ref) or "run"
    return f"{project}-{kind}-{safe}-{moment:%Y%m%d-%H%M}"


def project_to_cmux(state: Json, event: str, workspace: str | None, runner: Runner) -> None:
    """Mirror a state to the cmux sidebar: status keys, progress, log and notify.

    Args:
        state: Current state.json content.
        event: One-line log entry.
        workspace: cmux workspace id, or None to skip projection.
        runner: Executes a cmux command.
    """
    if not workspace:
        return
    target = ["--workspace", workspace]
    runner(["cmux", "set-status", "state", state["state"], *target, "--color", COLORS[state["state"]]])
    runner(["cmux", "set-status", "stage", state["stage"] or "-", *target])
    runner(["cmux", "set-status", "next", state["next_human_action"] or "none", *target])
    if "progress" in state:
        runner(["cmux", "set-progress", str(state["progress"]), *target, "--label", state["stage"] or state["state"]])
    runner(["cmux", "log", *target, "--level", "info", "--", event])
    if state["state"] in NOTIFY:
        runner(
            [
                "cmux",
                "notify",
                "--title",
                f"{state['project']} {state['kind']} {state['ref']}",
                "--body",
                state["next_human_action"] or state["state"],
            ]
        )


def init_run(project: str, kind: str, ref: str, clock: Clock = now) -> tuple[str, Json]:
    """Create a run directory with a queued state.json.

    Args:
        project: Project code, 2 to 5 lowercase letters or digits.
        kind: One of KINDS.
        ref: Ticket or PR reference.
        clock: Time source.

    Returns:
        The run id and the initial state.

    Raises:
        ValueError: On a bad project code, kind, or when AGENT_PROJECT disagrees.
    """
    if not (2 <= len(project) <= 5 and project.isalnum() and project.islower()):
        raise ValueError("project must be 2 to 5 lowercase letters or digits")
    if kind not in KINDS:
        raise ValueError(f"kind must be one of {KINDS}")
    if os.environ.get("AGENT_PROJECT") != project:
        raise ValueError(
            f"AGENT_PROJECT is {os.environ.get('AGENT_PROJECT')!r} but the run is for {project!r}: stop, you may be in the wrong project"
        )
    moment = clock()
    run_id = new_run_id(project, kind, ref, moment)
    state = {
        "run_id": run_id,
        "project": project,
        "kind": kind,
        "ref": ref,
        "state": "queued",
        "stage": "",
        "round": 0,
        "agents": [],
        "next_human_action": None,
        "updated": stamp(moment),
    }
    write_state(run_path(run_id), state)
    return run_id, state


def update_run(
    run_id: str,
    *,
    state: str | None = None,
    stage: str | None = None,
    round_: int | None = None,
    progress: float | None = None,
    next_action: str | None = None,
    agents: list[str] | None = None,
    workspace: str | None = None,
    runner: Runner = cmux_run,
    clock: Clock = now,
) -> Json:
    """Apply changes to a run, append to log.txt and project to cmux.

    Args:
        run_id: Existing run id.
        state: New state, one of STATES.
        stage: Current stage text, for example ``validate 2/3``.
        round_: Current loop round.
        progress: Fraction 0..1.
        next_action: What the human must do, or ``none``.
        agents: Entries ``role=state[:note]`` that replace or add an agent row.
        workspace: cmux workspace id. Defaults to CMUX_WORKSPACE_ID.
        runner: Executes cmux commands.
        clock: Time source.

    Returns:
        The new state.

    Raises:
        ValueError: On an invalid value.
        FileNotFoundError: When the run does not exist.
    """
    current = read_state(run_id)
    if state is not None:
        if state not in STATES:
            raise ValueError(f"state must be one of {STATES}")
        current["state"] = state
    if progress is not None:
        if not 0 <= progress <= 1:
            raise ValueError("progress must be between 0 and 1")
        current["progress"] = progress
    if stage is not None:
        current["stage"] = stage
    if round_ is not None:
        current["round"] = round_
    if next_action is not None:
        current["next_human_action"] = None if next_action == "none" else next_action
    for entry in agents or []:
        head, _, note = entry.partition(":")
        role, _, agent_state = head.partition("=")
        if agent_state not in AGENT_STATES or not role:
            raise ValueError(f"agent entry must be role=state[:note], state in {AGENT_STATES}")
        row = next((a for a in current["agents"] if a["role"] == role), None)
        if row is None:
            row = {"role": role, "state": agent_state}
            current["agents"].append(row)
        row["state"] = agent_state
        if note:
            row["note"] = note
    moment = clock()
    current["updated"] = stamp(moment)
    event = f"{current['state']} {current['stage']}".strip()
    write_state(run_path(run_id), current)
    with (run_path(run_id) / "log.txt").open("a") as log:
        log.write(f"{current['updated']} {event}\n")
    project_to_cmux(current, event, workspace or os.environ.get("CMUX_WORKSPACE_ID"), runner)
    return current


def main(argv: list[str] | None = None, runner: Runner = cmux_run) -> int:
    """Run the CLI. Exit 0 ok, 2 on invalid input or an unknown run."""
    parser = argparse.ArgumentParser(prog="agent-state", description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init")
    init.add_argument("--project", required=True)
    init.add_argument("--kind", required=True)
    init.add_argument("--ref", required=True)
    setter = sub.add_parser("set")
    setter.add_argument("run_id")
    setter.add_argument("--state")
    setter.add_argument("--stage")
    setter.add_argument("--round", type=int, dest="round_")
    setter.add_argument("--progress", type=float)
    setter.add_argument("--next", dest="next_action")
    setter.add_argument("--agent", action="append", default=[], metavar="role=state[:note]")
    setter.add_argument("--workspace")
    show = sub.add_parser("show")
    show.add_argument("run_id")
    args = parser.parse_args(argv)
    try:
        if args.command == "init":
            run_id, _ = init_run(args.project, args.kind, args.ref)
            print(run_id)
        elif args.command == "set":
            update_run(
                args.run_id,
                state=args.state,
                stage=args.stage,
                round_=args.round_,
                progress=args.progress,
                next_action=args.next_action,
                agents=args.agent,
                workspace=args.workspace,
                runner=runner,
            )
        else:
            print(json.dumps(read_state(args.run_id), indent=2))
    except (ValueError, FileNotFoundError) as error:
        print(f"agent-state: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
