---
name: setup
description: Use when installing or upgrading git, gh, gh stack, Superpowers or the agent CLIs, choosing models per tool, or when the session-start hook reported a tool below its floor.
---

# Setup

All versions, models and cooldown settings live in one file, `data/versions.json`. Never look them up or recall them. Run the command.

| Need | Command |
|---|---|
| Table of installed versus floor and target | `agent-versions show` |
| Exit 1 and the fix when a tool is below its floor | `agent-versions check` |
| Model tier to alias and id | `agent-versions models` |
| Cooldown setting for a package manager or bot | `agent-versions cooldown <name>` |

- Below the **floor**: stop. Give the developer the `Fix:` line `agent-versions check` printed. Do not continue.
- Below the **target** but above the floor: tell the developer, offer the fix, continue only if they say so.
- `unreadable` means the tool exists but its output did not parse. Say so. Do not treat it as ok.
- `missing` is fine for optional tools (copilot, gh-stack) unless the work needs them. `gh stack` is needed only for stacked PRs.

To change a version, edit `data/versions.json` from the `source` URL in its entry and set `checked`. Change a floor only for a real reason. The `tests/` in this plugin check the file's shape.

## Superpowers

Superpowers (https://github.com/obra/superpowers) is installed once per tool. Its floor and target are in `versions.json` under `plugins`.

- Claude Code: `/plugin install superpowers@claude-plugins-official`
- Cursor: `/add-plugin superpowers`. The Cursor marketplace copy has lagged upstream before, so check its version.
- Copilot CLI: `copilot plugin marketplace add obra/superpowers-marketplace`, then `copilot plugin install superpowers@superpowers-marketplace`

## gh stack

`gh stack` is an extension, not core `gh` (checked 2026-10-27). `agent-versions show` reports `gh-stack` as `missing` only when `gh` itself is not installed, and as `unreadable` when `gh` exists but its extension list has no parsable stack version. If `gh stack --help` works while it says `unreadable`, `gh stack` has been built in: skip the install. If `gh stack` exits with code 9, stacked PRs are not enabled for this repo or host: stop and tell the developer.

## Models per tool

Tier names in AGENTS.md map to the ids from `agent-versions models`.

- Claude Code: main agent on the strongest tier, subagents on mid. In `.claude/settings.json`, `"model": "opus"` and an `env` block pinning `ANTHROPIC_DEFAULT_OPUS_MODEL` and `ANTHROPIC_DEFAULT_SONNET_MODEL` to the ids printed. Alternative: `"model": "opusplan"` (strongest in Plan Mode, mid for execution).
- Copilot: set `model` in the custom agent file, or use the model picker.
- Cursor: pick the strongest model for brainstorming and planning. A `model:` in `.cursor/agents/*.md` can be silently ignored, so check which model the subagent really ran on.

Before the first real task, ask one subagent to state its model ID, so you know the routing works.
