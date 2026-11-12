# Measuring a way of working

`agent-telemetry` tags Claude Code's OpenTelemetry export with a project and a config version. Change one thing (a hook, a model mix, a CLAUDE.md), give it a new config version, run similar work, and compare with `agent-telemetry report`. Pair it with an outcome (merged without rework, time to green, `agent-learn status`). Three assumptions are not yet verified and are listed in skill `agent-telemetry:telemetry`.
