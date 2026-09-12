# EVM diligence completion-quality repair

Implemented and reviewed 2026-09-10. EVM workflow/reporting 2.4.0; network backend
3.0.0, evidence schema 1 and strict profile evm-evidence-v2 remain unchanged.

## Observed failure and user intent

The user challenged the PONS report ending with “the investigation remains partial”
and asked for completed investigations, allowing additional time. This maintenance
reviews that execution as workflow evidence only; it does not reuse token state as
current research or change the frozen PONS report.

The earlier skill explicitly targeted 5–10 minutes, reserved the final two minutes,
and directed Partial/Blocked delivery at the deadline. The PONS session used a finite
140-attempt cap and a 390-second remaining collection window. Its final accounting
recorded 91 charged attempts (including conservative duplicate external charges),
49 unused request slots, and expired time. Normal report freeze accepted the resulting
budget-stopped coverage after validating consistency. Required LP custody, exits,
economics and creator-history work remained unfinished. Successful live RPC was
available; this was not simply a missing-provider problem.

The previous label honestly disclosed unfinished work. Removing it without completing
the work would conceal the failure. The repair changes execution and finalization as
well as presentation.

## Final behavior

- Standalone broad EVM research uses 5–10 minutes as a progress checkpoint, with
  10–20 minutes as a planning expectation rather than a new hard deadline.
- Intake plans a considered finite request cap and an operational session with room
  for follow-up; the supported example is 200 attempts / 1,800 seconds. Authorization,
  explicit hard limits, per-request timeouts and request accounting remain intact.
- All eleven surfaces need an actual scoped investigation or affirmative
  not-applicable evidence. Feasible consequential follow-ups remain active work.
- Normal freeze emits completion_review_version 1 / completion_status complete and
  rejects not_checked surfaces and pending/budget_exhausted/out_of_scope closure.
  Attempted but unresolved facts require evidenced external boundaries tied to the
  same surface. They retain unknown ratings; completed research is not a safety pass.
- An explicit --checkpoint preserves interrupted or requested interim output, labels
  it as unfinished, and cannot silently act as a completed report. Old reports retain
  their original validation and replay semantics.
- Completed defaults describe specific unavailable facts and future evidence, rather
  than assigning unfinished work to the user. Chat ends with the supported assessment
  or what would change it; validation details stay in the artifact.
- The ordinary market runtime reference explicitly exempts standalone broad EVM
  invocation. Quick-screen, market-research and Solana budgets are unchanged.

## Implement, review, improve

An independent offline skill-creator forward review evaluated: (1) ten minutes with
working RPC and 49 requests left but LP/exits unattempted; (2) meaningful investigation
ending at unavailable creator records; (3) an explicit five-minute user deadline;
(4) the ordinary market runtime reference.

It correctly chose continued work in case 1, completed review with specific uncertainty
in case 2, an explicit interruption/checkpoint in case 3, and the standalone EVM policy
in case 4. It identified three remaining defects: unfinished-work assembly defaults,
a generic delivery-reserve stopping phrase, and boundary evidence borrowed from a
different surface. All three were corrected; the third has a negative regression.
The sibling runtime reference also received the explicit invocation-scope note.

The gate checks declarations and source binding. It cannot establish semantic relevance,
force remote evidence to exist, guarantee RPC honesty, or prove exhaustive discovery.
Changing closure labels or calling an inaccessible fact a pass remains prohibited.

## Validation

- Canonical EVM standard-library suite: 295 passed.
- Crypto research suite: 31 passed.
- Rapid rug-check suite: 18 passed.
- Solana diligence suite: 23 passed.
- Mirrored Claude EVM suite: 295 passed.
- Total: 662 passing tests across five suites (includes the mirrored EVM tests).
- New regressions cover premature completion rejection, genuine external limits,
  missing boundary support, cross-surface borrowing, legacy markers, default final
  rejection, explicit checkpoint freezing, immutable drafts and completed rendering.
- Skill frontmatter validators pass for canonical and Claude copies. System/bundled
  Python initially lacked PyYAML; a wheel was installed only under a temporary
  directory for these checks, with no project/global dependency changes.
- git diff --check passes. Mirror comparison shows only documented Claude wording,
  sibling paths, release-record depths and its port note.

No new token/provider research, signing, broadcasting, commits or pushes occurred.
Frozen evidence, historical reports, credentials, project-only registration and the
network request/accounting engine were not changed.

## Changed files

Canonical EVM changes:

- SKILL.md and references/completion-and-delivery.md
- references/decision-review.md, evidence-and-output.md, improvement-loop.md,
  source-routing-and-execution.md, stopping-and-escalation.md,
  strict-report-profile.md and supported-research-flow.md
- scripts/bundle_assemble.py, render_report.py, report_profile.py and validate_bundle.py
- tests/test_completion_review.py plus the four existing assembly/checkpoint fixtures
  in test_assessment_reporting.py, test_decision_review.py, test_research_helpers.py
  and test_stopping_review.py
- assets/report.template.json, reporting-release.json and workflow-release.json

These are mirrored into .claude/skills/crypto-evm-token-due-diligence with its documented
port differences and updated CLAUDE-CODE-PORT.md. Project README.md, HANDOFF.md and
skills/crypto-research/references/runtime-and-browser.md document the revised scope.
This file records the implementation and review.

Suggested commit: Make broad EVM diligence completion-driven
