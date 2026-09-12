# Current evidence profile

New broad reports use schema 1 with `validation_profile: "evm-evidence-v2"` on both
manifest and report. The validator CLI requires this by default. Existing supported
artifacts use explicit `--profile legacy-v1`; do not add a strict marker to incomplete
old evidence. Python `validate()` retains its compatibility default; supported new
assembly/freeze callers must pass `required_profile=CURRENT_PROFILE`.

## Identity, pins and provenance

Every successful chain-ID and header observation is checked, including repeated or
unused observations. Contradictions invalidate evidence; raw replies remain available.
For a numbered pin set `state_profile: "numbered_rechecked"` and
`recheck_evidence_ids` to fresh, successful, distinct header observations captured
after its state reads. `canonical_hash` instead requires canonical block-hash state
parameters; provider support must be observed, never assumed. Unsupported/null reads
are gaps. No fallback to `latest` is permitted.

Chain-ID discovery may use `pin_id: null, provenance_level: "chain"`. This records
chain-level provenance without inventing an observed state block. State and execution
evidence still require their exact pins. Capture failures can be documents with
`observation_status` and original request/failure data; they cannot directly prove a
resolved state claim.

## Atomic findings

Reporting 2.1.0 adds `Unverified` for a pure coverage gap, requiring all five fields:
`claim_type: coverage_gap`, `evidence_type: unknown`, `confidence: unknown`,
`impact: unknown`, `adverse_severity: unknown`. Observed harm or adverse inference cannot
use this signal. Pure gaps do not satisfy high/critical concern visibility. Older strict
summary rows labeled Potential Risk can still be read; the current renderer displays
typed pure gaps neutrally, and new assembly emits Unverified. Legacy-v1 rendering remains
unchanged; new signals and adoption/economics topics require the strict profile.

Each finding explicitly supplies `subject_scope_id`, unique `participant_scope_ids`,
`claim_type`, `impact`, `adverse_severity` and `support`. The subject must match the
finding's chain/address. Separate distinct subjects into atomic findings.

Each support row is `{evidence_id, role, scope_id}`. Roles are `direct`, `identity`,
`source`, `calculation`, `corroboration`, `counterevidence`, or `failed_attempt`.
The existing `evidence_ids` must equal their union. A resolved finding needs direct
evidence at its subject identity/pin; an unrelated token runtime or an identity label
cannot supply that binding. Roles describe evidence use; they do not prove the
semantic relevance of arbitrary prose. Review selectors, source correspondence,
units and actors separately.

`claim_type` is `state_observation`, `source_analysis`, `historical_execution`,
`inference`, or `coverage_gap`. `impact` is `benefit`, `adverse`, `neutral`, or
`unknown`; adverse findings have an explicit low/medium/high/critical severity.
Every high/critical adverse finding independently appears in the summary as
Potential Risk or Bad, including low-confidence inferences. Summary visibility does
not upgrade evidence confidence. A generic unknown cannot substitute for it.

Typed `historical_execution` adds `execution` with `receipt_evidence_id`, `result`
(`success` or `reverted`) and decoded `effects`. Success requires receipt status 1
and a raw-linked effect on the subject. A revert can truthfully prove failure with
no persisted effects. The initial effect decoder supports standard ERC-20 Transfer
events using `kind: erc20_transfer`, `log_index`, `asset_scope_id`, `from_scope_id`,
`to_scope_id`, decimal-string `amount_raw` and `units: raw_token_units`.
It checks the emitter, topics, amount and actors against the raw receipt. Transfer
effects alone do not certify sale proceeds, profit, current sellability or a complete
economic cycle; those conclusions require reconciled quote flows and contrary checks.
The outer transaction sender/bundler is never automatically the economic seller.

## Derived evidence and coverage

Derived artifacts require `input_evidence_ids` and `derivation` with `tool`, `version`,
`operation`, explicit `parameters`, `source_urls`, and `input_sha256` mapping every input
ID to its captured digest. All transitive inputs must be registered, present and
unchanged; cycles fail. Hashing a comparison table alone is insufficient. Incidental
unreferenced notes need not be packaged as evidence.

Broad reports include bounded `discoveries` and exactly one `coverage_records` row
per risk dimension. Fields: `dimension`, `surface`, `status`, `outcome`, `gap`,
`stop_reason`, `next_check`, `evidence_ids`, `discovery_ids`, `finding_ids`.
Status is `checked`, `partial`, `unavailable`, `not_checked`, or `not_applicable`.
An honest not-checked surface may have no attempted evidence; record its own missing
check and next evidence rather than borrowing an LP gap for reward accounting.
Coverage findings must match their dimension's rating. A pass requires checked
coverage and resolved evidence. Structural validation cannot establish discovery
completeness or decide whether free-text explanations are economically adequate.

Reporting 2.2.0 adds `closure_review_version: 1`, required by new assembly. Under this
marker every partial/unavailable/not-checked coverage row has the evidence-linked
`closure` object defined in [stopping-and-escalation.md](stopping-and-escalation.md).
Missing reviews, intake placeholders, pending routes, unsupported exhaustion and
decision-critical scope exclusions fail. Completed coverage cannot retain unknown findings
or stale closure records. Captured attempts must belong to that surface's evidence.
Older strict sources without a marker and closure objects remain valid without a
retrospective review claim; new closure data requires the marker and strict profile.
The schema/profile IDs stay unchanged; frozen engines reproduce their original output.

## Decision review and actionability

Reporting 2.6.0 requires `decision_review_version: 2` for new assembly (version 1 is
retained for older reports), with the exact
[decision-review contract](decision-review.md#versioned-decision-review). Typed adverse
verdicts and mitigation actions need adverse findings; requirement gates need explicit
user quotations; all-gap packets cannot claim affirmative support. High/critical concerns
must remain in the verdict basis, synthesis and mitigation actions as well as the summary.
Neutral terms do not require a warning label. Missing review, stale references and action
bases inconsistent with coverage fail validation. Existing strict sources without this
marker remain compatible. Semantic review still owns prose truth, quoted-user intent,
credibility attribution and whether a stated mechanism warrants an adverse assessment.

## Completed report versus research checkpoint

Reporting 2.5.0 emits `completion_review_version: 2`, `completion_status: complete |
checkpoint`, and the matching `delivery_status: final_report | internal_checkpoint`.
Normal freeze requires all eleven surfaces to
have been investigated or affirmatively found not applicable. Residual uncertainty
requires captured attempts and an evidenced `exhausted`, `unavailable` or
`not_yet_observable` boundary. `not_checked`, `pending`, `budget_exhausted` and
`out_of_scope` cannot support completed broad delivery. The existing evidence, unknown
ratings and decision gates still apply; completed research does not turn unknowns into passes.

`freeze --checkpoint` explicitly saves internal unfinished work. The task remains
active. `bundle_assemble.py deliver` validates a completed frozen report and rejects
checkpoints, contradictory delivery markers and older completion versions for new
final delivery. Storage validation alone never authorizes a final response. Old reports
retain their original validation/replay semantics, including completion review version 1.
See [completion and delivery](completion-and-delivery.md) for the operating policy.

Reporting 2.6.0 emits decision review version 2. Zero actions are valid; completed reports
reject `investigate` actions, and severe findings still require supported mitigation.
Version 1 remains valid for older output. Source correspondence 1.1.0 additionally supports
unchanged literal tails before terminal CBOR when the entire suffix is unreachable by
fallthrough or a valid jump; replay selects the recorded comparison version.
