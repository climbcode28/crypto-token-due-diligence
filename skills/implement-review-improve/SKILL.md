---
name: implement-review-improve
description: Implement a specified phase or all remaining phases of a saved Markdown plan, using an independent reviewer subagent to review each phase before improving and verifying it. Use when the user explicitly invokes implement-review-improve for a phased execution and review cycle, including deep-plan outputs.
disable-model-invocation: true
---

# Implement Review Improve

## Purpose

Run this cycle for the requested phase, or for each remaining phase when the user requests all phases:

1. Implement the requested plan phase.
2. Spawn an independent reviewer subagent to review the actual changes for defects and worthwhile improvements.
3. Apply in-scope fixes and re-verify. In all-phase mode, continue to the next phase only after the current phase passes its acceptance checks.

Discover the project's stack, rules, patterns, and commands each run. Prefer the simplest implementation that meets the phase's requirements and the project's quality standards. Avoid speculative abstractions and unrelated cleanup. No findings is a valid review result; do not invent refactors to fill a stage.

## Required Inputs And Scope

- `plan_file`: path to a saved Markdown plan.
- `phase`: a phase identifier, an unambiguous step, or `all` for all remaining phases. An explicit request to implement the whole plan selects `all`.

Resolve these from the user's request and current conversation first. If the plan is missing, look in the target project's established plan locations (for example `plans/`, `docs/plans/`, `.plans/`, or root-level plan files). Do not search unrelated personal directories. If the intended plan or phase remains ambiguous, ask one concise question with the candidate paths or identifiers. Use available question tools only where appropriate to the current mode.

Read the complete plan for context, decisions, execution notes, and dependencies, but implement only the requested phase or, in all-phase mode, the remaining phases in dependency order. For deep-plan output, include its shared design, assumptions, phase acceptance criteria, validation, and handoff requirements. Do not reinterpret a request to update this skill as permission to execute a project plan.

## Stage 0 — Prepare

### Locate The Project And Protect Existing Work

- Establish the target repository or workspace from the request and plan; do not assume the shell's current directory is the target. Ask if the target cannot be determined reliably.
- Inspect Git status and relevant existing diffs when available. Distinguish pre-existing edits from this run's changes, preserve them, and avoid destructive resets or broad cleanup. For overlapping edits, read and integrate carefully; ask only if there is a material conflict in intent.
- Check that required earlier phases and external prerequisites are satisfied by the current state. Do not trust a checkbox alone or silently execute earlier phases. If a prerequisite is missing, explain the evidence and what is needed; continue only independent work that remains valid within the requested phase.
- If the plan materially conflicts with current code or constraints, surface the mismatch before implementing the affected decision. Adapt routine details using current evidence and report the deviation. Ask about changes to scope, behavior, contracts, or consequential design choices.

### Discover Guidance And Patterns

- Read applicable ancestor and nested `AGENTS.md` files for affected paths. Follow the actual instruction hierarchy and path scope; do not invent a precedence list in which root guidance always overrides nested guidance.
- Read relevant contribution docs, architecture notes, ADRs, and existing project instructions. Legacy `.cursor/rules/`, `.cursorrules`, `CLAUDE.md`, or similar files may provide useful project conventions; apply relevant content without treating tool-specific commands or metadata as capabilities of the current agent.
- Use applicable skills exposed in the current session when they materially help. Do not bulk-load every skill or assume unsupported discovery locations.
- Identify affected modules, interfaces, dependencies, schemas, migrations, routes, configuration, and deliverables.
- Find a maintained reference implementation and reuse shared utilities, UI primitives, clients, test helpers, schemas, and naming conventions. Respect areas marked legacy or undergoing migration.

### Discover Validation

- Read language manifests, package-manager declarations and lockfiles, build/task scripts, monorepo configuration, and relevant CI jobs. Prefer documented repository scripts and scope them to the affected package when supported.
- Identify applicable lint, format-check, type-check, test, coverage, build, and manual or browser checks. Record working directories, prerequisites, required sequencing, and enforced thresholds. Resolve conflicting lockfiles from project guidance or CI rather than guessing a package manager.
- Treat plan commands as guidance to verify against the current repository. If a command or tool is unavailable, identify the gap; do not invent tooling or install a new validation system just to complete a checklist.
- Use a pre-change baseline check only when it helps distinguish existing failures from regressions or the repository requires it. Avoid an expensive full-suite run without a reason.

Give a short discovery update before editing: requested phase, target project, relevant conventions, implementation approach, validation, and any blockers. Keep routine details brief.

## Stage 1 — Implement

1. Implement the phase's deliverables and acceptance criteria using the discovered patterns. Change only files needed for this phase and its validation.
2. Add or update meaningful tests for changed behavior and regressions where appropriate or required by the project. Do not add tests that merely mirror the implementation or tests for low-impact edits with no meaningful behavior to verify.
3. Run the applicable checks at the project's configured strictness. Include coverage when enforced or materially affected; type-check/build when the changed surface warrants it; manual or browser verification when acceptance depends on an observable flow that automated checks do not cover.
4. Diagnose failures. Fix issues caused by this phase; distinguish pre-existing failures and environment limitations with evidence. Do not weaken tests, skip assertions, or relax lint, typing, or coverage requirements to make the run pass.
5. Continue directly to review without routine confirmation. If implementation is partially blocked, still review valid completed changes and preserve a clear account of what remains incomplete.

Use the execution permissions and tools actually available in the session. A skill cannot override a read-only or Plan-mode restriction. If execution is unavailable, explain the limitation and the remaining action without claiming implementation occurred.

## Stage 2 — Review

After implementing each phase, spawn one independent reviewer subagent using the host's available subagent tool. Prefer a read-only reviewer agent definition when the host exposes one (for example a project or personal agent named `phase-reviewer`); otherwise use the general subagent type and state the read-only mandate in the prompt. Use a fresh reviewer for each phase, with minimal inherited conversation when supported. Do not substitute a second self-review when delegation is available. In all-phase mode, complete this review and the resulting fixes before advancing to the next dependent phase.

Give the reviewer the absolute project and plan paths, the selected phase and acceptance criteria, applicable project guidance, changed-file scope, and the pre-phase baseline or diff needed to distinguish your changes from existing user work. Include untracked files. Supply actual verification commands/results, not a favorable interpretation or a list of defects you expect it to find. Ask it to inspect the final files, diff and relevant callers independently; your implementation summary is not the evidence.

The reviewer owns analysis only: it must not edit files, revert others' changes, commit, push, spawn additional agents, or perform live/external actions. It may run safe local checks within the task's existing permissions. Request concrete findings with severity, file/line, failure case, and suggested remedy, or an explicit statement that no actionable findings were found. Require it to name checks it could not complete.

Wait for the review result before declaring the phase complete. While it runs, perform independent local verification without changing the files under review. The main agent assesses each finding against the plan and evidence, applies justified fixes in Stage 3, and explains any rejected or deferred finding. Do not accept a suggestion merely because a reviewer proposed it.

If subagents are unavailable or forbidden by the host/user, disclose that limitation and perform a direct review using the same criteria; label it as a fallback, never as independent review. If a reviewer fails or times out, retry once when feasible, then disclose the failure and use that fallback. If the user explicitly requires independent review as a completion gate, keep the gate blocked instead of substituting self-review.

The reviewer applies project rules first, then the applicable checks below. Drop irrelevant items.

**Correctness and behavior**

- Phase acceptance criteria, compatibility with existing callers, edge cases, error paths, and unintended behavior changes
- Authentication, authorization, validation, and sensitive-data handling where affected
- Data ownership, state transitions, asynchronous races, retries, and side effects where relevant
- Established API, configuration, routing, asset-path, and deployment conventions
- Migration compatibility, rollout order, and rollback implications when changed

**UI and accessibility**

- Existing components and styling conventions; no needless parallel library or abstraction
- Loading, empty, success, and failure states appropriate to the flow
- Semantics, labels, keyboard access, and focus behavior
- User-visible behavior verified at a suitable level, including browser checks when needed

**Architecture and maintainability**

- Module placement, public interfaces, import boundaries, and dependency direction
- Appropriate reuse and separation of concerns without speculative generalization
- Types, schemas, configuration, and dependencies follow project conventions
- No accidental debug output, dead code, unrelated formatting churn, or unexplained generated-file changes
- Comments explain non-obvious intent when useful; do not remove valuable explanation merely to shorten code

**Verification quality**

- Tests target observable behavior and failure modes rather than reproducing implementation details
- Existing helpers, fixtures, and mocking boundaries are reused appropriately
- Applicable checks and required thresholds cover the changed surface
- Evidence supports claimed outcomes; compilation alone does not establish functional correctness

Record concrete findings by severity with file/line references where useful, the failure condition or maintainability cost, and a proposed fix. Separate defects and required convention fixes from optional preferences. If no actionable findings exist, say so and proceed to the completion check without manufacturing improvements.

## Stage 3 — Improve And Verify

1. Apply clear correctness fixes and worthwhile refactors within the phase's scope automatically. Preserve intended behavior unless correcting a defect against the plan. Do not ask the user to re-authorize routine fixes already covered by this workflow.
2. Defer unrelated improvements and speculative redesigns. If a finding needs a consequential product decision or additional authorization, explain the concrete issue and ask only for the missing decision while continuing independent work.
3. Re-run checks affected by the fixes, plus any required project gates not yet completed. Do not repeat unchanged passing checks without a dependency, failure, or unresolved risk that warrants it.
4. Inspect the final diff for accidental scope expansion and confirm that fixes addressed the findings without introducing a new problem. Continue repairing failures attributable to this phase until it is verified or a concrete blocker prevents progress; do not stop on a fixable failure merely because the first review pass finished.
   Return substantive behavior/security fixes or disputed unresolved findings for a focused follow-up review: continue the same reviewer where the host can resume it, otherwise spawn a fresh reviewer and hand it the prior findings and the fix diff. Do not rerun a full review for cosmetic edits or invent issues to force another iteration. Disclose a failed follow-up as a review gap; apply the same fallback/completion-gate rule as Stage 2.
5. Reconcile every acceptance criterion with its evidence. Update a plan's completion markers only if the user requested progress tracking or the project workflow requires it; preserve the plan's design and future phases.

## Completion And Final Report

In single-phase mode, stop after that phase's implementation, review, and improvement cycle. In all-phase mode, repeat the cycle for each remaining phase without routine confirmation between phases; verify completed prerequisites before relying on them. A blocked phase does not count as complete: continue only work independent of that blocker, and report what remains. Stop when all requested phases pass their checks or further progress needs user input or an external change. Do not add unrequested enhancements.

Report concisely:

- Phase(s) completed, or partial/blocked status with exactly what remains
- What changed and why, with links to changed files
- Review findings fixed, remaining actionable findings, and relevant deferrals; “no actionable findings” is acceptable
- Whether review was performed by an independent subagent or the disclosed direct-review fallback
- Checks actually run and their results, including failures, unavailable checks, and residual uncertainty
- Any material deviation from the plan and the handoff state for the next phase
- A suggested commit message when files changed

Never run `git commit` or `git push` unless the user explicitly requests it in the conversation. Leave changes in the working tree. If a required step depends on a push, ask the user to commit/push and explain what can resume afterward.

A phase is complete only when its required deliverables and acceptance checks are satisfied. Never equate a blocked check, a drafted change, or an unverified assumption with a passing result.
