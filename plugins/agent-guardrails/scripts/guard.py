"""PreToolUse hook that blocks destructive Bash commands.

Reads the hook event as JSON on stdin. Exit code 2 blocks the call and sends the
reason on stderr to the agent. Exit code 0 lets the normal permission flow run.
Standard library only, so it starts fast and needs no install.

Set ``AGENT_GUARD_DISABLE=1`` outside the agent session to switch it off.
"""

from __future__ import annotations

import json
import os
import re
import shlex
import sys
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

DISABLE_ENV = "AGENT_GUARD_DISABLE"
SEGMENT_SPLIT = re.compile(r"\|\||&&|;|\||\n")
GIT_OPTS_WITH_VALUE = {"-C", "-c", "--git-dir", "--work-tree", "--namespace"}


@dataclass(frozen=True, slots=True)
class Verdict:
    """Outcome of checking one command.

    Attributes:
        blocked: True when the command must not run.
        reason: Message for the agent, empty when allowed.
    """

    blocked: bool
    reason: str = ""


ALLOWED = Verdict(blocked=False)


def _deny(reason: str) -> Verdict:
    return Verdict(blocked=True, reason=reason)


def _short_flags(args: Iterable[str]) -> set[str]:
    """Return every single-letter flag found in bundled short options."""
    letters: set[str] = set()
    for arg in args:
        if arg.startswith("-") and not arg.startswith("--") and len(arg) > 1:
            letters.update(arg[1:])
    return letters


def _split_git(tokens: list[str]) -> tuple[str, list[str]]:
    """Return the git subcommand and its arguments, skipping global options."""
    index = 1
    while index < len(tokens):
        token = tokens[index]
        if token in GIT_OPTS_WITH_VALUE:
            index += 2
        elif token.startswith("-"):
            index += 1
        else:
            return token, tokens[index + 1 :]
    return "", []


def _check_git(tokens: list[str]) -> Verdict:
    sub, args = _split_git(tokens)
    shorts = _short_flags(args)
    if "--no-verify" in args or (sub == "commit" and "n" in shorts):
        return _deny("Skipping hooks with --no-verify is not allowed. Fix the cause instead.")
    if sub == "reset" and "--hard" in args:
        return _deny("git reset --hard can destroy work. Use a normal commit or ask the developer.")
    if sub == "clean" and ("--force" in args or "f" in shorts):
        return _deny("git clean with force deletes untracked files. Dry-run with git clean -n and ask the developer.")
    if sub in {"checkout", "restore"} and any(a in {".", ":/"} for a in args):
        return _deny(f"git {sub} . discards all local changes. Name the exact files, or ask the developer.")
    if sub == "push":
        plain_force = "--force" in args or "f" in shorts
        if plain_force:
            return _deny("Plain force push is not allowed. Use gh stack rebase and gh stack submit --auto, or ask.")
    if sub == "branch" and ("-D" in args or ("--delete" in args and "--force" in args)):
        return _deny("Deleting a branch with -D is not allowed unless you created it and the developer agrees.")
    if sub == "worktree" and args[:1] == ["remove"] and ("--force" in args or "f" in shorts):
        return _deny("git worktree remove --force can lose work. Remove only your own clean worktree.")
    if sub == "stash" and (not args or args[0] not in {"list", "show"}):
        return _deny("git stash is shared by all worktrees. Make a WIP commit on your own layer instead.")
    return ALLOWED


def _check_rm(tokens: list[str], cwd: str) -> Verdict:
    args = tokens[1:]
    flags = {a for a in args if a.startswith("-")}
    shorts = _short_flags(flags)
    recursive = "r" in shorts or "R" in shorts or "--recursive" in flags
    if not recursive:
        return ALLOWED
    targets = [a for a in args if not a.startswith("-")]
    cwd_real = Path(cwd).resolve() if cwd else None
    for target in targets:
        if any(ch in target for ch in "*$`") or target.startswith("~") or ".." in target.split("/"):
            return _deny("rm -r with a glob, variable, home or parent path is not allowed. List the exact paths first.")
        if target.startswith("/") and (cwd_real is None or not Path(target).resolve().is_relative_to(cwd_real)):
            return _deny("rm -r outside the working tree is not allowed.")
        if target in {".", "./"}:
            return _deny("rm -r on the current directory is not allowed.")
    return ALLOWED


INFRA_RULES: tuple[tuple[tuple[str, ...], str], ...] = (
    (("terraform", "apply"), "terraform apply"),
    (("terraform", "destroy"), "terraform destroy"),
    (("kubectl", "delete"), "kubectl delete"),
    (("helm", "uninstall"), "helm uninstall"),
    (("aws", "s3", "rm"), "aws s3 rm"),
)


def _check_infra(tokens: list[str]) -> Verdict:
    for prefix, label in INFRA_RULES:
        if tuple(tokens[: len(prefix)]) == prefix:
            return _deny(
                f"{label} changes shared infrastructure. Write the command in the work record and ask the developer."
            )
    if tokens[:1] == ["aws"] and any(t.startswith(("delete-", "terminate-")) for t in tokens[1:4]):
        return _deny("Deleting or terminating cloud resources is not allowed. Ask the developer.")
    return ALLOWED


def check_command(command: str, cwd: str = "") -> Verdict:
    """Check a whole shell command line.

    Args:
        command: The Bash command the agent wants to run.
        cwd: Working directory of the agent, used for the rm path rule.

    Returns:
        A Verdict that is blocked when any segment breaks a rule.
    """
    for segment in SEGMENT_SPLIT.split(command):
        try:
            tokens = shlex.split(segment)
        except ValueError:
            continue
        while tokens and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*=.*", tokens[0]):
            tokens = tokens[1:]
        if not tokens:
            continue
        head = Path(tokens[0]).name
        if head == "git":
            verdict = _check_git(tokens)
        elif head == "rm":
            verdict = _check_rm(tokens, cwd)
        else:
            verdict = _check_infra([head, *tokens[1:]])
        if verdict.blocked:
            return verdict
    return ALLOWED


def main(stdin_text: str, environ: dict[str, str] | None = None) -> int:
    """Run the hook.

    Args:
        stdin_text: The hook event as JSON text.
        environ: Environment, defaults to os.environ.

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
    if event.get("tool_name") != "Bash":
        return 0
    command = str(event.get("tool_input", {}).get("command", ""))
    verdict = check_command(command, str(event.get("cwd", "")))
    if verdict.blocked:
        print(f"Blocked by agent-guardrails: {verdict.reason}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.stdin.read()))
