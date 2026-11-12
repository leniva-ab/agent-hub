# Agent hub

Decoupled plugins for coding agents: skills, agents, hooks and settings in one place. Each plugin does one job, has its own version, and can be enabled or left out per repo. Today it ships the Claude Code layout.

| Plugin | Job |
|---|---|
| `team-standard` | The standard bundle: core, guardrails, setup and Superpowers. |
| `agent-core` | Workflow, verification, and the verifier and researcher subagents. |
| `agent-guardrails` | Blocks destructive git, `rm` and infrastructure commands. |
| `agent-setup` | Version floors and a quiet session-start check. |
| `agent-review` | Multi-agent PR review. Opt in. |
| `agent-greenfield` | New-project process and dependency choice. Opt in. |
| `agent-cmux` | cmux conventions and the multi-project control plane. Opt in. |
| `agent-routing` | Denies subagent spawns that would inherit the session model. Opt in. |
| `agent-tokens` | Token hygiene: doctor, context audit, raw-output keeper. Opt in. |
| `agent-telemetry` | Local OpenTelemetry, tagged by config version, with a report. Opt in. |
| `agent-learning` | Correction log and repeat-rate metric for a learning loop. Opt in. |
| `integration-jira`, `integration-github`, `integration-commits` | Tracker, stacked PRs, commit rules. Enable what the repo uses. |

Details and token costs: [docs/plugins.md](docs/plugins.md).

## Use it in a repo

1. Copy `examples/project/.claude/settings.json` into the repo and set a release tag. Install by hand with `/plugin marketplace add leniva-ab/agent-hub`. Everyone who opens the repo is offered the same marketplace and the same plugin set.
2. Copy `examples/project/AGENTS.md`, fill in the settings table, and add repo-specific rules. Keep it short. Plugins cannot ship an always-loaded `CLAUDE.md` or `AGENTS.md`, so this file stays in the repo.

## Docs

| Read | For |
|---|---|
| [docs/plugins.md](docs/plugins.md) | What each plugin gives you, and its always-on token cost |
| [docs/executables.md](docs/executables.md) | Executables that plugins put on PATH |
| [docs/versions.md](docs/versions.md) | Versioning, dependencies, pinning a repo to a tag |
| [docs/releases.md](docs/releases.md) | release-please, the release app, rulesets |
| [docs/evals.md](docs/evals.md) | Testing what a plugin makes Claude do, with and without it |
| [docs/measuring.md](docs/measuring.md) | Comparing ways of working by tokens and cost |
| [docs/naming.md](docs/naming.md) | Naming rules for plugins, commands, skills, env vars |
| [docs/other-tools.md](docs/other-tools.md) | Copilot, Codex, opencode and Cursor |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Set up, tests, code style, commits, adding a plugin |
| [LICENSE](LICENSE) | MIT, copyright LeNivA AB |
