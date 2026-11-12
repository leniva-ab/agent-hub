# Plugins

Each plugin does one job, has its own version, and can be enabled or left out per repo. The short list is in the [README](../README.md).

| Plugin | What it gives you | Always-on cost* |
|---|---|---|
| `team-standard` | Bundle only. Pulls in `agent-core`, `agent-guardrails`, `agent-setup` and `superpowers`. | none of its own |
| `agent-core` | Skills `workflow` and `verification`. Subagents `verifier`, `researcher`, and an opt-in `orchestrator`. The build itself is Superpowers' `subagent-driven-development`. | ~250 tokens |
| `agent-guardrails` | A hook that blocks destructive git, `rm` and infrastructure commands. Skill `safety`. | ~43 tokens |
| `agent-setup` | A session-start hook that speaks only when a tool is below its version floor. Skill `setup` with install steps. | ~48 tokens |
| `agent-review` | Multi-agent PR review: nine category reviewers, validator, deduper, summarizer. Opt in. | ~886 tokens |
| `agent-greenfield` | New-project process and evidence-based dependency choice. Opt in. | ~126 tokens |
| `agent-cmux` | cmux conventions and the multi-project control plane. Opt in. | ~90 tokens |
| `agent-routing` | A hook that denies subagent spawns that would inherit the session model. Skill `model-routing`. Opt in. | ~47 tokens |
| `agent-tokens` | Token hygiene: doctor for `tokf` and `sem`, context audit, raw-output keeper. Skill `token-hygiene`. Opt in. | ~60 tokens |
| `agent-telemetry` | Local OpenTelemetry for Claude Code, tagged by config version, with a report. Skill `telemetry`. Opt in. | ~58 tokens |
| `agent-learning` | Correction log, promotion to lasting places, repeat-rate metric. Skills `retro` and `promote-lesson`. Opt in. | ~96 tokens |
| `integration-jira`, `integration-github`, `integration-commits` | Tracker, stacked PRs, commit rules. Enable what the repo uses. | ~45 to ~48 tokens each |

\* Projected by `claude plugin details` on Claude Code 2.1.322, 2026-11-12. These are estimates and may differ from actual usage. Skill and agent bodies cost tokens only when they are used. `team-standard` is a bundle, so its cost is the sum of the plugins it pulls in.

Executables that plugins put on PATH are in [executables.md](executables.md).
