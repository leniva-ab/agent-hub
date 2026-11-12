---
name: github-stacks
description: Use when the git host is GitHub and work is delivered as stacked PRs with gh stack: one worktree and one stack per task, agent-safe commands, exit codes.
---

# GitHub worktrees and stacked PRs

Use when the git host is GitHub and the team uses stacked PRs. Without `gh stack`, use plain small PRs, one per subtask, each based on the previous branch.

One task = one worktree = one stack of small PRs.

1. Start every task in its own git worktree via `using-git-worktrees`. Superpowers puts it in `.worktrees/` unless told otherwise. Make sure that folder is git-ignored. Never work in the main checkout.
2. In the worktree run `gh stack init <first-branch>`, then `gh stack add <branch-name>` for each next layer (`-Am "message"` stages and commits in the same step, see `gh stack add --help`). Branch names are used exactly as given, so name them yourself, for example `PROJ-123-1-api-layer`. Without a name, `-m` generates one like `03-24-add_login`. One subtask = one layer = one small PR on top of the previous one.
3. Each layer builds and passes its own tests. Commit per layer.
4. `gh stack submit --auto` pushes all branches and creates or updates the stacked PRs without opening the interactive editor. New PRs start as drafts. Add `--open` to mark them ready for review, only after the layer's checks and self-review pass.
5. Read the stack with `gh stack view --json` (or `--short`). Never run bare `gh stack view`, `gh stack submit`, `gh stack modify` or `gh stack switch`: they open interactive screens and will hang.
6. Fix review comments on the right layer: `gh stack up` / `gh stack down` to move, fix, then `gh stack rebase` and `gh stack submit`. Do not force-push by hand.
7. Merge only when the developer says so. PRs must be open and not drafts, and branch protection still applies. `gh stack merge --yes` lands the stack up to the chosen PR in one all-or-nothing step (a merge queue, if the repo has one, takes over). Then run `gh stack sync`.
8. When the ticket is Done, clean up with `finishing-a-development-branch`. Never use `git worktree remove --force`. If removal is refused because of uncommitted or untracked files, stop, name the files and ask.

PR titles follow skill `integration-commits:commits` if the repo uses it. Link the ticket in every PR description and post the PR links in the work record (ticket comment or PR description).

If `gh stack` exits with code 9 (stacked PRs not enabled), stop and tell the developer. Do not fall back to one huge PR. Exit code 3 is a rebase conflict: resolve it, then run `gh stack rebase --continue`.
Run `gh stack --help` if unsure. Do not guess flags.
