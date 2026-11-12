---
name: greenfield
description: Use when starting a new project from scratch or choosing architecture, language, framework or data store. Runs brainstorming in rounds, compares options on evidence, records decisions, and builds a walking skeleton before any feature.
---

# Greenfield: new project from scratch

The aim is the simplest design that meets the ranked quality needs, chosen on evidence, with the whole lifecycle set up before the first feature. Brainstorm in rounds with the `brainstorming` skill, one invocation per round. Each round ends with a short summary the developer approves. Do not move on without a yes. Save the output where skill `agent-core:workflow`, Flow says, not in the Superpowers default paths.

## Round 1: Problem and limits

Ask one question at a time. Write the answers into `docs/specs/<project>.md`.

- Problem statement in two sentences. Who has it, what they do today.
- Success metrics that can be measured later, each with a number and a way to measure it.
- Non-goals. What this will not do.
- Constraints: team skills, budget, deadline, compliance, hosting, organisation standards, existing systems. State each as a constraint. Do not hide a preference inside one.
- Open questions, each with an owner.

## Round 2: Quality attributes

Rank the top three to five (for example security, reliability, maintainability, performance, operability, cost). For each, write one scenario with a measurable target: "when X happens, the system does Y within Z". Everything after this is judged against these scenarios.

## Round 3: Options and evidence

For each major decision (architecture style, language and runtime, framework, data store, hosting, integration), do this:

1. List at least three options. One is always the simplest or most boring option that could work, and one is "no new component".
2. Dispatch one Researcher subagent per option with `dispatching-parallel-agents`, fresh context, strongest or mid-size tier. Each fills the same template: how it meets each ranked scenario, cost to run and to maintain, what it makes hard, reversibility (easy or hard to undo), and evidence with source and date. Unknown stays "unknown". Do not estimate.
3. Compare the options in a table against the ranked scenarios. Choose the best option for this situation, not the one that is most familiar or most impressive to build. Team skill counts as a stated constraint, not as a tie-breaker.
4. If the evidence does not separate the top two, run a time-boxed spike for each in a scratch worktree and measure it against the scenario targets. Throw the spikes away. Keep only the numbers.
5. Default to the simplest deployment unit that meets the scenarios (for example one modular application). Split only on evidence such as a scaling need, a team boundary or an independent release need.
6. Use a pattern only when a named problem requires it, and name that problem in the decision record. Duplicate knowledge is removed (DRY). Code that merely looks alike is left alone until the third real use. Do not build for needs nobody has stated.

## Round 4: Challenge

A separate Reviewer agent (use `requesting-code-review` on the decision records and spike results), fresh context and strongest tier, receives the spec, the scenarios and the chosen design and tries to refute it. It looks for failure modes, cost at ten times the load, the maintenance burden, and what the team would regret in two years. The orchestrator answers each point with evidence or changes the design.

## Round 5: Decide and record

Write one decision record per decision in `docs/architecture/adr/NNNN-<title>.md`, at most one page:

```
Status: accepted | superseded by NNNN
Context: the scenarios this decision serves
Decision: what we chose
Options considered: each with its evidence (source, date) and why it lost
Consequences: what gets easier, what gets harder
Revisit when: a measurable trigger (for example "p95 above 300 ms for a week")
```

Dependencies chosen go in the record of the decision that needed them, with the evidence table from `dependencies.md`. The developer approves each record.

## Round 6: Walking skeleton

Plan the thinnest end-to-end slice with `writing-plans` and build it through the normal flow (skill `agent-core:workflow`, Flow), before any feature. It must run through the full pipeline. It includes:

- repo layout, build, lint and format, lockfile, pinned tool versions
- the unit and e2e harness, and the skill `agent-core:verification` gates enforced in CI (coverage on changed code, mutation, e2e)
- a dependency update bot with a 3-day cooldown, a known-vulnerability scan on every build, and a secrets scan
- configuration and secrets handling, structured logging, a health check and the basic metrics that serve the success metrics from round 1
- versioned, repeatable releases and a one-command local start
- a README that tells a new developer how to run, test and release (the one markdown file for humans)

Only when the skeleton is green in CI does feature work begin, through the normal flow in skill `agent-core:workflow`, Flow.

## Keeping quality for the whole life of the project

- Definition of done for every change is skill `agent-core:verification`. CI enforces it, so it does not depend on anyone remembering.
- After each release, compare the success metrics from round 1 with what was measured. Record the result in the work record and raise a task when a target is missed.
- Review dependencies monthly with the same evidence table. Remove what is unused.
- When a "revisit when" trigger fires, reopen that decision record and supersede it with a new one.
- When an agent repeats the same mistake twice, use `writing-skills` to capture the lesson, or fix the instruction that caused it in `AGENTS.md` or an adapter.

When any dependency, language or framework is on the table, also use skill `agent-greenfield:dependencies`.
