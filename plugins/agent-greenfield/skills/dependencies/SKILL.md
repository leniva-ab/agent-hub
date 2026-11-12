---
name: dependencies
description: Use before adding, upgrading or choosing any dependency, language, runtime or framework. Evidence table, hard gates, latest stable version with a 3-day cooldown, and the cooldown setting for each package manager.
---

# Dependencies and versions

A claim needs a source and a date. If you cannot get a number, write `unknown`. Never estimate. If a registry or API is not reachable from your environment, mark the item `not verified` and tell the developer.

## 1. Do we need it at all

Add a dependency only if the cost of owning it is lower than the cost of writing and maintaining the code. Check in this order: the standard library, a dependency we already have, a small piece of our own code. Write the answer in the decision record. "No new dependency" is always a candidate.

## 2. Gates: any failure rejects the candidate

- The licence is compatible with the project.
- Not archived, not deprecated, and no unfixed known vulnerability (check OSV).
- Supports the latest stable version of our runtime.
- Has a release or meaningful commit in the last 12 months. This is a default, tune it in the decision record if you must.
- The version we would use was published at least 3 days ago (the Flow table).

## 3. Evidence table: compare at least two candidates plus "no dependency"

Fill one column per candidate. Put the source and the date next to each number.

| Signal | Why it matters |
|---|---|
| Downloads per month and the 12-month trend | real use, and whether it is growing or fading |
| Last release date and releases per year | release cadence |
| Commits per month over 12 months, last commit date | activity |
| Active contributors in 12 months, and the share held by the top one | bus factor |
| Contributing organisations, or foundation governance | survival if one person leaves |
| Issues opened vs closed over 12 months, median time to first response | maintainer responsiveness and trend |
| PRs opened vs merged, median time to merge | whether outside contributions land |
| Open security advisories, and how fast past ones were fixed | risk |
| OpenSSF Scorecard: `Maintained`, `Vulnerabilities`, `Signed-Releases`, `Code-Review`, `Dependency-Update-Tool` | supply-chain practices |
| Number of transitive dependencies and install size | footprint we also take on |
| Breaking changes in the last 3 major versions, and whether semver is followed | upgrade cost |
| Stars | a weak signal only. They can be bought and they lag. Use them to break ties, never to decide. |

Where to get the numbers, if reachable: the registry page or API for downloads and release dates, `gh api` for repository activity, contributors, issues and PRs, `scorecard --repo=github.com/<owner>/<repo> --show-details` (set `GITHUB_AUTH_TOKEN`), OSV for vulnerabilities, deps.dev for dependency graphs and version dates.

Decide in this order: gates, then maintenance and trend, then bus factor and governance, then footprint, then stars. Explain the choice in a few sentences. Do not invent a score that looks more exact than the data. Dispatch one Researcher subagent per candidate with `dispatching-parallel-agents` so each fills the same table independently.

## 4. Versions: latest stable, with a 3-day cooldown

- Use the latest stable release. Never an alpha, beta, release candidate or snapshot.
- Do not install a version published less than 3 days ago. Read the publish date from the registry. Do not guess it.
- A security fix may skip the cooldown only if the developer says yes this session. Record that in the PR.
- Runtimes and frameworks: use the latest stable release. If it has a short support window, say so in the decision record and plan the upgrade date. Read the release notes for deprecations before choosing.
- Move forward. Use the current idiomatic features of the language and framework. Do not add compatibility code for older versions unless the decision record names a consumer that needs it.
- Pin exact versions in a lockfile and commit it.

Enforce the cooldown in the tooling so nobody has to remember it. Do not recall the setting. Run `agent-versions cooldown <npm|pnpm|yarn|bun|pip|uv|dependabot|renovate|maven|gradle|go|cargo>` (no name lists all). It prints the file, the line and the minimum tool version. Where it says there is no native setting, use Dependabot or Renovate and check the publish date by hand.

A cooldown delays installs. It does not detect malicious packages, so keep the vulnerability scan and the lockfile review as well.

## 5. After you add it

- Record the evidence table in the decision record (skill `agent-greenfield:greenfield`, round 5) or the PR description.
- The update bot keeps it current. Review all dependencies monthly with this table. Remove what is unused.
- Replace a dependency when its signals drop below the gates, not because something newer is fashionable.
