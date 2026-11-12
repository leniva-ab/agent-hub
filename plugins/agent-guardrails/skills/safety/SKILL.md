---
name: safety
description: Use before any destructive git, rm or infrastructure command, and when a command was blocked by the guard hook. Lists what is never allowed and why.
---

# Safety

The `guard` hook in this plugin blocks the commands in the never-list. This skill explains the rules so you do not try them.

## Safety

- **Know where you are.** Before any write or delete, `git rev-parse --show-toplevel` and `git branch --show-current` must match your task worktree and branch. If not, stop.
- **Never, without the developer saying so this session:** `git reset --hard`, `git clean -fd`, `git checkout .` or `git restore .` outside your own worktree; `git push --force`; `git branch -D` or `git worktree remove --force` on anything you did not create; `git stash` (the stash is shared by all worktrees, so use a WIP commit); `rm -rf` with a variable, a glob or a path outside your worktree; `--no-verify`; editing hooks, CI or branch protection to get green; anything that changes shared infrastructure, cloud accounts or secrets.
- **Before deleting,** list what will go (`ls`, `git clean -n`) and delete only what you created.
- **Conflicts.** One writing agent per worktree. Run `git fetch` and `git worktree list` first. If another branch or PR touches the same files, tell the developer. Resolve a rebase conflict in the commit it belongs to. Never take one side wholesale.
- **Secrets** never go into tickets, PRs, commits, logs or the repo. If you see one, say so and stop using it.
- **Commands that cannot hang.** Use non-interactive forms. A command that opens an editor, pager or prompt is the wrong command.
