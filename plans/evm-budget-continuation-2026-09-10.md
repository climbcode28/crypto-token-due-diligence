# EVM diligence: continued research and final-delivery enforcement

Implemented and reviewed 2026-09-10. Canonical and Claude Code copies now carry
workflow/reporting 2.5.0 and backend 3.1.0. Investigation schema 2 and completion
review version 2 are additive; evidence/collection/cache schemas, the eleven research
dimensions and strict report profile remain unchanged.

## Scope and diagnosis

The user requested a general skill repair so analyst-selected limits no longer cause
routine delivery of unfinished investigations. This is skill maintenance, not another
token investigation. Earlier research was used only to identify workflow failures;
its facts, evidence and frozen reports were not reused as current token research or
rewritten.

The prior completion gate prevented a budget-stopped report from being labeled
completed, but still let an agent finish its response with a valid checkpoint. The
helper also treated a chosen operational estimate as an immutable request/time limit.
Improving the time target had left a second premature-stopping path through requests.
Tests of truthful checkpoint labeling did not test continued investigation and delivery.

## Final behavior

- Plan all eleven surfaces and remaining requests/time, collection overhead and a
  considered contingency. Null template estimates must be filled; unfinished offline
  analysis can legitimately require zero requests. Estimates are not evidence.
- Separate current operational allowances from original finite ceilings. Preserve
  actual user/provider constraints and record ceiling provenance. There is no universal
  numeric allowance, automatic spending authorization or automatic cap renewal.
- Review the remaining plan before batches and after consequential discoveries or
  handoffs. The helper includes consumed attempts and held reservations. Proactive
  shortfalls prompt explicit same-session replanning inside the original ceilings;
  an exhausted allowance or expired operational timer can use the same path.
- Record every review and operational revision in the existing SQLite ledger. Preserve
  investigation/cache identity, used attempts and reservations. Existing worker
  connections observe revised limits. Legacy sessions retain their original bounds.
- A ceiling shortfall stays an active planning/authorization question, not an external
  evidence boundary or a partial research answer. Finish useful captured-evidence
  analysis, trim optional expansion and resolve a necessary scope/budget decision.
  Never omit a required surface, reset the ledger, edit its bounds or silently spend
  beyond authorization. No claim is made that finite budgets can cover every discovery.
- `freeze --checkpoint` saves internal progress and leaves the task active. New reports
  explicitly distinguish `internal_checkpoint` from `final_report`. The separate
  `bundle_assemble.py deliver` command validates a completed frozen source and rejects
  checkpoints. A successful save is not successful final delivery.
- User-requested interim findings, cancellation, actual hard deadlines and unavoidable
  authorization/access interruptions stay distinct from an ordinary final report.
  Unavailable facts after meaningful research remain Unverified; skipped work cannot
  masquerade as unavailable evidence or a passing check.
- Receipt/header-only imports no longer advance the runtime-backed state snapshot
  and force unrelated runtime/metadata collection. Explicit pin selection still
  requires runtime evidence; historical claims retain their own time basis.

## Implement, review, improve

New regressions exercise exhausted operational requests, proactive shortfalls including
reservations/overhead, unchanged ceilings and counters, stale worker connections,
operational timeout extension within the original deadline, fixed/legacy sessions,
malformed plans, zero-request pending work, real CLI review/replan, and irrelevant
limit flags. Completion regressions reject inconsistent delivery markers, reject
checkpoint delivery, accept completed delivery and preserve frozen storage on errors.
The assembly regression imports later non-runtime evidence without making new RPC
calls for rendering or silently changing the state snapshot.

An independent agent received realistic synthetic requests and the skill without an
intended answer. It exercised the actual commands offline in an isolated directory:

| Scenario | Observed result |
| --- | --- |
| 200 consumed; 80 further attempts fit original ceiling 600 | Replanned operational total to 280, retained identity/usage/ceiling and continued accounting. |
| 30 active slots left, six held reservations, 57 further attempts | Replanned to total 233, preserving reservations and original ceiling. |
| Explicit user ceiling 50 exhausted | Further charge/replan refused; limit review required, no fabricated completion. |
| Other scoped work finished; creator history externally unavailable | Completion component accepted the evidenced boundary while keeping the fact unknown. |
| Explicit caller deadline cannot fit remaining work | Deadline extension refused; routed research retains the caller's hard limit. |
| Pending final freeze, checkpoint save, checkpoint delivery | Rejected final, accepted internal save, rejected final delivery of that save. |
| Completed synthetic review with evidenced external boundaries | Freeze, delivery and independent rendered validation passed without changing unknowns to passes. |

Review found a pre-existing exception-handler issue: rejected handoff to a frozen
bundle wrote diagnostic files inside it. The handler now skips frozen roots. Added
regression coverage and independent recheck confirmed rejection leaves all 47 files
and hashes in the probe unchanged. Two stale instructions about operational limits
and delivery reserves were also clarified. An initially absent work-plan template
was created during implementation, then independently populated and validated.

The independent [evaluation and dated resolution](evm-budget-continuation-2026-09-10/EVALUATION.md)
and [final frozen-storage probe](evm-budget-continuation-2026-09-10/frozen-handoff-resolution.json)
are retained alongside the budget/delivery/compatibility outputs. Earlier probe findings
are preserved as observed, with the subsequent resolution recorded rather than erased.

## Validation and limits

- Canonical EVM suite: 305 passed.
- Claude EVM suite: 305 passed.
- Crypto research: 31 passed; rapid rug check: 18 passed; Solana diligence: 23 passed.
- Total: 682 passing tests, including the mirrored EVM tests.
- Both skill-format validators passed. PyYAML was installed only into a temporary
  directory for this validator; no project/global Python dependency was changed.
- Mirror inspection retains only documented Claude tool/path/release-record differences.
- `git diff --check` passed. No commits, pushes, live token/provider research, signing,
  broadcasting, credential changes or historical evidence edits occurred.

These tests establish the exercised workflow, accounting and delivery invariants.
They cannot guarantee remote evidence availability, source truth, correct analyst
judgment, every concurrent/crash behavior, or that an agent always follows instructions.
The repair prevents the reproduced mechanical paths under the supported flow; it
does not promise that every token fact will become verifiable or authorize unlimited
research. Genuine external uncertainty must stay visible.

## Changed files

Canonical changes are `SKILL.md`; the backend/workflow/reporting release records and
report/work-plan templates; completion, supported flow, source routing, stopping,
strict profile, evidence/output, backend and improvement-loop references;
`investigation.py`, `bundle_assemble.py`, `report_profile.py`, `render_report.py`,
backend/reporting version declarations and operational version telemetry;
`test_budget_replanning.py`, `test_completion_review.py`, and `test_research_helpers.py`.
All are mirrored into the Claude copy with its port notes updated. README.md and
HANDOFF.md describe the new policy; this record and its synthetic evaluation outputs
document implementation and verification.

Changes remain uncommitted. Suggested commit message:
`Fix EVM diligence continuation and final-delivery enforcement`
