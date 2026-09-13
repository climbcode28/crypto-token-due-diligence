# Solana/EVM parity implementation record

Plan: `solana-evm-parity-plan-2026-09-11.md`.
The user authorized all phases sequentially, with implement → review → improve →
verify and this record updated before advancing. No commits or pushes.

Initial checkout: `fc60201`; only the supplied plan was already untracked.
Canonical Solana files are the editable scope. EVM, Claude, registrations, private
credentials and frozen history remain unchanged. Validation runs from repository
root with Python standard-library unittest and `PYTHONDONTWRITEBYTECODE=1`.

| Phase | Status | Gate / next work |
| --- | --- | --- |
| 1 | Complete | Legacy compatibility and v2 specification verified |
| 2 | Complete | Standalone transport/session and 286.9-second tooling review verified |
| 3 | Complete | Strict methods, bounded batches, fresh checks and durable partial output verified |
| 4 | Complete | Pinned token layouts, PDA vectors and integer holder/control facts verified |
| 5 | Complete | Loader, controller/bypass and source-assurance facts verified |
| 6 | Complete | Bounded captures, exact discovery and durable source ownership verified |
| 7 | Complete | Separate CPMM/AMM v4 reserves, version ambiguity and sampled LP custody verified |
| 8 | Complete | Protocol-specific range math, position custody, bundles and dynamic arrays verified |
| 9 | Complete | Separate bin/range/compounding principal, NFT permissions and vesting verified |
| 10 | Complete | Historical effects, direct sale reconciliation and scoped quotes verified |
| 11 | Complete | Pump layouts, migration binding and bounded creator flows verified |
| 12 | Complete | Exact evidence closure, bounded unknowns and decision visibility verified |
| 13 | Complete | Eight-family typed facts, exact totals, limits and stable unjudged findings verified |
| 14 | Complete | Notes-to-draft, immutable lane snapshots and recoverable composition verified |
| 15 | Complete | Shared-session broad runner, receipt sampling and bounded lane handoffs verified |
| 16 | Complete | Atomic delivery, safe citations and isolated frozen replay verified |
| 17 | Complete | Bounded reviewed feedback, standalone guidance and unchanged policy verified |
| 18 | Functional gates passed; live parity unmet | Acceptance corpus and all three live cases recorded; completed broad live parity not demonstrated |

## Phase 1 — compatibility and v2 contract

Implemented the explicit profile dispatcher, isolated installed legacy reader,
v2 field specification, unjudged note/work-plan templates and immutable synthetic
golden fixtures. [baseline.json](baseline.json) records the original script/reference
hashes, component versions, Python version and actual suite outcomes. Fixtures were
captured **before** edits using the trusted current collector with synthetic transport;
their original five-file engine snapshot is preserved as data, never executed.

Changed paths under `skills/crypto-solana-token-due-diligence`: `scripts/solana_bundle.py`,
new `scripts/solana_legacy_v1.py`, `references/bundle-v2.md`, `assets/note.template.json`,
`assets/work-plan.template.json`, `assets/release.json`, `tests/test_solana_legacy.py`,
and `tests/fixtures/legacy_v1/`. Added this record and baseline. The pre-existing plan
was amended only to capture the user's continuing authorization and tooling research
addition to Phase 2; its design and remaining phase requirements are preserved.

Versions: legacy collector compatibility `engine_version=1.0.0` and workflow 1.0.1
unchanged; reporting development version `2.0.0-dev.1`. Default and supported reading
profile remains `legacy-v1`; v2 is specified and explicitly rejected without mutation.
Planned profile/note/session/adapter versions are recorded independently.

Acceptance evidence:

- Golden collection and independent-evidence bundles validate through explicit
  `--profile legacy-v1`, and rendered bytes match the captured reports exactly.
  Missing/altered evidence, wrong subject, copied recheck and unknown→completed
  mutations are rejected on temporary copies.
- Copying only the dispatcher and legacy module to an isolated directory reproduces
  both reports, with no EVM sibling and poisoned current collector/common modules.
  Original fixture inventories and historical evidence are unchanged.
- Specification explicitly covers all eleven surfaces, exact identities and contexts,
  derived dependencies, effects, lane ownership, coverage versus ratings, unknowns,
  completion/checkpoints, decisions, budgets and safe frozen delivery/replay.

Review: inspected actual dispatcher diff, all new file contents, golden partial
report output and negative mutations. All **21** extracted legacy function ASTs
match the original source exactly. No actionable defects remained. Deliberately
preserved schema-1 restrictions and incomplete historical snapshots; v2 runtime
validation belongs to subsequent phases and is not claimed implemented.

Checks actually run:

- Baseline README suites: router **30**, EVM **428**, Solana **23**, all passed.
  EVM had two existing HTTPError temporary-file ResourceWarnings, no failures.
- New legacy suite: **5 passed** (including the five negative fixture mutations).
- Full Solana suite after changes: **28 passed** in 2.014 seconds.
- `git diff --check`: passed. No dependency installs or provider checks.

Blockers: none. Phase 1 acceptance criteria satisfied before starting Phase 2.

## Phase 2 — transport, budgets and tooling review

Preparation: Phase 1 gates above passed. Reviewing narrow EVM HTTP/provider and
session primitives plus retry/production regressions before porting. No live
provider checks are needed for implementation tests. The user added a five-minute
primary-source tooling review; its dated findings and phase-mapped integration
decisions will be recorded before Phase 3. Custom dRPC setup remains deferred.

Implemented: local `solana_transport.py` ports the narrow HTTPS/provider primitives
with no EVM imports. `solana_session.py` provides durable SQLite attempts, grants,
response-body byte accounting, response records, original absolute timing, per-family
retry eligibility, phase marks and bounded replans. `solana_collect.py` uses local
transport and supports opt-in `--profile solana-evidence-v2 --session <existing-run>`
for its existing mint schedule. The expanded schema-2 schedule is Phase 3; this
intermediate collector still emits its legacy mint packet and does not claim broad
or v2-report completion. New collector snapshots contain local dependencies; old
fixtures/snapshots retain original bytes.

New paths: `assets/runtime-provenance.json`, `scripts/solana_transport.py`,
`scripts/solana_session.py`, `tests/test_solana_transport.py`,
`tests/test_solana_session.py`, `tests/test_solana_imports.py`, and
[tooling-research.md](tooling-research.md). Updated collector/release metadata and
the plan's user-requested research gate. Collector development version 2.0.0-dev.2,
transport 1.0.0, session contract 1. Legacy engine compatibility remains 1.0.0.

Acceptance evidence:

- Four competing processes cannot exceed shared or lane grants. Zero grants send
  nothing, spent lane grants cannot be recreated, retries stop after one, and final
  recheck capacity remains reserved. Redirects are refused by RPC transport (one
  charged send, no authenticated forwarding); web redirect traversal is Phase 6.
- Reopened sessions preserve target, timing, IDs, attempts and retry eligibility.
  Existing unrelated/finalized directories are refused without changed bytes.
  Lost workers retain pessimistically charged reserved bytes and attempt records.
- Concurrent requests reserve response bytes before send. The transport never reads
  an uncharged overflow probe byte. Late replies and secret echoes become typed
  failures, with sanitized durable evidence. Invalid inputs/permissions send nothing.
- Isolated imports and provider preflight run with no EVM sibling, zero socket
  activity and no generated files. The collector integration test accounts all nine
  actual synthetic calls, including four reserved rechecks, in one session.
- The tooling review ran **19:54:29–19:59:15 UTC, 286.9 seconds**, within the
  requested five-minute budget. It selects current public sources and wallet-free
  optional quotes, documents conflicting/unknown limits, source/runtime boundaries,
  and maps concrete follow-through to Phases 3–11. Custom dRPC remains deferred.

Review and improvements: fixed a late-response status mismatch between the attempt
column and stored packet; preserved typed transport refusals in collector evidence.
Reviewed retry/production vectors from EVM without copying its validator or state
model. Corrected two test defects (invalid synthetic key and monkeypatch that broke
Python SSL class import) before successful reruns. No remaining actionable finding
in the phase's implemented surface. Byte totals count response bodies, not TCP/TLS
overhead; interrupted bodies conservatively retain their full reserved allowance.

Checks: transport **11 passed**, session **10 passed**, imports **2 passed**;
full Solana **51 passed**; router **30 passed**, EVM **428 passed** (same two
pre-existing ResourceWarnings). `git diff --check` passed. No live provider checks,
SDK installs, global permissions/registration changes, EVM or Claude edits.

Blockers: none. All Phase 2 gates satisfied before beginning Phase 3.

## Phase 3 — method validation and sample engine

Preparation: Phase 2 session/transport and tooling gates passed. Implement the
strict method boundary, context-preserving batch scheduler and explicit observation
reuse. The v2 collector will consume the original session and reserve fresh final
checks; protocol/account semantics remain gated to their later phases.

Implemented: strict read-only `solana_wire.py`, bounded `solana_presets.py`, immutable
`solana_cache.py`, and `solana_collect_v2.py` (kept separate from the frozen legacy
schedule for reviewability). The CLI selects the new packet only with the explicit
v2 profile/session. Common helpers now distinguish 32-byte keys from 64-byte signatures.
Session/transport enforce strict opt-in responses, public RPC windows across provider
namespaces, and recorded additional final reservations from unspent ordinary capacity.
No capacity is added to the original ceiling. Read intentions, schedules and replies
survive worker termination; summary failure emits a partial packet retaining the durable
session. Capture status remains distinct from unjudged research status.

New tests: `test_solana_wire.py` (8), `test_solana_cache.py` (3),
`test_solana_collector_v2.py` (10), and the socket-free `solana_fixture.py` helper.
Collector development version 2.0.0-dev.3, transport 1.1.0, wire/cache 1.0.0;
v2 collection packet schema 2. Legacy engine/profile version semantics are unchanged.

Acceptance evidence:

- Wrong JSON-RPC IDs, ambiguous envelopes, bad contexts, shortened arrays, wrong
  mint/owner filters, duplicate results, unsupported methods and contradictory
  successful network/header/account observations fail closed. Raw failure categories
  and null account positions remain visible; unsupported transaction versions do not
  produce transaction facts.
- Deterministic batches preserve addresses, indices, missing positions and their real
  contexts. Synthetic baseline retains four distinct slots (100–103); exactly one
  initial and one later independent header request exist per slot. Critical accounts
  and genesis are independently re-read after their original observations. Three
  concurrent requests is the upper bound, including rolling dependency scheduling.
- Named immutable captures bind full parameters, provider, investigation, network,
  synthetic mode, time and digest. Explicit age bounds govern reuse; current reads
  and rechecks never use this cache. Historical transaction reuse retains its signature,
  slot and original header. Failed reads cannot become successful cache entries.
- Restart tests preserve both retry eligibility and consumed final grants; completed
  sample resumes preserve attempts and cached bytes. Killed workers retain completed
  replies and charged in-flight attempts. Deadline-expired sessions reject further
  discretionary reads; lost responses retain pessimistic byte accounting.
- Equivalent sequential and batched synthetic reads yield identical address/context/
  raw-account facts while using three total calls across the two schedules. This is
  a correctness comparison, **not a live speedup measurement**.

Review improvements: fixed final-grant reallocation on completed-sample restart,
checked provider/owner identity on resume, prevented sample-prefix contamination,
included epoch contexts in header reservations, retained all critical initial reads,
and added summary-failure regression coverage. Reviewed the actual CLI/common diff
and all new scheduler/cache/wire files. No actionable phase-scoped findings remain.

Checks: initial targeted suites **19 passed**; two review regressions added; final full
Solana suite **72 passed** in 4.320 seconds, including all legacy golden fixtures and
standalone imports. `git diff --check` passed. No live RPC, installs or EVM/Claude changes.

Blockers: none. All Phase 3 gates satisfied before starting Phase 4. Token-account
wire relationship checks establish requested byte relationships only; semantic holding
account/extension/controller conclusions remain assigned to Phases 4–5.

## Phase 4 — token controls, addresses and owner aggregation

Preparation: Phase 3 gates passed. Pin official token interface revisions and PDA
vectors before adding account layouts. Preserve all existing mint and unknown-TLV
behavior; use integer quantities and explicitly scoped owner samples.

Implemented `solana_accounts.py` and `solana_addresses.py`, holder sampling in
`solana_presets.py`/v2 collector, and expanded surface guidance. Versioned account and
address components are 1.0.0; original mint/legacy behavior remains unchanged.
`assets/layout-sources.json` records **26** downloaded official source/license files
with immutable revisions, byte counts and SHA-256 digests. Downloads were read only
into `/private/tmp`; no repositories were executed and no packages installed.

Pinned revisions: Token-2022 `a3e696e42a9fbf87dea68af1443d354fc4054a9b`,
Solana SDK `d89042bd5ef842c9a933be8dfd1abcf7fdef9ab7`, associated-token
interface `2dc55ee1009d787eea7e1c401b8f27e6892bff4b`. Layout provenance
is not proof of any live deployed program version. Added small official PDA vectors
and synthetic integer/frozen-account fixtures under `tests/fixtures/`.

Acceptance evidence:

- Original SPL/Token-2022 holdings retain exact mint/program, spending owner, state,
  delegate/allowance, close authority and optional native reserve. Present all-zero
  COption keys and Some(0) reserves remain distinct from absent values.
- Valid base fields survive malformed/unsupported TLV, with explicit error/inventory
  gaps. Wrong base-account roles fail before emitting mint/holding facts. Known tags
  are checked against the pinned interface; unknown tags retain raw hashes. Original
  legacy Token-2022 boundary tests continue passing without changed golden bytes.
- Withheld fees, memo/CPI guards, hook/pausable markers and authority controls have
  scoped decoders. Encrypted balances/withheld quantities remain unknown. Display
  multipliers never change atomic supply; metadata/group pointers remain metadata
  relationships. The current permissioned-burn authority is separately inventoried.
- Fee selection requires a captured epoch containing the mint context; old/unknown
  epochs cannot establish current fees. Revoked freeze authority never clears an
  observed holding account's frozen state. Controls always retain unresolved paths.
- Same-response mint/holdings produce integer owner totals, exact ratio inputs,
  rounded display strings, observed coverage, missing/mismatched accounts, discovery
  ranks versus sampled amounts, and separately evidenced custody exclusions. Values
  above floating-point precision retain exact decimal strings. No address label is
  treated as a burn and no spending owner is asserted to be a beneficial owner.
- All four pinned official PDA vectors match; seed lengths/counts, on-curve candidates,
  canonical 64-byte signatures, bounded SDK bump search and token-program-specific
  ATA seed order are covered. Decompression is explicitly not signing/subgroup validation.

Review fixes: scoped epoch evidence to the mint's epoch interval, bounded ratio display
precision, rejected wrong extended base types before partial decoding, retained all
unknown quantities and added an independent stored integer fixture. Actual account/
address files, pinned source structs and invalid neighboring layouts were reviewed.
No actionable phase-scoped findings remain.

Checks: initial targeted addresses **5**, accounts **7**, holders **5** passed; three
review/fixture tests added. Final full Solana **92 passed** in 4.386 seconds; legacy
goldens and offline-import gate included. `git diff --check` passed. No live RPC.

Blockers: none. Phase 4 acceptance criteria satisfied before Phase 5.

## Phase 5 — program and controller paths

Preparation: Phase 4 gates passed. Resolve tested loader/ProgramData and multisig
layouts from pinned primary sources, then build bounded authority edges and explicit
source-assurance levels. Unknown controllers retain evidence and unresolved paths.

Implemented `solana_programs.py`, `adapters/spl_multisig.py`, `adapters/squads_v4.py`
and a small shared bounded binary reader/package. Added
`references/programs-and-authorities.md` and `source-correspondence.md`.
Program/controller/source-assurance components are version 1.0.0. Pinned **11**
additional official source/license files (37 total in layout provenance), including
Squads production revision `af94153ff77a28b6effe46b9c94baaa93742b48c` and the
already-pinned Solana SDK loader interfaces. A guessed obsolete instruction filename
returned 404; repository-tree inspection resolved the actual `multisig_config.rs`
source before implementation. This was resolved, not treated as absent functionality.

Acceptance evidence:

- Upgradeable v3 checks full Program state, its ProgramData PDA/address/owner,
  metadata variant, upgrade-authority option and deployment slot. Metadata slices
  cannot produce complete code hashes. Recognized v2 loader observations are scoped
  to that loader; unknown/native runtime behavior does not become a safe-token claim.
  Independent later program checks require distinct requests and monotonic contexts;
  changed authority/code/deployment fields are reported as changes.
- Authority graphs retain evidenced roles and separate current paths from possible
  future program upgrades. Three-edge/twenty-account bounds include auxiliary parent
  and ProgramData accounts. Unknown logic, missing nodes, cycles and truncation remain
  visible while preserving observed authority edges.
- SPL multisig requires its complete signer set/threshold. Squads requires the exact
  owner/discriminator, stored-bump PDA, complete sorted member permissions, threshold,
  timelock and Option/configuration fields. Wrong/unverified PDA relationships and
  truncated member data fail. Configuration authority is an explicit bypass path.
- Spending-limit parent/PDA/vault/mint/amount/member/destination relationships are
  checked before creating graph edges. A foreign limit cannot become a claimed
  parent's bypass. Independent spending-limit membership, unrestricted destination
  cases and voting/timelock bypass are recorded. Sampled limits do not prove exhaustiveness.
- Publication, third-party status, compatible hash equality, local artifact equality
  and independent reproduction are separate. Incomplete bytes, mismatches and service
  unavailability cannot become unpublished-source findings. Supplied matching bytes
  alone explicitly leave independent build provenance unproven. No build was run and
  no pool configuration is proven by a program repository.

Review fixes: verified spending-limit candidates against the claimed parent before
adding edges; retained other valid paths when a candidate fails; counted the union of
controller/auxiliary accounts; required distinct recheck evidence and nondecreasing
contexts; required captured publication references and refused unsafe source URLs.
Reviewed actual decoders/graph, callers, pinned layouts/authorization checks and negative
fixtures. The Squads decoder is independent; no AGPL implementation was imported or run.
No actionable phase-scoped findings remain.

Checks: initial targeted suites **15 passed**; two graph regressions added. Final full
Solana **109 passed** in 4.511 seconds; `git diff --check` passed. Legacy fixture bytes,
EVM/Claude files and registrations remain unchanged. No live RPC, wallet or builds.

Blockers: none. Phase 5 acceptance criteria satisfied before Phase 6.

## Phase 6 — web capture and discovery

Preparation: Phase 5 gates passed. Review the EVM web capture primitives, then apply
the shared session grants and tooling-review source routes to safe public captures,
exact-mint discovery and durable URL ownership. All README suites are a phase gate.

Implemented anonymous HTTPS captures and offline discovery, network/protocol registries,
source-routing/platform references and regression fixtures. Capture source ownership,
redirects, retries, byte allowances and provider rate/backoff are durable in the common
session. Every intake position survives URL deduplication/caps. Original credential
URLs are refused before persistence; refused redirect destinations never leak secrets.
Raw failure and later successful retry bodies have distinct immutable artifacts.

Exact-mint DEX Screener/GeckoTerminal parsers retain missing quantities, rejected rows,
conflicting duplicate candidates and indexer-attributed project links. GitHub metadata,
commit and root-tree SHA bindings remain distinct, with explicit truncated-tree coverage.
IDL and verification services support bounded raw captures only; they do not assert
source correspondence. Registry program adapters remain disabled until their gates.

Primary public documentation checked on 2026-09-11: Solana cluster URLs/limits, DEX
Screener routes, keyless GeckoTerminal, GitHub API rate headers, and the sources linked
in protocol-registry.json. Full mainnet genesis is cross-referenced to the immutable
ChainAgnostic namespace revision 463bae5625aaa8c184ccc74f1db457da8a43e72b;
its draft publication is registry context, not a live genesis observation. Devnet/testnet
remain resettable and require independent expected genesis. No live provider success
is claimed. GitHub uses 60/hour, Meteora 30/second; response backoff can be stricter.

Review findings fixed: separate Git commit/tree hashes; refuse API redirects outside
the attributed route; retain each retry's raw artifact; honor Retry-After across restarts;
honor GitHub remaining/reset headers even on HTTP 200; count the public RPC new-connection
ceiling (40/10 seconds). A multi-scenario collector fixture now uses separate investigations
and asserts each intended negative cause so rate exhaustion cannot mask its assertions.
One test insertion misplaced a pre-existing deadline assertion; restored its original
scenario before final verification. No remaining actionable phase-scoped findings.

Acceptance evidence: deterministic redirects/429/403/credential refusals/zero grants/
source caps/deadlines/provider backoff all pass; wrong networks/mints/missing values/
malformed APIs/duplicate pools cannot fabricate facts. Offline discovery does no network
I/O and imports retain standalone isolation. Full question and all input URL positions
remain accounted, including unattempted caps and single-owner attribution.

Checks: web capture **10**, discovery **7**, final full Solana **126 passed** in 4.831s;
all README suites also passed: router **30**, EVM **428** (same two pre-existing resource
warnings), Solana **125** before the final GitHub regression. `git diff --check` passed.
Versions: transport 1.2.0, session runtime 1.1.0, capture/discovery/registries 1.0.0.
No installs, live RPC, registrations, EVM/Claude changes, commits or pushes.

Blockers: none. All Phase 6 gates satisfied before starting Phase 7.

## Phase 7 — Raydium pool adapter contract

Preparation: Phase 6 gates passed. Pin current official CPMM/AMM v4 layouts and reserve
formulas before implementation. Pool labels propose candidates; program ownership,
vault relationships, fee/OpenOrders dependencies and sampled LP custody require evidence.

Implemented the explicit `adapters/base.py` contract, two distinct Raydium modules,
registry capabilities, deterministic declared pool selection, atomic dependency presets,
liquidity/custody reference and synthetic offset/math fixtures. Adapter/discovery versions
are 1.0.0/1.1.0; protocol registry is 1.1.0. The two adapters are enabled for their tested
account capabilities only. Quotes, lock programs and live deployment correspondence are
not implied. Default diligence remains legacy until Phase 18.

Added 26 pinned official source/license records (63 total). CPMM revision
`59fb845a9e5bb569c8b2f3415f13b0c0ebcc6b92`, legacy AMM
`c613c87c41edbe21112c9b8341774a70009c6d7b`, current AMM
`d26944bfb76fb5fa8f91e5d440c2050ed358ef81`, Raydium OpenBook fork
`3847088b66f96b70a888c20fbf01e46ec23ad632` and upstream comparison
`c85e56deeaead43abbc33b7301058838b9c5136d` are byte-hashed in layout-sources.
All downloads were data-only temporary reads; no upstream code was installed or executed.

Acceptance evidence:

- CPMM verifies owner/discriminators, exact layouts, mint order/programs, authority,
  vault/LP PDAs, fee-config PDA/rates/reserved fields and mint/holding relationships.
  Independently specified vaults 10000/20000 minus fee buckets 140/260 yield 9860/19740.
- AMM v4 verifies its own layout, fee/PnL fields, OpenBook market/owner/mints and event
  queue. A maker bid adds 70 coin and spends 100 quote, yielding legacy reserve candidates
  10270/20300 after pending PnL. Missing/foreign dependencies preserve vault evidence and
  block the aggregate. Wrong program/layout/target/vault mutations fail for both families.
- Actual current AMM source removed OpenBook without changing the pool layout. This
  evidence-driven refinement exposes both source-scoped reserve candidates, with no
  unqualified deployed total when they disagree. Common results can be emitted when
  formulas agree. This resolves a version-assumption risk, not an external blocker.
- LP samples retain spending owner, delegate/allowance, close authority, exact sampled
  accounts and both mint/accounting denominators. A 450 sample is 450/900 of current LP
  supply and 450/1000 of accounting supply. The 100 difference is never labeled burned
  or locked. Missing/later-sample holdings contribute no numerator. Controller roots and
  program upgrade observations remain separate; no locker is currently asserted supported.
- Pool ranking declares source/indexed USD basis; preserves unpriced/conflicting/capped
  candidates and never labels rank as canonical status. Presets retain denominators and
  dependencies in one batch; same-slot separate requests cannot supply atomic arithmetic.

Review improvements: preserve valid legacy candidates when pending PnL exceeds only the
vault portion; reject unknown CPMM reserved layouts and LP decimal mismatch; retain mint
extension observations; propagate missing LP sampling gaps; distinguish complete program
control from missing metadata; check event flags/fee tiers and bounded ring traversal.
One unused test import initially prevented a test load; removed it and reran all affected
checks. Inspected actual adapter/dispatch/preset/discovery contents and negative paths.
No actionable phase-scoped findings remain.

Checks: pool contract **5 passed**, Raydium **12 passed**, final full Solana **143 passed**
in 4.776s, including unchanged legacy golden fixtures and standalone imports.
`git diff --check` passed. No live RPC/trades, commits, pushes, EVM/Claude or registration
changes. Blockers: none. Phase 7 gates satisfied before starting Phase 8.

## Phase 8 — concentrated positions

Preparation: Phase 7 gates passed. Pin official Raydium CLMM/Orca Whirlpool layouts,
position representations and tick/principal math. Resolve only specifically discovered,
bounded positions; represent NFT holding/delegation and program control separately.

Implemented Raydium CLMM/Orca Whirlpool adapters, common bounded position evidence
processing and separate protocol integer tick tables. Added `position_sample` plans,
capability/registry versions, range-custody guidance, independent synthetic fixed-offset
fixtures and numeric vectors. Concentrated adapter version 1.0.0; registry 1.2.0.

Pinned 27 source/license records (90 total): Raydium CLMM
`ed7c84a54ced59c55981780546adb0b4583dcf85`, Orca current
`408c945fef4c49ab70def4303377cfaf8f0f3c99`, and historical Orca math
`e528dd23bb41571f92cfdb49a2f15d4fa0b01bec`. Current Orca uses its own license;
corrected the initial math annotation after reading that license. Historical Apache
numeric tables are identical to current tables, verified by extracting/comparing every
numeric coefficient; retained its original notice. Wire layouts are independently
implemented, with no imported or executed external runtime.

Acceptance evidence:

- Raw pool/position owners, sizes/discriminators, PDA seeds, mint order/programs, vault
  authorities, config and boundary arrays are bound before principal arithmetic. Raydium
  permissioned seed indices and Orca fee-tier seeds remain distinct from tick spacing.
- For L=1000000 and range -100..100, tick 0 gives principal 4987/4987; tick -200 gives
  9999/0 and tick 200 gives 0/9999. Outside-range positions have no active-liquidity
  share but retain principal. Current active liquidity is never a whole-pool principal
  denominator. Each protocol reproduces its distinct official min/max tick constants.
- Fixed and dynamic Orca arrays yield identical principal; dynamic tags/bitmap, pool
  relationships, sizes and bounds are checked. Missing ticks, invalid arrays, wrong pool,
  spacing/price inconsistency and overflow refuse the affected calculation. Stored fee
  and reward checkpoints remain separate from principal and unknown later growth.
- SPL and Token-2022 NFT base ownership retain actual owner/delegate/allowance, state,
  mint extension/freeze controls and separate program upgrade evidence. Orca bundles
  require exact mint/PDA/index and active bitmap. Ownership-transfer fixtures update the
  current owner without retaining a creator assumption. Token-2022 bundle and unknown
  layout/lock representations remain explicit unsupported custody paths.
- At most six captured position leads are resolved; duplicate/unbounded inputs fail.
  Per-position atomic plans include config, price, mints/vaults, arrays, position and
  NFT/bundle dependencies. Later holding samples cannot claim custody of the initial
  principal snapshot. Sampling never establishes exhaustive or globally locked liquidity.

Review fixes: included config in the atomic principal gate; used exact protocol fee
bounds and Raydium exclusive maximum price; preserved downward tick-crossing boundaries;
validated executable flags on configurations/bundles; attached controller evidence IDs;
kept quantity encodings integral; corrected Orca license attribution. Reviewed actual
modules/presets/dispatch and negative/ownership/boundary fixtures. No remaining actionable
phase-scoped findings. Unknown dynamic/adaptive fee quotes, locker configurations and
live fee growth are declared capabilities, not silently completed work.

Checks: CLMM **7 passed**, Whirlpool **7 passed**; final full Solana **157 passed** in
5.413s. `git diff --check` passed. No RPC/trades/installations, commits/pushes or edits to
EVM/Claude/registrations/history. Blockers: none. Phase 8 gates satisfied before Phase 9.

## Phase 9 — Meteora products

Preparation: Phase 8 gates passed. Pin DLMM bin/position state and DAMM v2 position,
principal and lock semantics independently; retain neighboring products as unsupported.

Implemented Phase 9: `scripts/adapters/meteora_dlmm.py`, `meteora_damm_v2.py` and
small `meteora_common.py` evidence helpers, explicit adapter dispatch, bounded
position dependency presets, registry capabilities and liquidity/custody guidance.
New tests: `tests/meteora_fixture.py`, `test_solana_dlmm.py` (9 tests) and
`test_solana_damm_v2.py` (13 tests). Meteora adapters version 1.0.0; registry 1.3.0.
The source inventory now has 128 entries, including 38 pinned Meteora source files.

Acceptance evidence:

- DLMM recognizes the actual program and fixed 904-byte pair, 10,136-byte bin arrays
  and 8,120-byte PositionV2. Exact named positions use at most two arrays for 70 bins,
  including negative-index boundaries. Independently specified shares 25/100 and
  50/100 over bins -1/0/1 produce gross principal 750/1,000, not vault reserves.
  Missing bins retain decoded bin/vault facts while refusing a position total.
- DAMM v2 independently decodes its 1,112-byte Pool and 408-byte Position. Range
  mode uses DAMM's actual liquidity scaling (a 1,000×2^64 position produces 500/500
  at the specified price range). Compounding mode uses tracked reserve shares
  (5,000/10,000) with the actual pool-liquidity denominator, including dead liquidity.
  Layout 0's untracked reserves cannot supply that compounding calculation.
- Named NFT custody verifies Token-2022 supply, retained pool-authority issuance,
  pool freeze authority, and the actual holding. Token allowance and protocol
  delegate bits are separate; a zero token allowance is required by the delegate
  path. Owner-ATA-only removal does not become unrestricted fee/principal control.
- Stored unlocked, vested and permanent quantities, checkpoint fees, and accrued
  fees are separate. Inner/external vesting must reconcile the position vested
  total, then use the same-bank Clock and the pool's slot/timestamp mode. A 200×2^64
  release changes modeled available principal from 250/250 to 350/350; missing
  schedules/Clock keep the refresh quantity unknown without erasing stored facts.
- Wrong owning programs, neighboring discriminators, missing/mismatched mints/vaults,
  unknown modes/versions, excessive fees, stale/mixed packets, invalid delegation,
  overallocated position samples, and vesting underflow all refuse affected facts.
  DAMM v1/DBC are unsupported distinct candidates, never aliases.

Review and improvements: inspected all three final modules, call sites, presets,
fixtures and documentation against pinned definitions. Corrected Clock metadata
binding to `context_slot`; kept the DAMM retained NFT authorities and zero-allowance
protocol semantics instead of applying other protocols' revoked-authority pattern.
Changed the proposed NFT transfer boolean into an observed allowance plus an unknown
execution field, since frozen/extension controls can prevent transfer. Added tests
for per-position atomic plans and separate/contradictory Clock observations. No
remaining actionable findings. SDKs were not installed; upstream program code was
not vendored. Source metadata accurately distinguishes DLMM's package ISC declaration
from DAMM v2's Noncommercial Licence.

Checks: initial targeted suites **19 passed**; after review, full Solana **179 passed**
in 6.544 seconds, including all **22** new Meteora tests. `git diff --check` passed.
No RPC calls, transactions, dependency installations, commits or pushes. EVM/router
and frozen history unchanged. Unknown traversal, unsupported expanded positions,
operator paths and executable exits are declared capability limits, not passing facts.

Blockers: none. Phase 9 acceptance criteria satisfied before starting Phase 10.

## Phase 10 — historical effects and exit quotes

Preparation: Phase 9 gates passed. Review historical transaction wire bindings,
pinned token/swap instruction interfaces and optional public quote schemas. Build
strict effect locators and exact sale verification before any proceeds conclusion;
keep local estimates and external read-only quotes separate from executed trades.

Implemented Phase 10: `scripts/solana_transactions.py`, `solana_swaps.py`,
`solana_quotes.py`, historical/header/quote presets, CPMM quote capability and
source registry updates. Added `references/transactions-and-proceeds.md`,
`exits-and-quotes.md`, transaction fixtures and three regression suites.
Transactions/quotes versions 1.0.0; pool adapters 1.1.0; registry 1.4.0.
Source inventory now has 138 immutable entries, including ten new instruction/math
sources. Public quote schemas were reviewed in official documentation, not probed live.

Acceptance evidence:

- Equivalent legacy/v0 receipts retain identical effects using historical loaded
  keys only. Missing keys/balances/inner metadata, failed execution, wrong signature,
  slot/time, future versions and readonly effect accounts refuse affected effects.
  Failed execution retains the real network fee and no reverted token flows.
- Six protocol families have distinct tested swap role decoders. Typed token and
  position effects retain exact locators. A verified ordinary sale requires one
  direct supported swap and matching SPL source/vault/output balances and owners;
  the fixture seller differs from the fee payer. Wrong pool/mint, unrelated flows,
  nested/multihop ambiguity and reinitialization cannot become verified sales.
- WSOL fixtures distinguish existing rent/balance refunds, ephemeral creation,
  closure and other native transfers from gross consideration. Native disagreement
  leaves net proceeds unresolved while preserving a matched swap; profit is unknown.
  The two-receipt ceiling and indexed activity remain separate fields.
- Exact size policy prioritizes user quantities and uses captured-price dollar
  equivalents only with correct assets/freshness; otherwise three disclosed probes.
  Independently specified CPMM quantities 100/1,000/10,000 produce outputs
  196/1,812/9,924 with input creator fees, and 195/1,811/9,922 with output fees.
  Fee components and slippage thresholds stay distinct. Tiny inputs, zero fee-split
  denominator, disabled/frozen/unsupported state and missing Clock refuse estimates.
- Jupiter/Raydium quote fixtures bind captured bytes, route/mints/amounts, minimum
  output, fees, impact conventions and capture context. Invalid route legs, unrelated
  assets and assembled transaction responses are rejected. Concentrated/bin/local
  quotes without full execution semantics remain explicitly unsupported, while
  narrower position facts and observed sales remain available.

Review improvements: checked actual modules/callers and pinned token, six swap and
CPMM math definitions. Traced DAMM's custom dispatch instead of interpreting its
empty Anchor stubs. Fixed mint/burn metadata binding, writable account checks,
WSOL initialization order and preexisting-account ambiguity, the pinned CPMM
zero-denominator failure, malformed public quote legs, and account counts for the
three token initialization variants. Regression tests cover these fixes. No remaining
phase-scoped actionable findings; limits are stated in capabilities and reference text.

Checks: final full Solana **205 passed** in 6.356 seconds, including **26** new
transaction/sale/quote tests. `git diff --check` passed. No live RPC or quote calls,
transactions, dependency installations, commits/pushes or EVM/Claude/history edits.

Blockers: none. Phase 10 acceptance criteria satisfied before starting Phase 11.

## Phase 11 — Pump stages and creator activity

Preparation: Phase 10 gates passed. Pin current official Pump/PumpSwap IDLs and
migration semantics before enabling either adapter. Keep launch candidates, verified
initialization, completed curve and verified migration distinct; use bounded exact-key
history and effect reconciliation without human-identity or cash-out assumptions.

Implemented Phase 11: `adapters/pump_curve.py`, `pump_swap.py`, `pump_common.py`,
`pump_layouts.py`, `pump_instructions.py`, `solana_launch.py`; explicit dispatch,
transaction/rebuy effects, exact-mint retained launch leads, Pump/history presets,
registry and `references/launch-and-creator.md`. Added independent raw-byte Pump
fixtures and three suites. Pump/launch 1.0.0, transactions 1.1.0, discovery 1.2.0,
registry 1.5.0. All eight required adapter entries are enabled with scoped capability
metadata. The 147-entry inventory includes nine official Pump files pinned to
`9c82f61cb711b044a17f770ab8ce9f9bdf78f333`. The pinned public-docs tree has no LICENSE;
only interface facts were implemented, with no SDK/upstream executable code vendored.

Acceptance evidence:

- Curve/global and PumpSwap/global/fee layouts come from each owning program's own
  current IDL. The older cross-program type copies differ and are not used as aliases.
  Curve real balances 500/1,000 versus virtual 1,000/2,000 stay distinct. A complete
  curve has zero real base reserves and remains migration-unverified without a receipt.
  Default quote pubkey means native SOL; non-native quotes require their own ATA.
- PumpSwap actual reserves 10,000/20,000 stay separate from a signed virtual quote
  adjustment (the -1,000 fixture gives effective pricing reserves 10,000/19,000).
  LP holding 450 uses actual mint 900 and accounting 1,000 separately. Pool creator,
  coin creator, mutable setter/admin/boost roles and unknown beneficiaries remain distinct.
- Exact migration needs successful historical Pump migration, destination initialization
  CPI, target/counter-asset funding, matching pool/vault/LP identities, completed curve
  and later current custody. Wrong asset/destination/LP, missing funding, failed receipts,
  incomplete curve and older state refuse migration. Stale 83-byte layouts, unknown
  reserved bytes, fake suffixes, wrong programs and mixed account packets fail closed.
- Launch time needs exact successful launch and inner mint initialization, not an
  earliest signature or indexer timestamp. Exact-mint publications remain leads. Native
  dynamic/flat fee tables are scoped; unsupported special/non-native selection and Pump
  executable quotes stay unknown with raw fee/configuration facts retained.
- Two attributed creator/treasury keys retain window/page/sample limits. Sales and
  rebuys recompute from exact historical effects. Allocation, transfer direction,
  fee operations and withdrawal operations remain separate. No transfer/exchange
  label/shared funding becomes personal cash-out or human identity. Prior links
  separate historical signer continuity from a recorded creator argument.
- Inventory conservation is restricted to a stated unchanged account subset, atomic
  opening/closing snapshots, spanning per-account history and every interpreted
  receipt. 10,000 - 1,000 = 9,000 reconciles; a 9,500 close preserves a 500 mismatch.
  Missing receipts, ownership changes and incomplete history remain unresolved.

Review improvements: inspected all new modules, callers, source definitions and
fixtures. Fixed PumpSwap exact-quote buy's required OptionBool, preserved preset
context floors, recomputed supplied sale/rebuy claims, separated curve fee components,
restricted prior links to mainnet, and rejected short/empty history pages as proof
of archive coverage. Enforced pagination slot order and exact boundary coverage;
added regressions. No remaining phase-scoped actionable findings. Unimplemented
special fee/execution routes are declared limits, not passing checks or exhausted research.

Checks: final full Solana **225 passed** in 6.607 seconds, including **20** new
Pump/launch/creator tests. `git diff --check` passed. Official sources were read
without executing them; no RPC calls, trades, installs, commits/pushes or changes
to EVM/router/Claude/registrations/frozen history.

Blockers: none. Phase 11 acceptance criteria satisfied before starting Phase 12.

## Phase 12 — strict evidence and assessment validation

Preparation: Phases 1–11 gates passed. Implement the specified v2 profile without
changing the default/legacy reader. Bind raw evidence, samples/rechecks, derivation
closure and historical effects before validating coverage and analyst decisions.
Complete bounded unknowns must remain distinguishable from untouched standard work.

Implemented `solana_profile.py`, explicit installed `solana_derivations.py`, four
profile/decision/completion/evidence suites and shared fixtures, with the strict
profile, decision and completion references. V2 validation is explicitly selectable;
legacy remains the default and its golden bytes are unchanged. Reporting version
2.0.0-dev.12; profile/derivation runtime 1.0.0. Authoring and delivery remain gated
for their later phases.

Acceptance: valid partial, completed with bounded external unknowns, all-gap
insufficient-evidence and severe-adverse fixtures pass. Missing/hash-changed/cyclic
derived inputs, copied checks, uncited or masked genesis contradictions, wrong
subjects, document-as-runtime claims, unsupported effects, omitted state contexts,
fabricated source alternatives and false coverage completion fail. All findings in
each dimension must remain in coverage; high/critical concerns survive summary,
decision axes and mitigation review. Changed critical values block stability claims
while independent observations remain usable. Captured publication can support a
publication claim directly. Exact user question/focus, eleven surfaces, four axes
and quoted requirements are preserved; structural validity is not economic truth.

Review: inspected new modules and final callers, paired favorable/adverse/unknown
reports and negative mutations. Fixed coverage omissions, dishonest fallback source
labels, and creation of an empty report on failed rendering. Added the regression.
No remaining phase-scoped blocker. Validation never mutates evidence or the draft.

Checks: final Solana **248 passed** in 7.638 seconds, including 23 new tests; router
**30 passed** in 0.557 seconds and EVM **428 passed** in 17.556 seconds. EVM retained
the two baseline HTTPError temporary-file ResourceWarnings. `git diff --check`
passed before the final render-order fix; the fix changes no legacy rendered bytes.
No live RPC, install, commit/push, registration or other-specialist changes.

Blockers: none. Phase 12 acceptance criteria satisfied before starting Phase 13.

## Phase 13 — compact facts and pipeline findings

Preparation: all preceding gates passed. Reuse the strict evidence resolver and
installed typed derivations; compact output must preserve exact integer totals,
source/time/sample limits, control observations and explicit omitted-detail indexes.

Implemented `solana_facts.py`, `solana_pipeline_note.py`, the explicit v2 `facts`
command and two suites with a shared protocol-to-bundle fixture. Facts are rebuilt
only after strict raw/dependency verification; they retain complete typed outputs,
exact evidence aliases/digests, sample contexts, original question/focus/URLs, control
observations and missing-read counts. Compact display has a 12-KiB soft target with
an omitted-detail index; material controls/limits may exceed it rather than vanish.
Machine findings have stable bounded IDs, precise typed scope and no selected signal.
Coordinator notes are separate and never overwritten. Component versions 1.0.0;
reporting 2.0.0-dev.13, legacy still default.

Acceptance: all eight product families retain byte-derived principal, reserve,
position and custody facts and generate valid unjudged v2 findings. A missing CPMM
configuration preserves vaults but yields null reserves. Failed public capture does
not erase independent controls. Supply/authority changes replace affected text and
digests with stable IDs; repeat generation is byte-identical. Exact large integer
holder totals, 50.0000% sample share and two-account owner aggregates require no
mental addition, and beneficial ownership stays unresolved. Maturity metrics have
explicit source/time limits and no organic-use or fraud inference.

Review fixes: corrected inconsistent synthetic same-slot mints in the new combined
fixtures (the validator correctly rejected them); used the registry's `pumpswap`
identifier; bounded long IDs, exposed oversized field omissions, rejected symlink
note directories and removed repeated evidence recomputation from the CLI. Reviewed
new source and generated all-family findings. No remaining phase-scoped blockers.

Checks: facts **6 passed**, pipeline **4 passed**, final Solana **258 passed** in
8.719 seconds; `git diff --check` passed. No live RPC, installs or commits/pushes.
Phase 13 acceptance criteria satisfied before starting Phase 14.

## Phase 14 — compose, scaffold and preflight

Preparation: strict v2 evidence and all-family pipeline findings pass. Add compact
analyst notes, exact alias resolution, ownership and persistent explicit overrides;
validate prospective reports before atomically replacing a draft under a lock.

Implemented `solana_compose.py`, `solana_scaffold.py`, v2 CLI compose/scaffold and
manifest-based init, updated note template and `references/compose.md`. Compose
expands exact aliases, source roles and dependency samples, derives independent
ratings, retains every dimension's findings, and checks current-stage errors before
draft writes. Lane imports must match registered paths/digests/ownership; shared
sources may be cited. Lanes own their prefixes and checklists. Coordinator assigns
pipeline signals without restating facts; explicit corrections require reason and
current input digests. Opposing cross-owner signals become coordinator issues.
Reporting 2.0.0-dev.14; compose/scaffold 1.0.0; default unchanged.

Acceptance: compact notes expand to valid partial and completed-with-bounded-unknown
drafts, including both self-checked lanes. Repeated composition preserves bytes and
findings. Alias ambiguity, stale IDs/digests, wrong claim/strength, missing concern,
illegal coverage, placeholders and cross-owner replacement fail with field paths.
`--check` creates no lock/draft/evidence file. Scaffold preserves original request,
focus/URLs and pending work with null signals/TODO decisions. It refuses to replace
an analyst note. Corrections survive regenerated pipeline notes; severe concerns
are retained in summary and required in decision-axis/mitigation review.

Review improvements: a mutable lane-note inventory would invalidate the prior
draft during editing. Replaced it with immutable content-addressed note snapshots
and tested editing/failed composition against the previous valid report. Added
serialized report/manifest mutation, rollback and interrupted-write recovery; a
journal makes an interrupted draft explicitly undeliverable. Rejected symlink
outputs before reading rollback bytes and added enum-specific corrective guidance.
Reviewed actual new source, CLI callers, full lane round trips and malformed notes.

Checks: compose **8**, scaffold **3**, preflight **3**, all passed; full Solana
**272 passed** in 10.517 seconds; router **30 passed** in 0.550 seconds; EVM **428
passed** in 21.028 seconds with the two baseline ResourceWarnings. Preflight was
rerun after the final diagnostic/rollback-path hardening: **3 passed**. Final
`git diff --check` passed. No remaining phase-scoped blocker; no live RPC or installs.
Phase 14 acceptance criteria satisfied before starting Phase 15.

## Phase 15 — broad runner and lane handoffs

Preparation: the shared durable budget, captures, all protocol facts and note-to-draft
path are verified. Integrate those maintained commands around one original intake
and deadline, with public RPC, two early pointer briefs and honest partial fallback.

Implemented `solana_broad_collect.py`, `solana_import.py`, two owned lane briefs,
runbook/project/adoption references and three integration suites. One start preserves
original question, focus, URLs, deadline and shared grants; it collects controls,
holders, exact pool dependencies, LP custody candidates, up to two historical receipt
candidates, local quote probes and explicit program metadata limits. Facts and an
unjudged partial draft survive source failures. Focused controls omit markets/lanes.
Two named coordinator presets serialize and reuse the original session. Same-owner
pending captures resume; other owners reuse registered evidence without new requests.

Acceptance: a rich single-start fixture retains reserves 9,860/19,740, observed LP
custody 450, owner aggregates, discovery metrics, both self-contained briefs and a
valid partial draft. Receipt integration independently verifies 1,000 target units
sold for 500 counter-asset units with historical owner binding and no profit claim.
Two edited synthetic lane notes self-check and compose through the maintained helpers;
pending checklists remain incomplete. Routing delay, late grants, wrong networks,
blocked sources, concurrent presets and repeated start preserve timing and accounting.

Review fixes: preserved edited notes/draft/work plan on completed-start resume;
validated preset syntax before consuming either slot; serialized followups; rejected
completed-lane placeholders; corrected Gecko routing and alias subject defaults;
added transfer-hook program leads. An empty signature sample initially lacked a
subsequent network check: the new receipt stage now brackets every history read with
fresh identity/critical checks even when no transaction candidate is returned.
Review covered new untracked modules, caller paths, owned imports and documentation.

Checks: final full Solana **288 passed** in 12.562 seconds; the added two-lane
rehearsal then passed with all **5 lane-contract tests** (289 total tests now).
Router **30 passed** in 0.558 seconds; EVM **428 passed** in 19.763 seconds in this
phase, retaining its two baseline ResourceWarnings. CLI help and `git diff --check`
passed. Reporting 2.0.0-dev.15; broad runner/import 1.0.0; derivation runtime 1.1.0
uses unchanged persisted schema 1.0.0. Public RPC only; no live calls or installs.
No remaining phase-scoped blocker. Phase 15 acceptance satisfied before Phase 16.

## Phase 16 — frozen delivery and replay

Preparation: broad start, owned notes, evidence closure and legacy golden readers
pass. Add safe human rendering, atomic new-directory finalization, hash-only
verification and explicit trusted replay with a complete standalone engine snapshot.

Implemented `solana_render.py`, `solana_replay.py`, finalize/checkpoint/read/verify/
replay CLI actions, three reference guides, a complete-note fixture and three suites.
Finalize composes/preflights in a private staging tree, copies all inventoried evidence
and every local script/adapter/asset, validates, renders and byte-compares through
isolated copied-engine execution before atomically publishing a new directory.
Existing output and active analyst draft stay intact on failure. Final status now
requires the physical frozen inventory. Checkpoints retain unjudged/partial work and
are explicitly undeliverable as completed broad research.

Acceptance: completed adverse/externally bounded reports deliver with the full
reading checklist and adjacent original-source or confined frozen-file citations in
the same call. Four conclusions, original focus, all findings/concerns, eleven
coverage rows, exact typed quantities/control paths and evidence ledger survive.
Hash-only verification/read execute no frozen code and fetch nothing. Explicitly
trusted replay ignores poisoned PYTHONPATH, changed installed renderer behavior,
working-directory imports and bytecode; copied engine reproduces report/checklist
bytes without changing source files. Tampered/missing/unlisted/symlink dependencies,
synthetic without opt-in, pending/focused/malformed delivery and fake delivered
labels are rejected. Existing legacy goldens still pass unchanged.

Review improvements: moved final semantic checks before physical-freeze diagnostics;
updated the old disabled-render test to exercise an actually invalid report; replaced
an overbroad source-string import check with an AST caller-path check plus child
isolation regression. Corrected a macOS `/var` symlink alias by canonicalizing the
output parent. Rendered null now preserves its typed adjacent status (absent is not
silently reclassified unknown); incomplete drafts are not mislabeled checkpoints.
Escaped Markdown/HTML/unsafe paths and added absolute local answer citations. Manually
inspected rich CPMM (9,860/19,740 and LP custody 450), adverse-authority and incomplete
reports; no remaining actionable phase-scoped finding.

Checks: full Solana **301 passed** in 17.904 seconds; router **30 passed** in 0.472
seconds; EVM **428 passed** in 17.509 seconds with its two baseline ResourceWarnings.
After final rendering/citation corrections, delivery **5** and citations **3** passed;
CLI help and `git diff --check` passed. Reporting 2.0.0-dev.16; render/replay 1.0.0.
No live collection, installs, registrations, EVM/Claude edits or commits/pushes.
Blockers: none. Phase 16 acceptance criteria satisfied before Phase 17.

## Phase 17 — operational memory and maintained guidance

Preparation: standalone runtime, broad orchestration and immutable report replay are
verified. Add bounded nonblocking operational records and separately reviewed,
versioned/expiring lessons; update canonical skill/current-state docs only, preserving
provider policy and registrations. Default remains opt-in until Phase 18 gates.

Implemented `solana_operations.py` and `solana_maintain.py`, integrated nonblocking
stage feedback, empty default lesson data/memories, improvement guide, operational/
guidance suites and current skill/agent/runbook/evidence/root documentation. Retained
the schema-1 contract separately with explicit legacy reading. The skill entrypoint
is 174 lines; owned briefs are 589/637 words before their automatically appended
intake, commands, captures and compact facts. Essential rules were retained rather
than padded to an approximate word target.

Acceptance: each run stores at most eight closed-schema records; corrupt, expired,
future, injected or wrong-version inputs do not load or alter behavior. Ingestion
deduplicates without promotion. Promotion requires hash-bound ordered failure/success,
matching RPC scope, a supported retry/distinct source, actual dated review, applicability
and expiry. Text comes only from fixed maintained rules, never source prose or token
facts. No active lessons. Feedback failure during a real helper call (synthetic wire)
still leaves a valid draft; maintenance never modifies permissions or verdicts.

Review improvements: required recovery evidence to predate its review; bounded lesson
expiry against review time; rejected changed RPC scope and clarified HTTP status checks.
Updated obsolete transport/deadline/provider wording and four-skill counts. All local
Markdown links, UTF-8/frontmatter, common CLI help, checklist commands and current
release summaries checked. The full pre-project HANDOFF policy retains SHA-256
`1d985d9f190cb1f741af29f49a0a38591e6911306522322691a642e9892a1901`;
project EVM and Personal router/Solana symlink targets remain unchanged. EVM, Claude,
private credentials and frozen history were not edited.

Checks: operations **6**, guidance **4**, full Solana **311 passed** in 19.350 seconds;
router **30 passed** in 0.518 seconds; EVM **428 passed** in 18.521 seconds, with the
same two baseline ResourceWarnings. `git diff --check` passed. Reporting/workflow
2.0.0-dev.17; operations/maintenance 1.0.0. Default remains opt-in. No installs or
live collection. No remaining phase-scoped blockers; Phase 17 accepted before Phase 18.

## Phase 18 — acceptance and measured activation

Preparation: all seventeen implementation/review gates pass. Build the independent
expected-outcome matrix and an equivalent-demand seven-run scheduler benchmark, then
rehearse maintained orchestration and execute the single authorized round of three
fresh bounded public-mainnet cases. Record live limitations separately; do not promote
functional success into an unmeasured live-parity claim.

Implemented the independent expected-material-facts corpus, eight acceptance tests,
maintained seven-repetition scheduler benchmark and an offline live-ledger audit.
The acceptance matrix (`acceptance.md`) covers all eight protocol adapters and all
22 positive/adverse/unknown scenarios. Independent constants cover quantities,
ownership denominators, control alternatives, actual sale effects, bounded rights,
audit versions and severe-concern visibility. Reports were reviewed for factual
calibration separately from structural validation. Synthetic full-completion and
actual CLI delivery preserve the original request, all eleven surfaces and four
assessment axes; untouched/budget-only work remains an undeliverable checkpoint.

The single preregistered public round is complete: USDC, PYUSD and a recent Pump
launch. Original clocks, two bounded research lanes and at most two coordinator
presets were used for each case. See `live-results.md` and
`live-metrics.json`. All **102** started network attempts have
completion records, all cases fit the 120-attempt/64-MiB envelope, and all frozen
inventories still verify. No extra cases, repeat round, paid access or real trades.
Model: gpt-6-astra (OpenAI); macOS 26.6.2 arm64, Python 3.14.7. Exact per-case clocks,
lane stops, helper/attempt intervals, observations and remaining coverage are saved.

Live total times were **393.626382 / 269.367908 / 250.526074 seconds**, median
**269.367908 seconds**. Start helpers took 2.677722 / 2.890193 / 4.192937 seconds.
Actual root tool actions were 12 / 17 / 21, a documented proxy for model-facing
steps rather than user turns. All cases used maintained collection/notes/delivery
commands, at most one coordinator-requested offline note repair, no per-run
assembly scripts and no second freeze attempt. Missing mandatory rechecks remained
gaps. Every result is partial, with zero verified sale receipts and zero principal
ownership samples; this is **not a live rich-case parity pass**. A successful quote
or public product API publication did not become proven execution or holder rights.

Direct review found and fixed these phase-scoped defects after the affected live
checkpoint was frozen, before proceeding to the next live case where applicable:

| Severity | Finding and fix | Regression evidence |
| --- | --- | --- |
| P1 | Structured controller roots reached an address-only graph and prevented usable controller facts. Pass deduplicated addresses, preserve role/evidence root links, and retain the owning token program even with null mint/freeze authorities. | Broad-runner controller/root-link assertions and all-null-authority coverage. |
| P1 | A preset rejected an exact indexed pool because its lead account was not yet captured. Validate the exact current-run candidate and reserve the immutable preset before a bounded lead/dependency batch. | Indexed-pool prefetch succeeds; foreign key performs no calls or preset allocation. |
| P1 | Dexscreener counterpart base-token project links could be attributed to a quote-side target. Follow project links only for the exact base mint while retaining the raw market publication. | Target-as-quote regression keeps project links empty. |
| P1 | Unusable optional epoch or newer unpinned mint data could hide valid authority observations. Exclude unusable optional epoch from fee selection; retain both latest and earlier usable mint derivations with explicit temporal scope. | Changed later authority/supply remains visible and unusable; earlier pinned snapshot remains usable and labeled. Missing epoch does not erase base controls. |
| P1 | Observed Pump allocation lengths rejected known layouts with zero trailing padding. Support exact 124/301-byte allocations and completed all-zero curve reserves; reject nonzero tails or incomplete zero curves. Preserve signed virtual-quote reserves separately from custody. | Curated original account bytes/hashes plus independent numeric expectations and invalid near-neighbor cases. No migration or fresh-pin claim. |

All fixes preserve exact identity, strict consistency, immutable old reports and
finite admission. No external access failure or missing source was converted into a
passing research check. The raw Pump bytes were compared to the already pinned
upstream schema; the fixture is offline decoding evidence, not a rewritten live run.
Focused repairs passed before subsequent cases. The intermediate full Solana suites
passed at 319 (18.992s), 322 (19.577s), then final 323 after default activation.

Final checks: Solana **323 passed** in **21.463s**, router **30 passed** in **0.505s**,
EVM **428 passed** in **17.851s**. The same two baseline EVM HTTPError ResourceWarnings
remain; no failures. Focused acceptance **8 passed** in **2.190s**, including default
v2 CLI finalize/read and explicit legacy golden rendering. No Claude suite was
required because EVM implementation was unchanged. Final link/registration/import,
protected-file hashes, whitespace and benchmark results are recorded below.

Activated `solana-evidence-v2` as the default after functional acceptance. Release
collector/workflow/reporting/v2 workflow **2.0.0**; discovery/derivations **1.3.0**;
facts/broad runner/session import/Pump adapters **1.1.0**. Legacy collector/reader
**1.0.0**, legacy workflow **1.0.1** remain explicit and unchanged. Canonical
release `engine_version` retains **1.0.0** as the compatibility field specified by
the plan; a final guidance assertion prevents conflating it with the v2 versions.
Updated canonical
skill, runbook, compose/evidence guidance, README and current project HANDOFF section.
Release metadata explicitly records functional acceptance passed and live parity
unmet. Rollback instructions are in `acceptance.md`.

Remaining gate: completed broad live parity is **unmet**, owing to incomplete
critical consistency, custody, actual sale receipts and research coverage. Known
implementation defects from this round are fixed and regression-tested; their live
coverage improvement has not been remeasured. The plan expressly forbids repeating
the round until favorable and requires stopping after this acceptance report.
All eighteen phases were executed, but **the overall plan is not marked complete**.
No further phase follows; a future live validation round needs a separate instruction.

Final benchmark: seven responsive sequential/scheduled pairs with deterministic
250ms RPC / 500ms HTTP ±50ms jitter, seed 0. Measured medians **8.976761s / 7.185621s**,
**1.249267×** speedup (19.95% lower helper wall time). Each retained identical
semantic wire data, 30 RPC + 3 HTTP attempts, 34 account reads and 15,768 bytes;
four critical reads and all four usable rechecks. Peak RPC/web concurrency 3/2
versus 1/1. Slow pair **20.129540s / 15.896939s**, 429 pair **9.221366s / 7.435145s**,
timeout pair **9.210297s / 7.432791s**; failure profiles each charged one extra
attempted account read and RPC. Every started attempt completed; reports passed.
All automatic-facts helpers met the 90s synthetic responsive target. These are
injected-latency offline measurements, not model/provider or completed-research
speed claims. Runtime/fixture SHA-256 values and all CPU/elapsed rows are in
`benchmark.json`.

Final review corrected a P2 metadata conflict with the plan: `engine_version`
had been conflated with v2 release versions. Restored the legacy compatibility
label and added an assertion against `solana_common.ENGINE_VERSION`; guidance
**4 passed in 0.378s** afterward. The benchmark's exact pre-correction metadata is
retained in `benchmark-release.json`; only the label changed,
so no runtime benchmark repeat was needed. All benchmark runtime source hashes
still match the final code.

Protected-file review: **55** baseline EVM/router file hashes match, HEAD is still
`fc6020193f1471af0f6c49e0ca54b625e624eebf`, and EVM/router/Claude/history/registration
trees have no changes. Root and record Markdown local-link checks passed (78
targets); all 50 benchmark runtime and three fixture source hashes match. Canonical
skill links, frontmatter,
CLI help, exact provider-policy hash, import isolation and symlink targets passed
their suites. Final `git diff --check` passed. Full changed-file inventory:
`changed-files.txt`, including new fixtures and references.

Suggested commit message: `feat(solana): add evidence-v2 diligence workflow and parity acceptance`.
No commit, push, package install, personal registration change or further live work.
