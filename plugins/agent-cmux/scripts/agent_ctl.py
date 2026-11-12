"""The overview: one table of every run across all projects, most urgent first."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime

from agent_state import Json, runs_dir

ORDER = ("waiting_human", "blocked", "failed", "running", "queued", "done", "cancelled")


def load_runs(project: str | None = None) -> list[Json]:
    """Read every state.json under the runs directory, skipping unreadable ones."""
    runs: list[Json] = []
    root = runs_dir()
    for path in sorted(root.glob(f"{project or '*'}/*/state.json")):
        try:
            runs.append(json.loads(path.read_text()))
        except (OSError, json.JSONDecodeError):
            continue
    return runs


def age(updated: str, moment: datetime) -> str:
    """Format the time since ``updated`` as s, m, h or d."""
    seconds = max(
        0, int((moment - datetime.strptime(updated, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)).total_seconds())
    )
    for limit, unit, size in ((60, "s", 1), (3600, "m", 60), (86400, "h", 3600)):
        if seconds < limit:
            return f"{seconds // size}{unit}"
    return f"{seconds // 86400}d"


def sort_runs(runs: list[Json]) -> list[Json]:
    """Order by urgency, then oldest update first."""
    return sorted(runs, key=lambda r: (ORDER.index(r["state"]) if r["state"] in ORDER else len(ORDER), r["updated"]))


def render(runs: list[Json], moment: datetime) -> str:
    """Render the overview table."""
    rows = [("PROJECT", "RUN", "STATE", "STAGE", "AGE", "NEXT")]
    rows.extend(
        (
            r["project"],
            f"{r['kind']} {r['ref']}",
            r["state"],
            r.get("stage") or "-",
            age(r["updated"], moment),
            r.get("next_human_action") or "none",
        )
        for r in sort_runs(runs)
    )
    widths = [max(len(row[i]) for row in rows) for i in range(5)]
    return "\n".join(
        "  ".join(cell.ljust(width) for cell, width in zip(row[:5], widths, strict=True)) + f"  {row[5]}"
        for row in rows
    )


def main(argv: list[str] | None = None, moment: datetime | None = None) -> int:
    """Run the CLI."""
    parser = argparse.ArgumentParser(prog="agent-ctl", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    status = sub.add_parser("status")
    status.add_argument("--project")
    status.add_argument("--hide-done", action="store_true")
    status.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    runs = [r for r in load_runs(args.project) if not (args.hide_done and r["state"] in ("done", "cancelled"))]
    if args.json:
        print(json.dumps(sort_runs(runs), indent=2))
    elif runs:
        print(render(runs, moment or datetime.now(UTC)))
    else:
        print("no runs")
    return 0


if __name__ == "__main__":
    sys.exit(main())
