"""Tests for the destructive-command guard."""

from __future__ import annotations

import pytest

import guard


@pytest.mark.parametrize(
    "command",
    [
        "git reset --hard HEAD~1",
        "git -C /work/repo reset --hard",
        "git clean -fd",
        "git clean -n -f",
        "git checkout .",
        "git restore .",
        "git push --force origin main",
        "git push -f",
        "git push -uf origin x",
        "git branch -D feature",
        "git worktree remove --force ../wt",
        "git stash",
        "git stash pop",
        "git commit -n -m x",
        "git commit --no-verify -m x",
        "git push --no-verify",
        "cd x && git reset --hard",
        "echo hi; git stash drop",
        "FOO=1 git reset --hard",
        "rm -rf *",
        "rm -rf $DIR",
        "rm -rf ~/x",
        "rm -rf ../other",
        "rm -rf /etc",
        "rm -r .",
        "terraform apply",
        "terraform destroy -auto-approve",
        "kubectl delete pod x",
        "helm uninstall app",
        "aws s3 rm s3://b --recursive",
        "aws ec2 terminate-instances --instance-ids i-1",
    ],
)
def test_blocks_destructive(command: str) -> None:
    assert guard.check_command(command, "/work/repo").blocked, command


@pytest.mark.parametrize(
    "command",
    [
        "git status",
        "git diff --stat",
        "git log --oneline -5",
        "git push --force-with-lease origin x",
        "git push origin x",
        "git stash list",
        "git stash show",
        "git branch -d merged-branch",
        "git checkout feature-x",
        "git restore src/a.py",
        "git clean -n",
        "git commit -m 'fix: x'",
        "git worktree add ../wt -b x",
        "git worktree remove ../wt",
        "rm file.txt",
        "rm -rf build",
        "rm -rf /work/repo/build",
        "terraform plan",
        "kubectl get pods",
        "aws s3 ls",
        "gh stack submit --auto",
        "echo 'git reset --hard'",
        "ls | grep stash",
    ],
)
def test_allows_safe(command: str) -> None:
    assert not guard.check_command(command, "/work/repo").blocked, command


def test_main_blocks_with_exit_code_2(event, capsys) -> None:
    assert guard.main(event("git reset --hard"), {}) == 2
    assert "Blocked by agent-guardrails" in capsys.readouterr().err


def test_main_allows_other_tools(event) -> None:
    assert guard.main(event("git reset --hard", tool="Read"), {}) == 0


def test_main_disabled_by_env(event) -> None:
    assert guard.main(event("git reset --hard"), {"AGENT_GUARD_DISABLE": "1"}) == 0


def test_main_ignores_bad_json() -> None:
    assert guard.main("not json", {}) == 0
