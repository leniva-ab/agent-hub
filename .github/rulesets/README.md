# Rulesets

Declarative copies of the repository rulesets, so they can be reviewed and re-applied.

| File | Protects |
|---|---|
| `main-ci.json` | the default branch: the CI checks must pass (other main rules live in the existing "Copilot review for default branch I" ruleset) |
| `release-branches.json` | `release/v*`: no deletion or force push, linear history, signed commits, squash-only PRs, CI checks |
| `tags.json` | all tags: no update, delete or force move. Only repository admins and the release app can create them. The JSON lists admins only: after import, add the release app under Bypass list (Add bypass, pick the app, mode Always), because its id is not known here. |

Apply with `gh api -X POST repos/leniva-ab/agent-hub/rulesets --input .github/rulesets/<file>.json` as a repository admin, or paste the JSON in Settings, Rules, Rulesets, New ruleset, Import a ruleset. Update an existing one with `PUT ./rulesets/<id>`.
