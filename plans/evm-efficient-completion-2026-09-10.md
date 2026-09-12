# EVM efficient completion repair — 2026-09-10

The user requested analysis and repair after the PONS review took about 45 minutes and
ended with a list of useful additions. The intended result is an ordinary broad review
completed in approximately 10–15 minutes, with feasible follow-ups performed during the
run and a completed report delivered. This maintenance changes the skill, not the frozen
PONS assessment or its evidence.

## Findings from the actual run

The read-only audit used the current conversation's `research/pons-2026-09-10-01a08c0f`
ledger, draft and source captures. It did not rerun token research or reuse them as fresh
onchain facts. First to last charged operation spanned **33.94 minutes**; the last charge
to final report freeze added **9.75 minutes**. These intervals include reasoning, browser,
coordination and idle time; they are not pure network durations. The ledger contains
362 conservative charged operations, including 12 chain-ID checks and 60 block-header
reads. Web tools were conservatively charged, so 362 is not a measured HTTP count.

The main causes were:

- The plan allocated 2,700 seconds and 25 requests to nearly every surface at intake,
  encouraging a long serial investigation instead of a concrete short critical path.
- Many small follow-up batches repeated setup and pin overhead. Important quote dependency
  and source checks occurred near the end, while optional context had already expanded.
- Findings were assembled through a bespoke coordinator script late in the run. Exact-ID
  collisions, missing scoped references and missing outcomes caused repeated freeze/fix
  cycles. The existing handoff helper did not offer a multi-error early preflight.
- Decision review required one to three actions even in a completed report. This encouraged
  generic export/ledger/audit follow-ups, despite other text saying feasible work must finish.
- The matcher falsely rejected two implementation layouts with unchanged literal data
  between an instruction-aligned INVALID and terminal CBOR. USDG proxy has a separate
  valid metadata jump destination and remains conservatively unsupported by this matcher.
- Some track stop rules still named a deadline as closure, conflicting with the broad
  completion rule. Missing export access was too easily described as missing onchain facts.

Some missing information also had legitimate limits: an agent cannot publish an independent
auditor's absent report, prove an unbound human identity, or infer all-time accounting from
sampled receipts. The repair preserves those boundaries and avoids representing them as
ordinary operations deferred to the user. Lack of a convenient export requires checking
available reconstruction before declaring the underlying fact unavailable.

## Implemented changes

Workflow/reporting **2.6.0**, decision review **2**, source comparison **1.1.0**; RPC
backend remains **3.1.0** because transport/accounting behavior is unchanged.

- A 10–15-minute end-to-end schedule starts architecture, source correspondence, custody,
  history access and dependency checks early. Incremental lane JSON feeds report assembly
  while collection continues. Concrete exceptions require a specific overrun explanation.
- Scope is expressed as eleven finite evidence questions. Lifetime multi-wallet accounting,
  human beneficial ownership and full external issuer audits require a relevant trigger;
  ordinary diligence retains current authority, material liquidity, exits and economics.
- Missing position exports trigger permitted indexed events/native-position and bounded RPC
  reconstruction checks. Current getters, exact pool keys and covered liquidity reconcile;
  absence of a UI export is not itself an external evidence boundary.
- `bundle_assemble.py check DRAFT` reports accumulated hash/reference faults together without
  mutating the draft or declaring research complete. `resolve-evidence` uses exact original
  collector IDs, with address/pin disambiguation; it never guesses by suffix.
- New completed reports reject `investigate` actions. Zero actions is valid, and the renderer
  omits an empty next-step section. Real adverse findings still require justified mitigation;
  pure missing evidence cannot support an adverse verdict. Historical v1 decisions still read.
- Source comparison permits unchanged literal tails only after an actual instruction-aligned
  INVALID with no valid JUMPDEST anywhere in the suffix, checking compiled and transformed
  bytes. Literal bytes remain exact. Old comparison version 1.0.0 reproduces its old rule.
- Updated the canonical skill, relevant references/templates, README/HANDOFF and Claude copy.
  Kept project-only Codex registration, private provider policy, pin/identity standards,
  existing rubric and frozen historical bytes unchanged. No commits or pushes.

## Review and validation

An independent source review identified the distinct safe literal-tail and unsafe metadata
jump cases. Five new negative/positive regressions cover literal preservation, reachable
suffix entry, jumps introduced or removed by metadata and fake delimiters inside PUSH data.
Version replay has an additional regression. New assembly/action tests exercise exact alias
resolution, multiple concurrent faults, hash tampering, read-only preflight, empty final
instructions, rejected research deferral and retained critical-risk mitigation.

An independent offline workflow forward review exercised available event reconstruction,
truly inaccessible historical events after primary/alternate attempts, a local source-match
failure and an actual critical seizure capability. It found three stale instruction groups
(action minimum, old decision version, deadline-as-closure); all were corrected and reread.
Four synthetic cases logged 16 operations with assertions passing and no network calls.
This is procedural validation, not a live token result or measured live latency.

Validation results:

| Check | Result |
| --- | --- |
| Canonical EVM suite | 317 passed |
| Claude EVM suite | 317 passed |
| Market research suite | 31 passed |
| Rug-check suite | 18 passed |
| Solana diligence suite | 23 passed |
| Skill frontmatter validation, canonical and Claude | Passed using temporary PyYAML dependency; no project dependency added |
| Diff whitespace and port parity | Passed; only documented Claude adaptations differ |
| Original PONS reporting-engine replay | Identical report SHA-256 reproduced using its frozen 2.5.0 engine |

Offline saved-input measurements: 275-artifact draft preflight completed in **0.081 seconds**;
WETH and USDG implementation correspondence succeeded in **0.0022** and **0.0064 seconds**.
All six source/runtime hashes were unchanged. The USDG proxy comparison correctly retained
its unsupported result. Measurements are saved in the ignored maintenance run at
`research/evm-skill-maintenance-2026-09-10/offline-validation.json`.

These checks establish the specific fixes and compatibility, not a guarantee that all
networks or arbitrary tokens finish in 15 minutes or that unavailable facts become known.
A fresh live end-to-end benchmark has not been run during this maintenance. Future runs
must measure against the new target rather than cite synthetic timings as proof.

Suggested commit message: `fix(evm): streamline completed diligence and remove deferred research`

## Changed files

- `.claude/skills/crypto-evm-token-due-diligence/CLAUDE-CODE-PORT.md`
- `.claude/skills/crypto-evm-token-due-diligence/SKILL.md`
- `.claude/skills/crypto-evm-token-due-diligence/assets/report.template.json`
- `.claude/skills/crypto-evm-token-due-diligence/assets/reporting-release.json`
- `.claude/skills/crypto-evm-token-due-diligence/assets/workflow-release.json`
- `.claude/skills/crypto-evm-token-due-diligence/references/adoption-and-assessment.md`
- `.claude/skills/crypto-evm-token-due-diligence/references/bundle-format.md`
- `.claude/skills/crypto-evm-token-due-diligence/references/completion-and-delivery.md`
- `.claude/skills/crypto-evm-token-due-diligence/references/decision-review.md`
- `.claude/skills/crypto-evm-token-due-diligence/references/dependencies-redemption.md`
- `.claude/skills/crypto-evm-token-due-diligence/references/evidence-and-output.md`
- `.claude/skills/crypto-evm-token-due-diligence/references/fees-and-proceeds.md`
- `.claude/skills/crypto-evm-token-due-diligence/references/improvement-loop.md`
- `.claude/skills/crypto-evm-token-due-diligence/references/pool-history.md`
- `.claude/skills/crypto-evm-token-due-diligence/references/project-credibility.md`
- `.claude/skills/crypto-evm-token-due-diligence/references/source-routing-and-execution.md`
- `.claude/skills/crypto-evm-token-due-diligence/references/strict-report-profile.md`
- `.claude/skills/crypto-evm-token-due-diligence/references/supported-research-flow.md`
- `.claude/skills/crypto-evm-token-due-diligence/scripts/bundle_assemble.py`
- `.claude/skills/crypto-evm-token-due-diligence/scripts/evm_decode.py`
- `.claude/skills/crypto-evm-token-due-diligence/scripts/render_report.py`
- `.claude/skills/crypto-evm-token-due-diligence/scripts/report_profile.py`
- `.claude/skills/crypto-evm-token-due-diligence/scripts/validate_bundle.py`
- `.claude/skills/crypto-evm-token-due-diligence/tests/test_assembly_preflight.py`
- `.claude/skills/crypto-evm-token-due-diligence/tests/test_completion_review.py`
- `.claude/skills/crypto-evm-token-due-diligence/tests/test_decision_review.py`
- `.claude/skills/crypto-evm-token-due-diligence/tests/test_research_helpers.py`
- `HANDOFF.md`
- `README.md`
- `plans/evm-efficient-completion-2026-09-10.md`
- `skills/crypto-evm-token-due-diligence/SKILL.md`
- `skills/crypto-evm-token-due-diligence/assets/report.template.json`
- `skills/crypto-evm-token-due-diligence/assets/reporting-release.json`
- `skills/crypto-evm-token-due-diligence/assets/workflow-release.json`
- `skills/crypto-evm-token-due-diligence/references/adoption-and-assessment.md`
- `skills/crypto-evm-token-due-diligence/references/bundle-format.md`
- `skills/crypto-evm-token-due-diligence/references/completion-and-delivery.md`
- `skills/crypto-evm-token-due-diligence/references/decision-review.md`
- `skills/crypto-evm-token-due-diligence/references/dependencies-redemption.md`
- `skills/crypto-evm-token-due-diligence/references/evidence-and-output.md`
- `skills/crypto-evm-token-due-diligence/references/fees-and-proceeds.md`
- `skills/crypto-evm-token-due-diligence/references/improvement-loop.md`
- `skills/crypto-evm-token-due-diligence/references/pool-history.md`
- `skills/crypto-evm-token-due-diligence/references/project-credibility.md`
- `skills/crypto-evm-token-due-diligence/references/source-routing-and-execution.md`
- `skills/crypto-evm-token-due-diligence/references/strict-report-profile.md`
- `skills/crypto-evm-token-due-diligence/references/supported-research-flow.md`
- `skills/crypto-evm-token-due-diligence/scripts/bundle_assemble.py`
- `skills/crypto-evm-token-due-diligence/scripts/evm_decode.py`
- `skills/crypto-evm-token-due-diligence/scripts/render_report.py`
- `skills/crypto-evm-token-due-diligence/scripts/report_profile.py`
- `skills/crypto-evm-token-due-diligence/scripts/validate_bundle.py`
- `skills/crypto-evm-token-due-diligence/tests/test_assembly_preflight.py`
- `skills/crypto-evm-token-due-diligence/tests/test_completion_review.py`
- `skills/crypto-evm-token-due-diligence/tests/test_decision_review.py`
- `skills/crypto-evm-token-due-diligence/tests/test_research_helpers.py`
