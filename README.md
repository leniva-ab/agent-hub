# Agent hub

Central home for skills, agents, hooks and settings for coding agents. Today it ships the Claude Code layout. Copilot, Codex and opencode adapters are planned and not built yet (see "Other tools"). Decoupled plugins for working with coding agents. Each plugin does one job, has its own version, and can be enabled or left out per repo.

| Plugin | What it gives you | Always-on cost* |
|---|---|---|
| `team-standard` | Bundle only. Pulls in `agent-core`, `agent-guardrails`, `agent-setup` and `superpowers`. | none of its own |
| `agent-core` | Skills `workflow` and `verification`. Subagents `verifier`, `researcher`, and an opt-in `orchestrator`. The build itself is Superpowers' `subagent-driven-development`. | ~340 tokens |
| `agent-guardrails` | A hook that blocks destructive git, `rm` and infrastructure commands. Skill `safety`. | ~64 tokens |
| `agent-setup` | A session-start hook that speaks only when a tool is below its version floor. Skill `setup` with install steps. | ~75 tokens |
| `agent-review` | Multi-agent PR review: nine category reviewers, validator, deduper, summarizer. Opt in. | ~1,200 tokens |
| `agent-greenfield` | New-project process and evidence-based dependency choice. Opt in. | ~170 tokens |
| `agent-cmux` | cmux conventions and the multi-project control plane. Opt in. | ~135 tokens |
| `integration-jira`, `integration-github`, `integration-commits` | Tracker, stacked PRs, commit rules. Enable what the repo uses. | ~70 tokens each |

\* Measured with `claude plugin details`. Skill and agent bodies cost tokens only when they are used.

## Use it in a repo

1. Copy `examples/project/.claude/settings.json` into the repo, set a release tag. The repo is `leniva-ab/agent-hub`. Install by hand with `/plugin marketplace add leniva-ab/agent-hub`. Everyone who opens the repo is offered the same marketplace and the same plugin set.
2. Copy `examples/project/AGENTS.md`, fill in the settings table, and add repo-specific rules. Keep it short. Plugins cannot ship an always-loaded `CLAUDE.md` or `AGENTS.md`, so this file stays in the repo.
3. Run `claude plugin validate .` and `claude plugin validate plugins/<name> --strict` before a release.

## Versions

- Each plugin has a semver `version` in `.claude-plugin/plugin.json`. A set `version` pins users until you change it.
- Release with `claude plugin tag --push` from the plugin folder. It creates `<plugin>--v<version>`.
- Plugins depend on each other with ranges, for example `{"name": "agent-core", "version": "^1.2"}`. Ranges resolve against those tags.
- Repos pin the whole marketplace with a `ref` (tag or SHA) in `extraKnownMarketplaces`. Upgrading is a one-line change in each repo.
- Model names in agent files are aliases (`opus`, `sonnet`, `haiku`). Pin the real model in the repo's `settings.json` env, as in the example.
- `superpowers` comes from the official marketplace. The marketplace file allows that cross-marketplace dependency with `allowCrossMarketplaceDependenciesOn`.

## Commands instead of searching

Each plugin's `bin/` is on the Bash tool's PATH while the plugin is enabled. The skills name these commands, so the model runs them instead of working out how. All need Python 3.13 or later (tested on 3.13, 3.14 and 3.15), standard library only, with pytest suites.

| Command | Plugin | What it replaces |
|---|---|---|
| `agent-versions show\|check\|models\|cooldown <name>` | agent-setup | looking up tool versions, model ids and the 3-day cooldown setting. Reads `data/versions.json`, the one file for all of them. A SessionStart hook runs `check` and speaks only when a tool is below its floor. |
| `agent-detect [build\|test\|lint\|coverage\|e2e]` | agent-core | guessing build and test commands. AGENTS.md table, then Makefile, then build files. Prints the source. `NOT FOUND` means ask. |
| `agent-gate --report <file> --base <ref>` | agent-core | judging diff coverage by eye. Cobertura, JaCoCo, lcov or Go profile. Fails on any uncovered changed line or branch, and on changed source files missing from the report. |
| `agent-evidence new\|check` | agent-core | hand-written evidence JSON. `check` rejects a pass without evidence and `verified: true` with any check not passing. |
| `agent-state init\|set\|show` | agent-cmux | writing `state.json` and the cmux sidebar calls by hand. One call updates the file, `log.txt` and the sidebar. |
| `agent-ctl status` | agent-cmux | the overview table, most urgent first. |

## Other tools

Skills (`skills/<name>/SKILL.md`) are the portable part. Agents, hooks and settings differ per tool. This repo ships the Claude Code layout. For Copilot and Cursor, reuse the `skills/` folders and add each tool's own manifest and agent folder. Nothing here has been tested in those tools.

## Tests

`agent-guardrails`, `agent-setup`, `agent-core` and `agent-cmux` have pytest suites (each with its own `conftest.py`): `cd plugins/<name> && python3 -m pytest tests`.

## Code style

The scripts use only the Python standard library and target 3.13 or later. They pass `ruff check` and `mypy --strict`. The settings are in `ruff.toml`. These are developer tools, not runtime dependencies: `uvx ruff check plugins/*/scripts` and `uvx mypy --strict plugins/<name>/scripts`.

## Releases and protection

- **Releases.** `release-please` opens one release PR per plugin when conventional commits land on `main` (or on a `release/v*` branch). Merging it bumps `plugins/<name>/.claude-plugin/plugin.json`, writes the changelog and creates the tag `<name>--v<version>`, the same format `claude plugin tag` uses. Config is in `release-please-config.json` and `.release-please-manifest.json`.
- **Release app.** The workflow gets its token from the Leniva AB release GitHub App (client id `Iv23lifrF9kQk25GZHkC`). Its repository permissions are Contents and Pull requests, read and write. Install it on this repo. Set the variable `RELEASE_APP_CLIENT_ID` and the secret `RELEASE_APP_PRIVATE_KEY` (the app's private key, PEM) at organization level, with access limited to selected repositories, so the same values serve every repo that releases this way. Add the app to the bypass list of the `release tags` ruleset in each repo, so it can create tags. PRs opened by the app start CI, so the required checks can pass.
- **Rulesets.** `.github/rulesets/` holds the rulesets for `release/v*` branches, tags and required CI. They must be applied by a repository admin (see the README in that folder).
