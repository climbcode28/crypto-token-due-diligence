# Maintaining Implement Review Improve For Codex

Read this file only when customizing or maintaining the skill, not during ordinary phase execution.

This is a personal, project-agnostic skill. Keep project-specific stacks, paths, package managers, and validation commands out of the workflow. Stage 0 discovers them in the target project. File names listed as discovery examples are not prescribed project conventions.

## Preserve These Behaviors

- Implement, review, and improve exactly one requested phase, then stop.
- Read the whole plan for shared context and dependencies; execute only the selected phase.
- Discover applicable instructions, current toolchain, maintained patterns, and proportionate verification each run.
- Protect pre-existing work and respect the user's commit/push preference.
- Apply routine in-scope fixes without unnecessary approval pauses; ask only about material ambiguity or missing authorization.
- Permit a clean review with no refactors; do not manufacture findings or force tests for every edit.
- Report blocked or failed validation honestly and distinguish it from completion.
- Keep explicit invocation in both places unless the user requests automatic selection: `agents/openai.yaml` with `policy.allow_implicit_invocation: false` for Codex, and `disable-model-invocation: true` in the `SKILL.md` frontmatter for Claude Code and Cursor.

## Customization Guidance

Prefer project guidance such as `AGENTS.md` for project-specific conventions instead of modifying this personal copy for one repository. If the user requests a separate project skill, use the skill locations supported by the active Codex environment and verify discovery rather than assuming duplicate-name precedence.

Use available Codex tools and actual instruction precedence. Avoid obsolete tool names, capitalized `.Codex/` paths, embedded secrets, or assumptions about the source computer. Keep review criteria conditional on the changed behavior and the project's requirements.

After editing, validate the frontmatter and invocation policy, then inspect the workflow for scope leaks, unnecessary approval loops, and false completion claims. Check that the required inputs can be resolved from existing context and that failures lead to repair or a concrete blocker, not premature success.
