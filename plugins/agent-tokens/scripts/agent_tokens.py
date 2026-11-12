"""Token hygiene helpers: a doctor for filter tools, a context audit, and a raw-output keeper.

Commands:

``doctor``
    Checks that ``tokf`` and ``sem`` are on PATH and are the right programs, and flags settings that
    work against the prompt cache or tool deferral. Both tools are optional. This plugin does not
    install any hook for them.

``audit [DIR]``
    Counts lines in CLAUDE.md files and lists rules files that have no ``paths:`` scope, which load at
    every session start.

``raw [--dir DIR] -- COMMAND...``
    Runs a command, prints its output, and keeps the full output in a file. Use it for commands whose
    output is evidence, because a Bash output filter may shorten what the agent sees.

Standard library only, so it starts fast and needs no install.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

CLAUDE_MD_LINE_LIMIT = 200
FRONTMATTER_PATHS = re.compile(r"^paths:", re.MULTILINE)
SLUG_CHARS = re.compile(r"[^a-z0-9]+")

type Runner = Callable[[list[str]], str | None]
type Which = Callable[[str], str | None]


@dataclass(frozen=True, slots=True)
class Check:
    """One line of a report.

    Attributes:
        name: What was checked.
        status: One of ``ok``, ``info``, ``missing`` or ``warn``.
        detail: Short explanation.
    """

    name: str
    status: str
    detail: str


def run_command(command: list[str]) -> str | None:
    """Run a command and return its combined output.

    Args:
        command: Program and arguments.

    Returns:
        Output text, or None when the program cannot be run or times out.
    """
    try:
        done = subprocess.run(command, capture_output=True, text=True, timeout=10, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return done.stdout + done.stderr


def _tool_check(name: str, which: Which, run: Runner, wrong_marker: str | None = None) -> Check:
    path = which(name)
    if path is None:
        return Check(name, "missing", "not on PATH. Optional.")
    version = (run([path, "--version"]) or "").strip().splitlines()
    first = version[0] if version else "version unknown"
    if wrong_marker and any(wrong_marker.lower() in line.lower() for line in version):
        return Check(name, "warn", f"{path} is not the intended tool ({first}). Use the full path or npx.")
    return Check(name, "ok", f"{path} {first}")


def _settings_mention(home: Path, needle: str) -> bool:
    for name in ("settings.json", "settings.local.json"):
        path = home / ".claude" / name
        if path.is_file() and needle in path.read_text(encoding="utf-8", errors="replace"):
            return True
    return False


def doctor(which: Which, run: Runner, environ: Mapping[str, str], home: Path) -> list[Check]:
    """Check the filter tools and token-related settings.

    Args:
        which: PATH lookup.
        run: Command runner.
        environ: Environment.
        home: Home directory, where user settings live.

    Returns:
        A list of checks, in display order.
    """
    checks = [
        _tool_check("tokf", which, run),
        _tool_check("sem", which, run, wrong_marker="GNU parallel"),
    ]
    if which("tokf") is not None:
        hooked = _settings_mention(home, "tokf")
        checks.append(
            Check(
                "tokf hook",
                "ok" if hooked else "info",
                "found in user settings" if hooked else "not found in user settings. Not installed by this plugin.",
            )
        )
    if environ.get("ENABLE_TOOL_SEARCH", "").lower() == "false":
        checks.append(
            Check("ENABLE_TOOL_SEARCH", "warn", "false loads every MCP tool definition into context. Unset it.")
        )
    return checks


def _count_lines(path: Path) -> int:
    return len(path.read_text(encoding="utf-8", errors="replace").splitlines())


def audit(project: Path, home: Path) -> list[Check]:
    """Audit the files that load into every session.

    Args:
        project: Project directory.
        home: Home directory.

    Returns:
        A list of checks, one per file found.
    """
    checks: list[Check] = []
    candidates = [
        project / "CLAUDE.md",
        project / ".claude" / "CLAUDE.md",
        home / ".claude" / "CLAUDE.md",
    ]
    for path in candidates:
        if path.is_file():
            lines = _count_lines(path)
            over = lines > CLAUDE_MD_LINE_LIMIT
            detail = f"{lines} lines" + (f", over {CLAUDE_MD_LINE_LIMIT}. Move detail to path rules or skills." if over else "")
            checks.append(Check(str(path), "warn" if over else "ok", detail))
    rules = project / ".claude" / "rules"
    if rules.is_dir():
        for path in sorted(rules.rglob("*.md")):
            text = path.read_text(encoding="utf-8", errors="replace")
            head = text[3 : text.find("\n---", 3)] if text.startswith("---") and "\n---" in text[3:] else ""
            scoped = FRONTMATTER_PATHS.search(head) is not None
            checks.append(
                Check(
                    str(path),
                    "ok" if scoped else "warn",
                    "scoped by paths" if scoped else "no paths: scope, so it loads at every session start",
                )
            )
    return checks


def raw_dir(environ: Mapping[str, str], home: Path) -> Path:
    """Return the folder where raw output is kept.

    Args:
        environ: Environment, read for ``AGENT_TOKENS_RAW_DIR`` and ``AGENT_RUNS_DIR``.
        home: Home directory.

    Returns:
        The folder path.
    """
    if environ.get("AGENT_TOKENS_RAW_DIR"):
        return Path(environ["AGENT_TOKENS_RAW_DIR"])
    runs = Path(environ["AGENT_RUNS_DIR"]) if environ.get("AGENT_RUNS_DIR") else home / ".agent-runs"
    return runs / "raw"


def run_raw(command: Sequence[str], folder: Path, now: datetime | None = None) -> tuple[int, Path]:
    """Run a command, print its output and keep the full output in a file.

    Args:
        command: Program and arguments.
        folder: Folder for the raw file. Created if missing.
        now: Timestamp for the file name, defaults to the current UTC time.

    Returns:
        The command's exit code (127 when it cannot be started) and the raw file path.
    """
    stamp = (now or datetime.now(UTC)).strftime("%Y%m%d-%H%M%S-%f")
    slug = SLUG_CHARS.sub("-", " ".join(command).lower()).strip("-")[:40] or "command"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{stamp}-{slug}.txt"
    try:
        done = subprocess.run(list(command), capture_output=True, text=True, check=False)
    except OSError as error:
        output, code = f"cannot run {command[0]}: {error}\n", 127
    else:
        output, code = done.stdout + done.stderr, done.returncode
    path.write_text(f"$ {' '.join(command)}\n{output}\n[exit {code}]\n", encoding="utf-8")
    sys.stdout.write(output)
    return code, path


def _print_checks(checks: Sequence[Check]) -> None:
    for check in checks:
        print(f"{check.status:<8}{check.name}  {check.detail}")


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point.

    Args:
        argv: Arguments after the program name, defaults to sys.argv.

    Returns:
        Process exit code.
    """
    args = list(sys.argv[1:] if argv is None else argv)
    command = args[0] if args else ""
    home = Path.home()
    if command == "doctor":
        checks = doctor(shutil.which, run_command, os.environ, home)
        _print_checks(checks)
        return 1 if any(c.status == "warn" for c in checks) else 0
    if command == "audit":
        project = Path(args[1]) if len(args) > 1 else Path.cwd()
        checks = audit(project, home)
        _print_checks(checks)
        return 1 if "--strict" in args and any(c.status == "warn" for c in checks) else 0
    if command == "raw":
        rest = args[1:]
        folder = raw_dir(os.environ, home)
        if rest[:1] == ["--dir"] and len(rest) >= 2:
            folder, rest = Path(rest[1]), rest[2:]
        if rest[:1] == ["--"]:
            rest = rest[1:]
        if not rest:
            print("usage: agent-tokens raw [--dir DIR] -- COMMAND...", file=sys.stderr)
            return 64
        code, path = run_raw(rest, folder)
        print(f"raw: {path}", file=sys.stderr)
        return code
    print("usage: agent-tokens doctor | audit [DIR] [--strict] | raw [--dir DIR] -- COMMAND...", file=sys.stderr)
    return 64


if __name__ == "__main__":
    sys.exit(main())
