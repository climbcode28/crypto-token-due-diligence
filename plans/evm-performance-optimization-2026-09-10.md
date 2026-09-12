# EVM diligence performance plan — target 5–10 minutes end to end

Drafted 2026-09-10 from a read-only audit of the canonical skill, the Claude Code copy,
seven saved PONS/AI/HOOKR research runs, their SQLite ledgers and collector telemetry, and
the Codex and Claude Code session transcripts of the two most recent PONS runs. No token
research was rerun and no frozen evidence was changed. Goal: ordinary broad EVM diligence
completes in **5–10 minutes** while still reporting every key conclusion the current
skill assesses (controls, LP custody, exits, concentration, launch/creator flows, fees,
adoption, economics, delivery, dependencies, disclosure).

## 1. Thesis

The network is not the bottleneck; the model's turn count is. In the 45-minute PONS run,
all ten RPC collections together spent **24.6 seconds** on the wire (median request 0.20 s).
The rest was model turns at 16–28 s each: reading 27,000 words of instructions, exchanging
~100 lane messages, running budget ceremonies, hand-writing collection plans, installing
a Keccak library, and then writing and debugging a 43 KB bespoke report-assembly script.
Every one of the eleven saved runs wrote its own assembly/discovery script. The plan below
replaces those recurring model-authored steps with shipped deterministic helpers, cuts the
lane protocol to one return message, and puts the run on a fixed 8-minute schedule.

## 2. Measured baseline

### Runs

| Run (workspace) | Host / lanes | Wall clock | Main-session turns | s/turn | Charged ops | Delivered | Findings / summary rows |
| --- | --- | --- | --- | --- | --- | --- | --- |
| pons-2026-09-10-01a08c0f | Codex, 3 lanes | 45.1 min | ~130 | 28 | 362 | yes, engine 2.5.0 | 23 / 8 |
| pons-20260910-01 | Codex, 2 lanes | 18.9 min | 68 | 16.5 | 190 | yes, engine 2.6.0 | 20 / 9 |
| pons-20260910T153836Z | Codex | 19.1 min | — | — | 272 | no | — |
| pons-2026-09-10-fresh | Codex | 24.5 min | — | — | 200 / 200 exhausted | no (checkpoints) | — |
| pons-20260909T1831Z | Codex | 8.2 min | — | — | 85 | yes, 2.0.0; all 11 ratings unknown | 7 / 7 |
| pons-20260910T0040 | Codex | 8.5 min | — | — | 91 | yes, 2.3.0 | 18 / 9 |
| ai-artificial-inu-2026-09-08 | Claude Code, 3 Agent lanes | ~29 min to bundle | — | — | — | bespoke build_bundle.py | — |

The three 8-minute runs predate the completion-quality repair and delivered mostly-unknown
ratings, which the user rejected. The 17-minute run (`pons-20260910-01`) is the current
quality bar: it reached the same key conclusions as the 45-minute run (fixed supply, no
mint/upgrade path, locker covers a minority of active liquidity, three-size quotes, 30.39%
burned, creator initial allocation burned not sold, published repo, indexed adoption figures,
explicit unknowns). The target is that report's substance in a third of the time.

### Where the 45 minutes went (coordinator session)

| Window | Activity | Cost |
| --- | --- | --- |
| 0:00–1:45 | Read AGENTS/HANDOFF/README + 4 references, hand-fill work plan, init session, provider check | 10 turns |
| 1:45–6:00 | Spawn lanes at 2.1, 2.4 and 5.9 min; each lane re-loads the skill and reads ~26 reference files | 3 lanes × ~90 turns |
| 6:00–32:30 | 10 collector runs (24.6 s network total), 12 recorded reviews + 4 replans, 22 send_message + 6 followup_task out, ~70 lane messages in, 3 hidden browser tabs, 9 Sourcify lookups | ~75 turns |
| 32:30–37:50 | Write `assemble_report.py` (43 KB) | one 293 s generation |
| 37:50–43:00 | Run/fix it; context compaction at 39:20 (227K → 83K tokens) forced re-reading the script just written | 268 s gap + turns |
| 43:00–48:40 | Freeze/validate repair loop (“provenance lacks scope identity”, ID collisions), deliver | ~10 turns |

### Where the 19 minutes went (current-best run)

| Window | Activity |
| --- | --- |
| 0:00–1:45 | Context, intake, bootstrap |
| 1:45–4:00 | Spawn 2 lanes, import, Sourcify lookup, inline JSON inspection scripts |
| 3:25–4:30 | Hunt for a Keccak library, `pip install pycryptodome` into the run (382 files) |
| 6:00–9:30 | Write `plan_reads.py`, `discover_logs.py`, `exit_plan.py`; run collectors; one collection invalid, redone as `state-fixed` |
| 6:50–7:20 | Read `rpc_collect.py` / `investigation.py` source to learn the helper API |
| 11:50–15:00 | Write `assemble_findings.py` (26 KB), 187 s generation |
| 15:00–18:10 | 12 turns fixing validator errors (“invalid support binding”), then `deliver` |

### Recurring taxes across all Sep 10 sessions (main + lanes)

| Tax | Evidence |
| --- | --- |
| Per-fetch budget charging in lanes | 62, 84, 58, 34 `investigation.py charge` calls in the four 45-min lanes; 39 and 24 in the 17-min lanes. Each is a shell turn before a web read. |
| Budget ceremony in the coordinator | 12 reviews + 4 replans (45-min), 3 + 1 (17-min); each a turn plus a hand-edited 11-surface work plan |
| Instruction volume | 27,127 words across SKILL.md + 14 broad-mode references, plus 4,019 words of AGENTS/README/HANDOFF; every lane re-read 26 files; contexts reached 228–234K tokens in all three 45-min lanes |
| Reading helper source instead of docs | 42 `sed/rg` reads of scripts in the 45-min main, 27 in the 17-min main |
| Keccak absent | 3 runs implemented it (pip pycryptodome, `solc` compilation of a PoolKey contract, hand-written keccak.py) |
| Bespoke assembly | 11 of 11 runs wrote a report/findings builder (13–43 KB); 45-min run also wrote `finalize_handoff.py`, `reconcile_*.py`, `derive-rebalance.py` |
| Header/pin overhead | 12 chain-ID + 60 header reads = 20% of the 45-min run's 362 charged ops, from 12 separate collector invocations |
| Raw JSON in context | 663 KB draft, 549 KB manifest; inline `cat`/`python3 -` dumps drove the compaction |

Validation is not a cost: the current validator runs in 0.15–0.27 s on both bundles.

### Discovery endpoints checked today (one request each)

Dexscreener `token-pairs/v1/robinhood/<token>` returned 30 pairs in 0.16 s. Robinhood
Blockscout `api/v2` returned HTTP 403 to a curl request even with a browser user agent,
matching the earlier memory note that Blockscout flakes. The pipeline must treat explorer
JSON as optional with RH Scan / Robinscan page capture as the documented alternate.

## 3. What does not change

- Exact `(chain ID, token address)` identity, `eth_chainId` verification, numbered pins with
  fresh rechecks, no `latest`, redaction, the read-only method allowlist, session accounting,
  paid-use gates and the private env sourcing rule.
- Strict profile `evm-evidence-v2`, eleven dimensions, four-axis decision review, Good /
  Potential Risk / Bad / Unverified semantics, and the rule that unknowns never pass.
- Fresh investigation per run; no reuse of earlier token evidence.
- Frozen historical bundles, engine snapshots and replay.
- Canonical folder is edited first; the Claude Code copy mirrors it per `CLAUDE-CODE-PORT.md`.

## 4. Workstreams

Ordered by expected saving. Each lists the mechanism, evidence, files, tests and saving.

### WS1 — Compose layer: compact lane notes → strict report (largest saving)

**Problem.** A strict finding needs 21 fields plus typed `support` rows, `concern`, per-surface
`coverage_records` with `closure`, eleven `ratings`, `summary`, `decision_review` and every
evidence address as a `scope` entry with runtime/proxy status. No run could author this by
hand, so every run generated a 13–43 KB Python builder and then debugged validator errors.

**Change.** Add `bundle_assemble.py compose DRAFT NOTE.json` that accepts a compact note and
deterministically expands it:

```json
{
  "findings": [
    {"id": "token-controls", "dimension": "token_controls", "topic": "token_and_liquidity",
     "signal": "Good", "claim": "source_analysis", "strength": "strongly_supported",
     "confidence": "high", "impact": "benefit", "subject": "target",
     "text": "Matched runtime is a fixed-supply ERC-20 with no mint, seizure, tax, pause or upgrade path.",
     "evidence": ["runtime", "source-match-token", "owner", "metadata-total_supply"]}
  ],
  "coverage": {
    "token_controls": {"status": "checked"},
    "canonical_lp_principal_custody": {"status": "partial", "gap": "...", "priority": "decision_critical",
      "attempts": [{"check": "...", "outcome": "...", "evidence": ["nfpm-positions", "locker-runtime"]}],
      "boundary": "unavailable", "basis": "...", "next_check": "..."}
  },
  "decision": {"verdict": "findings_with_limits", "scope": "...", "synthesis": {"technical_exposure": "...", "...": "..."},
               "actions": []},
  "text": {"verdict": "...", "conditions": "...", "main_reasons": "...", "strongest_contrary_evidence": "...",
           "unresolved_questions": "...", "change_evidence": "..."}
}
```

The expander:

- resolves evidence aliases with the existing `resolve_evidence` (exact original IDs, address/pin disambiguation);
- derives `support` roles mechanically: `direct` for same-address evidence at the finding pin, `source` for source-match artifacts, `identity` for runtime rows of other scopes, `calculation` for derived rows, `failed_attempt` for gap rows; sets `evidence_ids` to the union;
- derives `participant_scope_ids` from evidence addresses and auto-creates missing `scope` entries from collected runtime rows (status, SHA-256, EIP-1967 slot reads when present, proxy `unresolved` otherwise);
- builds `coverage_records` + `closure` from the compact form, mapping `boundary` to the validator's dispositions and copying attempt evidence into the surface's evidence list;
- derives `ratings` from findings per the existing pass/concern/unknown rules, and `summary` from findings that carry a `topic`;
- fills the `decision_review` with the axis conclusions, deriving `finding_ids`/`coverage_dimensions` from the findings' dimensions, and copies `concern` objects onto adverse findings from `mechanism`/`consequence` fields;
- runs `preflight` and prints all errors at once with the note field that caused each.

Add `bundle_assemble.py finalize DRAFT --out REPORT` = compose → check → freeze → deliver in one process, printing the report path or the first blocking error. Add `bundle_assemble.py facts DRAFT` that prints a compact (≤ 8 KB) decoded view of the draft (pins, metadata, decoded getters, balances as decimals, pool composition, quote outputs, evidence alias list) so the coordinator never dumps raw JSON into context.

**Files.** `scripts/bundle_assemble.py` (new subcommands, ~250 lines), `assets/lane-note.template.json`, `references/compose.md` (short field guide), `tests/test_compose.py` (note → valid freeze; every validator failure class mapped to a note-level error message; adverse finding without mechanism rejected; alias ambiguity surfaced; idempotent recompose).

**Saving.** 5–8 minutes per run (script generation 3–5 min + 10–12 repair turns). Removes the largest single wall-clock item in both measured runs.

### WS2 — One-shot standard broad collection pipeline

**Problem.** Each run hand-writes 6–12 collector plans as inline Python, runs them as separate
processes (each paying chain + header + recheck), and derives selectors/topics/PoolIds by
installing libraries. Plans fail (`state` invalid → `state-fixed`) and get redone.

**Change.** Add `scripts/broad_collect.py` (a composition over the existing `Collector`,
`bootstrap`, `source_lookup` and session helpers; no new transport):

1. **Start** (`broad_collect.py start --chain-id --address --run DIR --question ... [provider flags]`): creates the workspace, initializes the session from a built-in standard plan (see WS6), writes `intake` draft, runs the offline availability check, and returns within 2 s with `discovery.json` scheduled.
2. **Discovery, parallel threads (~10 s):** Dexscreener exact-address pairs (dedupe by pair address; v4 needs manager/key), Sourcify `intake` and `correspondence` profiles for the token, optional explorer JSON (Blockscout v2 with browser UA; on 403 record the gap and leave the RH Scan / Robinscan alternate to the liquidity lane), token GitHub/website links from the Dexscreener `info` block for the project lane brief.
3. **RPC phase 1, one collection:** chain, head, header pin, runtime, four metadata, standard control getters (`owner`, `paused`, EIP-1967 implementation/admin/beacon slots, `getRoleAdmin`/`hasRole` only when the ABI exposes them), and, when Sourcify returned an ABI, every zero-argument view getter that the ABI exposes (selectors derived with the bundled Keccak from WS3, ABI as the verified signature source). Clone classification as today.
4. **RPC phase 2, same pin, second collection derived from phase 1 + discovery:** per discovered pool `token0/token1/fee/liquidity/slot0` (v3), `getReserves` (v2) or PoolManager `getSlot0/getLiquidity` with a Keccak-derived PoolId (v4); NonfungiblePositionManager `positions/ownerOf/getApproved` for position IDs named in the launch receipt logs; balances (`balanceOf`) of dead address, each pool, creator, launch recipient and lockers; creation and launch receipts (from discovery) at their historical pins; QuoterV2 static quotes at three sizes on the canonical pool when a quoter address is known for the chain (configurable table, Robinhood entries recorded from the saved runs, verified by `eth_getCode` in the same batch). Recognized launch platforms (Pons V1/V2 getters seen in saved runs: `deployer`, `launchFactory`, `liquidityPool`, `pairToken`, `poolFee`, `maxTxBps`) get their getter presets; unrecognized platforms skip to generic reads.
5. **Final rechecks**, then `facts.json`: decoded values with evidence aliases (owner, supply, decimals, balances in decimal units, pool composition and percent of active liquidity per position, quote outputs and size impact, position owners/approvals, proxy slots, source-match status, receipt-decoded ERC-20 transfers with actor roles), plus a per-surface `coverage_hint` (which of the eleven surfaces already have observations, which have none).
6. Imports both collections into the draft and registers the source-match artifact. Writes phase timestamps into the session ledger (WS7).

Two collections instead of twelve cuts pin overhead from 72 reads to 6 and removes plan
authoring turns. Expected duration: 20–40 s for ~120–180 reads at the measured 0.2 s latency
with 4 workers, plus ~10 s discovery. Add `--preset` follow-ups for the coordinator's
judgment calls: `receipts --tx H1,H2` (receipt + tx at historical pins), `positions --pool P
--ids ...`, `logs --address A --topic T --from --to` (bounded, adaptive range), `getters
--address A --abi FILE`, `balances --asset A --holders ...`. Each preset is one command, one
collection, same session and cache.

**Files.** `scripts/broad_collect.py`, `scripts/presets.py` (plan generators), `assets/chain-registry.json` (per-chain quoter/NFPM/PoolManager candidates, verified live by code reads), `tests/test_broad_collect.py` using the existing fixture transport (full synthetic run ends with a deliverable draft and zero network), `tests/test_presets.py`.

**Saving.** 3–5 minutes (plan authoring, redo of invalid plans, 10 collector turns → 1–3, no per-collection review ceremony). Also removes ~60 pin-overhead requests per run.

### WS3 — Bundled Keccak-256 and ABI helpers

**Problem.** The skill states that `hashlib.sha3_256` is not Keccak and offers no substitute,
so runs installed pycryptodome, compiled Solidity with `solc`, or wrote `keccak.py`.

**Change.** Add `scripts/keccak.py` (pure standard-library Keccak-f[1600], ~80 lines) with
test vectors (`keccak256("")`, `transfer(address,uint256)` → `a9059cbb`, the ERC-20 Transfer
topic, a known v4 PoolId from the saved PONS evidence). Extend `evm_decode.py`: `selector SIG`,
`topic SIG`, `poolid --currency0 --currency1 --fee --tick-spacing --hooks`, `create2`, and
`calldata` for any signature with static types (dynamic types still rejected). ABI signatures
come from Sourcify/verified ABI captures; the docs keep saying selectors are leads, not
semantics.

**Files.** `scripts/keccak.py`, `scripts/evm_decode.py`, `tests/test_keccak.py`.

**Saving.** 1–2 minutes when selectors/topics/PoolIds are needed (every Robinhood run so far).

### WS4 — Lane protocol: brief in, one note out, hard cutoff

**Problem.** Lanes ran 27–40 minutes, each re-read the skill and ~26 references, hit ~230K
context, charged the budget before every fetch (up to 84 shell turns per lane), and streamed
~70 interim messages that each cost the coordinator a turn.

**Change.**

- Two lanes, not three: **liquidity/market** and **project/creator**. Controls stay with the
  coordinator because they are RPC-driven and the coordinator owns RPC.
- `broad_collect.py brief --lane liquidity|project` prints a ≤ 1,500-word self-contained brief:
  target/pins, `facts.json` excerpt, the lane's checklist (from `source-routing-and-execution.md`
  distilled), the output note schema, the fetch helper command, and the stop rule. The brief
  says explicitly: do not read SKILL.md or references, do not call `investigation.py`, do not
  write scripts, return one note.
- Coordinator pre-charges each lane once at spawn (`investigation.py charge --operation
  lane_project --count 30`); lanes report actual fetch counts in the note. Conservative
  accounting is preserved; ~60 shell turns per lane disappear.
- Lanes return **one** note in the WS1 schema (findings, coverage rows for their owned
  surfaces, captured URLs with retrieval times) plus their captured files. No interim messages
  except a single optional mid-point handoff if the coordinator asks.
- Hard lane cutoff **4 minutes** wall clock from spawn, stated in the brief; the coordinator
  proceeds at 4:30 with whatever returned and records absent lanes as not-checked surfaces.
- Claude Code: define `.claude/agents/evm-liquidity-lane.md` and `evm-project-lane.md` with
  `tools: Read, Write, WebFetch, WebSearch, Bash` (Bash for the fetch helper only), no Agent,
  `model` left to default. Codex: the spawn message is the brief; the brief's first line tells
  the lane to ignore the auto-injected skill text.

**Files.** `scripts/broad_collect.py brief`, `references/lane-briefs.md` (the two checklists),
`.claude/agents/*.md` (Claude copy only), `tests/test_lane_note_roundtrip.py`.

**Saving.** Lane wall time 27–40 min → ≤ 4 min; coordinator loses ~40 inbound-message turns.

### WS5 — Bounded web capture helper

**Problem.** Lanes wrote `fetch-public.py`, `apply_patch` files per page, or used hidden
browser tabs for JSON that a documented API serves; Claude Code `WebFetch` returns a summary,
not raw bytes, so evidence provenance is weak.

**Change.** Add `scripts/web_capture.py URLS.json --out DIR --session S` (batch, 4 threads,
browser UA, 20 s timeout, 16 MB cap, redirects recorded, raw bytes + `provenance.json` with
URL, status, retrieval UTC, SHA-256, and a ready `artifact` descriptor). Presets:
`--preset dexscreener|sourcify|blockscout|github-tree|github-file`. On 403/JS-only shells it
records the gap and names the alternate. Lanes call it once per batch instead of per page.

**Files.** `scripts/web_capture.py`, `tests/test_web_capture.py` (fake opener), doc line in the lane brief.

**Saving.** 1–2 minutes per lane; better evidence than summaries.

### WS6 — Instruction diet and context hygiene

**Problem.** 27K words of mandatory broad-mode reading; SKILL.md is 228/290 lines (Claude Code
guidance targets under 200); the Claude copy also injects paths only, so the model still
spends a turn reading HANDOFF. Raw JSON dumps drove a mid-assembly compaction.

**Change.**

- New `references/runbook.md` (≤ 800 words): the exact 7-command sequence with expected
  durations and the decision points between them. Broad mode reads SKILL.md + runbook only;
  the other references become trigger-loaded (they already carry triggers).
- SKILL.md trimmed to ≤ 180 lines: identity/pins/evidence rules, the runbook pointer, labels,
  delivery gate, credentials rule. Policy prose that duplicates references is removed, not
  rewritten.
- `provider_context.py --policy` prints the current-policy section of HANDOFF (first heading)
  in addition to paths; the Claude copy's `!` injection uses it so provider policy arrives at
  load with zero turns. Codex runs it once.
- Explicit rule: never `cat` collection/draft/manifest JSON; use `bundle_assemble.py facts`.
  `broad_collect.py` prints ≤ 40 lines per command.
- Work plan: `broad_collect.py start` fills `work-plan.json` from the standard plan's phase
  estimates; the model edits it only when it adds presets.

**Files.** `SKILL.md` (both copies), `references/runbook.md`, `scripts/provider_context.py`,
`assets/work-plan.template.json` defaults, `tests/test_provider_context.py`.

**Saving.** 1–2 minutes at start; smaller contexts make every later turn faster (measured
16–28 s/turn at 160–230K context).

### WS7 — Budget ceremony folded into the pipeline

**Problem.** Reviews and replans were run manually 16 times in the 45-min run and the template
forced 11 hand-estimated numbers at intake, which produced a 400-request / 2,700-second
opening plan.

**Change.** `broad_collect.py` runs `review` internally before phase 2 and before each
preset and prints the action inline; `replan` remains explicit and rare. Add phase
timestamps (`intake`, `discovery`, `phase1`, `phase2`, `lanes_spawned`, `lanes_returned`,
`composed`, `frozen`, `delivered`) to the session ledger and a `status --timeline` view. The
frozen report's context block records the phase timings so every run self-benchmarks.

**Files.** `scripts/investigation.py` (timeline table, additive schema 3 with schema-2 reads intact), `scripts/broad_collect.py`, `tests/test_budget_replanning.py` additions.

**Saving.** ~10 turns per run; produces the live benchmark the README says is missing.

### WS8 — Fixed schedule and cutoffs

Standard run, times from invocation:

| Minute | Coordinator | Lanes |
| --- | --- | --- |
| 0:00–0:30 | Policy excerpt (injected or 1 turn); `broad_collect.py start` | — |
| 0:30–1:30 | Pipeline runs in background; coordinator spawns both lanes from `brief` as soon as `discovery.json` exists (~15 s) | Start fetching |
| 1:30–2:00 | Read `facts`; decide ≤ 2 presets (e.g. locker/position, extra receipts) | — |
| 2:00–3:30 | Run presets; source-match surrounding contracts if discovered | — |
| 4:00–4:30 | Lane notes due (hard cutoff at 4:00) | Return one note each |
| 4:30–6:00 | Write the coordinator note (controls, exits, custody, concentration, decision, texts); `finalize` | — |
| 6:00–7:00 | One repair round at most; chat answer from the frozen report | — |
| 10:00 | Cap. Beyond it: `freeze --checkpoint`, and continue only for a named decision-critical trigger with a one-line explanation | — |

Target 5–7 minutes typical, 10 cap. The cap is a schedule, not a new evidence threshold;
the completion gate still rejects `pending`/`not_checked` surfaces (see section 6).

### WS9 — Host-specific plumbing

**Claude Code copy.**

- SKILL.md frontmatter: `allowed-tools` for `Bash(python3 *)`, `Bash(set +x*)`, `Read`,
  `Write`, `Agent`, `WebFetch(domain:api.dexscreener.com)`, `WebFetch(domain:sourcify.dev)`,
  `WebFetch(domain:github.com)`, `WebFetch(domain:raw.githubusercontent.com)`,
  `WebFetch(domain:rh-scan.com)`, `WebFetch(domain:robinscan.io)`,
  `WebFetch(domain:robinhoodchain.blockscout.com)`, `WebSearch`. Documented behavior:
  pre-approval lasts for the invocation turn.
- Add project `.claude/settings.json` `permissions.allow` with the same Bash/WebFetch patterns
  so multi-turn runs do not stall on prompts (project-level is the documented place for a
  shared allowlist; `settings.local.json` stays personal).
- `!` injection: keep the `|| echo` guard (a failing command aborts the skill; 2-minute timeout).
  Add the `--policy` excerpt.
- Run the pipeline with `run_in_background: true` and wait with `Monitor` on `discovery.json`
  and `facts.json` rather than polling; launch both `Agent` lanes in one message.
- `.claude/agents/evm-*-lane.md` as in WS4.

**Codex (canonical folder).**

- Add `agents/openai.yaml` (display name, short description, default prompt) like the sibling skills.
- Spawn lanes with the brief; lanes are told to ignore the auto-injected skill body.
- Use `write_stdin` polling only for the background pipeline; no per-fetch shell turns.

### WS10 — Versioning, mirroring, verification

- Versions: workflow **3.0.0** (orchestration changes), backend **3.2.0** (pipeline, presets,
  Keccak, fetcher; transport/accounting unchanged), reporting **2.7.0** (compose is additive;
  profile unchanged). Release JSONs record this plan as `review_record`.
- Keep all 317 existing tests green in both copies; add the suites named above. Add a
  synthetic end-to-end test: fixture transport → `start` → presets → compose → `finalize` →
  `deliver`, asserting zero network, a valid frozen bundle, and total helper time under 5 s.
- Mirror to the Claude copy per `CLAUDE-CODE-PORT.md`; `diff -rq` must show only the documented
  differences plus the new `.claude/agents` files and frontmatter block.
- **Live acceptance:** one fresh PONS run per host after implementation. Record phase timings
  from the ledger in `plans/evm-performance-optimization-2026-09-10/live-results.md`. Pass
  criteria: `deliver` succeeds; wall clock ≤ 10 min (target ≤ 7); no bespoke script written;
  coordinator ≤ 35 turns; and the parity checklist below is met against `pons-20260910-01`.

**Parity checklist (must appear in the new report with evidence links):** token control
conclusion with source-match status; owner/proxy/upgrade status; canonical pool identity and
locked-position share of active liquidity; three-size quotes with impact; historical sale
evidence or explicit gap; burned/dead share and denominator; creator initial allocation and
its disposition; creation/launch receipt decoded; fee recipient/treasury authority; adoption
figure with source and window; repo/source disclosure; quote-asset dependency status; all
eleven ratings with coverage; explicit Unverified rows for anything not established.

## 5. Expected effect

| Item | Today (measured) | After |
| --- | --- | --- |
| Instruction reading at start | 1.5–1.7 min, 27K+4K words | ≤ 0.5 min, ≤ 4K words |
| Collector invocations / pin overhead | 7–12 runs, 36–72 pin reads | 2–4 runs, 6–12 pin reads |
| Keccak / selector work | 1–1.5 min (pip, solc) | 0 (bundled) |
| Lane wall time | 10–40 min | ≤ 4 min |
| Coordinator inbound lane turns | ~70 | 2 |
| Budget ceremony turns | 16 (45-min), 4 (17-min) | 0–2 |
| Report assembly | 3–5 min script + 10–12 fix turns | 1–2 turns |
| Coordinator turns | 68–130 | ≤ 35 |
| Peak context | 161K–234K tokens | < 100K |
| End to end | 18.9 / 45.1 min | 5–7 min typical, 10 cap |

These are projections from the measured turn costs; the live acceptance run in WS10 is the
proof.

## 6. Policy reconciliation the user must confirm

The completion policy (`completion-and-delivery.md`) says feasible required work cannot be
deferred, and the freeze gate rejects `pending` surfaces. A 5–10-minute run is compatible
only if “feasible required work” is defined by the **standard scope**: the pipeline's phase
1–2 reads, the two lane checklists, and at most two coordinator presets. Anything beyond is
deepening on a conclusion-changing trigger, which may use the 10-minute cap and, past it,
either a checkpoint or an explicitly explained overrun (current policy). Recommended wording
for `completion-and-delivery.md`: “A completed ordinary review is the standard scope
executed to its stopping rules; additional work requires a named trigger.” This keeps the
eleven-surface floor and the no-pass-for-unknowns rule while making the time target
achievable. If the user prefers unbounded deepening instead, the 10-minute target cannot be
promised for every token, and the plan still removes 15–35 minutes of overhead.

Other decisions: two lanes (recommended) or three; a committed project `.claude/settings.json`
allowlist (recommended) or personal `settings.local.json`; whether explorer JSON access
(Blockscout 403 today) is worth a browser-based alternate inside the pipeline or stays a
lane responsibility (recommended: lane responsibility, RH Scan / Robinscan pages).

## 7. Risks and non-goals

- The pipeline's generic getters depend on Sourcify ABI availability; unverified tokens fall
  back to the fixed getter set plus storage slots, and `facts.json` says so.
- Quoter/NFPM/PoolManager addresses per chain must be verified by code reads each run; the
  registry is a candidate list, never identity.
- Compose cannot judge prose truth; the semantic review step in `decision-review.md` remains.
- Hosts differ: Claude Code `WebFetch` summaries are not raw evidence; the fetch helper is the
  evidence path on both hosts.
- No change to rubric weights, dRPC authorization, purchases, or the rug-check/Solana skills.
- Not a promise that unavailable facts (position exports, audit reports, identities) become
  known faster; they become explicit gaps faster.

## 8. Implementation order

1. WS3 Keccak + WS1 compose + `facts` (no behavior change to collection; immediate 6–10 min saving; can be validated offline against the saved `pons-20260910-01` draft).
2. WS2 pipeline + presets, WS7 timeline, WS6 runbook/SKILL trim, provider policy excerpt.
3. WS4 lane briefs + WS5 fetch helper, `.claude/agents`, settings allowlist.
4. WS9 host plumbing, WS10 versions/mirror/tests.
5. Live acceptance run on each host; record timings; adjust the schedule table from data.

## 9. Files expected to change

Canonical `skills/crypto-evm-token-due-diligence/`: `SKILL.md`; new `scripts/broad_collect.py`,
`scripts/presets.py`, `scripts/keccak.py`, `scripts/web_capture.py`; edited
`scripts/bundle_assemble.py`, `scripts/evm_decode.py`, `scripts/investigation.py`,
`scripts/provider_context.py`, `scripts/backend_common.py` (SOURCE_FILES list); new
`references/runbook.md`, `references/compose.md`, `references/lane-briefs.md`; edited
`references/completion-and-delivery.md`, `supported-research-flow.md`,
`source-routing-and-execution.md`, `deterministic-backend.md`, `improvement-loop.md`; new
`assets/lane-note.template.json`, `assets/chain-registry.json`, `agents/openai.yaml`; edited
`assets/*-release.json`, `assets/work-plan.template.json`; new tests listed above.
Claude copy: mirrored files plus `.claude/agents/evm-liquidity-lane.md`,
`.claude/agents/evm-project-lane.md`, project `.claude/settings.json`, updated
`CLAUDE-CODE-PORT.md`. Project: `README.md`, `HANDOFF.md`, this plan and its `live-results.md`.

## Implementation record — 2026-09-10

Implemented with the implement-review-improve workflow after the user approved the plan
and its section-6 recommendations (standard scope defines a completed ordinary review; two
lanes; committed project allowlist). Versions: **workflow 3.0.0**, **backend 3.2.0**,
reporting engine **unchanged at 2.6.0** (the validator and renderer did not change; the
plan's provisional 2.7.0 was unnecessary), pipeline 1.0.0, note schema 1, investigation
schema 3, source comparison 1.1.0.

### What was built

| Workstream | Delivered |
| --- | --- |
| WS1 compose | `scripts/compose.py`; `bundle_assemble.py compose | facts | finalize`; `references/compose.md`. Note-level errors are collected and reported together; the draft is untouched on error. Existing scopes can be referenced by id; lane captures are registered on first citation. |
| WS2 pipeline | `scripts/broad_collect.py start | collect | brief | status`; `scripts/presets.py`; `assets/chain-registry.json`; four pinned phases (token; pools/balances/architecture/quote assets/creation receipt; quotes/positions/Safe getters; actor code), Dexscreener/Sourcify/explorer discovery, source match, `facts.json`, `work-plan.json`, automatic in-ceiling replan. |
| WS3 Keccak | `scripts/keccak.py` (permutation cross-checked against hashlib SHA3 at every block boundary; PONS v4 PoolId reproduced); `evm_decode.py selector | topic | poolid`, explicit `--derive`. |
| WS4 lanes | `assets/lane-brief-liquidity.md`, `assets/lane-brief-project.md`, `broad_collect.py brief`; `.claude/agents/evm-liquidity-lane.md`, `evm-project-lane.md`; two lanes, 4-minute cutoff, pre-charged budget, one note each. |
| WS5 capture | `scripts/web_capture.py` (batch, 4 threads, browser UA, redirects recorded, 403/shell detection, provenance, `--register`). |
| WS6 diet | Canonical `SKILL.md` 137 lines (was 228); Claude copy 181 lines (was 290); `references/runbook.md`; `provider_context.py --policy` injected at load in Claude Code; references updated to the standard scope and 5–7 minute schedule. |
| WS7 ceremony | `investigation.py mark` and `status --phases` (schema 3; schema 1–2 sessions still open); pipeline records intake, discovery, phase1–4, facts. |
| WS8 schedule | Runbook and completion reference carry the minute-by-minute schedule and the 10-minute cap rule. |
| WS9 hosts | Claude: frontmatter `allowed-tools`, `.claude/settings.json` allowlist, agent definitions, `run_in_background` + `Monitor` guidance. Codex: `agents/openai.yaml`, brief-based spawning. |
| WS10 | Release JSONs, README, HANDOFF, port notes, mirror; five suites green. |

### Independent review and live acceptance

Two independent reviewers (code review of the new helpers; forward review of the
instructions) returned 29 and 14 findings. All high and medium items were fixed and
regression-tested: lane capture path traversal, `#direct` on documents, control-address
heuristic, incomplete-coverage findings, Bad-in-unavailable coverage, exact subject/pin
evidence, empty summaries, action semantics, staged capture registration, explorer/Dexscreener
identity validation, unbounded decimals, credential URLs, brief JSON validity, lane-absent
path, unready briefs, missing command arguments, focused-question routing, three-lane and
old-target leftovers. The live acceptance run is recorded in
[live-results.md](evm-performance-optimization-2026-09-10/live-results.md): a completed,
delivered PONS report in 10.0 minutes with the parity checklist met except one creator-flow
reconciliation recorded as a gap.

### Verification

| Check | Result |
| --- | --- |
| Canonical EVM suite | 350 tests OK (317 existing + keccak, compose, pipeline, helper and review regressions) |
| Claude EVM copy suite | OK; `diff -rq` shows only the documented differences |
| Market research, rug-check, Solana suites | OK |
| `git diff --check` | clean |
| Synthetic end-to-end | fake RPC + fake fetch → pipeline → two notes → compose → finalize → `deliver` accepted, under 10 s, zero network |
| Real-evidence smoke test | Copy of the saved 17-minute PONS draft, analyst layers reset, one 13-finding coordinator note → `finalize` delivered a completed report in 0.39 s with pass/concern/unknown/not-applicable ratings derived as designed |
| Live pipeline test (PONS, chain 4663, authorized dRPC) | `broad_collect.py start` finished in **11.2 s wall clock**, 157 requests: matched source (solc 0.8.30), six pools with state, three quotes with size impact, 30.40% burned, factory owned by a 2-of-3 Safe with signer code reads, USDG proxy dependency, Dexscreener links; explorer JSON 403 recorded as a gap |

Refinements found by the live test and fixed before acceptance: token-amount getters
(`maxTxAmount` and similar) were misread as addresses and cost 12 reads (name- and
magnitude-aware heuristic now; regression added); control getters absent from a verified
ABI were probed anyway (now only ABI-exposed getters are probed; phase 1 is `complete`);
v4 `getSlot0` values were not surfaced under `slot0`; the post-pipeline review returned
`replan` without acting (now replans inside the ceilings with a recorded reason).
