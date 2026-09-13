---
name: implement-review-improve
description: Cursor entry point for implement-review-improve. Implements one specified phase from a saved Markdown plan, reviews the resulting changes, applies in-scope fixes and verifies acceptance criteria with the project's own conventions and commands, then stops before the next phase. Invoke explicitly with /implement-review-improve.
disable-model-invocation: true
---

# Implement review improve (Cursor pointer)

This file only registers the skill for Cursor. The skill itself is
`skills/implement-review-improve/SKILL.md` in this repository, shared unchanged with Claude
Code and Codex.

Read `skills/implement-review-improve/SKILL.md` and follow it exactly, resolving the plan
file and phase from the user's request. Treat `skills/implement-review-improve/` as the skill
root for any relative path. Its `LLM-INSTRUCTIONS.md` is for maintaining the skill, not for
running a phase. Nothing here changes the skill's rules or the repository's guidance in
`AGENTS.md`, including the rule never to commit or push unless explicitly asked.
