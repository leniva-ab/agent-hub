---
name: workflow
description: Use for any code change, bug fix, feature, refactor or new project in a repo that follows the team standard. Defines roles, the step flow with Superpowers skills, loops and principles.
---

# Team workflow

Project commands come from `agent-detect`, never from memory. It reads the AGENTS.md settings table first, then the Makefile, then the build files, and prints each command with its source. Use `agent-detect test` for one command. A command marked `unconfirmed` is shown to the developer once and added to AGENTS.md on a yes. `NOT FOUND` means ask. Never invent a command.

Tool versions and models come from `agent-versions` (plugin `agent-setup`). Run `agent-versions check` once at the start of a session.

## The work record

Plan, progress and evidence live in one place, never in repo files:

1. the tracker ticket (checklist, subtasks, comments) if one is given
2. otherwise the task-list tool and the PR description
3. otherwise the conversation

The repo holds only: requirements in `docs/specs/`, architecture decisions in `docs/architecture/`, code and tests. Do not create plan, notes, progress, todo or summary files. Redirect Superpowers' default `docs/superpowers/specs/` to `docs/specs/`, and never write `docs/superpowers/plans/`. Update an existing doc instead of adding one.

## Roles

| Role | Model | Does | Never does |
|---|---|---|---|
| Orchestrator | strongest | clarifies, plans, runs `subagent-driven-development`, rules on conflicts, writes the work record, pushes | writes feature code itself |
| Implementer, task reviewer, final reviewer | chosen by `subagent-driven-development` (least powerful model that fits the task, strongest for the final review) | use that skill's own prompts | push, write the work record |
| Verifier | strongest, fresh context | proves the whole result (skill `agent-core:verification`) | be the implementer or reviewer of that work |
| Researcher | mid-size | one option or candidate per agent, in parallel | recommend a winner |

- Every subagent starts fresh. Name its model on every dispatch, as Superpowers requires. Tier names map to real models in skill `agent-setup:setup`.
- If you are not on the strongest model while clarifying or planning, tell the developer.
- Subagents in parallel only when their file sets do not overlap (`dispatching-parallel-agents`).

## Flow

Use the Superpowers skill for each step. If Superpowers is not installed, do the same step by hand and tell the developer once. A skill's own process is not repeated here.

| # | Step | Skill | Who | Gate |
|---|---|---|---|---|
| 1 | Clarify | `brainstorming` (new project: in rounds, see skill `agent-greenfield:greenfield`) | Orchestrator | developer approves the spec. No code before this. |
| 2 | Plan | `writing-plans` | Orchestrator | each subtask is small and every acceptance criterion (AC) is testable |
| 3 | Isolate | `using-git-worktrees` | Orchestrator | one worktree per task, never the main checkout |
| 4 | Build | `subagent-driven-development`, which uses `test-driven-development` | the skill's implementer and reviewers | the skill's task reviews pass and its final whole-branch review is clean |
| 5 | PR comments | `receiving-code-review`. Use `requesting-code-review` too only if the work was not built with `subagent-driven-development` | Orchestrator | no open Critical or Important finding |
| 6 | Verify | `verification-before-completion`, plus skill `agent-core:verification` | Verifier (ours, independent) | skill `agent-core:verification` passes |
| 7 | Finish | `finishing-a-development-branch` | Orchestrator | evidence recorded in the work record |

Also:

- **Any bug, failing test or surprising result:** run `systematic-debugging` before you change code. A failed verification goes there too.
- **Independent work in parallel** (research per option, unrelated failures, subtasks with disjoint files): `dispatching-parallel-agents`.
- **The same mistake twice:** use `writing-skills` to turn the lesson into a skill, or fix the instruction that caused it. Do not add a paragraph here.

Checked against Superpowers 7.0.0: every skill named here exists, and the defaults below still apply. `subagent-driven-development` owns the build: its briefs, its implementer and reviewer prompts, its ledger, its fix rounds and its final review. Do not add a second set of any of them.

Overrides to Superpowers defaults (this file wins on these):

- Save specs to `docs/specs/` and decisions to `docs/architecture/adr/`. Superpowers lets a stated preference override its default paths, so tell it so.
- The plan file is scratch, because `subagent-driven-development` needs one on disk. Write it to `.superpowers/plans/<name>.md`, never to `docs/superpowers/plans/`. Make sure `.superpowers/` is ignored (`git check-ignore .superpowers`). If it is not, add it to `.git/info/exclude`, which is local. Copy the task list into the work record. The Superpowers ledger under `.superpowers/sdd/` ignores itself. Leave it alone and uncommitted.
- Only the orchestrator pushes, opens PRs and writes to the tracker.
- Finish with small PRs, one per subtask (or one commit per subtask without a git host), not one big PR.
- Done needs the independent verifier's evidence JSON from skill `agent-core:verification`. The final review in `subagent-driven-development` does not replace it.

A task of a few subtasks can use `executing-plans` instead of subagents. With a git host, open small PRs, one per subtask. Without one, leave one commit per subtask on the task branch for the developer to merge.

## Briefs

`subagent-driven-development` builds the briefs (its `task-brief` script) and has its own implementer, task-reviewer and re-review prompts. Do not write a second set. Add only what is specific to this project: the build and test commands from the project's AGENTS.md table, and a pointer to skill `agent-guardrails:safety`.

## Token economy

- Use a skill only when its description fits the task. Subagents get a brief, not this skill.
- Pass file paths and spec ids, not pasted text. Do not re-read files you just wrote.
- Run focused tests while building. Run the full suite once, in verification.
- Use quiet flags. Write long output to a scratch file and read only the failures or the tail.

## Loops

Every loop has an exit, a maximum and an escalation. Never loop without a counter. After the spec and plan are approved, execution does not wait for the developer. Rule on conflicts, record each ruling, and keep going.

| Loop | Exit | Max rounds | Then |
|---|---|---|---|
| Build: implement, task reviews, fix, final review | clean final review | as set by `subagent-driven-development` (5 fix rounds in 7.0.0, the last two on a more capable model) | the orchestrator rules and continues. It stops only for the four cases in that skill: an irreversible or destructive action, a security-sensitive action, a side effect outside the worktree (merge, push to a shared branch, publish), or a plan so broken that every path is a guess |
| Verify: verify, `systematic-debugging`, fix, new verifier | `verified` is true | 3 | stop and report the failing checks |
| Review findings: reviewer, validator, evidence | confirmed or rejected | 2 | drop as unproven |
| Clarify: brainstorm, summary, approval | developer approves | no limit | the developer decides |

The same failure twice means change the approach. Do not retry it a third time.

## Principles and style

- **Evidence, not guesses.** Every fact you rely on has a source and a date, or is marked `unknown`. A command you did not run is not a result.
- **Simplest thing that works (KISS).** Choose the simplest design that meets the stated needs. Use a pattern only to solve a named problem. Do not build for needs nobody has stated.
- **DRY means one source of knowledge.** Remove duplicated knowledge. Leave code that only looks alike until the third real use.
- **Few dependencies.** Add one only after the check in skill `agent-greenfield:dependencies`. Use the latest stable release, at least 3 days old, and no compatibility code for old versions without a named need.
- **Pick the best for the situation,** not the most familiar or the most impressive. Record the choice and the rejected options in a decision record.
- **Quality from the first commit.** The gates in skill `agent-core:verification` are enforced in CI, so quality does not depend on memory.
- **Visible state.** With several runs or projects, every run reports its state and the next human action (skill `agent-cmux:control-plane`).
- Follow the language, framework and conventions already in the repo. Ask before adding a dependency. Small commits and small PRs.
