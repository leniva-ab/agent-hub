---
name: cmux
description: Use only inside cmux (CMUX_WORKSPACE_ID is set): targeting panes explicitly, the socket, browser panes and logins, session restore.
---

# cmux (macOS)

Applies when `CMUX_WORKSPACE_ID` and `CMUX_SURFACE_ID` are set in your shell. With several runs or projects, also use skill `agent-cmux:control-plane`.

cmux is a macOS terminal for running several agents side by side, with workspaces, split panes, an in-app browser, notifications, and a CLI plus socket API that agents can use. cmux is not part of the version table in skill `agent-setup:setup` because it is optional and no version floor is known. Check what your install supports with `cmux capabilities --json`.

## Load the cmux skills first

The cmux project ships agent skills for its CLI, workspaces and browser. Load them before your first cmux command, and when they disagree with this file on command syntax, the skills win for your installed version.

- Skills: `cmux-cli`, `cmux-workspace`, `cmux-browser` (the repo also has `cmux-config`, `cmux-ref` and others).
- Install for one agent: `npx skills add manaflow-ai/cmux-skills --skill cmux-cli cmux-workspace cmux-browser --agent claude-code` (needs Node). List first with `npx skills add manaflow-ai/cmux-skills --list`.
- To pin exactly: clone `manaflow-ai/cmux-skills`, check out a commit you have reviewed, and symlink the skill folders into `~/.claude/skills/` or `.agents/skills/`. The repo had no release tags on 2026-10-28, so a commit hash is the only pin.

## Layout: one ticket, one workspace

- One cmux **workspace** per ticket, named after the ticket key, with its working directory set to the ticket's worktree (skill `agent-core:workflow`, Flow).
- Inside it, one **surface** (tab) or split per role: the main agent, a build/test or log runner, and a browser when you need one. Long-running commands go in their own surface so the agent session stays free.
- Subagents normally run inside the main agent's session. Give a subagent its own surface only when it needs its own login or a long-running process, and only the main agent writes to Jira and runs `gh stack submit` .
- The developer should see progress without asking. Use the sidebar: `cmux set-status` for the current step and `cmux set-progress` for layers done out of total. Use `cmux notify --title "<ticket>" --body "<what you need>"` when you are blocked or waiting for approval.

## Always target explicitly

Input commands such as `cmux send` go to the **focused** terminal by default, and the developer can click elsewhere at any moment. Typing into the wrong pane is the main way agents damage things in a multi-pane setup.

1. First run `cmux identify --json` to learn your own workspace and surface ids.
2. Pass `--workspace` and `--surface` on every command that sends input, for example `cmux send --surface <id> "<command>"` and `cmux send-key --surface <id> enter`.
3. Read a surface's output before you send the next command to it. Check the `cmux-cli` skill for the read command in your version.
4. Record the ids of the workspaces and surfaces you create. Close only those with `cmux close-workspace --workspace <id>`. Never close or type into one you did not create.
5. Never send a command from the safety rules in skill `agent-guardrails:safety` to any surface.

## Socket

- Leave the socket in the default mode, "cmux processes only", so only processes started inside cmux can connect. Do not switch it to `allowAll` or full access, and do not change `CMUX_SOCKET_MODE` or `CMUX_SOCKET_PATH` yourself.
- If the developer uses password mode, the password comes from `CMUX_SOCKET_PASSWORD` or the `--password` flag. Never write it to the repo, a ticket or a log.
- Prefer the `cmux` CLI over raw socket calls. If you must call the socket, use the V2 JSON format (one JSON object per line with `id`, `method`, `params`) and pass explicit ids.

## Browser panes, logins and sessions

- Open a page with `cmux browser open <url>` or `cmux browser open-split <url>`, then address it by surface id on every call, for example `cmux browser surface:2 snapshot --interactive --compact`. Do not rely on the focused browser.
- After each action that changes the page, take a fresh snapshot before the next click or fill.
- **Logins:** do not type credentials. Ask the developer to sign in manually in that browser pane, then continue. Do not read or print cookies or storage.
- If a repeatable test needs a saved session, use `state save` / `state load` only with a file outside the repo, make it readable only by the developer's user, and delete it when the ticket is done. Never commit it.
- Keep one browser surface per purpose (for example your app and the Jira or AWS console), so sessions stay separate and clear.

## Session restore

cmux can restore workspaces, layout and agent sessions after a restart. After a restore, run `cmux identify --json` again and re-check the "know where you are" rule in skill `agent-guardrails:safety` before you continue. Ids from before the restart may no longer be valid.

Sources for this section: the cmux README, CLI reference, concepts, browser automation and socket API docs, and the `cmux-skills` repo, all read on 2026-10-28. cmux changes quickly, so trust the skills and `cmux capabilities --json` over this text.
