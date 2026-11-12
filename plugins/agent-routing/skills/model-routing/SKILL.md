---
name: model-routing
description: Use before dispatching any subagent, and when the routing hook denied a spawn. Says which model to name for which kind of task, and why to choose once per task.
---

# Routing

An unpinned subagent inherits the session's model. The `agent-routing` hook denies such a spawn, so the choice is made on purpose.

## Rules

- Name `model` on every dispatch, unless the subagent's own file pins one (the hook accepts that too). Use the aliases `haiku`, `sonnet`, `opus`. The real ids are pinned in the repo's `settings.json` env.
- Choose once per task. The prompt cache is scoped to the model, so a model switch in the middle of a session makes the next turn slow and uncached. Route at dispatch, not per turn.
- If a task turns out harder than its model, stop and re-dispatch with a stronger one. Do not keep retrying on the small model.

## Which model

| Work | Model |
|---|---|
| Search, grep, reading logs and test output, formatting, summarising a known file | `haiku` |
| Implementing a well-specified task, writing tests, one-option research | `sonnet` |
| Planning, architecture, review of a hard or risky change, debugging with no leads | `opus` |

These are starting points. Whether a cheaper model passed the same task is measured with `agent-telemetry`, not assumed.

## When the hook denies a spawn

Retry the same call with `model` set. Do not set `AGENT_ROUTE_DISABLE=1` from inside the session. Types that may inherit (for example `Explore`) are listed by the developer in `AGENT_ROUTE_ALLOW_INHERIT`.

## Audit

`agent-route audit` lists every agent file it can find and the model each pins. `--strict` exits 1 if any agent inherits.

The hook matches agent files by file name, so `plugin:verifier` finds `verifier.md`. It looks in the project's `.claude/agents`, the user's `~/.claude/agents`, folders in `AGENT_ROUTE_AGENT_DIRS` and installed plugins under `~/.claude/plugins/cache`. If a pinned agent is blocked anyway, pass `model` explicitly.
