# Evals

`claude plugin eval` runs a plugin against test cases and scores what Claude does. It answers a different question from `pytest`: not "does the script work" but "does the plugin make Claude do the right thing". Each case is a realistic prompt plus graders. Each case runs twice with the plugin and twice without it, so the report shows what the plugin added.

## What exists

The four newest plugins have suites in `plugins/<name>/evals/`: `agent-routing`, `agent-tokens`, `agent-telemetry` and `agent-learning`. Each has 3 or 4 cases:

- A case that checks the plugin's main advice or executable is named (for example `agent-tokens raw` for keeping raw output).
- A case for the hook in `agent-routing`: a subagent spawn must end up with an explicit model.
- An `ignores-unrelated-request` case: an unrelated question must not trigger the plugin's skills.

All graders are `regex` or `tool_used`, which cost nothing to grade. No grader calls a judge model. The only cost is the agent runs.

## Run them

Needs Claude Code 2.1.269 or later, git 2.31 or later, and a logged-in session or API key.

```
cd plugins/agent-routing
claude plugin eval . --trust-plugin --max-cost-usd 3 --no-publish
```

- Add `--ablation none` to skip the no-plugin runs and halve the cost.
- Add `--case <glob>` to run one case, `--runs 1` for a quick look.
- The cost is roughly cases × runs × 2 agent runs. Set `--max-cost-usd` every time.
- Results go to `evals/results/`, which is git-ignored.

## Reading the result

- `WITH` is the score with the plugin, `W/OUT` without, `Δ` the difference. A case that scores 1.0 both ways did not need the plugin.
- A `tool_used: Skill` grader only shows that the skill fired. It is not part of the score in a two-arm run.
- `suggests-clear-and-compact` tests advice that a plain model probably gives anyway. Expect a small `Δ` there. That is a finding about the skill, not a failure.
- `spawn-names-a-model` depends on plugin hooks running inside the eval session. If the `hook-fired` indicator never passes, check that first.

## Status

All cases load. They have not been run: the environment they were written in had no Claude login, so every run stopped with `auth_failed`. No scores exist yet. Run each suite once and record the first results here.

## CI

Not wired. A CI job needs `ANTHROPIC_API_KEY` as a secret and a cost ceiling. The command to use is in the [plugin evals docs](https://code.claude.com/docs/en/plugin-evals.md#run-evals-in-ci). Pin `--model` and `--judge-model` so a model rollout is not mistaken for a plugin regression.
