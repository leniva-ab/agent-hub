"""Model routing guard and audit for subagent dispatch.

Two commands:

``hook``
    PreToolUse hook for the ``Agent`` tool. It denies a spawn that would inherit the session model:
    no ``model`` in the call, and the named subagent does not pin one in its frontmatter. Exit code 2
    blocks the call and sends the reason on stderr to the agent. Exit code 0 lets the call run.

``audit``
    Lists the subagent files it can find and the model each one pins.

Standard library only, so it starts fast and needs no install.

Switches (set outside the agent session):
    ``AGENT_ROUTE_DISABLE=1``
        Turns the hook off.
    ``AGENT_ROUTE_ALLOW_INHERIT=Explore,Plan``
        Subagent types that may inherit the session model.
    ``AGENT_ROUTE_AGENT_DIRS``
        Extra agent folders, separated by ``os.pathsep``.
"""

from __future__ import annotations

import json
import os
import re
import sys
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

DISABLE_ENV = "AGENT_ROUTE_DISABLE"
ALLOW_INHERIT_ENV = "AGENT_ROUTE_ALLOW_INHERIT"
EXTRA_DIRS_ENV = "AGENT_ROUTE_AGENT_DIRS"
AGENT_TOOLS = frozenset({"Agent", "Task"})
MODEL_LINE = re.compile(r"^model:\s*(\S+)\s*$", re.MULTILINE)


@dataclass(frozen=True, slots=True)
class Verdict:
    """Outcome of checking one dispatch.

    Attributes:
        blocked: True when the spawn must not run.
        reason: Message for the agent, empty when allowed.
    """

    blocked: bool
    reason: str = ""


ALLOWED = Verdict(blocked=False)


def pinned_model(text: str) -> str | None:
    """Return the model pinned in an agent file's frontmatter.

    Args:
        text: The whole agent file.

    Returns:
        The model alias or id, or None when absent or set to ``inherit``.
    """
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    if end == -1:
        return None
    match = MODEL_LINE.search(text[3:end])
    if match is None:
        return None
    value = match.group(1).strip("\"'")
    return None if value == "inherit" else value


def _extra_dirs(environ: Mapping[str, str]) -> list[Path]:
    raw = environ.get(EXTRA_DIRS_ENV, "")
    return [Path(part) for part in raw.split(os.pathsep) if part]


def _agent_dirs(cwd: str, home: Path, environ: Mapping[str, str]) -> list[Path]:
    dirs = _extra_dirs(environ)
    if cwd:
        dirs.append(Path(cwd) / ".claude" / "agents")
    dirs.append(home / ".claude" / "agents")
    return dirs


def agent_files(cwd: str, home: Path, environ: Mapping[str, str], name: str = "*") -> Iterator[Path]:
    """Yield agent files from the project, user, extra and installed-plugin folders.

    Args:
        cwd: Working directory of the agent session.
        home: Home directory, where user agents and the installed plugin cache live.
        environ: Environment, read for extra folders.
        name: File stem to match, or ``*`` for all.

    Yields:
        Paths of agent markdown files, in lookup order.
    """
    for folder in _agent_dirs(cwd, home, environ):
        if folder.is_dir():
            yield from sorted(folder.glob(f"{name}.md"))
    cache = home / ".claude" / "plugins" / "cache"
    if cache.is_dir():
        yield from sorted(cache.rglob(f"agents/{name}.md"))


def find_pinned(subagent_type: str, cwd: str, home: Path, environ: Mapping[str, str]) -> str | None:
    """Find a model pinned by the named subagent.

    The lookup matches on the file name, so ``plugin:verifier`` finds ``verifier.md``.

    Args:
        subagent_type: Value of the ``subagent_type`` argument.
        cwd: Working directory of the agent session.
        home: Home directory.
        environ: Environment, read for extra folders.

    Returns:
        The pinned model, or None when no matching file pins one.
    """
    name = subagent_type.rsplit(":", 1)[-1]
    if not name:
        return None
    for path in agent_files(cwd, home, environ, name):
        model = pinned_model(path.read_text(encoding="utf-8", errors="replace"))
        if model is not None:
            return model
    return None


def check_dispatch(event: Mapping[str, object], environ: Mapping[str, str], home: Path) -> Verdict:
    """Decide whether one subagent spawn may run.

    Args:
        event: The parsed PreToolUse event.
        environ: Environment, read for the allow-list and extra folders.
        home: Home directory.

    Returns:
        A Verdict that is blocked when the spawn would inherit the session model.
    """
    if event.get("tool_name") not in AGENT_TOOLS:
        return ALLOWED
    tool_input = event.get("tool_input")
    args = tool_input if isinstance(tool_input, dict) else {}
    model = str(args.get("model") or "")
    if model and model != "inherit":
        return ALLOWED
    subagent_type = str(args.get("subagent_type") or "")
    allowed = {item.strip() for item in environ.get(ALLOW_INHERIT_ENV, "").split(",") if item.strip()}
    if subagent_type in allowed:
        return ALLOWED
    if find_pinned(subagent_type, str(event.get("cwd") or ""), home, environ) is not None:
        return ALLOWED
    label = subagent_type or "general-purpose"
    return Verdict(
        blocked=True,
        reason=(
            f"Subagent '{label}' would inherit the session model. "
            "Retry the same call with an explicit model: haiku for search and log reading, "
            "sonnet for implementation and research, opus for planning and review of hard changes. "
            "See skill agent-routing:model-routing."
        ),
    )


def run_hook(stdin_text: str, environ: Mapping[str, str] | None = None, home: Path | None = None) -> int:
    """Run the PreToolUse hook.

    Args:
        stdin_text: The hook event as JSON text.
        environ: Environment, defaults to os.environ.
        home: Home directory, defaults to the user's home.

    Returns:
        Process exit code: 2 to block, 0 to allow.
    """
    env = os.environ if environ is None else environ
    if env.get(DISABLE_ENV) == "1":
        return 0
    try:
        event = json.loads(stdin_text)
    except json.JSONDecodeError:
        return 0
    if not isinstance(event, dict):
        return 0
    verdict = check_dispatch(event, env, Path.home() if home is None else home)
    if verdict.blocked:
        print(f"Blocked by agent-routing: {verdict.reason}", file=sys.stderr)
        return 2
    return 0


def run_audit(
    strict: bool,
    cwd: str,
    environ: Mapping[str, str] | None = None,
    home: Path | None = None,
) -> int:
    """Print every agent file and the model it pins.

    Args:
        strict: When True, exit 1 if any agent inherits the session model.
        cwd: Working directory whose ``.claude/agents`` folder is included.
        environ: Environment, defaults to os.environ.
        home: Home directory, defaults to the user's home.

    Returns:
        Process exit code.
    """
    env = os.environ if environ is None else environ
    root = Path.home() if home is None else home
    unpinned = 0
    for path in agent_files(cwd, root, env):
        model = pinned_model(path.read_text(encoding="utf-8", errors="replace"))
        if model is None:
            unpinned += 1
        print(f"{path.stem}\t{model or '(inherits)'}\t{path}")
    return 1 if strict and unpinned else 0


def main(argv: Sequence[str] | None = None, stdin_text: str | None = None) -> int:
    """Entry point.

    Args:
        argv: Arguments after the program name, defaults to sys.argv.
        stdin_text: Hook event text, defaults to reading stdin for ``hook``.

    Returns:
        Process exit code.
    """
    args = list(sys.argv[1:] if argv is None else argv)
    command = args[0] if args else ""
    if command == "hook":
        return run_hook(sys.stdin.read() if stdin_text is None else stdin_text)
    if command == "audit":
        return run_audit(strict="--strict" in args[1:], cwd=str(Path.cwd()))
    print("usage: agent-route hook | audit [--strict]", file=sys.stderr)
    return 64


if __name__ == "__main__":
    sys.exit(main())
