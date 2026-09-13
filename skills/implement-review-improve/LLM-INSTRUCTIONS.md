# Maintaining Implement Review Improve

Read this file only when customizing or maintaining the skill, not during ordinary phase execution.

This is a personal, project-agnostic skill. Keep project-specific stacks, paths, package managers, and validation commands out of the workflow. Stage 0 discovers them in the target project. File names listed as discovery examples are not prescribed project conventions.

## Preserve These Behaviors

- Implement, review, and improve the requested phase; when all phases are requested, repeat that cycle in dependency order until all remaining phases pass or progress is blocked.
- Read the whole plan for shared context and dependencies; execute only the selected phase or explicitly requested all-phase scope.
- Spawn one fresh, read-only reviewer subagent per phase when supported, preferring a read-only reviewer agent definition (such as `phase-reviewer`) over a general subagent when the host exposes one. Give it primary artifacts and scope boundaries, keep fixes with the main agent, and wait for its findings before completion. Use a focused follow-up for substantive fixes, resuming the same reviewer where possible and otherwise briefing a fresh one with the prior findings; disclose unavailable/failed delegation and never describe fallback self-review as independent review.
- Discover applicable instructions, current toolchain, maintained patterns, and proportionate verification each run.
- Protect pre-existing work and respect the user's commit/push preference.
- Apply routine in-scope fixes without unnecessary approval pauses; ask only about material ambiguity or missing authorization.
- Permit a clean review with no refactors; do not manufacture findings or force tests for every edit.
- Report blocked or failed validation honestly and distinguish it from completion.
- Keep explicit invocation in both places unless the user requests automatic selection: `agents/openai.yaml` with `policy.allow_implicit_invocation: false` for Codex, and `disable-model-invocation: true` in the `SKILL.md` frontmatter for Claude Code and Cursor.

## Customization Guidance

Prefer project guidance such as `AGENTS.md` for project-specific conventions instead of modifying this personal copy for one repository. If the user requests a separate project skill, use the skill locations supported by the active agent tool (Claude Code, Codex or Cursor) and verify discovery rather than assuming duplicate-name precedence.

Use the tools actually available in the current agent and its real instruction precedence. Avoid obsolete tool names, capitalized `.Codex/` paths, embedded secrets, or assumptions about the source computer. Keep review criteria conditional on the changed behavior and the project's requirements.

After editing, validate the frontmatter and invocation policy, then inspect the workflow for scope leaks, unnecessary approval loops, and false completion claims. Check that the required inputs can be resolved from existing context and that failures lead to repair or a concrete blocker, not premature success.
