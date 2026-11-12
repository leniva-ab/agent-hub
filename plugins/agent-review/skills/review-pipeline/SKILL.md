---
name: review-pipeline
description: Use when asked to review a PR, branch or diff with the multi-agent pipeline: intake, parallel category reviewers, validator evidence loop, deduper, summarizer, human approval, posting.
---

# Review pipeline

Read `.agents/review.yml` in the project. If it is missing, use the defaults shipped in `${CLAUDE_PLUGIN_ROOT}/review.default.yml` and tell the developer. Schemas are in `${CLAUDE_PLUGIN_ROOT}/schemas/`.

The agents of this pipeline are `agent-review:review-<category>`, `agent-review:validator`, `agent-review:deduper` and `agent-review:summarizer`.

## Pipeline

```
intake -> reviewers (parallel, one per category)
       -> validator <-> reviewers (evidence loop, max 2 rounds per finding)
       -> deduper -> summarizer -> [human approves] -> orchestrator posts -> record
```

| Role | Tier (from yml) | Tools | Gets | Returns |
|---|---|---|---|---|
| Orchestrator | strongest | everything, and the only role that writes to GitHub or the tracker | PR or diff | run state, posted review |
| Reviewer, one per active category | per category | read-only | context pack and its own category contract | `finding.json` |
| Validator | strongest | read-only plus test and grep commands | all findings, the code | `verdict.json` |
| Deduper | small | read-only | confirmed findings, existing PR comments, earlier runs | merged list with a map of what was merged |
| Summarizer | mid | none | merged list | plain-language review text |

## Steps

1. **Intake (orchestrator).** Get the diff (`gh pr diff <n>` or `git diff <base>...<head>`), PR metadata (`gh pr view <n> --json title,body,files,baseRefName,headRefName`), CI status and existing review comments (`gh api repos/{owner}/{repo}/pulls/<n>/comments`). Drop files matching `path_filters`. Map each file to categories using `path_instructions`, then add every enabled category. Write the **context pack** to the run directory (skill `agent-cmux:control-plane`): the diff, the file list with categories, the spec and AC ids or decision records it relates to, CI status, existing comments. Reviewers read the pack. Do not paste it into their prompts.
2. **Reviewers.** Dispatch one fresh, read-only subagent per active category with `dispatching-parallel-agents`, at most `max_parallel` at once. Paste only its category contract (below), the path instructions that apply, and the pack path. It returns `finding.json`.
3. **Validator.** One fresh agent, never a reviewer. For each finding it re-derives the claim from the code and tries to refute it, running a test or a search when that settles it. It returns `confirmed`, `rejected` with a reason, or `needs_evidence` with one question.
4. **Evidence loop.** Send each `needs_evidence` question back to the reviewer of that category, which gathers evidence or withdraws. The validator checks again. At most `max_evidence_rounds`. A finding still unproven is not posted. Record it as `unproven` in the run record.
5. **Deduper.** Merge findings that point at the same lines or the same cause, even across categories. Keep the highest severity and list every category. Drop anything already said in an existing PR comment or already posted in an earlier run of this review. Drop findings matching `suppress`, and count them.
6. **Summarizer.** Turn the merged list into the review text. See "Output".
7. **Approval.** With `post: draft`, set the run to `waiting_human` and stop. The developer reads the findings in the workspace, edits or removes comments, and says go. With `post: auto`, continue.
8. **Post (orchestrator only).** Create one review with inline comments, event `COMMENT` (`gh api` to `POST /repos/{owner}/{repo}/pulls/<n>/reviews`, or the GitHub MCP review tools). Never approve or request changes unless `verdict` allows it and the developer asked.
9. **Record.** Put the counts per stage in the work record: raised, confirmed, rejected, unproven, merged, posted, plus models and run id.

Re-review after new commits: review only the new diff, re-validate findings still open, and mark fixed ones resolved. Do not repeat comments.


## Running a reviewer as a separate process (execution: panes)

Use this only with Claude Code. Other tools use `inprocess`. Each agent runs in its own cmux surface so the developer can watch it (skill `agent-cmux:control-plane`). Example for one reviewer, with flags checked against the Claude Code CLI reference on 2026-11-10 and not yet run end to end:

```bash
claude -p --model <model-for-tier> --output-format json \
  --json-schema "$(cat docs/agents/schemas/finding.json)" \
  --allowedTools "Read" "Grep" "Glob" "Bash(git diff *)" "Bash(git log *)" "Bash(git show *)" \
  --disallowedTools "Edit" "Write" \
  --max-turns 12 --name "<project>-<run>-<role>" \
  --append-system-prompt "<category contract>" \
  "Review according to the context pack at <run-dir>/context.md"
```

- If the tool list swallows the prompt, put the prompt before the flags or end the flags with `--`.
- `--bare` skips hooks, skills, memory and `CLAUDE.md`, which suits a reviewer that only needs its contract. Confirm that sign-in still works with it before you rely on it.
- Write each result to `<run-dir>/findings/<role>.json`. A role runner that also prints one readable line per step keeps the surface useful to watch.

## Loop limits

| Loop | Exit | Max | Then |
|---|---|---|---|
| Validator and reviewer evidence | confirmed, rejected or withdrawn | `max_evidence_rounds` | finding is `unproven`, not posted |
| Reviewer finds nothing new on re-review | no new findings | 1 pass | stop |
| A reviewer fails or returns invalid JSON | valid `finding.json` | 2 tries | mark that category `failed` in the run, continue with the rest, tell the developer |

## Output

Written for a human who has not read the diff.

- **Verdict line** (not an approval): the one-sentence state of the change and the count of findings by severity.
- **What this change does,** in three to five sentences.
- **Findings,** most severe first, then by file. Each has a short title, why it matters, and what to do. Add a GitHub `suggestion` block only when the fix stays inside the commented lines. Otherwise describe the fix.
- **Nits** batched into one comment, never one comment each.
- **Checked and clean:** the categories that found nothing.
- Stay within `max_comments_posted`. If there are more, post the most severe and list the rest in the summary.
- Tone: specific, polite, no filler. Say what and why, not "consider maybe".
