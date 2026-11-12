---
description: "A subagent spawn must end up with an explicit model. The hook denies a spawn without one."
tags: [hook]
runs: 2
max_turns: 8
allowed_tools: [Agent, Read, Glob, Grep, Skill]
---

Use the Agent tool to have a subagent count the files in the current directory. Do not count them yourself.
