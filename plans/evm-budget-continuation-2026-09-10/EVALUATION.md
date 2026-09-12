# Offline independent forward evaluation

This evaluation used the loaded skill-creator independent forward-testing procedure and current canonical EVM diligence instructions. It performed no network access, provider checks, credential access, real-token research, signing, broadcasting, repository edits, or subdelegation. All generated fixtures and results are isolated here. Synthetic RPC request counts are accounting observations, not network usage.

## Workflow outcomes

1. Nine pending surfaces, 200 consumed requests, 600 ceiling, 400 operational seconds and 1,200 absolute-ceiling seconds remaining; 80 requests and 300 seconds required: `review` returned `replan`; explicit `replan` raised the active total to 280 without changing identity, consumed attempts, deadline or ceiling. A follow-up review returned `continue`; a synthetic 10-attempt batch was charged successfully. The coordinator should continue already-authorized work, without asking for permission or delivering partial findings.
2. Interpreting 30 active requests left as max200 minus used170, six reservations leave 24 spendable. Essential45 plus overhead12 gives projected233 including the reservations. `review` returned `replan`, and replan raised the active total to233 while retaining six header reservations and ceiling420 (250 unused before replanning). If the prompt intended 30 *unreserved* requests instead, the arithmetic changes but the decision does not.
3. Explicit user ceiling50, all consumed, 12 required attempts pending: `review` returned `limit_review_required`. Replan was refused with exit2, zero revisions and unchanged limit/usage. An additional one-attempt charge was also refused. Continue useful zero-request analysis; preserve pending work and accurately describe the binding user limit. Any needed scope/budget decision is an active-work decision, not a fabricated completed report.
4. Creator history externally inaccessible after relevant permitted routes, other scope finished: a completion component with ten checked rows and one evidenced unavailable history row was accepted. The plan review returned `completion_review_required`, never final-delivery eligibility. This component checks structure only. In a real review the unavailable history remains Unverified and limits track-record conclusions; it does not establish clean history or misconduct.
5. Explicit caller deadline: a session with60 seconds remaining and120 seconds essential work returned `limit_review_required`; replan refused. The sibling `research_budget.py start/status` was exercised with total300/reserve60. Its library status at synthetic collection, reserve and final boundaries returned `collect`, `reconcile_and_deliver`, and `deliver_now`. The explicit caller deadline controls routed diligence; a deadline blocker/interim answer remains incomplete.

## Delivery fixture

A new synthetic chain31337 fixture used exact-address bootstrap, one session, one cache, intake/import/handoff and real CLI freeze/deliver operations. Bootstrap produced partial status with10 synthetic attempts because metadata errors were deliberately supplied; usable evidence imported successfully.

- Normal freeze with pending required work: exit2.
- Explicit checkpoint freeze: exit0, `internal_checkpoint`.
- Deliver checkpoint: exit2.
- After new fixture artifacts documented relevant primary and permitted alternate failures for each surface, normal freeze: exit0.
- Deliver completed externally-bounded fixture: exit0, `ready_for_final_delivery`.
- Independent `validate_bundle.py --allow-synthetic --rendered ...` returned VALID.
- Rendered report prominently says SYNTHETIC FIXTURE, preserves insufficient evidence and Unknown/Unverified findings, and does not turn missing facts into risk or passes.

The final full-bundle fixture used externally bounded unknowns across all surfaces to test gate behavior. The separate creator-only component isolates the ten-checked/one-history-unknown case. Neither is live evidence or proof of real research completeness.

## Compatibility and storage probes

Existing worker connections observed coordinator replanning without reopen: exhausted worker acquire false; one newly allowed acquire true; another excess acquire false. Original identity/ceiling and accounting persisted.

Fresh fixed sessions remained fixed and refused expansion. Synthetic schema1 sessions remained schema1, preserved their original bounds and refused replan/review migration. Unknown CLI options failed before creating a session. Init-only bound flags passed to replan were ignored; they did not expand original fixed bounds, and the operation still failed. This argument acceptance is a usability edge, not an observed ceiling escape.

### Actionable finding

`bundle_assemble.py handoff FROZEN_BUNDLE empty-lane.json` exits2 for missing draft.json but its exception path adds these files to the frozen bundle:

- `.operational-feedback.lock`
- `assembly-observation-cd78d9f4a8b9144a.json`
- `operational-feedback.json`

Existing evidence/report bytes are unchanged, but a rejected mutation changes frozen storage. Reproduced against a disposable copy only. `deliver CHECKPOINT` rejection is fully read-only. The failure recorder should avoid writes inside frozen bundles or route them to an explicit investigation root.

### Instruction friction

- The work-plan template initially did not exist during concurrent implementation. It was subsequently created, read, filled, and successfully validated through the actual `work_plan()` helper. This is resolved, not a remaining blocker.
- `stopping-and-escalation.md` lines38–39 says never bypass an operational limit without a nearby explicit-replan pointer. The loaded completion policy resolves the distinction, and it did not prevent the forward workflow; a local clarification would reduce ambiguity.
- `deterministic-backend.md` line97 unconditionally says initialize inside the shared deadline with delivery reserve, while line152 limits that reserve to explicit hard deadlines. The earlier wording could be narrowed.

## Artifacts and limits

Commands and machine output are in budget-results.json, delivery-results.json, supplemental-results.json, and compatibility-results.json. Reproduction scripts are run_budget_cases.py, run_delivery_cases.py, and run_compatibility_probes.py. Generated SQLite ledgers, plan files, frozen synthetic bundle and raw fixture artifacts remain in this directory.

Not tested: live provider/browser behavior, actual paid-use terms or credentials, real source relevance or completeness, actual token controls/liquidity/creator history, malicious fabricated prose detection, full unit suites, downstream document exports, or all possible concurrent/process crash behaviors. These probes provide workflow and structural confidence only.

## Resolution recheck — 2026-09-10T14:25:54.937373+00:00

All three review findings above are resolved in the current canonical files. The assembler failure recorder now excludes directories containing manifest.json. A fresh disposable copy of the frozen synthetic fixture was tested with the same rejected handoff command: exit2 for missing draft.json; the complete file map and content hashes stayed unchanged (47 files before and after, no added, modified or removed files). Detailed command and output are in frozen-handoff-resolution.json.

The stopping reference now explicitly directs inadequate operational allowances through same-session review/replan within finite ceilings and distinguishes revision from bypass. The backend session instructions now apply delivery reserves only to explicit hard deadlines and reference same-session replanning. One minor copy-edit remains in the stopping paragraph: “bypass an limit”; this does not affect the resolved behavior.

Only the requested frozen-handoff probe was rerun. No repository files, live services, credentials or unrelated evaluations were touched. The coordinator-reported unit-suite totals were not independently rerun in this recheck.
