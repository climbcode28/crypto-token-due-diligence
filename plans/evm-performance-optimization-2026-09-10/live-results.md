# Live acceptance run — PONS on Robinhood Chain (4663), 2026-09-10

Workspace `research/pons-acceptance-20260910T192059Z` (ignored). Host: Claude Code, this
project's copy of the skill, two `Agent` lanes (`evm-liquidity-lane`, `evm-project-lane`),
authorized dRPC. Same token as the 18.9-minute and 45.1-minute baseline runs.

## Wall clock (from `broad_collect.py start`)

| Elapsed | Event |
| --- | --- |
| 0:00 | pipeline start; `facts.json` at 0:12 (four pinned phases, 138 RPC reads, source matched) |
| 0:13 | lanes pre-charged, briefs printed |
| 2:09 | both lanes spawned (late: the coordinator read facts first; the runbook now says spawn first) |
| 2:44, 3:02 | presets 1–2: launch factory and legacy locker getters |
| 4:40 | liquidity lane note composed (one repair: invented dimension/status names; briefs now enumerate the allowed names) |
| 4:59 | project lane note composed (same repair class); it supplied the launch transaction hash from the project docs |
| 5:22, 5:49, 6:51 | presets 3–5 under the decision-critical custody trigger: launch receipt, launch position NFT, actor code/balances |
| 8:44 | coordinator note written |
| 9:59 | `finalize` composed, froze and delivered (two compose repair rounds: a scope-id reference bug, since fixed, and one nonexistent alias) |

Session ledger: 249 charged operations of a 260 allowance (400 ceiling), 17 phase marks.
Lanes used 8 and 9 web requests against 30 pre-charged each (default lowered to 20).

## Result versus the baselines

Delivered report: 23 findings, 15 summary rows, 215 evidence rows, 16 scopes, 2 pins, all
eleven ratings with coverage. Parity with the 18.9-minute report:

| Key conclusion | 18.9-min baseline | This run |
| --- | --- | --- |
| Token controls, source match | fixed supply, no mint/upgrade, matched | same, plus launch-limit expiry shown from the header's L1 height |
| Canonical pool and locked share | locker NFT 14.63% of active liquidity | locker NFT 109216, no approval, 14.48% of active liquidity |
| Quotes at three sizes | yes | yes (0.60% impact at 100k) |
| Burned share | 30.39% | 30.40% |
| Launch receipt decoded | yes | yes (mint, pool seed, 6.81% initial buy to a distinct recipient) |
| Creator flow after launch | early recipient transfers reconciled to burns | not reconciled (explorer HTML shells, JSON API 403); recorded as a gap with the route named |
| Admin authority | factory owner 171-byte contract | 2-of-3 Safe with three EOA signers, also protocol fee recipient, holds 0.30% |
| Adoption, promotion, docs, entity | repo + DefiLlama | Dexscreener volume and paid profile order; docs name this exact deployment; entity is an LLC without roles |
| Quote-asset dependencies | WETH only | USDG proxy and WETH |
| Audit | none found | none found |

One baseline conclusion was not reproduced (recipient burned its initial inventory); the
run recorded it honestly as unresolved rather than asserting it. Everything else matches or
exceeds the baseline, in **10.0 minutes** versus 18.9 and 45.1.

## What the run taught (all fixed before this record)

- Lanes invent dimension, status and topic names unless the brief enumerates them; the
  briefs now carry the allowed names and cap summary rows per lane at two.
- The coordinator must spawn lanes before reading facts; the runbook and SKILL.md say so.
- Declaring a readable scope id for an already auto-scoped address failed; compose now
  renames the scope and every reference (regression added).
- Getters absent from a verified ABI are not probed and have no alias; the facts summary
  now says "not in verified ABI (not probed)" instead of `None`.
- Expected next run with these fixes: about 7 minutes (lanes at 0:30, no repair rounds).

## Second live run (Codex, GPT-5.6 Sol Medium): 12 min 45 s, and what it taught

Same token, public Robinhood RPC with free flags. Completed report; 73 coordinator turns.
Forensics from the Codex rollout (main session plus two lane sessions):

| Bucket | Time | Share |
| --- | --- | --- |
| Coordinator model time (thinking and typing, 73 turns) | 11.2 min | 86% |
| Waiting on lanes (`wait_agent`) | 54 s | 7% |
| Process execution (Python helpers, RPC, web, shell) | 43 s | 6% |
| of which Python CPU | about 20 s | 3% |

RPC phases: 9.6 s wall clock for 30 s of summed request latency (four in flight). A Rust or Go
rewrite of the helpers would therefore save 15–25 s per run; the turn count is the lever.

Where the turns went, and the workflow 3.1.0 / backend 3.3.0 change for each:

| Loss | Cause | Fix |
| --- | --- | --- |
| 2.5 min, three workspaces | Head `eth_chainId` failed on transport (DNS, then HTTP) but was reported as "RPC chain does not match"; the model debugged env-variable names | Structured `start_failed` diagnostic distinguishing transport failure from chain mismatch; one transient retry inside the collector; identical command restarts in the same directory (`failed-attempt-N/` kept) |
| 1.5 min, 2 gaps of 74 s and 35 s | The 4,900-token brief was retyped as the spawn prompt (generation time) | `start` writes `lanes/<lane>/brief.md` and prints one-line pointer prompts; briefs forbid reading other runs |
| 1.1 min | Lane notes needed hand repairs (claim named with a strength value, Unverified on a non-gap, missing gap finding) | Briefs list every allowed name and the five common rejections; lanes must run `compose --check` before returning; compose explains the claim/strength confusion |
| 2.5 min | Coordinator read `compose.py` (50 s) to learn the note schema, then hand-wrote an 18.8 KB note (94 s) | `bundle_assemble.py scaffold` writes the skeleton (scope, eleven coverage keys prefilled from lane notes, alias hints, TODO markers that compose rejects) |
| 1 min, two finalize rounds | `historical_execution` without `receipt_evidence_id` raised KeyError at freeze; `checked` coverage with open gap findings refused generically | Compose fills receipt id and result, derives target-token effects from the receipt, names the exact execution shape; checked+gaps downgrades to partial with a boundary or gives the exact fix; report_profile names missing keys |
| Two false gaps | `owner()` on the pool and `getOwners()` on the factory reverted (functions absent) and were logged as `unavailable` operations with lost coverage | Reverts are `observation_status: reverted`, marked per contract in facts, printed as answers, never operational observations |

Codex's own network-approval review agent ran for six minutes in the background during the
false starts; the first start failed with DNS resolution before approval. The restart path
above absorbs that without new workspaces.

Expected effect: about 35–45 coordinator turns and 7–9 minutes on the same model. This is a
projection from the forensics; a live 3.1.0 acceptance run has not been recorded yet.

## Third live run (Codex, GPT-5.6 Sol Medium) on 3.1.0: 6 min 42 s, but thin

Completed report, 34 coordinator turns, five findings and three Unverified summary rows for a
token with 91k indexed holders and a $420M indexed market cap. Root cause, from the run's
discovery captures and rollout: Cloudflare returned 403 to the fetcher's Chrome-style agent on
Blockscout (and, later that evening, to the default Python agent on the public RPC), so the
creation transaction was never discovered; without it no receipt, position, custodian, Safe or
launch-integrity read happened, both lanes reported gaps, and the coordinator ran no presets.

## Workflow 3.2.0 / backend 3.4.0: depth without turns (pipeline smoke, 2026-09-11)

`broad_collect.py start --no-lanes` against the public Robinhood RPC with free flags:

| Measure | Value |
| --- | --- |
| Pipeline wall clock | 14.1 s (phases 29 + 114 + 25 + 10 RPC requests, 8 explorer captures) |
| Explorer access | Blockscout API answered every request with the Safari-style agent (creation tx, counters, top-50 holders, transfers, signer transactions and token transfers) |
| Pipeline note | 11 findings composed with zero errors: controls (matched source, slots, supply, launch limits), launch execution (100% mint → pool seed → 6.81% initial buy → NFT 109216), position custodian + 2-of-3 Safe, pool depth (6.31M PONS + 1,284.8 WETH) with quotes, one receipt-verified sale, holder distribution (dead 30.44%, top-10 EOAs 8.68%, 91,417 holders), five side pools with reserves, admin owners, proxy dependencies, maturity (59.3 days, $24.1M liquidity, $105.8M 24h volume, $421M market cap), signer activity |
| Scaffold | `signals` skeleton for all 11 pipeline findings; every coverage key prefilled or TODO |

Two public-RPC behaviours surfaced and were fixed in the same pass: a fresh head pin returned
"unsupported block number" from lagging backends (now pinned three blocks behind the head and
retried as node lag), and the endpoint refuses the default Python agent (browser-like agent on
the transport). A full live 3.2.0 run with lanes and coordinator is the next measurement; the
expected report carries at least eight summary rows with Good/Potential Risk from the pipeline
observations and Unverified only for what no route could establish.
