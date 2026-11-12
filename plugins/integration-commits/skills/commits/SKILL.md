---
name: commits
description: Use when writing a commit message or PR title in a repo that enforces Conventional Commits and commitlint: format, 100-character limit, footer rules, lint commands.
---

# Commits and PR titles

Use when the repo enforces Conventional Commits / commitlint. Check the repo's own commitlint config first. It wins over this file.

Every commit message and every PR title follows Conventional Commits and must pass commitlint.
If the repo has its own commitlint config (`commitlint.config.*`, `.commitlintrc*`, or a `commitlint` key in `package.json`), that config wins.
Otherwise use these rules from `@commitlint/config-conventional`.

Format: `<type>(<scope>): <subject>`. The scope is optional. A `!` before the colon marks a breaking change.

| Part | Rule |
|---|---|
| type | Required, lower-case, one of: `build`, `chore`, `ci`, `docs`, `feat`, `fix`, `perf`, `refactor`, `revert`, `style`, `test` |
| scope | Optional, lower-case, a module or area such as `orders` or `deps`. Never the Jira key |
| subject | Required, imperative mood ("add", not "added"), starts lower-case, no full stop at the end. Not Sentence case, Start Case, PascalCase or UPPER CASE |
| header | The whole first line: at most 100 characters |
| body | Optional. Blank line before it. Each line at most 100 characters. Explain why, not what |
| footer | Optional. Blank line before it. Each line at most 100 characters |

Which type:

- `feat`: new behavior. `fix`: bug fix.
- `refactor`: no behavior change. `perf`: faster, same behavior.
- `test`: tests only. `docs`: documentation only. `style`: formatting only.
- `build`: build tooling or dependencies. `ci`: pipeline files. `chore`: everything else. `revert`: undo an earlier commit.

The Jira key goes in the footer, not the scope or the title: `Refs: PROJ-123`.
A breaking change uses `!` and a footer `BREAKING CHANGE: <what breaks>`.

Good:

```
feat(orders): add get order by id endpoint

Refs: PROJ-123
```

```
fix(orders): return 404 for unknown order id
```

Bad:

```
Added order endpoint.            no type, past tense, full stop
Feat(Orders): Add Endpoint       type, scope and subject not lower-case
feat(PROJ-123): add endpoint      scope must be lower-case, not the ticket key
```

Rules for you:

- Count the header before you commit. Over 100 characters: shorten the subject and move the detail to the body.
- One logical change per commit. A stack layer can have several commits, and all of them follow these rules.
- `gh stack add -m "<message>"` uses the message as the commit message, so it must pass too.
- A PR title is a commit header: same format, at most 100 characters. Each PR in a stack describes its own layer. Do not put the Jira key or `[2/3]` in the title, because GitHub already shows the stack. Start the PR description with `Jira: PROJ-123`. Squash merge uses the PR title as the commit message.
- Lint before you push, if commitlint is available: `npx commitlint --from origin/main --to HEAD` for commits, `echo "<title>" | npx commitlint` for a PR title. If it is not available, check by hand against the table.
- Fix a bad message with `git commit --amend` on the right layer, then `gh stack rebase` and `gh stack submit --auto`.
- Never skip commit hooks with `--no-verify`.
