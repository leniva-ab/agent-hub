---
name: promote-lesson
description: Use when deciding where a lesson should live (user CLAUDE.md, project CLAUDE.md, path rule, skill, hook or permission deny) so the agent reliably follows it.
---

# Promote

A lesson only helps if it is loaded when it matters, and if it is enforced when it must be. Pick the cheapest home that does the job.

| The lesson is... | Home | Target for `agent-learn promote` |
|---|---|---|
| A personal habit that holds in every repo | User `~/.claude/CLAUDE.md` | `user-claude-md` |
| A rule for this repo that applies everywhere in it | Project `CLAUDE.md` or `AGENTS.md`, short | `project-claude-md` |
| A rule for some files only (a language, a folder) | `.claude/rules/<name>.md` with `paths:` in its frontmatter | `rule` |
| A procedure with steps, needed only for some tasks | A skill (`skills/<name>/SKILL.md`), shared through a plugin when it applies to many repos | `skill` |
| Something that must never or always happen, mechanically | A hook, or a permission deny rule | `hook` or `permission-deny` |

## Why this order

- CLAUDE.md and rules are advice. The model usually follows them but can miss them. A hook is code, so it always runs. If a lesson came back after being written in CLAUDE.md, move it to a hook or deny rule if it can be checked mechanically.
- Everything in user and project CLAUDE.md, auto memory and rules without `paths:` loads at every session start, and costs tokens on every message. Rules with `paths:` and skills load only when relevant. Keep CLAUDE.md under 200 lines and move the rest out.
- Imports with `@` do not save tokens. Moving text into a path rule or a skill does.
- A lesson for many repos belongs in a plugin skill, not copied into each repo.

## Write it well

- State what to do, then the reason in a few words. "Run `ruff check` before committing: CI fails on lint."
- Name exact commands, paths and tools.
- If it can be checked by a command, say which command.
- Do not duplicate a line that is already there. Edit the existing line.
