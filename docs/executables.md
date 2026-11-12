# Executables

Each plugin's `bin/` folder is on the Bash tool's PATH while the plugin is enabled, so Claude runs these as bare commands. Claude Code's docs call them executables. They are not the `commands/` slash-command files of a plugin, which this repo does not use. The skills name these executables, so the model runs them instead of working out how. All need Python 3.13 or later (tested on 3.13, 3.14 and 3.15), standard library only, with pytest suites.

| Executable | Plugin | What it replaces |
|---|---|---|
| `agent-versions show\|check\|models\|cooldown <name>` | agent-setup | looking up tool versions, model ids and the 3-day cooldown setting. Reads `data/versions.json`, the one file for all of them. A SessionStart hook runs `check` and speaks only when a tool is below its floor. |
| `agent-detect [build\|test\|lint\|coverage\|e2e]` | agent-core | guessing build and test commands. AGENTS.md table, then Makefile, then build files. Prints the source. `NOT FOUND` means ask. |
| `agent-gate --report <file> --base <ref>` | agent-core | judging diff coverage by eye. Cobertura, JaCoCo, lcov or Go profile. Fails on any uncovered changed line or branch, and on changed source files missing from the report. |
| `agent-evidence new\|check` | agent-core | hand-written evidence JSON. `check` rejects a pass without evidence and `verified: true` with any check not passing. |
| `agent-state init\|set\|show` | agent-cmux | writing `state.json` and the cmux sidebar calls by hand. One call updates the file, `log.txt` and the sidebar. |
| `agent-ctl status` | agent-cmux | the overview table, most urgent first. |
| `agent-route hook\|audit [--strict]` | agent-routing | working out which agents pin a model. `hook` is the PreToolUse guard. `AGENT_ROUTE_DISABLE=1` switches it off. |
| `agent-tokens doctor\|audit\|raw -- <cmd>` | agent-tokens | checking `tokf` and `sem`, counting CLAUDE.md lines and unscoped rules, and keeping the full output of a command that a filter might shorten. |
| `agent-telemetry env\|sink\|report` | agent-telemetry | hand-written OpenTelemetry settings, and totals of tokens and cost by config version, project or model. |
| `agent-learn log\|promote\|list\|status` | agent-learning | remembering corrections by hand. Counts repeats and lessons that recur after being promoted. |

A plugin that has a `bin/` folder is not installed by claude.ai or Cowork. These plugins are for the Claude Code CLI.
