# Solana v2 acceptance

The independent expected-value corpus is
`skills/crypto-solana-token-due-diligence/tests/fixtures/acceptance/expected-material-facts.json`.
Its constants were authored from fixture inputs and protocol formulas, not exported
from the implementation. `test_solana_acceptance.py` checks material results and
report calibration in addition to structural validation. Synthetic subjects are
never represented as live token findings. Functional acceptance passed and v2 is
the default. The separate rich-case live-parity gate remains unmet.

## Outcome review matrix

All test paths in this table are under the Solana skill's `tests/` directory.
The expected outcome is a fact/concern/coverage judgment, not a target color count.

| Case | Independently required outcome and evidence |
| --- | --- |
| Mature token, delivered product and active market | `test_solana_acceptance.py`: retained $1m indexed liquidity / $500k 24h volume, dated v1.4 API publication, audit scoped to v1.2, real holder-right limits and all four axes. Public claims remain publication evidence, not tested runtime or organic adoption. |
| Revoked mint/freeze with retained extensions | Acceptance plus `test_solana_accounts.py`: base null authorities coexist with permanent-delegate key 8, hook program key 10 and paused state; no blanket safety inference. |
| Ordinary fee/buyback economics | Acceptance, accounts and quotes: current/scheduled fee terms stay distinct; discretionary buybacks do not become an enforceable distribution, equity right or allegation of malicious intent. |
| Changed supply/critical authority | Wire, collector, profile and evidence-edge tests: preserve transitions/context; changed critical data cannot support unchanged-state assertions. Unaffected usable facts remain available. Live integration review separately checks packet-level effects. |
| Several accounts per owner and excluded custody | Acceptance and holders: exact 2^59+101 owner total, 2^59+108 observed total, 2^60+17 denominator, 50.0000% share; integer precision, exclusions and spending-owner versus human distinction. |
| Wrong genesis/mint/layout/unused contradiction | Wire/profile/evidence-edge tests reject inconsistent identity even when the offending read is not cited. No completed exact-token report. |
| Mixed contexts/cache | Cache/collector/profile tests retain original slots and timestamps, reject stale current-state reuse and fabricated historical pins. |
| AMM v4 missing orderbook/PnL | Raydium/acceptance tests retain known vaults; unavailable effective reserves stay null. Current vault-only fixture reserves 9,900/19,800; CPMM 9,860/19,740 after independently specified reserved fees. |
| Out-of-range/bundled/bin-limited positions | Acceptance, CLMM, Whirlpool and DLMM: concentrated 4,987/4,987 principal, 17/23 fees; out-of-range 0/9,999 principal and zero active liquidity; missing bins retain known vault quantities, not full principal. |
| Multisig/config/spending bypass | Controllers/acceptance: 2-of-3 plus 3,600-second timelock does not conceal an independent configuration or spending-limit path. |
| Pump stages and actual migration | Pump/launch/acceptance: curve real 500/1,000 versus virtual 1,000/2,000; completion alone is not migration. Exact destination instruction/accounts/funding are required. PumpSwap 10,000/20,000 reserves, LP sample 450 versus mint supply 900 and pool field 1,000. |
| v0, inner instructions and temporary WSOL | Transactions/acceptance: exact loaded keys, -1,000 input/+500 output and reconciled 500 net, with rent/refund/fees distinguished and personal profit null. |
| Pool A deposit plus pool B swap; different payer | Sales/transactions tests require actual matched pool effects and historical spending owner. Fee payer cannot become seller or beneficiary by convenience. |
| Active market plus two verified receipts | Acceptance requires two distinct supported historical receipts; indexed broad activity and this verification sample remain separate. Two is not total market trading. |
| Quote unavailable despite successful sales | Acceptance preserves both valid receipts when local quote Clock dependency is missing; no honeypot inference from missing quote access. |
| Volume alongside material executable power | Acceptance/decision tests require severe control concern in summary, technical axis, mitigation review and reading checklist; activity does not erase it. |
| Full ask, focus, URLs, audit and prior launch | Broad/lane/compose/delivery tests preserve exact question, focus and owned URLs; decision requirements cannot omit original asks. Audit scope and historical evidence remain bounded. |
| Eleven surfaces with true external uncertainty | Completion/compose/delivery fixtures permit completed bounded work with supported primary/alternate failures and unknown ratings, without inventing a pass. |
| Untouched surface/missed lane/budget cutoff | Completion/handoff/lane/delivery tests retain partial/checkpoint status and reject completed broad delivery. |
| Redirect/retry/denial/lost worker/restart | Transport/web/session/cache tests charge every send, cap retries and bytes, enforce original absolute clock and grants, retain failures and reject refill/bypass. |
| Tampering and import shadow | Profile/preflight/replay/citations/import tests reject modified dependencies, code, bytes, inventory or unsafe paths. Hash-only verification does not execute bundled code; replay requires explicit trust. |
| Standalone, legacy and frozen current contract | Legacy/import/replay tests preserve original rendering, remove EVM dependency, and reproduce frozen output with isolated copied code/assets despite installed-engine changes. |

All eight adapters have separate expected quantity/custody assertions. DAMM v2's
independent fixture requires 500/500 position principal, 250/250 unlocked and 50/50
permanently locked component. No fixture may infer all principal locked from a
partial position/LP sample. Reading output preserves typed values, named controls,
quantity units, quote/execution distinctions and explicit scope limits.

## Measurement and activation gates

Seven equivalent-demand scheduler repetitions and separate slow/429/timeout cases
are recorded in `benchmark.json`. This measures injected-latency helper wall/CPU
time; it is not model latency or live provider performance. Request/response bytes,
critical reads/rechecks and actual attempt accounting must remain equivalent.

Final measured medians: sequential **8.976761s**, scheduled **7.185621s**,
**1.249267×** speedup (19.95% less helper wall time). Each responsive/slow run
retained 30 RPC + 3 HTTP attempts, 34 account reads, 15,768 response bytes and
all four critical reads with four usable rechecks. The 429/timeout profiles each
charged one extra attempted account read/RPC and recovered within the same bounds.
Peak RPC/HTTP concurrency was 3/2 versus the sequential reference's 1/1.
Slow, 429 and timeout pairs respectively measured 20.129540/15.896939,
9.221366/7.435145 and 9.210297/7.432791 seconds. All reports validated and all
started attempts completed; semantic request/response traces matched within pairs.

The benchmark records SHA-256 for every runtime Python source and its fixture
sources. Its recorded release hash corresponds to the exact metadata snapshot in
[benchmark-release.json](benchmark-release.json). Final review subsequently corrected
only that snapshot's conflated `engine_version` label in the current release;
benchmark runtime sources are unchanged. No new performance claim is inferred
from the metadata correction. Full elapsed/CPU/accounting rows remain in
[benchmark.json](benchmark.json).

`live-results.md` records the single finite three-case public round. A quick partial
checkpoint cannot pass the rich-case live-parity gate. Do not label the overall
plan complete while that gate is unmet. All three live cases finished within ten
minutes, with median partial handling 269.367908 seconds. They demonstrate bounded
degradation; they do not demonstrate completed broad live diligence.

Final README suites: **323 Solana passed** in 21.463 seconds, **30 router passed**
in 0.505 seconds and **428 EVM passed** in 17.851 seconds. The EVM suite emitted
the same two HTTPError temporary-file ResourceWarnings seen at baseline, without
failures. Focused final acceptance: **8 passed** in 2.190 seconds, including an
actual default-profile CLI finalize/read of independently specified completed
fixture notes and explicit legacy byte-preserving reading. The full suite also
contains the live-found regression repairs recorded in the implementation record.

Default profile `solana-evidence-v2`, collector/workflow/reporting version **2.0.0**.
Legacy schema-1 collection/read semantics remain 1.0.0 with workflow 1.0.1 and
explicit `--profile legacy-v1`; existing frozen evidence was not rewritten.
The existing `engine_version` stays **1.0.0** as the legacy collector compatibility
field required by the plan, separate from the new component versions.
Activation follows Phase 18 task 6's separate functional and live gates. It does
not remove incomplete custody, receipt, history, provider or unsupported-layout
limitations from reports. The original finite 120-attempt / 64-MiB / 600-second
envelope is unchanged. No new paid provider or custom Solana dRPC configuration.

Rollback: read old bundles through explicit legacy selection. If a release defect
requires disabling v2 as the default, restore the dispatcher's `DEFAULT_PROFILE`
to `legacy-v1` and update the corresponding release/skill/runbook declarations.
Keep v2 reading and frozen snapshots available; never migrate or edit retained
evidence to fit the rollback. Frozen hash-only verification is safe without code
execution; replay uses its own captured engine only with explicit trust.

Final guidance check after the compatibility-label correction: **4 passed** in
0.378 seconds. All 55 protected baseline EVM/router files matched their original
hashes; Git HEAD, EVM/Claude/history and registrations are unchanged. Root/record
Markdown checks found 78 existing local targets with no missing links. All 50
benchmark runtime source hashes and three fixture source hashes match. Canonical
skill/reference links, UTF-8/frontmatter, CLI help, policy hash, standalone imports
and registration targets passed the guidance/import suites. `git diff --check`
passed. Changes remain in the working tree; no commit or push.
