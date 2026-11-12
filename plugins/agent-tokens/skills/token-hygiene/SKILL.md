---
name: token-hygiene
description: Use when a session feels expensive or slow, before long unattended runs, and when choosing how to read big output or diffs. Habits that keep context small and the prompt cache warm, plus the agent-tokens commands.
---

# Tokens

Cost grows with context size, and the prompt cache only helps while the start of the request stays the same. These habits come from the Claude Code cost and prompt-caching docs. Savings figures from tool vendors are not repeated here: measure with `agent-telemetry`.

## Keep context small

- `/clear` between unrelated tasks. `/rename` first if you will come back.
- `/compact <what to keep>` at a phase boundary, for example `/compact keep failing test output and the changed files`. A "Compact instructions" heading in CLAUDE.md sets the default.
- Compact or clear before a long idle. The cache expires after idle time, so the next turn pays to rebuild it.
- Name exact files and symbols in prompts. A vague prompt triggers repo-wide reads.
- Put noisy exploration in a subagent, so only its answer returns to the main context.
- Read big output through a filter: `tail`, `head`, `grep`, or a command with a quiet flag. Do not paste whole logs.

## Keep the cache warm

- The match is exact. A change anywhere in the start of the request recomputes everything after it.
- Do not switch models mid-session (see `agent-routing:model-routing`), and do not add or remove MCP servers mid-session.
- Do not put timestamps or other changing text in CLAUDE.md or in skills that load early.
- `/usage` shows the cache hit ratio and miss causes.

## Keep tool definitions out

- MCP tool definitions are deferred by default, so only names are in context until a tool is used. Do not set `ENABLE_TOOL_SEARCH=false`.
- Prefer a CLI (`gh`, `aws`, `gcloud`) over an MCP server when both exist. Turn off servers the task does not use. `/context` shows what takes space.

## Thinking

Thinking tokens bill as output. On current models `MAX_THINKING_TOKENS` is ignored, and `/effort` steers thinking. Lower it for routine work and raise it for hard problems. Treat it as a modest lever and check the result with `agent-telemetry`.

## Executables

| Command | Use |
|---|---|
| `agent-tokens doctor` | Is `tokf` or `sem` installed and the right program? Is tool deferral on? |
| `agent-tokens audit [DIR] [--strict]` | CLAUDE.md files over 200 lines, and rules files with no `paths:` scope that load every session. |
| `agent-tokens raw -- <command>` | Run a command, show its output, and keep the full output in a file. Prints `raw: <path>` on stderr. |

## Filter tools (optional, not enabled here)

`tokf` filters Bash output and `sem` gives entity-level diffs. This plugin installs no hook for either, because the interaction with other hooks is not verified.

- Bash filters change only Bash output. Read, Grep and Glob are not covered.
- Do not run two Bash output rewriters at once.
- After a filter rewrites output, later hooks see the filtered text. For evidence, run the command through `agent-tokens raw` so the full output is kept.
- `sem` is also the name of GNU Parallel's tool. `agent-tokens doctor` warns when the one on PATH is not Ataraxy's.
- Scope `sem` to agent sessions. Do not let a setup step change the developer's global `git diff`.
