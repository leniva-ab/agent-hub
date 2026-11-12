---
name: review-common
description: Shared rules and finding format for every category reviewer in the review pipeline. Preloaded by the reviewer agents.
---

# Shared reviewer rules

- You review one category only. Ignore everything else.
- Judge the changed lines and the code they touch. Do not flag old code unless this diff made it newly wrong.
- A finding without evidence is not a finding. Evidence is `file:line` quotes plus the reasoning, or the output of a command you ran.
- Report at most `max_findings_per_category`. Prefer the few that matter. If the category is clean, return `clean: true` and say what you checked.
- Do not edit anything.

Return JSON that matches `${CLAUDE_PLUGIN_ROOT}/schemas/finding.json`.
