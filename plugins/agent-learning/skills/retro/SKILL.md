---
name: retro
description: Use at the end of a task or work session, or when the developer says "retro", to turn corrections and surprises into lasting changes and to check whether earlier lessons stuck.
---

# Retro

Goal: the developer should not have to give the same instruction twice. A retro takes what went wrong or was corrected, stores each lesson where the agent will read it, and checks that earlier lessons worked.

## Steps

1. **Collect.** List corrections from this session: things the developer told you to do differently, and things you had to redo. Add any in Claude Code's auto memory (`/memory` opens it). For each one not yet logged, run `agent-learn log "<what to do instead>" --tag <short-lesson-name>`. Write the instruction, not the complaint. Reuse a tag when it is the same lesson as before.
2. **Check what recurs.** Run `agent-learn status`. A line starting `recurring after` means a lesson was promoted and still came back. That is the most important finding: the lesson went to the wrong place or was too vague. Fix that before adding anything new.
3. **Promote each open lesson.** Run `agent-learn list --open`. For each, pick the home with skill `agent-learning:promote-lesson`, write it there, then `agent-learn promote <id> --to <target> --ref <file>`.
4. **Prune.** Remove or merge lines in CLAUDE.md, rules and auto memory that are now duplicated, outdated, or covered by a hook. Run `agent-tokens audit` if `agent-tokens` is installed. Keep CLAUDE.md under 200 lines.
5. **Report.** Say in a few lines: lessons promoted and where, lessons that recurred, what was pruned, repeat rate from `agent-learn status`. Do not list every step.

## Rules

- Propose edits to CLAUDE.md, rules, skills and hooks. Show the exact text and the file. Apply them only after the developer agrees. These files shape every later session.
- One lesson per line. Specific and testable: "Use `click` for CLI entry points", not "write good CLIs".
- Do not store anything the developer did not say or clearly accept. No guesses about preferences.
- Never store secrets, tokens or personal data in any of these files.
