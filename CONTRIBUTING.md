# Contributing

## Set up

Python 3.13 or later. The scripts use only the standard library. The developer tools are not runtime dependencies:

```
uvx ruff check plugins/*/scripts
uvx mypy --strict plugins/<name>/scripts
cd plugins/<name> && python3 -m pytest tests
```

## Code style

The scripts use only the Python standard library and target 3.13 or later. They pass `ruff check` and `mypy --strict`. The settings are in `ruff.toml`.

## Tests

Every plugin with scripts has a `tests/` folder with its own `conftest.py`. CI runs them on Python 3.13 and 3.15. The list of plugins it runs is in `.github/workflows/ci.yml`.

## Evals

Tests check that scripts work. Evals check that a plugin makes Claude do the right thing, with and without it. Put cases in `plugins/<name>/evals/`. See [docs/evals.md](docs/evals.md). Evals call the model, so run them with `--max-cost-usd`.

## Naming

Follow [docs/naming.md](docs/naming.md).

## Commits

Conventional Commits, with the plugin name as the scope: `feat(agent-routing): ...`. `release-please` reads them to open release PRs, see [docs/releases.md](docs/releases.md).

## Add a plugin

1. Create `plugins/<name>/` with `.claude-plugin/plugin.json` (`version` `0.1.0`), and the parts it needs: `skills/`, `agents/`, `hooks/hooks.json`, `scripts/`, `bin/`, `tests/`.
2. Add it to `.claude-plugin/marketplace.json`, `release-please-config.json` and `.release-please-manifest.json`.
3. If it has tests, add its name to the loop in `.github/workflows/ci.yml`.
4. Add a few eval cases in `evals/`: one for the main behaviour and one that an unrelated request does not trigger it.
5. Add a row to [docs/plugins.md](docs/plugins.md), and to [docs/executables.md](docs/executables.md) if it ships an executable.

## Before opening a PR

```
claude plugin validate .
claude plugin validate plugins/<name> --strict
```
