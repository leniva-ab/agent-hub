# Versions

- Each plugin has a semver `version` in `.claude-plugin/plugin.json`. A set `version` pins users until you change it.
- Release with `claude plugin tag --push` from the plugin folder. It creates `<plugin>--v<version>`. In this repo `release-please` normally does this, see [releases.md](releases.md).
- Plugins depend on each other with ranges, for example `{"name": "agent-core", "version": "^1.2"}`. Ranges resolve against those tags.
- Repos pin the whole marketplace with a `ref` (tag or SHA) in `extraKnownMarketplaces`. Upgrading is a one-line change in each repo.
- Model names in agent files are aliases (`opus`, `sonnet`, `haiku`). Pin the real model in the repo's `settings.json` env, as in `examples/project/.claude/settings.json`.
- `superpowers` comes from the official marketplace. The marketplace file allows that cross-marketplace dependency with `allowCrossMarketplaceDependenciesOn`.
