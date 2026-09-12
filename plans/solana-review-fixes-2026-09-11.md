# Plan: Solana skill review fixes (2026-09-11)

Source: a deep-dive review of `skills/crypto-solana-token-due-diligence` after the v2
refactor (commit 3f44d99 on `archive/pre-publish`, content in the single `main` commit).
The review combined two live public-RPC runs on dogwifhat (`research/solana-review-2026-09-11/`),
a read of the three earlier live ledgers, and six parallel subsystem code reviews
(transport/session, adapters, accounts/programs, transactions/quotes/discovery,
offline pipeline, guidance). All 323 Solana tests passed before any change.

Execution follows the implement-review-improve workflow phase by phase. Never commit
or push. Run the three README unittest suites after each phase.

## Root cause of "live rich-case parity unmet"

Every live run (mine and the three recorded ones) died the same way on the default
public endpoint `api.mainnet-beta.solana.com` (free tier):

1. `getTokenLargestAccounts` is disabled there (HTTP 429, `x-ratelimit-method-limit: 0`,
   `retry-after: 10`). Every run hit it exactly once.
2. `session_request` turned that method-specific 429 into a backoff on the whole RPC
   namespace for ten seconds, and the queue never waits: every later read in the sample
   was refused as `budget_denied` within milliseconds. The critical recheck, headers and
   network recheck were never sent, so the mint fact was unusable, identity stayed
   unresolved, and the related/pool/receipt/program stages were skipped. `start` returned
   in about two seconds with `diagnostics: []`.
3. Per-method free-tier windows are real and low (per 10 s): `getBlock` 6, `getBlockTime` 10,
   `getSignaturesForAddress` 10, `getTransaction` 10, `getProgramAccounts` 10,
   `getTokenAccountsByOwner` 10, `getAccountInfo` 50, `getMultipleAccounts` 50, most
   others 150; connections 40/10 s. The header strategy alone (two `getBlock` per context
   slot per sample) exhausts the `getBlock` window inside one start.
4. No live run ever sent `getSignaturesForAddress` or `getTransaction`, which is why every
   run reported 0/2 verified sales.

`getProgramAccounts` filtered by an LP mint works on the free tier (0.6 s, 1,325 LP
holders for the Raydium WIF/SOL pool), so LP-holder discovery has a free path. No
credential-free alternate endpoint serves `getTokenLargestAccounts` from this machine.

## Phase 1: Public-RPC transport robustness

Files: `scripts/solana_transport.py`, `scripts/solana_session.py`,
`scripts/solana_collect_v2.py`, `assets/network-registry.json`, `assets/release.json`,
`assets/runtime-provenance.json`, tests `test_solana_transport.py`,
`test_solana_session.py`, `test_solana_collector_v2.py`.

Deliverables:

- Catch `http.client.HTTPException` (IncompleteRead, BadStatusLine, LineTooLong) as
  `transport_failure`; always finish the attempt row (try/finally) so no read strands a
  concurrency slot; run `recover_expired()` when the collector opens a session.
- Scope 429/503 backoff to `(namespace, method)` for RPC, never the whole namespace.
  A 429 whose `x-ratelimit-method-limit` header is `0` marks the method unavailable for
  that namespace for the rest of the session (typed status `method_unavailable`, no
  further sends, not a token finding); a 429 without a stated wait imposes no backoff
  because the collector already paces its single retry.
- Wait instead of fail: `LimitError` carries `until`; `execute()` sleeps until the
  backoff, connection window, or per-method window frees (bounded by remaining
  collection time and a 30 s cap), then re-acquires. Waiting is not an attempt.
- Per-method windows from `network-registry.json` (`method_limits_per_10s`) enforced in
  `Session.acquire` with the same wait hint; the 120-attempt ceiling is unchanged.
- Node-lag RPC errors (`-32016`, `-32004`, `-32005`) become the transient `node_lag`
  status so the single retry applies after a short delay; the retry sleeps at least
  `retry-after` or one second.
- Transport opener disables environment proxies; monotonic guard is anchored to each
  cutoff, not the deadline; `consistency()` keys on the data slice so a full read and a
  sliced read of one address at one slot are not contradictory.
- Version bumps: transport, session runtime, collector; provenance differences updated.

Acceptance: synthetic tests for each bullet; the full Solana suite passes; a live
focused start on dogwifhat completes pool, receipt and program samples with no
`network_unresolved` sample and with `getSignaturesForAddress`/`getTransaction` sent.

## Phase 2: Free-path holder discovery, fewer header reads, start diagnostics

Files: `scripts/solana_wire.py`, `scripts/solana_presets.py`, `scripts/solana_accounts.py`,
`scripts/solana_collect_v2.py`, `scripts/solana_import.py`, `scripts/solana_broad_collect.py`,
fixtures `tests/solana_fixture.py`, `tests/broad_fixture.py`, tests.

- Holder scan: a bounded `getProgramAccounts` on the mint's token program with
  `dataSize` 165, `memcmp` on the mint at offset 0 and `dataSlice` (0, 72: mint, owner,
  amount), context included, at most 5,000 rows under the 1 MiB read cap. The collector
  issues it only when `getTokenLargestAccounts` is unavailable on the namespace; the
  scan is a discovery lead ranked by amount, and the same-batch holdings sample and
  denominator follow exactly as for the largest method. `aggregate_holders` accepts either
  discovery and records the discovery method, the number of accounts scanned and the
  scanned total. Token-2022 mints keep an explicit gap (variable account sizes).
- LP-mint leads use the same fallback for SPL LP mints (Raydium AMM v4 and CPMM).
- Program metadata reads become one sliced `getMultipleAccounts` instead of one
  `getAccountInfo` per program-data account (fewer context slots, fewer headers).
- `start` diagnostics report refused methods, unsent reads with reasons and any stage
  that ended unresolved, so the coordinator sees what happened without reading ledgers.
- Presets: `holders` (largest or scan plus the holdings sample) and `pool_activity`
  (`getSignaturesForAddress` on a captured pool, limit at most 25, receipts for the first
  candidates up to four) so a coordinator can recover concentration and receipts.

Acceptance: synthetic tests for the scan validation, the collector fallback, the LP-lead
fallback, program batching and the presets; a live broad start on dogwifhat shows an LP
custody sample and no `network_unresolved` sample.

## Phase 5: Sale verification and quotes (transactions review)

Files: `scripts/solana_transactions.py`, `scripts/solana_import.py`, `scripts/solana_quotes.py`,
`scripts/solana_discovery.py`, `scripts/solana_launch.py`, `scripts/adapters/pump_instructions.py`,
`scripts/solana_broad_collect.py`, tests and fixtures.

- Accept the DEX swap effect at any instruction depth, scoping transfer matching to the
  swap's own subtree by stack height and keeping the exact pool/vault binding; label
  aggregated routes.
- Allow extra transfers out of the same vault only to adapter-declared fee sinks
  (PumpSwap protocol fee and creator vault, DAMM v2 referral, DLMM host fee) and record
  them as protocol fees.
- Derive `rebuys` alongside `sales` from the same candidates; classify candidates before
  spending the receipt budget (fetch until two direct target swaps, at most four).
- Token-2022 trades verify when neither mint carries transfer-fee, hook or confidential
  extensions; accept a missing boundary balance on either side when in-transaction
  creation/closure is proven, reconciling against the vault delta.
- Public quote source `jupiter_v1_lite` (`lite-api.jup.ag/swap/v1/quote`), keyed v2 kept
  as an alternate; the importer derives `public_quote` for captured quote URLs.
- Project links from indexers require cross-source corroboration before automatic
  capture; otherwise they are retained as unverified indexer profiles.
- Launch history operations (`history`, `prior_launches`, `creator_activity`) are derived
  from retained pages and receipts; decode legacy curve `buy` and system
  `CreateAccountWithSeed`/`Allocate`/`Assign`; page limit read from the request.

## Phase 6: Token-2022 metadata and adapter details (accounts and adapter reviews)

- Decode TokenMetadata (type 19), TokenGroup (21) and TokenGroupMember (23); surface the
  metadata update authority as a power; capture name, symbol and URI; demote holder
  aggregation to partial only for holding-side unknown extensions.
- Name the rounding policy on ratio rows.
- DAMM v2 delegate permissions include AddLiquidity (bit 0) and LockPosition (bit 7);
  Pump `create_v2` requires the pinned 16 accounts; drop unevidenced 150/300 allocation
  sizes and state the reserved-tail policy in the capability descriptor.

## Phase 7: Importer, profile and delivery (offline pipeline review)

- `pin()` mirrors the profile's bracket, namespace and header rules and marks partial
  instead of letting `refresh` raise; out-of-bracket history reads degrade to unusable.
- Captures and presets carry an explicit dimension so every surface can evidence an
  external limit; quote hosts map to `sellability_exit_depth`.
- Aggregate derivations (`quote_sizes`, `holders`, `controllers`) use the latest usable
  packet per address and usable roots only.
- Per-operation derivation versions; the profile reports an engine version difference
  rather than a tamper-style recomputation failure on genuine older bundles.
- `read` returns the report path, verdict, axes, findings and coverage instead of the
  whole markdown; render adds the EVM-shape summary (labeled findings with adjacent
  citations and four Conclusions bullets).
- Signal assignments bind to input digests; one recheck batch may satisfy several initial
  samples; stability compares decoded fields excluding supply; non-string `concern` is a
  compose error, not a render crash; `facts --check` writes nothing.

## Phase 3: Guidance and instruction diet

Files: `SKILL.md`, `references/*.md`, `assets/lane-brief-*.md`, `assets/network-registry.json`,
`agents/openai.yaml`, `tests/test_solana_guidance.py`, `README.md`, `HANDOFF.md`, `AGENTS.md`,
router `skills/crypto-token-due-diligence/SKILL.md`.

- Define the skill directory and run variables once; use them everywhere; remove the
  HANDOFF/README/env ceremony from the public-only Solana path.
- Add a Deliver section matching the EVM chat contract (verdict, 4–8 labeled findings,
  per-finding source links, grouped Unverified, four Conclusions bullets, 300–600 words,
  sale-sample rule, no stronger recommendation than the decision review).
- Standard flow becomes start → spawn lanes → facts/presets → edit note → finalize;
  `compose --check` is the repair tool. Fix `compose.md` (bundle root, no scaffold step).
- Remove stale "v2 not default" wording; fix the registry URL; document required flags,
  the `brief`/`status` actions, adapter ids and the pool-lead rule; fix the router's
  `--seconds` line; frontmatter names pump.fun/Raydium/Orca/Meteora and excludes EVM.
- Make `test_solana_guidance.py` robust (no HANDOFF hash pin, no `~/.codex` check,
  skip when the repo root is absent).

## Phase 4: Lane workflow ergonomics

- `lane-check` imports the lane's own captures so a one-shot subagent can cite them;
  compact facts print citeable evidence IDs; lane briefs carry the note schema, enums,
  header fields and a one-finding example with absolute paths; `start` prints the
  compact facts summary.

## Phase 5: Findings from the adapter, accounts, transaction and offline reviews

Filled in when those reviews land (see the implementation record below).

## Final: verification and live acceptance

- Three suites green; benchmark re-run and hashes refreshed; release/provenance versions.
- Live broad run on dogwifhat with both lanes dispatched, two presets, compose and
  finalize; record the ledger and timings under `research/solana-review-2026-09-11/`.

## Implementation record

### Phase 1 (2026-09-11, second session)

Changed: `scripts/solana_session.py` (LimitError wait hints; METHOD_LIMITS with a 1 s window
margin stored per session; per-method and per-source backoff tables; `disable_method`,
`unavailable_methods`, `blocked`; projected wall clock; final-owner retries may draw on the
contingency grant), `scripts/solana_transport.py` (HTTPException handling with a finally-finish;
per-method backoff only for a stated Retry-After; `x-ratelimit-method-limit: 0` marks the method
unavailable; node-lag codes transient; proxies disabled), `scripts/solana_collect_v2.py` (`_send`
waits within `MAX_WAIT_SECONDS` and remaining time; retry pause; `recover_expired` on open;
collector version 2.1.0), `scripts/solana_wire.py` (slice-aware consistency key),
`scripts/solana_profile.py` (new statuses), `assets/network-registry.json` (public RPC URL fixed,
per-method windows recorded), `assets/release.json`, `assets/runtime-provenance.json`. Tests:
`tests/test_solana_public_limits.py` (10) and `PublicProviderTests` in
`tests/test_solana_broad_collect.py` (end-to-end refused-method run). Fixtures gained a
`largest_refused` mode and `getProgramAccounts` rows for Phase 2.

Verification: Solana suite 334 passed. Live broad start on dogwifhat
(`research/solana-review-2026-09-11/wif-run3-broad`): all four stages finished, 73 attempts,
55 account reads, 87 observations, 16 facts, `getSignaturesForAddress` and two `getTransaction`
sent for the first time in any live run, Raydium AMM v4 reserves decoded. The run still drew six
`getBlock` 429s at the exact window edge and lost four header-recheck retries to an exhausted
final grant; the window margin and contingency fallback were added afterwards and are covered
by tests. Independent review of the diff found two further defects, both fixed: attempt
deadlines equalled the collection cutoff (a lost worker's slot was never reclaimable, and the
new wait loop would stall on it), now capped at 60 s; and the contingency fallback fired for any
exhausted final read, now only for the single transient retry. It also showed the provider still
refused `getBlock` at six per window, so local pacing is five.

### Phase 2 (same session)

Changed: `scripts/solana_wire.py` (sliced program scans with a bounded row count and prefix
check; block-time reads in consistency), `scripts/solana_presets.py` (`holder_scan`,
`discovery_leads`, scan-aware `holding_sample`), `scripts/solana_accounts.py` (either discovery
method; `discovery` record with census counts), `scripts/solana_collect_v2.py` (scan fallback
when the largest-accounts method is refused; header rechecks via `getBlockTime`),
`scripts/solana_import.py` (scan subject/dimension/discovery; header pairs accept block-time
rechecks; `pool_activity` leads), `scripts/solana_profile.py` (scan subject rule; block-time
header pairs), `scripts/solana_broad_collect.py` (LP-lead scan fallback; one sliced batch for
program metadata; `provider_diagnostics`; `facts_summary` in the start output; self-contained
lane briefs with a note contract; lane-check imports the lane's own captures; `holders` and
`pool_activity` presets; version 1.2.0), `scripts/solana_facts.py` (citeable titles),
`scripts/solana_operations.py` (method enum), fixtures and tests.

Verification: Solana suite 336 passed. Live broad starts on dogwifhat:
`wif-run4-broad` (before the block-time recheck) 72 attempts, 17 of 17 typed facts usable,
LP-holder scan 429 KB succeeded, target-mint scan hit the 1 MiB cap and became an evidenced
limit, one `getBlock` 429, 76 s; `wif-run5-broad` (with block-time rechecks) 67 attempts,
13 `getBlock` plus 13 `getBlockTime`, zero 429s, 31.7 s wall clock, 16 ordinary attempts left
for presets, two receipts fetched (0 verified sales, expected until Phase 5).

### Phase 6 (fork, same session)
Task: implement Phase 6 of plans/solana-review-fixes-2026-09-11.md (implement → self-review → improve → verify), files limited to accounts/programs/Meteora/Pump adapters and their tests.

#### Stage 0 discovery
Python 3.14 stdlib; verification = `python3 -m unittest discover -s tests -q` from the skill dir (336 OK at start). Upstream layouts verified by fetching token-2022 `interface/src/extension/mod.rs` @a3e696e (enum 0–28, TLV u16/u16, unknown types → InvalidAccountData), token-metadata `interface/src/state.rs` (update_authority MaybeNull 32, mint 32, name/symbol/uri Borsh strings, additional_metadata Vec<(String,String)>) and token-group `interface/src/state.rs` (TokenGroup 32+32+u64+u64 = 80; TokenGroupMember 32+32+u64 = 72; both Pod).

#### What changed
- `scripts/solana_accounts.py` (LAYOUT_VERSION 1.1.0): new `_borsh_string`/`_token_metadata` decoders for extension 19 (every length bounded by the TLV entry, ≤4096-byte strings, ≤64 pairs, exact consumption, UTF-8 checked, embedded mint must equal the account when the address is known; fields `authority`, `mint`, `token_name`, `token_symbol`, `token_uri`, `additional_metadata_count`, `additional_metadata_sha256`, `mint_matches`); fixed-size 21 `token_group` (authority, mint, size, max_size) and 23 `token_group_member` (mint, group, member_number; no authority). `decode_mint(account, *, address=None)` threads the address through `_extensions`/`_extension`; `controls()` passes the target mint so the metadata update authority becomes power `token_metadata_authority`. `aggregate_holders` demotes to `partial` only for missing accounts, holding-side unknowns (types 5/17 or undecoded holding extensions) or invalid mint TLV — an unknown mint extension no longer demotes the sample. `ratio()` rows carry `"rounding": "half_up", "places": 4`.
- `scripts/solana_programs.py`: `authority_graph` decodes mints with their address so a metadata self-reference mismatch is an `invalid_extensions` gap and the update authority is a `token_metadata_authority` edge.
- `scripts/adapters/meteora_damm_v2.py`: delegate permissions add `add_liquidity` (bit 0) and `lock_position` (bit 7) as `allowed`/`absent`; the unconditional exit gap moved to `limitations` (a scanned compact-facts key) so a fully resolved sample reaches `observed`.
- `scripts/adapters/meteora_dlmm.py`: same `limitations` treatment for the depth gap.
- `scripts/adapters/pump_curve.py`, `pump_swap.py` (CAPABILITY version 1.2.0): allocations limited to evidenced 115/124 and 261/301; `reserved_tail_policy` declared.
- `tests/pump_fixture.py`: synthetic pool allocation 300 → 301 (evidenced length).
- `assets/release.json`: accounts_version 1.2.0, meteora_adapters_version 1.1.0, pump_adapters_version 1.2.0; `assets/runtime-provenance.json`: one differences line.

#### Tests added
- `tests/fixtures/acceptance/pyusd-live-mint.json`: real PYUSD (2b1kV6…GXo) Token-2022 mint bytes from the earlier live ledger (baseline_mint_0, slot 446296535, sha256 d7362e41…c84d), decoding fixture only.
- `test_solana_accounts.py`: documented-layout decode of 19/21/23 (+controls power), overrun/trailing/wrong-mint/bad-UTF-8/short-group are extension errors that keep base facts, real PYUSD bytes decode all eight extensions with no unknowns (name "PayPal USD", symbol "PYUSD", Paxos URI, update authority 2apBGMs…YJjk).
- `test_solana_holders.py`: unknown mint extension keeps `sampled` (ratio rounding fields asserted); holding-side unknown demotes.
- `test_solana_controllers.py`: metadata authority edge, no unknown_extension gap, wrong embedded mint → invalid_extensions gap.
- `test_solana_damm_v2.py`: bits 0/7 absent on the fixture mask, allowed when set, existing tri-state unchanged.
- `test_solana_pump.py`: 150/300 refused, capability lists and tail policy asserted.

#### Verification
All modules I touched pass: accounts, holders, controllers, damm_v2, dlmm, pump, programs, whirlpool, clmm, raydium, pool_contract, facts (each OK). The full suite was 342 OK after my changes; a later full run shows 2 failures + 10 errors that all originate in the concurrent Phase 7 fork's in-progress edits to `solana_compose.py` (signal assignments now require `input_digests`) and `solana_derivations.py` (CHANGED_IN version gate) — none reference my files.

#### Self-review findings and fixes
- Extension-row key collision (`name` = extension name vs token name) crashed decode → renamed token fields `token_name/token_symbol/token_uri`.
- First `scope_limits` key for the Meteora limitation was not in `solana_facts.LIMIT_KEYS` and would have vanished from compact facts → moved under `limitations` and verified it surfaces via `scan()`.
- Holder test initially demoted for the wrong reason (holding program mismatch) → fixture holdings now Token-2022.
- Registry check: `assets/protocol-registry.json` "300" is Dexscreener's rate limit, not a Pump allocation; left untouched.

#### Deferred / notes for the parent
- `solana_derivations.CHANGED_IN` (owned by the Phase 7 fork) should also list `mint`, `controls` and `pool` at 1.1.0: this phase changes their output shapes (metadata rows, ratio rounding fields, Meteora `limitations`), so frozen bundles get the "operation version differs" message instead of a recompute failure.
- Pump `create_v2` account variants and legacy `buy` decoding (L1/L2) belong to the other fork's `pump_instructions.py` and were not touched.
- DLMM/DAMM v2 `limitations` is a result-level list; downstream nothing keyed on the old gap strings (grep confirmed).

### Phase 7a (fork, same session)
Stage 0: Python 3.14 stdlib, unittest discover from the skill dir, no lint; rules from AGENTS.md and the plan (no commits, version bumps, frozen evidence immutable, legacy-v1 untouched). Reference shapes: the EVM renderer's `render_summary` for the chat-shape summary; overrides' `input_digests` rule for digest binding.

#### Changed

- `scripts/solana_derivations.py` (VERSION handling only): contract `VERSION` 1.0.0 → 1.1.0, `RUNTIME_VERSION` 1.4.0; new `CHANGED_IN` map (contract version in which each operation's output last changed: controllers, discovery_pools, holders, mint, controls, pool, transaction, sales, rebuys, launch, history, prior_launches, creator_activity, public_quote at 1.1.0 per the coordinator's note; unchanged ops such as program/source_assurance/quote_sizes/local_quote/inventory stay recomputable from 1.0.0), `version_tuple`, `recomputable(operation, recorded)` → 'ok' | 'operation version differs from installed engine; use read/replay' | 'derivation recorded by a newer engine; use read/replay'. The importer already stamps `derivations.VERSION`, so new bundles record 1.1.0 without any importer change.
- `scripts/solana_profile.py`:
  - P5: `_derive` consults `recomputable` before the recompute check; bad version strings → 'unsupported operation version'.
  - P2 (profile half): boundary conditions degrade to unusable instead of raising — a `getSignaturesForAddress` read outside the verified genesis bracket or from another namespace; a pinned sample outside the bracket/namespace, with a changed header, stale or undated, or a header from another provider (sample goes to `Evidence.unpinned`, observation to `Evidence.degraded[eid]=reason`); a critical initial sample whose only recheck was degraded is unpinned too ('critical recheck unavailable'); an execution outside the bracket stays unusable. Identity contradictions (genesis mismatch, same-slot state/header contradictions in `consistency()`, structural mismatches) remain hard failures.
  - P10: new `Evidence.stability(addresses, v, w)`: byte-equal accounts are stable; a mint whose account metadata and decoded fields are equal except `supply_atomic` is stable with `Evidence.stability_changes[obs]={address:['supply_atomic']}`; any other change (lamports, authorities, extensions, non-mint data) is unstable as before.
  - P11: every finding carrying `concern` must have an object with exactly basis/mechanism/consequence text; adverse rule unchanged on top.
- `scripts/solana_render.py` (1.1.0): report.md gains a `## Summary` section after the header: verdict line, label legend, `| Surface | Assessment | Finding |` table of summary findings labeled ✅ Good / 🟡 Potential Risk / 🔴 Bad with adjacent evidence citations, a `### Research gaps` table for ⚪ Unverified, then `**Conclusions**` with exactly four axis bullets (`Unjudged; …` for drafts/checkpoints); the Assessment section keeps requirements/mitigations/actions (axes no longer duplicated there). `reading()` is compact: verdict entry carries axis texts, requirements, mitigations, actions; finding entries carry id/dimension/signal/label/summary flag/claim/strength/impact/confidence/text/concern/limitations/time-basis kind/citations; typed facts keep summary/limits/attention and full details except publication ops (discovery/repository/public quote) which are capped at 40 lines with an explicit remainder note; coverage rows carry dimension/rating/status/boundary/reason/pending_work/decision_impact. Concern rendering stringifies values.
- `scripts/solana_replay.py` (1.1.0): `read()`/`finalize()` no longer return `markdown` (use `report_path`); older frozen checklists get the same publication-detail cap at read time. Frozen live checkpoints: read payload 302→99 KB (usdc), 391→156 KB (pyusd), 165→88 KB (pump); `verify` unchanged; `validate` now reports the version message instead of "output does not recompute from bound inputs".
- `scripts/solana_compose.py` (1.1.0): `signal_assignments` entries accept `input_digests`; any assignment with a non-null signal must bind the current digest of each fact evidence the pipeline finding cites, else a field-specific `note.signal_assignments.<id>.input_digests` error that prints the expected digests; bare strings still work only for null signals.
- `scripts/solana_scaffold.py` (1.1.0): scaffolded assignments are pre-filled `{"signal": null, "input_digests": {...}}` so the analyst only sets the signal.
- `scripts/solana_facts.py` (1.2.0): `describe()` names the subject for program (address, loader, upgradeability, authority), controllers (roots, observed/reachable counts, status) and source_assurance (program plus each level); `missing_reads` rows carry `reason` from the profile's degrade map.
- `scripts/solana_bundle.py`: `facts --check` writes nothing.
- `assets/release.json`: profile_runtime 1.2.0, render 1.1.0, replay 1.1.0, compose 1.1.0, facts 1.2.0, scaffold 1.1.0, derivations 1.4.0. `assets/runtime-provenance.json`: one differences line.

#### Tests

- Fixtures: `profile_fixture.derived()` stamps `derivations.VERSION`; `compose_fixture.assign(b, signal, ids=None)` builds digest-bound assignments; `delivery_fixture` uses it.
- New: profile — history outside bracket retained but unusable (inside read stays usable); sample outside bracket unpinned and its critical initial unpinned, validate fails only at the finding rule; operation version rules (differs / newer / unsupported / unchanged op recomputes); supply tick keeps stability with changed_fields while an authority change fails; concern shape for every finding. compose — assignment digest required/stale/scaffold-prefilled; string concern is a compose error. scaffold — digests prefilled. facts — degraded read reason; describe subjects; `facts --check` read-only vs plain facts writing. delivery — summary table label, legend, four Conclusions bullets exactly once each, compact verdict/finding entries with citations, no `markdown` key; checkpoint renders four `Unjudged` bullets. acceptance — summary row for the adverse control, conclusions block.
- Updated: tests that read `result['markdown']` now read `report_path`; assignment fixtures carry digests.
- Suite: 368 passed (from 336; includes the other forks' new tests present on disk at run time). Frozen checkpoints usdc/pyusd/pump: `read` and `verify` succeed; `validate` reports `manifest.derivations.<market-…>.version: operation version differs from installed engine; use read/replay`.

#### Self-review findings and fixes

- My first version test assumed `controls` was unchanged; after the coordinator's map widening it is not — test now asserts the differs message for controls 1.0.0 and 'ok' for quote_sizes.
- Bracket test mutated the packet times without the observation's captured_at → fixed the fixture mutation.
- Stability test's authority mutation forgot the COption tag → fixed.
- Assertion on the rendered table needed the escaped underscore (`token\_controls`).
- Considered mutating manifest sample statuses in memory for degrade; used side sets (`unpinned`, `degraded`) instead so validation never rewrites manifest objects.

#### Deferred / notes for the coordinator

- Importer half of P2 (pin() mirroring bracket/namespace/header rules) and P3/P4/P9 are outside this half, as instructed.
- If Phase 5 did not change some of the transaction-family operations, trim them from `CHANGED_IN`; a listed-but-unchanged op only loses recompute verification for pre-1.1.0 bundles.
- Guidance that says `read` returns the markdown should now say it returns `report_path` plus the compact checklist (docs are outside my ownership).
- `Evidence.degraded` reasons are surfaced in facts `missing_reads`; the pipeline note and coverage closure do not yet cite them (P3 territory).

### Phase 5 (fork, same session)
Task: implement Phase 5 of plans/solana-review-fixes-2026-09-11.md within the assigned files, self-review, improve, verify. No commits.

#### What changed

- `scripts/solana_transactions.py` (1.1.0 → 1.2.0)
  - `_frame(execution, swap)`: the swap's CPI frame and its direct children by recorded stack height. An outer swap owns its group's inner instructions; a nested swap (router/aggregator CPI) owns the instructions after it until the first at or above its height; a nested frame without heights is a typed gap.
  - `_verify_trades` rewritten: swap selected by exact pool at any depth; leg transfers are the frame's direct children; extra transfers are accepted only into the adapter-declared `fee_accounts` from the same vault (sells) or the trader's input account (buys) and recorded as `protocol_fees_atomic`; every leg account must move by the net of the leg's own flows (a fee-paying vault moves by output plus fee); a single-boundary trader account (created or closed in-transaction) is accepted on either side when `historical_owner` proves it, with the vault delta pinning the amount; Token-2022 legs verify only with `transfer_checked` and both boundary balances (a withheld fee or hook movement breaks the equality); aggregated routes tolerate exactly the onward/inbound hop touching the leg's user account and label `counter_asset_realization: converted_within_route` (native proceeds skipped then). Rows gain `route`, `protocol_fees_atomic`, `counter_asset_realization`, `token_programs`.
  - `classify_receipt(target, packet, pool)`: header-free pre-spend classification (supported swap at the exact pool; sell/buy by which side holds the target mint; direct/aggregated). Never a sale claim.
  - System program: `CreateAccountWithSeed` (op 3, with `seed`/`seed_base`) decodes as `native_account_create` so seeded temporary WSOL accounts reconcile; `Allocate` (8) and `Assign` (1) decode without amounts. Effects now carry `stack_height`.
- `scripts/solana_swaps.py`: every decoded swap carries `fee_accounts` (PumpSwap protocol fee recipient token account and coin creator vault ATA `a[10]`, `a[17]`; DAMM v2 referral `a[11]`; DLMM host fee `a[9]`; others empty; the program id placeholder means absent); a sink overlapping a swap role is refused.
- `scripts/adapters/pump_instructions.py`: `create_v2` requires the pinned 16 accounts and no longer labels an appended account as `quote_mint` (v2 quote is BondingCurve state); legacy curve `buy` decoded (16 accounts, 25-byte data with OptionBool track_volume).
- `scripts/solana_quotes.py` (1.0.0 → 1.1.0): source `jupiter_v1_lite` (`https://lite-api.jup.ag/swap/v1/quote`) consuming inAmount/outAmount/otherAmountThreshold/priceImpactPct (retained verbatim)/routePlan/contextSlot/swapUsdValue/platformFee; keyed `jupiter_v2` kept as alternate. `quote_request(url)` parses a captured quote URL (host/path → source, required parameters, benign route-shaping extras, wallet-bound parameters refused); `public_quote` compares the parsed request instead of an exact string so parameter order does not matter.
- `scripts/solana_discovery.py` (1.3.0 → 1.4.0): `source_plan(surface="token_info")` (GeckoTerminal token info), `token_info()` parser, `link_identity()` (twitter/telegram/discord handle or registered host), `corroborate_links()` (a Dexscreener link is `corroborated` only when a second indexer names the same identity; otherwise `unverified_indexer_profile`).
- `scripts/solana_launch.py` (1.0.0 → 1.1.0): `page_limit` read from the request.
- `scripts/solana_import.py` (derivations block only): captured quote URLs of either Jupiter source become `public_quote` facts for the exact mint; `history` per attributed key from `creator_history` preset pages (window genesis → latest context, coverage stays an explicit gap); `rebuys` derived alongside `sales` from the same candidates; `prior_launches` for the launch creator argument and launch signers; `creator_activity` for attributed creators with histories/sales/rebuys; `pool_activity` presets count as known pools.
- `scripts/solana_broad_collect.py` (two functions only): automatic receipts now probe recent pool signatures one at a time under the `receipts` sample name, classify each, and sample only receipts with a supported swap at the exact pool (at most two from at most four probes); the later sample resumes the probe without a second send; `receipt-classification.json` records every probe. Broad starts also capture GeckoTerminal token info; Dexscreener project links are auto-captured only when corroborated; decisions are written to `project-links.json`.
- Assets: `release.json` (`transactions_version` 1.2.0, `quotes_version` 1.1.0, `launch_version` 1.1.0, `discovery_version` 1.4.0, `pump_adapters_version` 1.2.0); `runtime-provenance.json` differences line.

#### Tests

- New `tests/fixtures/receipts/wif-raydium-amm-v4-routed.json`: the two live dogwifhat receipts (router CPI → Raydium AMM v4 swap at stack 2, transfers at stack 3) with their block headers, raw RPC bytes, no network use beyond the run that already fetched them.
- New `tests/test_solana_routes.py` (11 tests): live receipts verify as aggregated sales with the RPC-reported token-account owner as seller (not the fee payer) and classify as sell/aggregated; synthetic router wrapping verifies and a nested frame without stack heights is a gap; a stray sibling transfer outside the frame is refused; declared fee sinks are recorded and undeclared flows refused (sink needs boundary balances); PumpSwap sell declares its two sinks and refuses overlap; Token-2022 leg verifies only with both checked boundaries (withheld amount and missing boundary refused); an input account closed in-transaction reconciles against the vault and a wrong vault delta is refused; a seeded temporary WSOL rebuy verifies; Allocate/Assign decode; an onward hop marks conversion and an unrelated destination is refused; legacy curve buy decodes and create_v2 needs 16 accounts.
- `tests/test_solana_quotes.py`: lite quote with reordered/benign parameters, swapUsdValue, context slot; wallet-bound, wrong amount, wrong host, unknown parameter and transaction-bearing bodies refused.
- `tests/test_solana_discovery.py`: token info identities; corroboration by identity (host, handle) not by string; wrong-mint info refused.
- `tests/test_solana_launch.py`: page limit comes from the request.
- `tests/test_solana_broad_collect.py` (+3): probes classified before sampling with the swap probe reused (2 sends for 2 probes), sales 1 / rebuys 0 facts, strict validate accepts the unheadered probe; indexer links need the second source (captured when corroborated, not when the token-info page has no identities); a lane-captured lite quote becomes a usable `public_quote` fact.
- Fixtures: `tests/broad_fixture.py` gained a token-info response (`Web.token_info`), a lite-quote response and optional extra receipts (`RichRpc.receipts`); `tests/solana_fixture.py` unchanged by me.

Suite: `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -q` → 368 tests OK (25–27 s); `git diff --check` clean.

#### Self-review findings and fixes

- A fee leaving the vault made the vault's delta differ from the leg output; fixed by netting all leg flows (trade legs plus declared fees) per account before comparing with the boundary deltas.
- My first live-receipt test hardcoded a mistyped seller; replaced with the RPC-reported owner from the raw preTokenBalances so the expectation is independent of the code.
- `restrictIntermediateTokens` can never reach a capture (the capture layer refuses any query key containing "token"), so it was dropped from the benign set and the rule documented.
- `corroborate_links` predicate simplified to plain identity membership; classification test now runs the strict validator.

#### Deviations and notes for the parent

- Token-2022 verification uses a receipt-intrinsic rule (transfer_checked plus both boundary balances equal to the checked amount) instead of consulting decoded mint controls: threading controls through would have required editing `solana_derivations.py`, which was outside my file ownership. The rule is stricter, not looser: any withheld fee or extra hook movement breaks the equality or adds a flow.
- `solana_derivations.py` (edited concurrently by the parent) now carries a `CHANGED_IN` map; the output shapes of `transaction` (new `stack_height` on effects), `sales` and `rebuys` (new row keys) changed in this phase and should be recorded there as 1.1.0.
- `tests/broad_fixture.py` received small additive branches (token info, lite quote, extra receipts) although it was not in my explicit list; other fixtures were untouched by me.
- `solana_web_capture.RATES` has no entry for `lite-api.jup.ag` (default host handling applies); not in scope.
- Deferred (not in the Phase 5 bullets): X13 lead ranking across indexer scales; refusal of aggregated legs whose intermediate account is reused by more than one other hop remains conservative by design.

### Phase 7b (same session)

Changed: `scripts/solana_import.py` (pinning requires the sample inside the verified genesis
interval on the same provider with a same-provider header, mirroring the strict profile; RPC
attempts carry the surface of their sample or preset kind and quote hosts map to exits;
captures carry a declared dimension; quote sizes and holders use the latest usable snapshot;
the authority graph is built from usable roots and the latest usable packet per address),
`scripts/solana_collect_v2.py` (one recheck batch per initial critical read),
`scripts/solana_web_capture.py` (`dimensions` on registration, `web_dimensions` table, the
capture record carries `dimension`), `scripts/solana_broad_collect.py` (`capture --dimension`,
brief note), runbook and lane briefs. Tests: recheck partition, capture dimension, importer
boundary (a failed final network recheck leaves the run importable and keeps the prior usable
snapshot), usable aggregates. Suite: 372 passed.

### Post-phase fixes and live end-to-end acceptance (2026-09-12)

Fixes found by the live end-to-end run and applied afterwards: field-level pipeline
restatements inherit their fact's signal and the scaffold pre-fills one assignment per fact
(a coordinator judges about fifteen facts, not 143 fields); the reading checklist collapses
those restatements into a count, lists only referenced citations and drops provenance rows
from typed-fact details while keeping every quantity (payload 407 KB → about 150–190 KB);
`checkpoint` composes a valid coordinator note and reports `note_status`, falling back to the
last composed draft when the note is invalid; the legacy Whirlpool `swap` instruction (11
accounts, 42-byte data, discriminator f8c69e91e17587c8) is decoded, with the two live Orca
receipts stored as `tests/fixtures/receipts/wif-orca-legacy-swap.json`; GeckoTerminal
token-info captures are no longer fed to the pool-discovery derivation; lane briefs state
the adverse-signal and subject rules; runbook and README updated. Solana suite: 375 passed.

Live end-to-end run `research/solana-review-2026-09-11/wif-e2e` (dogwifhat, public endpoint):

| Step | Result |
| --- | --- |
| start | 31.7 s, 68 attempts, zero 429s, 13 usable facts, honest diagnostics (refused largest-accounts method, one unsent read) |
| lanes | liquidity note valid and complete (9 findings); project note valid, partial (11 findings); both dispatched with under three minutes to cutoff because the coordinator read facts first |
| preset | `pool_activity` on the Orca pool: two receipts; after the legacy-swap fix one verified aggregated sale (17,057,295 atomic WIF → 32,562,266 lamports, seller identified) and one verified direct rebuy |
| compose | multi-error check caught vocabulary slips, stale digests after the preset refresh, and undeclared program/pool subjects; all repaired from the error text |
| checkpoint | `checkpoint5`: composed note, conditional verdict, five requirement judgments (one met), six summary findings with adjacent citations, eleven coverage rows (concentration closed as an evidenced external limit), four Conclusions |

Completed broad delivery was not reached in this run: holder concentration is a provider
limit for a mint this large, the project lane lacked time to bind the site and creators, and
the USD 1,000 quote was not attempted. Those are research-scope limits, not pipeline
failures; the pipeline itself ran every stage on the public endpoint for the first time.

### Consolidated review and final fixes (2026-09-12)

An independent cross-phase review of the whole change set (synthetic end-to-end from start
through finalize and read, the three frozen live checkpoints, budget and evidence contracts,
guidance accuracy, test quality) found and I fixed: `lane-check` deadlocked on its own draft
lock whenever a lane had a new capture (outer lock removed; regression test runs the check in a
bounded thread); a `pool_activity` preset re-fetched receipts the start already sampled, and the
duplicate raised inside the sale verifier and silently dropped the sales/rebuys facts (signatures
already sampled or probed are skipped, the importer keeps one execution per signature, and a
duplicate is a row gap); a same-transaction round trip back into the leg's input account verified
as a sale (an inbound hop must precede the leg and an onward hop must follow it); inherited
field-level restatements copied the parent's impact, which made every child "severe" and pushed
them into the summary (children now inherit signal, confidence and concern only); `refresh` now
adds null assignments for new facts and refreshes digests of unjudged ones, and the compact facts
title line prints each fact's digest so a coordinator never opens a manifest to bind a signal;
guidance no longer says `read` returns Markdown or that legacy bundles are read with `read`;
two wall-clock-dependent tests use the virtual clock; a tautological and a dead-branch test were
repaired; the derivation version map lists only operations whose output changed.

Final state: Solana 379 passed, router 30, EVM 429; `git diff --check` clean; nothing committed.

### Follow-up session (2026-09-12, evening): probe classification, payload compaction, live completed delivery

Three items in order, nothing committed.

**1. `pool_activity` classifies probes like `start`.** `receipt_read`, `classify_probes` and
`record_probes` are shared by the start stage and the preset: each unseen recent signature is
probed one at a time and classified before any header is bought, only receipts with a supported
swap at the exact pool are sampled, the probe read name is reused so the sample never re-sends
it, and the classification rows carry their `sample` id. New optional parameter `probes`
(receipts to 8, default 4); `receipts` stays 0 to 4. An identical named preset resumes its own
classification without a new send. Regression test: a non-swap signature is probed and
skipped, the swap is probed, selected and sampled with one send per probe, the resumed preset
sends nothing, and `receipts > probes` is refused. Live (run b below): the preset probed two
signatures, selected both (one buy, one sell) and the sell became the run's verified sale.

**2. Reading payload compaction** (`solana_render` and `solana_replay` 1.2.0). Typed-fact
details are nested and omit provenance keys, nulls and empties; leaves already listed under
limits or attention are not repeated; share objects collapse to `num/den = pct%`; same-shaped
rows become column tables with constant columns hoisted; transaction facts list instruction
programs, merged pre/post token balances, changed/unchanged lamport tables and hoisted scope
strings; publication tables are capped at six rows; recurring addresses are `@aliases` resolved
once in `addresses` (well-known programs, WSOL, the target mint and the genesis hash get named
aliases); each typed fact carries its own pipeline finding (text and limitations are the fact's
summary and limits; pipeline defaults omitted); analyst findings cite evidence ids only, omit
labels, null concerns and false summary flags; attention and limit rows are strings with index
ranges collapsed; the coverage entry is a table; `read` keeps the absolute path only inside
`answer_link`. A regression test asserts every non-provenance leaf of every derivation output
survives (numbers, controllers, statuses), limits are listed, aliases round-trip, and the
synthetic delivery fixture reads under 60 KB.

| Bundle | Old renderer | New renderer |
| --- | --- | --- |
| WIF `wif-e2e/checkpoint5` (44 findings, 18 facts) | 177,650 B | 73,169 B |
| RAY run a checkpoint (20 facts, no composed findings) | — | 62,486 B read payload |
| RAY run b delivered (24 analyst findings, 19 facts) | 266,611 B | 84,745 B reading, 87,409 B read payload |

The under-60 KB target is **not met** on live bundles. What remains is analyst prose (24
findings, about 24 KB) and typed quantities (19 facts, about 43 KB; every state and execution
number is kept, checked leaf by leaf on this bundle, while indexer candidate tables beyond six
rows are capped with a remainder note as publication details were before), plus verdict,
coverage, citations and the alias table. Further lossless levers not taken: aliasing
addresses inside analyst prose (about 2 KB) and hoisting repeated limit sentences.

**3. Live completed broad delivery on RAY** (`4k3Dyjzvzp8eMZWUXbBCjEvwSkkk59S5iCNLY3QrkX6R`,
about USD 410M market cap per Dexscreener, SPL Token program, two Raydium AMM v4 pools sampled).
Both lanes were dispatched in the same message as `start` with a preamble that waits for the
note scaffold, then follows the printed pointer verbatim.

Run a (`research/…-2026-09-12-live-a`, received 17:25:37Z): start 40 s, 66 attempts, 16
facts; `pool_activity` probed/selected two buys; USD 1,000 Jupiter quote captured. It ended as
a checkpoint, not a delivery, for three reasons recorded here so they are not repeated: (i) a
second preset (`programs` on the AMM upgrade authority) ran after the ordinary budget was
exhausted, its main batch was budget-denied while the final-reserve recheck of the mint
succeeded unpinned, so the newest mint snapshot became unusable, `auto-controls` turned into a
coverage-gap pipeline finding and `token_controls` could no longer close (a resolved boundary
forbids gaps; an external limit needs failed attempts at two sources); (ii) both lane notes
failed self-check on support-subject declaration, an invalid participant kind (`account`) and
claim classes (state observation on document evidence, historical execution without an
execution effect); (iii) later coordinator captures were budget-denied.

Run b (`research/…-2026-09-12-live-b`, received 17:43:28Z, deadline 17:53:28Z): start 45 s,
68 attempts; one preset (`pool_activity` on the RAY/SOL pool) and one quote capture by
17:44:48Z; lane pointers carried the note-contract pitfalls; both lane notes passed self-check
on the first attempt (project 44 s before its cutoff, liquidity 4 s after); the coordinator note
was written from the facts by a scratchpad composition script (one project gap finding restated
as a bounded source analysis with an explicit limitation); `compose --check` valid,
`finalize` delivered at 17:47:55Z, 4 min 27 s after receipt, inside the +420 s target.
Verdict conditional; ratings: token_controls no_issue_detected, external_dependencies and
current_concentration concern, the other eight unknown; all eleven coverage rows checked and
resolved. Evidence: `research/…-live-b/final` (report.md, reading.json, evidence/); the
run-a checkpoint is `research/…-live-a/checkpoint`.

Open items found by the live runs: an evidenced external limit needs an `alternate` route that
the importer assigns only to GeckoTerminal captures, so non-market surfaces can complete only as
resolved; sales and rebuys derive from the first two candidate receipts, so preset receipts are
excluded when start already sampled two; a partial follow-up sample of the mint makes the newest
snapshot unusable and blocks completion (consider deriving controls from the latest usable
snapshot without a gap finding for the unpinned newer one); the quoted Jupiter route did not
touch the sampled pools; a verdict text beginning with "Conditional:" renders as
"Conditional: Conditional:" (cosmetic); lane briefs exceed the Bash 30 KB output cap and must be
opened with Read.

Final state: Solana 381 passed, router 30, EVM 429; README suite count updated; `git diff
--check` clean; nothing committed.
