# Solana evidence v2 contract

Profile `solana-evidence-v2` (the default), packet/report schema **2**, session/note/adapter
contracts **1**. Evidence, assessment and completion validation, authoring, rendering and
frozen delivery are all implemented. Unknown or mismatched profiles fail; readers
never infer a profile from convenient fields or relabel old evidence. The installed
`solana_legacy_v1.py` retains collector engine 1.0.0 semantics and original rendering.
It does not make old incomplete engine snapshots executable.

## Encoding and common fields

All files use UTF-8 JSON without NaN/Infinity, duplicate object keys or implicit
type coercion. Booleans are not integers. Atomic amounts are canonical unsigned
decimal strings (`0` or `[1-9][0-9]*`); signed deltas explicitly permit a minus
sign. Slots, epochs, counts and indices are nonnegative JSON integers within u64
unless a narrower layout applies. Arithmetic uses integers/rationals, with an
explicit denominator, units and rounding rule; UI decimals are never authority.
Times are timezone-aware UTC ISO-8601 strings; elapsed durations are finite seconds.
SHA-256 digests are 64 lowercase hex characters over exact retained bytes.

Local IDs match `[A-Za-z0-9_-]{1,80}` and are unique within their type. References
resolve within this investigation, never by ticker, fuzzy label or another run's
alias. Files are relative regular files confined to the bundle; reject absolute
paths, traversal, escaping symlinks and duplicate/conflicting inventory entries.
Source URLs are sanitized HTTP(S) without credentials or sensitive query values;
unsafe links remain plain escaped text. Render untrusted text as content.

`target = {family: "solana", genesis_hash, mint}` uses canonical case-sensitive
base58 32-byte keys. Signatures encode exactly 64 bytes and are a separate type.
`subject = {genesis_hash, kind, address}` has kind `mint`, `holding`, `program`,
`controller`, `pool`, `position`, `wallet` or `document`; document subjects still
name the exact target mint. Other networks require a separately identified scope.
Labels and a missing/system-owned account never establish beneficial ownership.

## Intake, work plan and session

Intake retains `investigation_id`, `target`, verbatim `question`, `focus`, every
`urls` entry and supplied metadata, `received_at`, `target_at`, `deadline_at`,
`user_hard_deadline` and `scope` (`broad` or `focused`). A format/replay request
selects an existing frozen report and creates no research allowance.

The durable session binds intake and provider namespace, `synthetic`, request and
byte ceilings, actual started attempts, completed responses, outstanding grants,
retry-family eligibility and phase timestamps. Default ceilings: 120 attempts,
64 MiB response bytes, 3 concurrent RPC, 2 per web origin. Reserve 15 attempts
per lane and 12 final/retry attempts before discretionary reads; never grant the
same remaining allowance twice. A retry/redirect is another attempt. Account
counts, bytes, source failures and reservations remain separately visible.
Admission acquires before send transactionally. Restarts preserve all usage and
identity. Replans need a recorded trigger and cannot enlarge authorized ceilings
or override a hard deadline. Provider preflight is offline and read-only.

Collection stops by `deadline_at - 120 seconds` or the selected shorter window.
Lane cutoff is the earliest of received time +240 seconds, collection cutoff and
user limit. Late starts get the remaining time, never a fresh window. The
[work plan template](../assets/work-plan.template.json) lists the eleven surfaces.
Work states are `pending`, `running`, `done`, `blocked`; a task's blocked state
does not itself establish an evidenced external research boundary.

## Packet, observations and sample consistency

Packet fields: `schema_version`, `profile`, `component_versions`, `target`,
`investigation_id`, `synthetic`, `collection_status`, `observations`, `samples`,
`derivations`, `artifact_sha256`, `attempts`, `limits`, `phase_marks`, `gaps`.
`collection_status` is `complete`, `partial`, `blocked` or `failed` for the
scheduled collection only. It never implies complete broad research.

Each observation has `id`, `subject`, `kind` (`rpc`, `document`, `derived`),
`status`, `artifact`, `sha256`, `captured_at`, `source`, `request_id` (for RPC),
`sample_id` (for state), and explicit `synthetic`. Status is `ok`, `null`,
`rpc_error`, `transport_failure`, `invalid`, `redacted`, `unsupported`, `stale`,
`timeout`, `permission_denied` or `budget_denied`. Missing is never zero or revoked.
The raw request/response envelope remains preserved even when unusable.

A sample contains `id`, `observation_id`, ordered `addresses`, exact
`address_indices`, `encoding`, `commitment`, `context_slot`, `captured_at`,
`block_evidence_id`, `block_recheck_evidence_id` and `recheck_of` where applicable.
Validate every returned array member and null; an array-length mismatch invalidates
the mapping. One multiple-account response is coherent at its returned context;
separate requests retain separate contexts. `minContextSlot` is a lower bound,
never a historical pin. Cache reuse names the original sample/context and passes
explicit age/drift limits. Mutable critical-state/header/network rechecks are new
requests captured later, not aliases of earlier evidence. Scan every successful
identity/header read for contradictions, including uncited observations. Changed
state is a transition invalidating only stability-dependent claims.

## Derivations, programs and transaction effects

Every derivation records `id`, `operation`, `version`, `parameters`, `subject`,
`inputs: [{id, sha256}]`, `units`, `output` and its transitive dependency IDs.
Missing, tampered, cyclic or wrong-subject inputs invalidate dependent claims.
Failed inputs can establish attempts/gaps only. Exact holder aggregation deduplicates
accounts by spending owner, records the same-sample mint supply, included/excluded
accounts with reasons, unresolved custody and discovery-versus-sample timing.

Program/account facts separate owning program, spending owner, delegate, close
authority, PDA controller and upgrade controller. Authority graph edges cite their
observations; unresolved/truncated edges remain unresolved. Source assurance levels
are `publication`, `third_party_verification`, `byte_correspondence` and
`independent_reproduction`; none substitutes for the others or proves configuration.
Adapter premises bind genesis, owner, version/discriminator, immutable official
source revision/digest, required reads and individually enabled capabilities.

Historical execution binds `signature`, `transaction_evidence_id`, `slot`,
`block_evidence_id`, `version`, `execution_status`, full historical account keys,
and indexed effects. Each effect has `id`, `kind`, `program`, `mint`, participants,
atomic amount and `locator: {outer_index, inner_index}` (inner index may be null).
Resolve loaded keys from historical metadata; failed transactions supply no
persisted token effects. A sale additionally binds the exact pool, supported swap,
target movement and counter-asset outcome. Signer/fee payer is not automatically
seller. WSOL rent, fees and unrelated flows must reconcile before net proceeds.
Quotes are modeled/API observations with route, inputs, output, minimum output,
fees, context, size policy and limitations; they are never execution effects.

## Notes, findings and ownership

The [note template](../assets/note.template.json) is an unjudged coordinator draft.
`owner` is `pipeline`, `coordinator`, `liquidity` or `project`. Lanes write their own
notes/captures only and may cite registered shared captures. Only the coordinator
serially mutates the expanded draft. `compose --check` is read-only. Failed compose
preserves the prior draft; repeats are idempotent. Scaffold `TODO` fields must fail
completed-report validation. Pipeline findings have stable `pipeline-*` IDs and
no automatic signal. Analyst overrides retain reason/evidence across rebuilds.

Findings contain `id`, `owner`, `dimension`, `claim`, `strength`, `confidence`,
`impact`, `signal`, `subject`, `participants`, `text`, `support`, `counterevidence`,
`time_basis`, `limitations` and optional `concern`. Claim enums: `state_observation`,
`source_analysis`, `historical_execution`, `inference`, `coverage_gap`. Strength:
`direct`, `corroborated`, `bounded`, `unresolved`. Confidence: `high`, `medium`,
`low`. Impact: `critical`, `high`, `medium`, `low`, `informational`. Signals:
`good`, `potential_risk`, `bad`, `unverified`, or null before judgment.
Adverse findings require `concern: {basis, mechanism, consequence}` with evidence,
not missing access. Support rows name `evidence_id`, exact `subject`, `role`
(`state`, `execution`, `publication`, `derivation`, `attempt`, `context`) and
`effect_id` for execution. Failed evidence cannot directly support resolved facts.
Publication evidence establishes the published claim, not executable behavior.

## Coverage, decision and delivery

Every broad report has exactly these dimensions:

1. `token_controls`
2. `canonical_lp_principal_custody`
3. `side_pool_removal_risk`
4. `sellability_exit_depth`
5. `current_concentration`
6. `historical_launch_integrity`
7. `admin_treasury_reward_custody`
8. `reward_accounting_liveness`
9. `utility_redemption_rights`
10. `external_dependencies`
11. `development_disclosure`

Each coverage row has `dimension`, `status`, `finding_ids`, `attempt_ids`,
`decision_impact`, `closure` and `pending_work`. Coverage status is `checked`,
`partial`, `unavailable`, `not_checked`, `not_applicable`; rating separately is
`unknown`, `concern`, `no_issue_detected`, `not_applicable`. Checked/N/A needs
affirmative evidence and no unresolved contradictory gap. Closure records
`reason`, `attempt_ids`, `next_route`, `boundary` and `standard_scope_complete`.
Boundaries distinguish `resolved`, `evidenced_external_limit`, `pending`,
`budget`, `implementation_gap`. Only the first two can close completed broad work.
Unknown ratings may remain after real bounded source attempts and feasible fallback.
Untouched work, missing lanes, helper failures or elapsed time cannot close it.

Report fields include `schema_version`, `profile`, `target`, `investigation_id`,
`manifest_sha256`, `synthetic`, `scope`, `research_status`, `delivery_status`,
`question`, `focus`, `findings`, `ratings`, `coverage`, `summary_ids`, `decision`,
`limitations`. Research status is `partial`, `blocked`, `completed`; delivery status
is `draft`, `checkpoint`, `frozen`, `delivered`. Checkpoints may be unjudged and
cannot masquerade as final broad reports; focused scope cannot pass broad delivery.

Decision contains `verdict_kind`, `text`, exact quoted `requirements`, `axes`,
`finding_ids`, `counterevidence_ids`, `mitigations`, `actions`. Verdict kind:
`insufficient_evidence`, `conditional`, `favorable`, `adverse`. All-gap reports use
insufficient evidence. Four axes are `technical_exposure`, `credibility_maturity`,
`token_economics`, `research_confidence`, each with text and finding/coverage links.
Requirements quote the user's actual words; probe sizes are not user positions.
Zero actions is valid. No deferred standard research as mandatory homework. Every
high/critical adverse finding survives the summary, relevant decision axis and
mitigation accounting; volume/popularity cannot erase control risk.

Finalize composes, reports multiple field-path errors, freezes to a new directory,
validates/renders/compares, then marks delivery. Failure cannot overwrite a prior
report or mark incomplete output delivered. The inventory binds all local code,
registry/layout data, profiles, evidence and rendered bytes. Verification hashes
without executing frozen code. Trusted replay requires explicit trust, synthetic
opt-in where needed and clean import isolation; no live fetches or bundle mutation.
Readable output preserves all material sample/custody/economics/assurance limits,
adjacent existing safe citations and four decision conclusions. Structural validation
checks necessary evidence relationships; analyst review still assesses interpretation.


## Implemented manifest mapping (Phase 12)

The reporting manifest is distinct from the raw schema-2 collection packet. It
contains full intake, artifact inventory, normalized observations, samples,
derivations, attempts and lane-note inventory. See [strict-report-profile.md](strict-report-profile.md)
for exact container and binding fields. Historical execution records are the
recomputed outputs of `transaction` derivations; their indexed effects resolve
through that derived evidence ID. This keeps execution and downstream sale/launch
results within one transitive evidence ledger rather than a second mutable copy.

Samples add `status` (`pinned` or `partial`) and `critical` boolean. Unpinned usable
wire responses may remain in partial snapshots but do not support resolved state.
Time basis includes `kind`, `sample_ids` and optional `stability`; all actual state
inputs must be named. A stability-dependent claim needs unchanged critical rechecks.
Capture artifacts retain native numeric transport times while normalized evidence
uses matching ISO UTC times. This preserves original bytes and replay determinism.

`source.capture` retains document capture metadata; derived operations can consume
those raw bytes without turning publication into state. Runtime commands validate v2
explicitly; `solana-evidence-v2` is the default profile. No schema-1 evidence is rewritten.
