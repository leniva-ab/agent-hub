---
name: telemetry
description: Use when comparing two ways of working (a changed prompt, hook, model mix or plugin set) by tokens and cost, or when setting up measurement for a project. Tags runs with a config version and reports totals.
---

# Telemetry

Claude Code can export OpenTelemetry metrics. The metric `claude_code.token.usage` carries tokens by `type` (`input`, `output`, `cacheRead`, `cacheCreation`) and `model`, and `claude_code.cost.usage` carries cost. Cost is an approximation. Use these totals to compare, not to bill.

The point is a fair comparison: change one thing, tag it with a new config version, run similar work, compare.

## Set up

1. Pick a short config version for the way of working you are about to try, for example `2026-11-a`. Change it whenever a plugin, hook, model mix or CLAUDE.md changes.
2. `agent-telemetry env --project <code> --config-version <label>` prints a JSON `env` block. Merge it into the project's `.claude/settings.json` (or `settings.local.json` if it should not be shared).
3. `agent-telemetry sink` in a spare terminal. It listens on `127.0.0.1:4318` and appends to `~/.agent-telemetry/otlp.jsonl`. Use `--file` and `--port` to change them.
4. Work as usual. `agent-telemetry report [--group-by config|project|model] [--file F]` prints tokens by type, the cache read share, and cost.

`cache_read_share` is cache-read tokens divided by input, cache-read and cache-creation tokens. A change that lowers it is breaking the cache.

## What the report cannot tell you

Totals do not say whether the work was good. Pair every comparison with an outcome you can see: merged without rework, time to green, number of repeat corrections (`agent-learning`), verifier pass. A cheaper config that fails more is not cheaper.

Compare only similar work. Two configs on different tasks prove nothing. Prefer the same fixture task run under both configs.

## Not yet verified

These are assumptions to check once, then delete from this list:

- Claude Code honours `OTEL_RESOURCE_ATTRIBUTES`, so `config.version` and `project` arrive as resource attributes. If the report shows `(untagged)`, it does not.
- Claude Code can export over `http/json`. If the sink answers 415, the exporter is sending protobuf.
- The temporality setting is honoured. The report handles both delta and cumulative series either way.

## Other backends

The sink is for a first look with no install. Any OTLP backend that takes HTTP can receive the same export by pointing `OTEL_EXPORTER_OTLP_ENDPOINT` at it. Langfuse takes OTLP over HTTP only.
