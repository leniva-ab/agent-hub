"""Check tool versions against ``data/versions.json`` and print the team's pinned facts.

One file holds every tool floor, target, model alias and cooldown setting, so agents
read facts from it instead of searching for them. Standard library only.

Commands:
    show              table of tools, installed version, floor, target, status
    check             exit 1 when a tool is below its floor (``--quiet``: problems only)
    check --hook      print SessionStart JSON only when there is a problem
    models            tier -> alias -> model id
    cooldown [name]   the 3-day cooldown setting for a package manager or bot
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DATA_FILE = Path(__file__).resolve().parents[1] / "data" / "versions.json"
type Json = dict[str, Any]
type Version = tuple[int, int, int]
type Runner = Callable[[list[str]], str | None]
type Finder = Callable[[str], str | None]


def run(command: list[str]) -> str | None:
    """Run a command and return stdout, or None if missing, slow or failing.

    Args:
        command: Program and arguments.

    Returns:
        Standard output text, or None.
    """
    try:
        done = subprocess.run(command, capture_output=True, text=True, timeout=3, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return done.stdout if done.returncode == 0 else None


def parse_version(text: str, pattern: str = r"(\d+\.\d+(?:\.\d+)?)") -> Version | None:
    """Extract a version from text as a comparable tuple.

    Args:
        text: Output of a version command.
        pattern: Regex whose first group is the dotted version.

    Returns:
        (major, minor, patch), or None when nothing matches.
    """
    match = re.search(pattern, text)
    if match is None:
        return None
    parts = re.match(r"(\d+)\.(\d+)(?:\.(\d+))?", match.group(1))
    if parts is None:
        return None
    major, minor, patch = parts.groups(default="0")
    return int(major), int(minor), int(patch)


def fmt(version: Version | None) -> str:
    """Format a version tuple, or a dash when unknown."""
    return "-" if version is None else ".".join(map(str, version))


@dataclass(frozen=True, slots=True)
class ToolStatus:
    """State of one tool.

    Attributes:
        name: Key in versions.json.
        installed: Version found, or None when absent or unreadable.
        floor: Minimum allowed version.
        target: Latest known good version.
        status: One of ok, below_floor, below_target, missing, unreadable.
        why: Why the floor exists.
        install: How to install or upgrade.
    """

    name: str
    installed: Version | None
    floor: Version
    target: Version
    status: str
    why: str
    install: str


def load(path: Path = DATA_FILE) -> Json:
    """Load versions.json."""
    data: Json = json.loads(path.read_text())
    return data


def inspect_tools(data: Json, runner: Runner = run, finder: Finder = shutil.which) -> list[ToolStatus]:
    """Inspect every tool in the data file.

    A tool whose program is absent is ``missing``. One whose output cannot be parsed is
    ``unreadable``. Neither is treated as below the floor, so there are no false alarms,
    except for tools marked ``required``.

    Args:
        data: Parsed versions.json.
        runner: Runs a command and returns its output.
        finder: Locates a program on PATH.

    Returns:
        One ToolStatus per tool, in file order.
    """
    result: list[ToolStatus] = []
    for name, spec in data["tools"].items():
        floor = parse_version(spec["floor"]) or (0, 0, 0)
        target = parse_version(spec["target"]) or floor
        program = spec.get("needs") or spec["cmd"][0]
        installed: Version | None = None
        if finder(program) is None:
            status = "missing"
        else:
            output = runner(spec["cmd"])
            installed = parse_version(output, spec["parse"]) if output else None
            if installed is None:
                status = "unreadable"
            elif installed < floor:
                status = "below_floor"
            elif installed < target:
                status = "below_target"
            else:
                status = "ok"
        result.append(ToolStatus(name, installed, floor, target, status, spec.get("why", ""), spec.get("install", "")))
    return result


def problems(statuses: list[ToolStatus], data: Json) -> list[str]:
    """Return one sentence per tool that blocks work.

    Args:
        statuses: Output of inspect_tools.
        data: Parsed versions.json.

    Returns:
        Sentences for tools below the floor, and for required tools that are missing.
    """
    out: list[str] = []
    for item in statuses:
        if item.status == "below_floor":
            out.append(
                f"{item.name} {fmt(item.installed)} is below the floor {fmt(item.floor)} ({item.why}). Fix: {item.install}"
            )
        elif item.status == "missing" and data["tools"][item.name].get("required"):
            out.append(f"{item.name} is not installed. Fix: {item.install}")
    return out


def render_table(statuses: list[ToolStatus]) -> str:
    """Render a plain-text table of tool statuses."""
    rows = [("TOOL", "INSTALLED", "FLOOR", "TARGET", "STATUS")]
    rows += [(s.name, fmt(s.installed), fmt(s.floor), fmt(s.target), s.status) for s in statuses]
    widths = [max(len(r[i]) for r in rows) for i in range(5)]
    return "\n".join("  ".join(cell.ljust(widths[i]) for i, cell in enumerate(r)).rstrip() for r in rows)


def cooldown_text(data: Json, name: str | None) -> str:
    """Describe the cooldown setting for one package manager or bot, or list all.

    Args:
        data: Parsed versions.json.
        name: Key under cooldown.settings, or None for every entry.

    Returns:
        Text to print. Raises KeyError for an unknown name.
    """
    block = data["cooldown"]
    entries = block["settings"] if name is None else {name: block["settings"][name]}
    lines = [f"Cooldown: {block['days']} days. {block['note']}"]
    for key, spec in entries.items():
        if "set" in spec:
            minimum = f" (needs {spec['min']} or later)" if "min" in spec else ""
            extra = f" [{spec['note']}]" if "note" in spec else ""
            lines.append(f"{key}{minimum}: in {spec['where']}: {spec['set']}{extra}")
        else:
            lines.append(f"{key}: {spec['note']}")
    return "\n".join(lines)


def models_text(data: Json) -> str:
    """List the model tiers with their alias and pinned id."""
    return "\n".join(f"{tier}: alias {m['alias']}, id {m['id']}" for tier, m in data["models"].items())


def build_parser() -> argparse.ArgumentParser:
    """Build the command line parser."""
    parser = argparse.ArgumentParser(prog="agent-versions", description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("show")
    check = sub.add_parser("check")
    check.add_argument("--quiet", action="store_true", help="print only problems")
    check.add_argument("--hook", action="store_true", help="print SessionStart JSON, only on problems")
    sub.add_parser("models")
    cool = sub.add_parser("cooldown")
    cool.add_argument("name", nargs="?")
    return parser


def main(
    argv: list[str] | None = None, runner: Runner = run, finder: Finder = shutil.which, data_file: Path = DATA_FILE
) -> int:
    """Run the command line tool.

    Args:
        argv: Arguments, defaults to sys.argv.
        runner: Command runner, replaceable in tests.
        finder: PATH lookup, replaceable in tests.
        data_file: Path to versions.json.

    Returns:
        Exit code: 0 ok, 1 problems found, 2 bad input.
    """
    args = build_parser().parse_args(argv)
    data = load(data_file)
    if args.command == "models":
        print(models_text(data))
        return 0
    if args.command == "cooldown":
        try:
            print(cooldown_text(data, args.name))
        except KeyError:
            print(f"unknown name {args.name!r}. Known: {', '.join(data['cooldown']['settings'])}", file=sys.stderr)
            return 2
        return 0
    if args.command == "check" and args.hook and os.environ.get("AGENT_PREFLIGHT_DISABLE") == "1":
        return 0
    statuses = inspect_tools(data, runner, finder)
    found = problems(statuses, data)
    if args.command == "show":
        print(render_table(statuses))
        return 0
    if args.hook:
        if found:
            text = "Tool versions below the team floor: " + " ".join(found) + " Details: run agent-versions show."
            print(json.dumps({"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": text}}))
        return 0
    if not args.quiet:
        print(render_table(statuses))
    for line in found:
        print(line, file=sys.stderr)
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
