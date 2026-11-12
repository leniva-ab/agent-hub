# Releases and protection

- **Releases.** `release-please` opens one release PR per plugin when conventional commits land on `main` (or on a `release/v*` branch). Merging it bumps `plugins/<name>/.claude-plugin/plugin.json`, writes the changelog and creates the tag `<name>--v<version>`, the same format `claude plugin tag` uses. Config is in `release-please-config.json` and `.release-please-manifest.json`.
- **Release app.** The workflow gets its token from the LeNivA AB release GitHub App (client id `Iv23lifrF9kQk25GZHkC`). Its repository permissions are Contents and Pull requests, read and write. Install it on this repo. Set the variable `RELEASE_APP_CLIENT_ID` and the secret `RELEASE_APP_PRIVATE_KEY` (the app's private key, PEM) at organization level, with access limited to selected repositories, so the same values serve every repo that releases this way. Add the app to the bypass list of the `release tags` ruleset in each repo, so it can create tags. PRs opened by the app start CI, so the required checks can pass.
- **Rulesets.** `.github/rulesets/` holds the rulesets for `release/v*` branches, tags and required CI. They must be applied by a repository admin (see the README in that folder).

Version rules for users of a plugin are in [versions.md](versions.md).
