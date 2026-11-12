---
name: verification
description: Use when proving that work is done: acceptance-criteria traceability, 100% diff coverage, mutation check, e2e runs, and the evidence JSON. Run by an independent verifier agent, never by the implementer.
---

# Verification

## Verification

The Verifier is a separate agent with fresh context. It runs `verification-before-completion` and then the checks below, which are this project's content on top of that skill. It gets the spec, the AC list, the diff range and the commands from `agent-detect`, and it does not take the implementer's word for anything. It works from a clean checkout or worktree.

1. **Traceability.** Every AC maps to at least one unit test. Every user-facing AC also maps to an e2e scenario. An AC with no test fails.
2. **Clean run.** Build, lint and the full unit suite pass from a clean state.
3. **Coverage.** Run the `coverage` command from `agent-detect`, then `agent-gate --report <file> --base <base>`. It prints JSON and exits 0 only when every changed source line and branch is covered and no changed source file is missing from the report (`unreported_files`). Paste its `percent` and `unreported_files` into the evidence. 100% line and 100% branch on changed and added code. Whole-project coverage must not drop. Exclusions are allowed only for generated code or truly unreachable defensive code, each marked in the code with a reason and listed in the evidence. Never exclude to reach the number and never lower the threshold.
4. **Tests that can fail.** Coverage alone does not show a test asserts anything. Run mutation testing on the changed code if a tool exists (for example PIT for Java, Stryker for JS/TS, mutmut for Python, cargo-mutants for Rust). Surviving mutants are killed or justified. With no tool, break the code in three places on purpose, confirm tests fail each time, and revert.
5. **E2E.** Start the real system locally or in an ephemeral environment and run each user-facing AC end to end. Record the command and what you observed. Mocking the system under test does not count. If the environment is unavailable, the result is `not verified`, never `pass`.
6. **Try to break it.** Check error paths, edge inputs and one plausible failure the spec did not mention. Report what you tried.
7. **Evidence.** Start with `agent-evidence new --task <id> --commit <sha>`, fill it in, and run `agent-evidence check <file>`. It must print `valid` before the JSON goes to the work record. The shape is below. `verified` is true only if every check passes. On any failure the orchestrator runs `systematic-debugging`, fixes it through new briefs, then starts a new Verifier. A previous verdict never carries over.

```json
{
  "task": "PROJ-123",
  "verified": true,
  "criteria": [
    {"id": "AC1", "unit": "OrderServiceTest.rejectsEmptyOrder", "e2e": "POST /orders returns 400", "result": "pass"}
  ],
  "checks": [
    {"name": "build and lint", "result": "pass", "evidence": "exit 0"},
    {"name": "unit tests", "result": "pass", "evidence": "58 run, 0 failed"},
    {"name": "diff coverage", "result": "pass", "evidence": "line 100%, branch 100%, 0 exclusions"},
    {"name": "mutation", "result": "pass", "evidence": "34 of 34 killed"},
    {"name": "e2e", "result": "pass", "evidence": "3 of 3 scenarios"},
    {"name": "review", "result": "pass", "evidence": "0 critical, 0 important"}
  ],
  "exclusions": [],
  "models": {"orchestrator": "<id>", "implementer": "<id>", "verifier": "<id>"},
  "commit": "a1b2c3d"
}
```

`agent-evidence check` rejects a pass with no evidence, a `verified: true` with any check not passing, and missing checks. Nothing is Done before `verified` is true and the JSON is in the work record.
