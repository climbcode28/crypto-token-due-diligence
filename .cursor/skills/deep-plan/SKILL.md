---
name: deep-plan
description: Cursor entry point for deep-plan. Stress-tests an idea, feature or strategy through dependency-aware questions, then saves a durable Markdown plan with executable phases. Planning only; it changes nothing but the plan file. Invoke explicitly with /deep-plan.
disable-model-invocation: true
---

# Deep plan (Cursor pointer)

This file only registers the skill for Cursor. The skill itself is `skills/deep-plan/SKILL.md`
in this repository, shared unchanged with Claude Code and Codex.

Read `skills/deep-plan/SKILL.md` and follow it exactly, using the user's text with this
invocation as the planning brief. Treat `skills/deep-plan/` as the skill root for any
relative path. Nothing here changes the skill's rules: the only permitted file change is the
requested plan file and its parent directory.
