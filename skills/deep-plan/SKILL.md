---
name: deep-plan
description: Stress-test and refine an idea, project, feature, or strategy through dependency-aware questions, then save a durable Markdown plan with executable phases. Use when the user explicitly invokes deep-plan for rigorous planning or a phased handoff. Planning only; does not execute the plan.
disable-model-invocation: true
---

# Deep Plan

## Purpose

Turn an idea into a rigorously challenged, dependency-ordered plan that a fresh Codex task can execute by reading a saved Markdown file. Support software and non-software work: adapt the questions, deliverables, and validation to the actual goal.

This is a planning-only workflow. The only file changes permitted by this workflow are the requested plan Markdown file and creation of its parent directory. Do not implement code, modify project configuration, install dependencies, run builds or tests, or execute planned actions. Read-only context inspection is appropriate.

Use the user's text accompanying the invocation as the planning brief. Preserve context and decisions already supplied in the conversation; do not restart an interview unnecessarily.

## Grill-Me Mandate

```text
Interview me relentlessly about every aspect of this plan until we reach a shared understanding.

Walk down each branch of the design tree, resolving dependencies between decisions one-by-one.
```

Treat this as the default operating contract. Do not offer a skip-ahead path or fill major gaps with assumptions to move faster. Focus the interview on consequential uncertainty, not questions already answered by the user or available evidence. Explicit user directions to change the process take precedence; if the user requests an early draft, label it as a draft and expose unresolved decisions and blocked phases rather than presenting it as ready to execute.

## Process

### 1. Load Context First

- Inspect the relevant project files, supplied documents, existing plans, current state, and applicable guidance before questioning. Keep inspection scoped to the task; do not scan unrelated personal files.
- For repository work, read applicable `AGENTS.md` and relevant project guidance, inspect recent changes and existing implementations, and identify architecture and execution conventions.
- For other work, inspect available briefs, constraints, stakeholders, resources, and existing workflows. Do not assume a repository or software stack exists.
- Distinguish observed facts, user decisions, and assumptions. Record useful source paths or links for the eventual handoff.
- Summarize the current understanding in 3–5 bullets before the first question.

### 2. Build The Decision Tree

Track the applicable branches and resolve their dependencies top-down:

- Goal, non-goals, users or stakeholders, and desired outcomes
- Entry points, workflows, deliverables, and ownership
- Success criteria, failure conditions, and must-not-happen outcomes
- Constraints: time, budget, resources, technical limits, security, privacy, and delivery
- Existing systems, processes, integration boundaries, and external dependencies
- Data, inputs, outputs, state, persistence, and access, where relevant
- Contracts, side effects, error handling, and edge cases
- User experience, accessibility, and loading, empty, and failure states, where relevant
- Rollout, migration, communication, monitoring, and rollback or contingency plans
- Validation, acceptance gates, and completion criteria

Apply only relevant branches. If one answer blocks another branch, ask about the blocking decision first.

### 3. Interview Relentlessly

- Ask one focused question at a time, using available question tools where appropriate to the current mode. Wait for answers before doing dependent planning; continue independent read-only investigation when useful.
- Prefer concise choices when they clarify trade-offs; use an open question when nuance matters.
- Challenge vague answers with sharper follow-ups. Surface consequential assumptions for confirmation or rejection.
- Ask what breaks if a critical decision is wrong, and what must never happen.
- For consequential choices answered with “whatever is best,” recommend an option, explain why, and seek alignment. If the user explicitly delegates the choice, exercise judgment and record the rationale instead of repeatedly seeking confirmation.
- Continue until the scope, major decisions, dependencies, and acceptance criteria are clear enough for execution.

### 4. Explore Alternatives

For each major decision with meaningful alternatives, present 2–3 viable approaches:

- Lead with the recommendation and why it fits the evidence and constraints.
- Explain costs, risks, and what would make another option preferable.
- Record rejected options and reasons. Do not invent alternatives where the choice is already settled or only one approach is viable.

### 5. Present The Design Incrementally

Present resolved design areas in short sections and check alignment where a material decision remains. Cover applicable architecture or work structure, ownership, deliverables, workflows, interfaces, edge cases, security, rollout, and validation.

If the user corrects a section, update dependent decisions before continuing. Before finalizing, ensure no unresolved question blocks an executable phase. A discovery phase may resolve an evidence gap only when its method, outputs, decision gate, and effects on later phases are explicit.

## Saved Plan Output

- Save a normal Markdown file that future Codex tasks can read by path. A chat response or a tool's transient planning state is not a substitute for the file.
- Honor the user's save path. Otherwise follow an established project plan location, or use `plans/<short-topic-slug>-plan.md` at the repository root. For work without a repository, use the current workspace root.
- State the proposed default location during the interview so the user can override it; do not require a separate location approval when the default is suitable.
- Create the parent directory if needed. If the chosen file already exists and replacing or updating it has not been authorized, ask before overwriting it or choose an unused filename and disclose the new path.
- Respect the current mode and filesystem permissions. If writing is unavailable, prepare the complete plan in the conversation and clearly explain that saving remains pending; do not claim the file was saved.

## Repo Execution Notes

Discover these notes for each planning task; do not customize this installed skill for each consumer project. Incorporate concise, relevant findings into the saved plan's execution notes:

- Applicable guidance files, file placement, naming, imports, module boundaries, and design conventions
- Actual package manager, scripts, generators and required flags, and code generation conventions
- Suitable build, lint, test, typecheck, and format commands, with working directories and required sequencing
- Environment prerequisites, known permission requirements, and commands to avoid when supported by project evidence
- For non-code work: tools, inputs, ownership, review requirements, and concrete validation procedures

Verify commands by reading manifests, scripts, and documentation without running them. Identify proposed paths as new and unavailable commands as unverified; do not invent a stack or claim validation has passed. Include enough guidance for another task to act without this conversation, while avoiding unnecessary duplication of reliably loaded project rules. Never copy secrets, credentials, or private endpoint values into plans.

## Required Plan Structure

Use this structure, adapting software-specific labels to the task. Repeat the phase block for every phase. Keep execution notes outside the phase list.

```markdown
# Plan: [Name]

## Current Understanding

- Goal and intended users or stakeholders
- Scope and non-goals
- What success means
- Relevant current state and source documents

## Decisions Resolved

- [Decision]: [Chosen option and rationale]

## Open Questions

- [Non-blocking question, owner or resolution method, and impact; or None]

## Assumptions To Validate

- [Assumption]: [Validation method, timing, and consequence if false]

## Recommended Design

[Concise design or approach, organized into relevant areas.]

## Rejected Options

- [Option]: [Why rejected]

## Risks And Mitigations

- [Risk]: [Mitigation and contingency where relevant]

## Repo Execution Notes

[Use “Execution Notes” for work without a repo. Include relevant guidance
paths, prerequisites, conventions, and validation procedures.]

## Implementation Phases

Each phase must be executable in a fresh Codex task using this plan and its
referenced sources. Complete a phase and its acceptance checks before starting
the next phase. Recheck applicable guidance and current state before execution.

### Phase 1: [Phase Name]

**Goal:** [The outcome this phase delivers]

**Dependencies:** [None, or specific prerequisites and completed phases]

**Files to create/modify or deliverables:**

- [Specific path or deliverable] — [Purpose; distinguish new from existing]

**Tasks:**

1. [Concrete task with enough context to execute]
2. [Next task]

**Acceptance criteria:**

- [ ] [Observable, testable outcome]
- [ ] [Another completion criterion]

**Validation:**

- [Exact command and working directory, or manual review procedure and expected result]

**Handoff and stop condition:** [Outputs and checks required before the next phase]

---

[Repeat for Phase 2 and subsequent phases.]
```

## Phase Design Rules

- Make each phase small and coherent enough for one focused execution session, with a useful outcome and clear stopping point.
- Order phases by dependencies. Identify prerequisites, external inputs, and approvals where actually needed; do not assume execution authorization from a planning request.
- Use logical boundaries that fit the work, rather than mechanically imposing setup/data/UI phases on every project.
- Include specific files or deliverables whenever known, concrete tasks, measurable acceptance criteria, and proportionate validation in every phase.
- Validate behavior in the phase that introduces it; do not postpone all testing or review to a final phase.
- Avoid phases that depend on unspecified future design choices. Explicitly mark later work conditional if it depends on a discovery outcome.
- Make handoffs self-contained: include decisions, contracts, sources, and prerequisites that would otherwise exist only in this conversation.

## Final Response

After saving, read back the plan and check it for missing sections, unresolved blockers, dependency errors, unsupported command claims, and incomplete phase handoffs.

Link to the saved file using its actual absolute path. Briefly describe the phases and any remaining non-blocking uncertainty, then provide this next-task prompt with the actual path substituted:

```text
Execute Phase 1 from the plan at [absolute path].

Read the plan and applicable project guidance first, then execute only Phase 1.
Verify its acceptance criteria, report the results and any blockers, and stop
before Phase 2. Do not commit or push unless I explicitly request it.
```

For software work, “Implement Phase 1” may replace “Execute Phase 1.” Do not begin execution as part of this planning workflow.
