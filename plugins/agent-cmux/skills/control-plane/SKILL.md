---
name: control-plane
description: Use when several agent runs or projects are active: run identity, state files, one workspace per run, status vocabulary and colours, the overview table, and limits that keep it followable.
---

# Control plane: many projects, many agents, one place to look

Use when more than one agent run is active, or when you run agents in cmux for several projects. Read skill `agent-cmux:cmux` first for the cmux rules.

The goal is that a human can switch between projects without having to remember anything. Every run says what it is, what state it is in, and what the human must do next.

## 1. Identity

- Each project has one short lowercase code, 2 to 5 characters (`ord`, `bil`). Set `AGENT_PROJECT=<code>` in every surface of that project. Set `AGENT_RUN_ID=<project>-<kind>-<ref>-<yyyymmdd-hhmm>` for every run.
- Before any write, check that `AGENT_PROJECT` matches the project of the repo you are in. If not, stop. This adds to the "know where you are" rule in skill `agent-guardrails:safety`.
- Run kinds: `review`, `build`, `verify`, `research`.

## 2. State is a file. cmux shows it.

Each run has a directory outside the repo: `${AGENT_RUNS_DIR:-$HOME/.agent-runs}/<project>/<run-id>/`. Nothing in it is committed.

```
state.json       the run's state (schema: ${CLAUDE_PLUGIN_ROOT}/schemas/state.json)
context.md       context pack
findings/        one JSON per reviewer
verdicts.json    validator output
merged.json      after dedupe
summary.md       text to post
log.txt          one line per event, timestamped
```

- Only the orchestrator writes `state.json`, and only through `agent-state`:
  - `agent-state init --project ord --kind review --ref PR-231` creates the run and prints the run id. It refuses when `AGENT_PROJECT` differs.
  - `agent-state set <run-id> --state running --stage "validate 2/3" --round 2 --progress 0.5 --next "none" --agent security=running`. One call writes the file atomically, appends `log.txt`, and updates the cmux sidebar (status, progress, log, notify) when `CMUX_WORKSPACE_ID` is set or `--workspace` is given.
  - `agent-state show <run-id>` prints the state.
- The sidebar is a projection of `state.json`. A cmux failure never fails the call. If they ever disagree, the file is right. Do not call `cmux set-status` by hand for these keys.
- Agents never delete run directories. Clean-up is a human action, with a dry run first.

## 3. Layout: always the same

One cmux window per project, named after the project. One workspace per run, named `<code> · <kind> <ref>`, for example `ord · review PR-231`. The state is not in the name, because it changes. It is in the status.

Every run workspace has the same shape, so the eye finds things without thinking:

| Place | Content |
|---|---|
| Large left pane | the orchestrator, interactive |
| Top right | stage board: a command that re-prints `state.json` as a table of agents and their states every few seconds |
| Bottom right | browser on the PR, ticket or app under test |
| Tabs in an "agents" pane | one surface per agent, in stage order: reviewers, validator, deduper, summarizer |

Each agent surface prints a one-line banner first: `<project> | <run-id> | <role> | <model>`. A surface title from the CLI is not documented, so the banner carries the identity.

One extra window, `ctl`, holds the project overview (section 5).

## 4. Status vocabulary

Use these keys and values everywhere. `cmux set-status <key> "<value>" --workspace <id> --color <hex> [--icon <name>]`.

| `state` value | Meaning | Colour | Notifies the human |
|---|---|---|---|
| `queued` | waiting for a slot | `#8e8e93` | no |
| `running` | agents are working | `#0a84ff` | no |
| `waiting_human` | needs a decision or an approval | `#ff9f0a` | yes |
| `blocked` | cannot go on without input | `#ff453a` | yes |
| `failed` | gave up after the loop limits | `#ff453a` | yes |
| `done` | finished, results waiting to be read | `#30d158` | no |
| `cancelled` | stopped by the human | `#8e8e93` | no |

Always set these three keys on the workspace:

- `state`: one of the values above.
- `stage`: the current step and round, for example `validate 2/3`.
- `next`: what the human must do, in one sentence, or `none`. Example: `approve 7 comments in the agents pane`.

Also use `cmux set-progress <0..1> --workspace <id> --label "<stage>"`, and `cmux log --workspace <id> --level info -- "<event>"` for the activity trail. Notify with `cmux notify --title "<code> <kind> <ref>" --body "<next>"` only for `waiting_human`, `blocked` and `failed`. Colour is never the only signal, so the text always says the state too. Icon names come from cmux. The documented example uses `hammer`, so check the `cmux-workspace` skill before choosing others.

## 5. The overview

The `ctl` window runs one command, `agent-ctl status`, which reads every `state.json` under `AGENT_RUNS_DIR` and prints one table, most urgent first:

```
PROJECT  RUN                 STATE          STAGE        AGE   NEXT
ord      review PR-231       waiting_human  approve      12m   approve 7 comments in the agents pane
bil      build PROJ-88       running        build 3/5    41m   none
inv      verify PROJ-12      blocked        e2e          1h    start the staging database
```

Order: `waiting_human`, `blocked`, `failed`, `running`, `queued`, `done`. Ties by age. This is the single place to look when you come back, and it answers "what are they doing, what is done, what do I do next". Options: `--project <code>`, `--hide-done`, `--json`.

## 6. Resume card

When the developer enters a workspace, the orchestrator pane shows, without being asked: the run id, the state, the last ten lines of `log.txt`, and `next`. The orchestrator re-prints it whenever the developer says "status".

## 7. Limits that keep it followable

- At most 3 active runs per project and 8 in total, by default. `AGENT_MAX_RUNS_PER_PROJECT` and `AGENT_MAX_RUNS_TOTAL` change them. More than that stay `queued`.
- A project never reads another project's run directory or state.
- Agents close only the workspaces and surfaces they created. A finished run's workspace stays open until the human closes it, so the results can be read.
- A reviewer agent is read-only. Tool allowlists enforce it. The prompt does not.

## 8. What is not documented in cmux

Checked on 2026-11-10 against the cmux docs and command reference. Handle by hand or test first:

- Creating a window from the CLI. Create the project windows once by hand, then pass `--window <id>`.
- Setting a surface title or a workspace tab colour from the CLI. A request for tab colour is open upstream.
- A description field on a workspace. Use the `next` status instead.
- The output format of `cmux list-workspaces --json`. Do not build on it. Use the state files.
