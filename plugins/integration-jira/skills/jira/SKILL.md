---
name: jira
description: Use when the tracker is Jira: discover issue types, fields, team and workflow before creating or moving tickets, ticket templates, and Atlassian MCP v2 setup.
---

# Jira adapter

Use when the tracker is Jira. The ticket becomes the work record.

The ticket key is given in the prompt (for example PROJ-123). If there is none, ask whether to create one.

Every team configures Jira differently: issue types, required fields, team field, workflow statuses and transitions. Never assume a name. Discover first, then act.

## Discover first (before you create or move anything)

Do this once per project key and keep the result in the session, not in the repo. Use the Atlassian MCP tools (use the discover tool if one seems missing).

1. **Project and issue types:** which types exist in this project, and which are hierarchy levels (epic, story/task, subtask). Names vary: "Story" may be "User Story", "Task" may be "Work item", and subtasks may be called "Sub-task".
2. **Create fields:** for the type you will create, list the required and available fields. Fill every required one. Do not guess a value for a field with allowed options. Pick from the list or ask.
3. **Team and epic link:** find how this project links work to a team (a Team field, a component, a label) and to an epic (a parent field or an epic link). Copy both from the parent or sibling tickets when they exist.
4. **Workflow:** read the current status of the ticket and the transitions available from it. Moving a ticket means using an available transition by its id. Do not assume a path like To Do, In Progress, In Review, Done.
5. **Look at neighbours:** read the parent epic and two or three recent sibling tickets of the same type. Match their title style, labels, sprint and description layout.

If a step fails or is ambiguous (no clear team field, several matching epics, a required field with no obvious value), stop and ask the developer one short question. Do not create a ticket on a guess.

## Pick the right level

| Issue type | Use it for | Agent creates it when |
|---|---|---|
| Epic | A goal with several stories, owned by a team | Only if the developer asks. Otherwise find and link an existing epic. |
| Story or task | One deliverable change | The prompt describes work with no ticket. Link it to the epic and team found in "Before you create or move anything". |
| Subtask | One piece of a story, one stack layer, one PR | The plan is approved. One subtask per layer (skill `agent-core:workflow`, Flow, step 3). |

If the project has no subtask type, use a checklist in the parent ticket instead and say so.

## Templates

Use the team's own template when one exists: copy the description layout from sibling tickets or from the project's default description. Otherwise fall back to these. Keep them short, use only the sections the team's fields do not already cover, and write them in the ticket's description.

Story or task:

```
Goal: <one sentence, the user or system outcome>
Context: <why now, links to spec or architecture docs in the repo>
Acceptance criteria:
- [ ] <observable, testable condition>
Out of scope: <what this ticket will not do>
Plan: <filled in after brainstorming and writing-plans, as a checklist>
```

Subtask:

```
Layer: <what this PR changes and nothing else>
Done when:
- [ ] <test or check that passes>
Branch: <branch name>   PR: <link, added after submit>
```

Epic (only when asked):

```
Outcome: <what is true when this epic is done>
Team: <from the team field, see "Before you create or move anything">
Stories: <list or JQL>
```

## While you work

- Put the plan in the ticket as a checklist (description or one comment).
- Create one subtask per stack layer after the plan is approved, using 4.2 and 4.3.
- Tick boxes and update the checklist in a comment as each step finishes.
- Move the status with the transitions found in "Before you create or move anything", and only forward through states that the workflow offers. If a transition needs extra fields (resolution, fix version), fill them from the ticket or ask.
- Never move a ticket to the done state of its workflow before the verification comment (skill `agent-core:verification`) is posted.
- If the board has an "in review" style status, use it when the stack is opened for review. If it does not, do not invent one. Say so in a comment instead.

## Connect the Atlassian MCP

Version: v2 endpoint only.

- Claude Code: `claude mcp add --transport http atlassian https://mcp.atlassian.com/v2/mcp`, then run `/mcp` and sign in
- Cursor: install the Atlassian plugin from the Cursor Marketplace
- VS Code / Copilot: Extensions view, search `@mcp Atlassian`, install
- Other clients: https://developer.atlassian.com/cloud/rovo-mcp/guides/getting-started/
- Already on the v1 URL? Replace it with the v2 URL and sign in again. v1 credentials do not carry over.
- v2 shows a few primary tools and a discover tool for the rest. If a Jira tool seems missing, use discover before concluding it is not available.
