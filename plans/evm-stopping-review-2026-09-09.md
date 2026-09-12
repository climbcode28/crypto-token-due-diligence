# EVM stopping review

## Scope

One implement-review-improve phase follows the user's request to make the EVM skill
earn its stopping point. Preserve the preceding, uncommitted 2.1.0 calibration work.
Apply the change to canonical and Claude Code copies, without live research or changes
to provider authorization, request limits, the delivery reserve or frozen evidence.

## Phase 1 — Investigate and justify remaining gaps

- Prioritize unknowns by their consequence for the user's decision; pursue the next
  useful authorized check while it fits the existing budget and source limits.
- Require a stopping review for every incomplete surface in newly assembled reports:
  decision impact, actual evidence-linked attempts, the next useful route and a
  specific explanation for stopping. Preserve honest not-attempted disclosures.
- Reject missing reviews and pending follow-up in new freezes. Distinguish an exhausted
  route, unavailable access, a budget cutoff, future evidence and scope exclusions.
  Do not turn recorded reasons into proof that research was exhaustive.
- Make decision-critical unknowns and stopping details visible. Preserve older report
  validation/replay; version the additive behavior and mirror Claude conventions.

## Acceptance

1. Untouched intake cannot silently become a reviewed frozen report.
2. A viable pending check cannot be represented as a completed stopping review.
3. Claimed attempts link to captured artifacts; no-attempt cutoffs remain explicit.
4. Critical unknowns cannot be dismissed as optional scope and remain visible even
   when they were omitted from the concise findings selection.
5. New assembly requires review; older sources without it remain readable without
   acquiring a retrospective claim that their stopping points were reviewed.
6. Meaningful regression tests cover validation, rendering, handoff and freezing.
   Run the README suites, Claude suite, local links and mirror checks; directly review
   final changes and apply in-scope improvements. Leave changes uncommitted.

## Implementation and review record

Phase 1 is complete. Workflow/reporting are **2.2.0** in both copies; backend **3.0.0**,
bundle/profile identifiers, authorization and collection limits are unchanged. The
preceding [2.1.0 calibration work](evm-assessment-calibration-2026-09-09.md) remains
in the working tree. No additional phase or live investigation was started.

### Changed files in this phase

Both the [canonical entrypoint](../skills/crypto-evm-token-due-diligence/SKILL.md)
and [Claude entrypoint](../.claude/skills/crypto-evm-token-due-diligence/SKILL.md)
load the new [stopping procedure](../skills/crypto-evm-token-due-diligence/references/stopping-and-escalation.md).
Changes within each skill directory:

- `SKILL.md`, `assets/reporting-release.json`, `assets/workflow-release.json`.
- New `references/stopping-and-escalation.md`; updated `adoption-and-assessment.md`,
  `bundle-format.md`, `evidence-and-output.md`, `source-routing-and-execution.md`,
  `supported-research-flow.md`, `strict-report-profile.md`, `improvement-loop.md`,
  `report-replay.md` and `reporting-scenarios.md` in `references/`.
- `scripts/bundle_assemble.py`, `report_profile.py`, `render_report.py` and
  `validate_bundle.py`.
- New `tests/test_stopping_review.py`; updated `test_assessment_reporting.py` and
  `test_research_helpers.py` in `tests/`.

Also updated root `README.md`, Claude `CLAUDE-CODE-PORT.md` and this plan. The
existing Claude-specific entrypoint/routing wording and deeper release paths were
preserved by merging against the pre-phase canonical files. Shared implementation,
tests and references match byte-for-byte. The project-only Codex symlink is unchanged.

### Review, improvement and acceptance

Directly reviewed the changed functions, callers, renderer, new tests, handoff/freezing
flow, instructions, synthetic scenarios and both copies' differences. Concrete findings:

- **P2, fixed — unearned intake freeze:** a bootstrapped draft previously froze with
  untouched intake reasons. New assembly always declares review version 1, and each
  incomplete coverage surface requires explicit closure data. A failed freeze leaves
  no final output; a reviewed handoff then freezes without mutating the draft.
- **P2, fixed — completion bypass:** initially the stopping gate only recognized pure
  coverage gaps. An unknown-evidence finding with another claim type could evade review
  by marking its surface checked. The gate now rejects any unknown finding in declared
  completed/not-applicable coverage. Tests cover both claim types and removal of stale
  reviews when a surface is actually resolved.
- Review also verified rejection of pending work, unreferenced attempts, borrowed
  surface evidence, unsupported exhaustion, critical scope exclusions, unversioned
  review data and invalid versions. Older strict sources without closure data remain
  valid without claiming retrospective review. Legacy output is preserved.

No actionable in-scope review findings remain. The only workflow adaptation was recording
this single phase from the ongoing request while preserving the prior uncommitted phase.

Acceptance criteria 1–3 are covered by intake, pending-route, attempt/reference and
handoff/freeze regressions. Criterion 4 is covered by critical scope-exclusion rejection
and rendered visibility for an unselected critical surface. Criterion 5 is covered by
older-source, version, legacy and replay tests. Criterion 6 is satisfied by the checks
below and direct review. Instructions require consequence-based scheduling and a useful
authorized next check before optional context; no new time or request allowance exists.

### Validation results

The initial 12-case regression run exposed the missing gate and rendering behavior.
After implementation and review improvements, the focused stopping suite passes all
**18 cases**. Final suites ran from the repository root using
`PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s <directory> -q`:

| Directory | Result |
| --- | --- |
| `skills/crypto-evm-token-due-diligence/tests` | 270 passed |
| `.claude/skills/crypto-evm-token-due-diligence/tests` | 270 passed |
| `skills/crypto-research/tests` | 31 passed |
| `skills/crypto-rug-check/tests` | 18 passed |
| `skills/crypto-solana-token-due-diligence/tests` | 23 passed |

**612 test executions passed**, including the mirrored EVM suite. Rendering checks
cover escaped text, evidence links, critical-gap visibility and rejection of tampered
Markdown. CLI tests exercise the updated review handoff before freeze. Existing
calibration, strict evidence and frozen replay regressions continue to pass.

`git diff --check`, local Markdown/release links, YAML/frontmatter/placeholder checks,
registration and expected canonical/Claude parity passed. The optional skill-creator
Python format helper remains unavailable because PyYAML was absent in the runtimes
checked during the prior phase; the existing Ruby YAML parser validated both entrypoints
separately. No dependency installation was needed or performed.

`report_replay.py verify` confirmed the original PONS bundle still carries reporting
engine 2.0.0 and its original evidence/source/output hashes. This was an integrity check,
not a new token investigation or fresh factual verification. No `history/` or `research/`
files changed.

The tests validate structure and declared consistency. Human review must still assess
whether attempts actually answer the question, alternatives are useful, priorities are
appropriate and budget/access claims are truthful. No empirical improvement in live
research completeness or investment prediction is claimed. Budget cutoffs remain
incomplete investigations; the change makes their limits explicit and reviewable.

All changes are uncommitted; no push was performed. Suggested commit message:
`Require evidence-backed stopping reviews for EVM diligence`.
