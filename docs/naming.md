# Naming

One rule per kind of thing, so a name says what it is.

| Thing | Rule | Example |
|---|---|---|
| Plugin | `agent-<area>` for agent behaviour, `integration-<tool>` for an outside system. `team-standard` is the bundle. | `agent-routing`, `integration-jira` |
| Executable | `agent-<function>`, named for what it does. It may differ from the plugin name. Lives in `bin/`. It is not a Claude Code `commands/` file. | `agent-route`, `agent-versions` |
| Script | `scripts/agent_<function>.py`, the executable name with underscores. A hook-only script is named for what it does. | `agent_route.py`, `guard.py` |
| Skill | Lowercase topic name that stands alone, because it appears as `<plugin>:<skill>`. A family shares a prefix. | `model-routing`, `review-security` |
| Agent | A role noun. | `verifier`, `deduper` |
| Hook | `hooks/hooks.json` calls `<executable> hook`, or a script named for what it does. | `agent-route hook` |
| Env var | `AGENT_<EXECUTABLE>_<SETTING>`. A kill switch is `AGENT_<EXECUTABLE>_DISABLE`. Names shared by several plugins drop the executable. | `AGENT_ROUTE_DISABLE`, `AGENT_PROJECT`, `AGENT_RUNS_DIR` |
| Data folder | `~/.agent-<name>`. | `~/.agent-runs`, `~/.agent-telemetry` |
| Tag | `<plugin>--v<version>`. | `agent-core--v0.1.0` |
| Commit | Conventional Commits, scope is the plugin name. | `feat(agent-routing): ...` |
