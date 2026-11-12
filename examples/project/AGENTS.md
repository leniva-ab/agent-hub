# AGENTS.md

Team workflow comes from the `team-standard` plugin. For any code change, bug fix, review or new project, use skill `agent-core:workflow` first.

## Project settings

| Setting | Command or value |
|---|---|
| build | |
| unit tests | |
| coverage on changed code (line + branch) | |
| e2e | |
| lint / format | |
| tracker | none / Jira / GitHub Issues / Linear |
| git host | none / GitHub / GitLab / other |

A blank value: look in the repo's build files, tell the developer what you found, and wait for a yes. Never invent a command.

## Project rules

Only what is true for this repo and not in the plugins. Keep it short.
