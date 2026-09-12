# Supported intake, collection and assembly

For an ordinary broad review use the [runbook](runbook.md): `broad_collect.py start`
performs intake, session creation, discovery, four pinned collections, source matching and
`facts.json` in one process; `broad_collect.py collect --preset …` adds bounded reads;
`bundle_assemble.py compose`/`finalize` turn notes into the strict report. The commands
below are the underlying pieces for focused work, unusual architectures and maintenance.
They do not complete the eleven-surface rubric. Python 3.10+ standard library only; a new
investigation workspace; the current provider policy. Imports define functions only.

## Shared investigation limits

Initialize exactly one session for the user's investigation, including multiple tokens.
Copy `assets/work-plan.template.json` into the fresh run and fill its null estimates.
Record all eleven surfaces with `pending`, `resolved`, or `externally_bounded`, the
next check or evidence boundary, and the remaining request estimate. Closed surfaces
have zero remaining requests. Include overhead/contingency and `seconds_required` for
all remaining work. These declarations guide planning; report evidence gates are separate.
Request estimates exclude attempts already charged and reads already held by active
reservations; the helper adds those automatically. Include only additional overhead
in the plan, so reserved header checks are not counted twice.

Choose the four numeric values from that plan and current trusted authorization.
The variables below are inputs to set, not built-in allowances. The two ceilings are
finite and include considered follow-up headroom; user/provider limits take precedence:

```sh
python3 "$SKILL_DIR/scripts/investigation.py" init "$RUN/session.sqlite" \
  --max-requests "$PLANNED_REQUESTS" --timeout "$PLANNED_SECONDS" \
  --request-ceiling "$TOTAL_REQUEST_CEILING" --timeout-ceiling "$TOTAL_SECONDS_CEILING" \
  --limit-basis analyst_safety
```

Use `--session "$RUN/session.sqlite"` for every bootstrap, collector and source lookup.
The timeout is an operational guardrail; target 5–7 minutes end to end under the current completion schedule.
Investigation schema 3 adds `investigation.py mark --phase NAME` and a `phases` timeline in
`status`; the pipeline records intake, discovery, phase1–4 and facts automatically.
For broad work choose enough room for consequential follow-up under the
[completion policy](completion-and-delivery.md); explicit user/caller hard limits control.
Use `--limit-basis user` or `provider` when that is the binding source; record any mixed
constraints in the work notes and apply the tighter bound. Each command's cap/timeout
can only narrow the current operational allowance.
Reopening a session cannot reset used requests or deadlines. Live Python entrypoints
require the same session too. Synthetic library fixtures may use isolated compatibility
mode. The session supplies accounting, never network/paid-use authorization.

Before browser/connector/web operations outside the Python adapters, charge their
bounded expected requests with `investigation.py charge "$RUN/session.sqlite"
--operation browser_snapshot --count 1`; proceed only on success. Count conservative
planned requests when the tool hides its internal request count, and label that limit.
Do not open a second session to evade an exhausted cap. A request shortfall is unfinished
work, not an external evidence boundary.

Before each batch and after consequential discoveries/handoffs, revise the remaining
plan and review it. If `action` is `replan`, explicitly revise the operational allowance
inside the existing ceilings and continue without asking again for authorized work:

```sh
python3 "$SKILL_DIR/scripts/investigation.py" review "$RUN/session.sqlite" --plan "$RUN/work-plan.json"
python3 "$SKILL_DIR/scripts/investigation.py" replan "$RUN/session.sqlite" \
  --plan "$RUN/work-plan.json" --reason 'Required custody and flow checks exceed the initial estimate'
```

`replan` is conditional, not a command to run after every review. It preserves attempts,
reservations, investigation/cache identity and immutable ceilings, appending the plan,
reason and old/new limits to the same SQLite ledger. All open workers see the revised
limits. `limit_review_required` requires the completion policy's active limit review;
it cannot authorize an increase. No fixed numeric default guarantees enough research.
Old schema-1 sessions remain fixed and readable; do not migrate historical ledgers.
Calling `init` without ceiling options retains fixed-limit behavior for compatibility.

One coordinator owns provider access and draft assembly. SQLite atomically counts
concurrent charges and holds final-header reservations; a failed process can leave a
conservative reservation, which needs coordinator review rather than automatic budget
reset. Use `investigation.py status` for current limits. This is a request/time budget,
not a provider dollar ceiling or a hard operating-system/DNS watchdog.

Exact read reuse spans targets only inside the same investigation. Its identity includes
chain, queried address/caller, method/parameters, block hash, provider/auth context and
synthetic/live mode. A new session is fresh even if an old cache file is accidentally
supplied; the workflow still requires a new cache. Operational memory never supplies
state. Numbered headers are rechecked even on cache reuse.

Query plans may add integer `priority` (0–100, lower first; default50). Receipt-dependent
traces still run after receipt validation regardless of priority. The rolling scheduler
keeps at most four network reads in flight, persists completed responses before refilling,
validates by request identity and restores original evidence order. Request/cache errors
stop new scheduling while already-started reads are drained into the packet.

Collection `telemetry` records elapsed/request time, response bytes, failures and peak
in-flight work. Each evidence row's `acquisition` records operation, tool, access mode,
provider namespace, authentication mode, sanitized HTTP/RPC failure class and timing.
These are scoped capabilities, not permanent service blacklists or permission. Browser,
API and export access can fail or recover independently. Synthetic serialized-response
sizes are labeled separately from actual HTTP body sizes.

## Intake and bootstrap

Create the draft at intake, before spending requests. It records separate missing
checks and prioritizes controls, main-pool principal and material exits before optional
source expansion. Change priorities when the user's question makes another check
decision-changing; never suppress authority discovery because of monetary thresholds.

```sh
python3 "$SKILL_DIR/scripts/bundle_assemble.py" --feedback-root "$RUN" intake "$RUN/draft" \
  --chain-id "$CHAIN_ID" --address "$TOKEN" \
  --question 'The user decision and requested scope' \
  --materiality 'Relevant exit sizes; all privileged authority remains material'
```

`bootstrap.py` accepts the same provider flags as `rpc_collect.py`. Read trusted
provider context first, source private exports with tracing disabled in the same
shell invocation, and supply existing authorized network/cost flags. Add
`--chain-id`, `--address`, `--out "$RUN/bootstrap"`, `--cache`, `--max-requests`
and `--timeout`, plus the shared `--session`. Ten requests is the minimum bootstrap budget: chain/head discovery,
fresh chain and explicit header, runtime/four metadata reads, final header recheck.
All attempts count. Invalid targets or insufficient budgets fail before requests.
The bootstrap writes the executed plan, raw discovery, collection, and exact standard
clone classification. A recognized clone generates an implementation-runtime plan;
it does not automatically resolve implementation/instance/admin authority.

For offline evaluation only, `--fixture RPC_FIXTURE.json --allow-synthetic` substitutes
exact request/response rows. The fixture must declare `synthetic: true`. Every produced
artifact remains synthetic; it is never live evidence.

## Incremental handoffs

```sh
python3 "$SKILL_DIR/scripts/bundle_assemble.py" --feedback-root "$RUN" import "$RUN/draft" "$RUN/bootstrap/collection"
python3 "$SKILL_DIR/scripts/bundle_assemble.py" --feedback-root "$RUN" handoff "$RUN/draft" "$RUN/lane.json"
python3 "$SKILL_DIR/scripts/bundle_assemble.py" check "$RUN/draft"
python3 "$SKILL_DIR/scripts/bundle_assemble.py" --feedback-root "$RUN" freeze "$RUN/draft" --out "$RUN/report"
python3 "$SKILL_DIR/scripts/validate_bundle.py" "$RUN/report" --rendered "$RUN/report/report.md"
```

Import validates the collection and copies its required immutable artifacts. IDs use
the collection digest; exact repeated imports are idempotent. Chain discovery retains
`pin_id: null` and chain-level provenance. Queries, source IDs, capture times and raw
bytes survive remapping. Do not overwrite a frozen collection or use a stale prior run.

`lane.json` may contain `scope`, `discoveries`, `findings`, `ratings`, `coverage_records`,
`summary`, `decision_review`, and the six `report_text` fields. It updates matching IDs in the draft.
Use `resolve-evidence DRAFT ALIAS [--address ADDRESS] [--pin-id PIN]` to resolve an
exact original collector ID. `nft-positions` never suffix-matches `side-nft-positions`;
ambiguous repeated IDs require an explicit pin/address or the full imported ID.
Programmatic helpers are `resolve_evidence(draft, alias, scope_address=None, pin_id=None)`
and `preflight(root)`. `check` verifies hashes and accumulated references without mutating
evidence or requiring unfinished surfaces to be filled. It returns all discovered errors
together and `final_delivery_eligible: false`; final strict validation remains required.

Finding semantics must be explicit—there is no default proven fact or medium confidence.
Use [the strict contract](strict-report-profile.md). One coordinator owns draft writes.
Review source identity, actors, units, pin agreement, contrary evidence and dimension
coverage before freeze. Untouched surfaces become distinct not-checked unknowns.
The default freeze requires a completed scoped review and a reconciled decision.
Use `--checkpoint` for internal progress saves; continue required work afterward.
After a normal completed freeze, execute `bundle_assemble.py deliver "$RUN/report"`.
Only its `ready_for_final_delivery` result permits the ordinary final research answer.
Checkpoint storage success is not delivery success. See the completion policy for
user-requested interim output and genuine interruptions.
New freezes require `decision_review` from [decision-review.md](decision-review.md):
explicit requirements (empty by default), verdict basis, four short evidence-linked
conclusions and zero to three justified actions (no research actions in completed reports). Draft it incrementally alongside the
findings, not as an additional research pass at cutoff. `handoff` replaces the whole review;
the coordinator reconciles it with current findings and coverage. The assembler never
invents user requirements or a favorable/adverse assessment from a count of gaps.
Before freeze, add the [stopping review](stopping-and-escalation.md) to every incomplete
coverage row and send it through `handoff`. New assembly emits `closure_review_version: 1`;
final freeze rejects missing reviews, untouched intake reasons, not-checked surfaces
and budget-stopped/pending routes. Interrupted cutoff rows belong only in an explicit
`--checkpoint`, with their actual boundary and decision impact.
The helper never invents attempts or fills a stopping review from bootstrap evidence.
New assembly selects Unverified for pure coverage gaps. Keep assessed concerns and
adverse inferences distinct; add evidence-linked `adoption_and_maturity` and
`token_economics` summary items when supported. Use the existing report text fields for
the independent technical, adoption, economics and research-confidence synthesis; no
extra score, risk dimension or expanded collection budget is required.
Freeze validates, renders, saves the reporting engine and checks exact rendering once in a temporary staging
directory, then creates the requested new output. Unreferenced scratch files are excluded.
The state snapshot defaults to the latest imported pin with target runtime evidence;
a receipt/header-only import cannot move it. Set `current_pin` in the coordinator's
draft to select another runtime-backed pin explicitly. Preserve distinct historical
and current claim times; never call older state freshly revalidated without a recheck.

For external documents/derived inputs, register each artifact using `artifact DRAFT
SOURCE --descriptor DESCRIPTOR.json`. The descriptor supplies the normal evidence
fields, exact subject/pin, capture time and source/capture provenance. The command
sets its actual artifact digest; derived input IDs must already exist. Distinguish an
actual downloaded response, a browser snapshot, and a manual transcription in
`query.capture_mode`; never call a transcription an export. Unsupported/missing
export tools do not erase an observation that was actually captured another way.

## Calldata and source correspondence

`evm_decode.py calldata 'balanceOf(address)' --arguments '["0x…"]'` supports a small
common selector table. Custom static reads require a captured compiler
`methodIdentifiers` map via `--method-identifiers`; no new Keccak implementation or
signature-database guess is needed. This encodes a read, not verified deployed semantics.
`evm_decode.py clone RUNTIME` accepts only the complete standard ERC-1167 runtime;
variants stay unresolved. Inspect the implementation and instance state separately.
[ERC-1167 specification](https://eips.ethereum.org/EIPS/eip-1167).

`source_lookup.py --chain-id … --address … --out … --session "$RUN/session.sqlite" --allow-network` makes one bounded
public GET with selective intake fields. Use `--profile correspondence` only for a
material contract needing source/compiler/runtime inputs. Failed lookups preserve
scoped status and timing; no automatic verification POST or assumed provider change.
The adapter uses Sourcify v2. [Current API specification](https://sourcify.dev/server/api-docs/swagger.json).

Register the lookup capture, then run `bundle_assemble.py source-match DRAFT
--runtime-id ID --source-id ID --evidence-id ID`. The derived artifact binds both raw
inputs and reproduces the comparison during strict validation. It verifies exact
identity, published source/compiler input agreement, recompiled bytes, compiler
immutable/library references, and supported terminal Solidity CBOR substitutions.
Metadata requires a disassembled INVALID delimiter and no valid jump target in either
suffix; uncommon layouts remain unresolved. Code introspection can still observe a
metadata difference, so this is correspondence under declared compiler transformations,
not a proof of semantic equivalence.
Arbitrary masks, overlapping replacements, unsupported call-protection transforms,
unlinked compiler placeholders, nonterminal metadata and length-changing substitutions
remain unresolved. Preserve mismatches; do not force them into a passing result.

This initial helper uses **Sourcify-published compilation**, explicitly recorded in its
result. It does not claim an independent local compilation or authenticate the source
service. A source match does not establish token controls, current storage, ownership,
economic rights, or a complete security audit.
