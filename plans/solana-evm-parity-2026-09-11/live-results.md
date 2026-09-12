# Public live acceptance — one finite round

Identities were registered in `live-identities.json` before RPC collection. Each case
has a fresh original clock, 120-attempt / 64-MiB ceiling and 600-second deadline;
lane cutoff 240 seconds, collection cutoff 480 seconds, delivery reserve 120 seconds.
Only credential-free public Solana RPC and public HTTP sources were used. No trades,
signing, paid provider, extra cases or automatic repeat round. Preselection and
implementation QA time are outside the case clocks and are not research latency.

## Measured outcome

All three cases produced substantive **partial checkpoints**. The median handling
time was **269.367908 seconds (4m29s)**; each finished within ten minutes. This
demonstrates bounded handling, not completed broad diligence. **Rich-case live
parity remains unmet**: every case has pending standard-scope work, zero verified
sale receipts and zero position/LP ownership samples. No additional round was run.

The maintained offline audit reads original ledgers and frozen delivery inventories;
it performs zero network requests and executes no bundled code. Exact measurements,
per-surface coverage, stage timings and lane clocks are in
[live-metrics.json](live-metrics.json). All 102 started attempts have completion
records; each case remained below 120 attempts and 64 MiB. Frozen integrity passed
for all three after subsequent implementation fixes.

| Case | Start helper seconds | Total seconds | Root tool actions | RPC / HTTP attempts | Response bytes | Account reads |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| USDC | 2.677722 | 393.626382 | 12 | 12 / 16 | 681,154 | 9 |
| PYUSD | 2.890193 | 269.367908 | 17 | 28 / 15 | 3,818,803 | 29 |
| Pump | 4.192937 | 250.526074 | 21 | 20 / 11 | 1,314,015 | 9 |

Root tool actions count actual coordinator calls from start through freeze, including
case-time bookkeeping and excluding lane internals. They are a proxy for the plan's
approximately 40 model-facing steps, not user turns or an independent model-latency
measurement. Summed durable attempt intervals were 9.095889 / 14.342320 / 19.244478
seconds respectively; they include processing and overlap concurrent calls, so they
are not elapsed wire wall time. Frozen times use original `delivery.json` filesystem
mtime. The model was **gpt-6-astra**, provider OpenAI; research lanes inherited it.
Host: macOS 26.6.2 arm64, Python 3.14.7 (Clang 21.0.0).

Critical initial/recheck counts were 2/1, 4/3 and 3/2. Missing mandatory rechecks
remain explicit gaps, never passes. This round used one public Solana provider;
mixed-provider live fallback was not validated. No bespoke collection or assembly
script was used; coordinator and lanes used the maintained start, facts, capture,
preset, note check, compose and checkpoint interfaces. There was at most one
coordinator-requested offline note repair per case and no repeat freeze round.

## USDC — established SPL token

Received 2026-09-12 00:35:57.866779 UTC. Automatic start/facts finished
00:36:00.544519 (~2.68 seconds). Frozen partial checkpoint at 00:42:31.493161 UTC
(393.626382 seconds, 6m34s rounded). Both original lane cutoffs were 00:39:57.866779.
Liquidity research 00:36:33–00:39:45.987206; project first explicit clock
00:36:51, stop 00:39:48.028180. Liquidity needed one offline subject-shape repair
00:41:49–00:42:31.485530; original research stop was preserved. Compose preflight
and checkpoint passed on the first coordinator attempt after that repair.

Ledger: 28 started attempts, 681,154 response bytes, 9 account reads. Recorded
failures/statuses include one 429, one redirect and eight transport failures.
Initial identity-stage helper time 2.398356 seconds; program follow-up 2.524157
seconds. Stage attempt deltas overlap simultaneous lane traffic and must not be
summed as independent network totals. Raw per-attempt ledger is retained.

Positive evidence: exact mint in Circle's own publication; qualified-business
Circle Mint redemption distinct from ordinary-holder market access; independent
bounded indexer publications with activity and candidate liquidity. No counterpart
token's project site was attributed to USDC. Later mint state and SPL program
metadata were retained. Supply changed between critical reads; controls stability
remained unsupported. Illustrative USD sizing is not a quote or execution.

Unfinished: principal/side-pool custody, holder concentration, 0/2 verified sale
receipts, executable $1,000 quote, controller governance, binding legal terms,
independent reserve/audit/build scope and historical creator/launch review. All
eleven standard surfaces retain pending work; none is falsely marked complete.
Lane HTTP transport failures include sandbox network limitations, not proof of
service outages. This is graceful degradation, **not rich-case parity acceptance**.

The live run exposed integration defects fixed afterward, without altering or
re-running this case: structured controller roots passed to an address-only graph;
an indexed pool follow-up requiring an already-captured pool account; and automatic
project-link traversal from a counterpart base token. Focused regressions and all
319 Solana tests passed after repairs (18.992 seconds).

Evidence: `research/solana-parity-2026-09-11/usdc/checkpoint` (frozen old engine),
`usdc-start.json`, `usdc-checkpoint-result.json`, and the original session ledger.

## PYUSD — Token-2022 extensions

Received 2026-09-12 00:46:23 UTC. Automatic facts finished 00:46:25.890193
(2.89 seconds). Frozen partial checkpoint at 00:50:52.367908 UTC
(269.367908 seconds, 4m29s).
Liquidity research 00:46:45–00:49:23.924431; project first clock 00:46:52,
research stop 00:50:14.074625, both before 00:50:23 cutoff. One offline checklist
repair changed grant-capped audit work from external-limit to pending; it added no
research and preserved the original stop. Compose and freeze passed without repair.

Ledger: 43 attempts, 3,818,803 response bytes, 29 account reads. Three 429s, one 404,
three redirects and one 1-MB response-limit event. Helper stages: initial
2.650417 seconds, controller preset 1.232256, pool preset 2.450498 (including exact
indexed-lead prefetch and dependencies). Host-approved lane HTTP succeeded.

Positive evidence includes PayPal exact-mint/operating-product documentation,
June 30 2026 Paxos stablecoin terms with conditional verified-customer redemption,
and substantial indexed market activity. Reserve attestations are distinguished
from code audits and PayPal custodial rewards from inherent token yield. Published
freezing/seizure discretion remains a high policy concern in the report summary;
it does not by itself prove the exact Solana executable path.

One successful Jupiter API quote at context 446296732: 1,000,000,000 PYUSD atoms
to 1,000,036,285 USDC atoms, minimum 995,036,104 at 50 bps, source USD value
999.944268929698000. Manifest/AlphaQ route, intermediate mint, fees and price-impact
definition limits remain recorded. This was a quote publication: 0/2 verified sale
receipts, no signed/built/executed trade.

Captured mint data includes retained permanent delegate, fee/hook authorities,
null current hook program, unknown extension 19 and a 1-of-4 mint-authority multisig.
The pool preset captured exact Orca PYUSD/USDC accounts and base vault quantities,
but incomplete critical consistency left the latest state derivations unusable.
Zero positions and no locked-principal assertion. Holder concentration, controller
paths, actual audit reports and creator history remain unfinished. This is a
substantive partial result, **not rich-case parity acceptance**.

Offline review afterward found that an unpinned optional epoch could taint controls
and a newer unpinned mint packet could hide an earlier usable snapshot. The importer
now retains both snapshots with explicit temporal labels and excludes unusable epoch
evidence from active-fee selection. It neither repairs missing consistency nor
silently treats earlier data as latest. This frozen case was not changed or repeated.

Evidence: `research/solana-parity-2026-09-11/pyusd/checkpoint`, its start/status and
checkpoint-result JSON files, and original session ledger.

## Pump — recent Duplicate launch

Exact mint `2fRDA5f353VXLs2PeLJNqqHqTMhrjJunAXmWWpLkpump`. Received
2026-09-12 00:54:18 UTC; start/facts finished 00:54:22.192937. Frozen checkpoint
00:58:28.526074 (250.526074 seconds, 4m11s rounded). Liquidity research
00:54:38–00:57:31.228131; project first clock 00:54:45, research stop
00:57:48.401486. Both stopped before 00:58:18 cutoff. One offline liquidity wording
repair distinguished capture-time sizing from subsequently usable state; it added
no research. Compose and checkpoint passed without a second freeze attempt.

Ledger: 31 attempts, 1,314,015 bytes, 9 account reads. One 404, one 429 and one
1-MB response-limit event. Initial helper stage 3.419726 seconds; PumpSwap and
curve presets 3.420273 / 3.459408 seconds. Both captured their exact indexed lead
but ended partial on unsupported account allocation lengths. These failures remain
in the frozen result despite later offline fixes.

Positive evidence: pinned Token-2022 mint snapshot with 992,661,429,372,584 atoms
at six decimals, null mint/freeze/metadata-pointer authorities and retained unknown
extension 19. Null base authorities do not resolve the complete control surface.
Pump's publication identified creator, curve, pool and a completed flag; no migration
receipt was verified. The roughly 4.5-hour history is not evidence of long maturity.

The project's captured HTML, 7,667-byte application script and exact-mint API status
describe an operating airdrop workflow. The API published 5,444 buys, 4,956 sends,
39,191,777.29529805 tokens sent and 25 signature leads; none is independently verified
execution. Page defaults are filled by JavaScript, not evidence that the product is
broken. Adjustable reserve-funded distributions to CATE holders are not purchaser
dividend or redemption rights. No backend/audit/creator-history verification was
completed; a creator API 404 is not absence of earlier launches.

Successful Jupiter quote at 00:55:11.124432: 1,947,131,171,215 input token atoms to
970,065,314 USDC atoms, minimum 965,214,988 at 50 bps, source USD value
969.966504188750752736292. Route: Pumpfun AMM → Scorch via USDT → Byreal USDC,
context 446298240 with retained per-hop slots. The input used roughly $1,000
spot sizing; this does not establish executed net $1,000 proceeds. Raw price-impact
definition and route fee limits remain disclosed. Indexed principal-pool liquidity
was about $64k with about $1.687m 24-hour volume; neither measures organic demand
or removable/locked principal. Zero ownership samples and 0/2 verified sales.

After freezing, offline review matched the 301-byte PumpSwap and 124-byte curve
allocations to pinned known layouts plus all-zero trailing allocation padding.
The parser now accepts those exact allocations and rejects nonzero tails. A terminal
curve with all four reserves zero is accepted only when complete; that still does
not prove migration. The captured PumpSwap signed virtual-quote field is
17,584,505,289 atoms and remains separate from custody reserves and unresolved
special-mode pricing. The small curated raw-account fixture preserves original
packet/data hashes; it proves decoding, not current pins, custody or migration.
Controller derivation also now retains the owning token program when all base mint
authorities are null. These repairs were tested offline without changing this case.

Evidence: `research/solana-parity-2026-09-11/pump/checkpoint`, start/status and
checkpoint-result files, original session ledger and the curated
`tests/fixtures/acceptance/pump-live-accounts.json`. Final regression and activation
results are in [acceptance.md](acceptance.md).
