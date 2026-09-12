# EVM findings and delivery consistency repair

Authorized by the user's comparison of two FLYBRAIN reviews and request to fix the
divergence. Additional constraint: preserve the performance work, with no additional
research tool calls, agent turns, live requests, lanes or presets.

## Reconciled result and correction

These are historical comparisons, not fresh token research. The same ten sampled
addresses and denominator (1 billion tokens) occur in both runs. Raw balances were
cross-checked through the evidence-backed `bundle_assemble.py facts --json` view.

| Run | Pinned UTC | Block | Exact aggregate raw units | Correct share |
| --- | --- | --- | --- | --- |
| Earlier `flybrain-20260911T043000Z` | 2026-09-11 03:50:18 | 59,951,224 | 321599582271731374462988959 | 32.1599582271731374462988959% |
| This task `flybrain-20260911T023000Z` | 2026-09-11 04:10:35 | 59,963,194 | 322615624730949702300600593 | 32.2615624730949702300600593% |

The earlier liquidity lane authored **43.13%** in `holder-concentration-observed`;
the coordinator copied it into synthesis and reasons. That number is unsupported by
its ten saved balances. This task's coordinator authored **32.2614%**, a small rounding
error from summing displayed percentages; exact four-place rounding is **32.2616%**.
The real same-cohort difference is about **0.1016 percentage points**, not 10.87 points.
The largest balance changed from 11.2898% to 11.2495%; the locker stayed at 8.1633%.
The pipeline's selected sample excludes target, dead and separately requested balances,
so a global top-ten ownership claim is not justified merely by the sample's length.

The other two quoted findings were not absent from this task's research:

- `locker-authority` records the same 2-of-3 factory/locker Safe, with token-specific
  positions and withdrawal powers still unverified. The chat omitted the threshold.
- `project-assurance-gap` records missing matched token source, independent audit,
  named accountable team and independent product adoption. Economics and reward gaps
  were recorded separately. The chat compressed these too aggressively.

Both original frozen reports, evidence bytes and snapshots remain unchanged. This
document is the additive correction. [Comparison and original hashes](evm-delivery-consistency-2026-09-11/comparison.json).

## Root causes and bounded changes

1. The pipeline summed only no-code wallets and listed code-bearing holders without a
   total. This invited model arithmetic and obscured a material observed balance share.
   `holder_summary` now sums unique atomic RPC balances, supplies exact four-place
   percentages, largest share, readable/missing counts and the denominator. Indexer
   balances and rounded percentages never feed the aggregate. Duplicate conflicting
   balances are rejected; zero/missing supply or absent balances do not become 0%.
2. All nonzero runtime was called a contract. Existing runtime reads now distinguish
   no-code, EIP-7702 designators, other code-bearing and unknown shapes. Length alone
   does not prove delegation; none of these shapes proves beneficial ownership.
3. Optional summary signals selected what reached the short reading layer. The existing
   `deliver` result now includes coverage IDs and gaps even when absent from summary
   rows. Existing answer instructions retain concentration numbers, custody/admin facts
   and economics/assurance limits during the same report-read and final-answer step.
   This is a concise handoff, not an additional verification call. Semantic correctness
   and chat compliance still require analyst judgment; it is not a prose theorem checker.
4. The maturity note no longer claims RPC reserve reads for every pool, since v4 state
   reads do not supply the same reserve evidence as address-based pools.

No automatic concentration risk threshold was added. An observed balance does not prove
one person controls it. Missing ownership data, absent unpromised payouts, pseudonymity
and missing audit evidence remain gaps rather than invented adverse findings.

## Performance and validation

- Backend **3.4.1**, workflow **3.2.1**, pipeline **1.0.1**; reporting stays **2.6.0**.
  Existing collection and report schemas and frozen replay remain compatible.
- Seven-run synthetic comparison: **78 RPC requests, 87 charged attempts** before and
  after. Normalized method/parameter multisets are identical. Tests enforce both counts.
- No extra tool calls, agent turns, lanes, source fetches, presets, report reads or
  network requests were added to the workflow. Local arithmetic and the compact handoff
  are performed inside existing operations.
- Normalized benchmark medians: **0.4109s before, 0.4006s after**. An earlier sample was
  **0.4235s vs 0.4629s**, showing ordinary host/timing variation. This supports no material
  local regression, not a claim of a live speedup or guaranteed wall-clock equality.
  Standalone helper timing was about **6.4 microseconds** for the ten-holder aggregate
  and **1.9 microseconds** for the delivery checklist; the real checklist was 2,664 JSON
  bytes. No new model turn was measured or required; model prefill latency was not tested.
  [Benchmark records](evm-delivery-consistency-2026-09-11/benchmark.json).
- Six new regressions cover exact sums despite wrong rounded inputs, duplicate/missing
  data and absent denominators, runtime shape, pipeline publication without automatic
  risk labels, and preservation of unselected coverage without changing frozen ratings.
- Canonical EVM **376**, Claude EVM **376**, research **31**, rug-check **18**, Solana
  **23** tests passed: **824 total**. One earlier suite attempt crossed the release-version
  edit and failed metadata equality; the final full runs used consistent versions and pass.
- `git diff --check` passed; mirror differences match the documented Claude port.
  Skill Creator's optional YAML validator could not run under the system Python because
  PyYAML is unavailable. Frontmatter was not changed. No package was installed.

## Review and changed files

Reviewed the incremental diff against a pre-edit working-tree snapshot, not HEAD, to
preserve the user's existing uncommitted performance work. Checked callers, missing-data
semantics, precision, classification, same request plans, snapshot compatibility and
port-only differences. No credentials, provider policy, registration, budgets or history
were changed. No commit or push was run.

Canonical files changed below; all twelve are mirrored in
`.claude/skills/crypto-evm-token-due-diligence/`, preserving Claude-specific differences:

- `skills/crypto-evm-token-due-diligence/SKILL.md`
- `skills/crypto-evm-token-due-diligence/scripts/facts.py`
- `skills/crypto-evm-token-due-diligence/scripts/broad_collect.py`
- `skills/crypto-evm-token-due-diligence/scripts/pipeline_note.py`
- `skills/crypto-evm-token-due-diligence/scripts/bundle_assemble.py`
- `skills/crypto-evm-token-due-diligence/scripts/backend_common.py`
- `skills/crypto-evm-token-due-diligence/tests/test_delivery_consistency.py` (new)
- `skills/crypto-evm-token-due-diligence/tests/test_broad_collect.py`
- `skills/crypto-evm-token-due-diligence/references/evidence-and-output.md`
- `skills/crypto-evm-token-due-diligence/references/runbook.md`
- `skills/crypto-evm-token-due-diligence/assets/backend-release.json`
- `skills/crypto-evm-token-due-diligence/assets/workflow-release.json`

Also changed `README.md` and the Claude `CLAUDE-CODE-PORT.md`; added this record and
its `comparison.json` and `benchmark.json` companions.

Suggested commit message: `Fix EVM holder arithmetic and preserve findings in concise delivery`.
