# Compact notes and composition

Use the installed `$S/scripts/solana_bundle.py`; `solana-evidence-v2` is the default
profile. The bundle root is `$RUN/draft` (it holds `manifest.json`). `finalize` composes;
these are the standalone tools for an omitted detail or a rejected note:

```sh
python3 "$S/scripts/solana_facts.py" "$RUN/draft" --check --category holders
python3 "$S/scripts/solana_bundle.py" compose "$RUN/draft" --check
```

`facts` checks raw input closure once and writes full `facts.json` plus
`notes/pipeline.json`. Its default display aims at 12 KiB. Material control and
coverage limits can exceed that soft target. The omitted-detail index names every
undisplayed category/typed record; `--category holders` selects a bounded view.
Exact totals, denominators, units and spending-owner limits are already computed.
Facts contain no assessment signal. Unsupported input invalidates its dependent
conclusion; it does not erase independent facts. Integrity failures must be repaired
from retained original evidence, never bypassed by changing a hash.

`start` already scaffolds `notes/coordinator.json`, `notes/liquidity.json` and
`notes/project.json`; `solana_bundle.py scaffold` recreates one only when it is missing.
The scaffold preserves original question, focus and URLs, lists the citeable aliases
under `alias_hints` and pending coverage, and leaves decisions as TODO. Edit this JSON
directly. No per-run script or helper-source read is needed.
The `decision_template` and `judgment_todo` must be replaced or removed before marking
research completed. Missing knowledge may remain precisely unverified; unfinished
standard work keeps the run partial.

A compact coordinator finding can be:

```json
{
  "id": "coordinator-mint-controls",
  "dimension": "token_controls",
  "claim": "state_observation",
  "strength": "bounded",
  "signal": "unverified",
  "text": "The mint configuration was sampled; controller paths remain unresolved.",
  "support": ["controls"]
}
```

Support cites alias keys: an evidence ID (`baseline_mint_0`), a derivation ID
(`auto-controls`), an operation name or `category:address`; the `fact-` prefix shown in
compact facts is display text, not an ID. Use a current exact evidence ID whenever an
operation/category alias is ambiguous.
Support may instead be `{ "alias": "ID", "role": "execution", "effect_id": "ID",
"subject": { "genesis_hash": "...", "kind": "mint", "address": "..." } }`.
The actual role, subject and effect must pass the strict profile. A missing support
subject defaults to that observation's typed subject, not a fee payer or implied
human. A support whose typed subject differs from the finding's subject (a program,
pool or assurance fact cited from a mint-subject finding) must be declared: set the
finding's `subject` to it or list it under the finding's `participants`, otherwise
composition reports `support subject not declared by finding`. Roles are `state`,
`derivation`, `execution`, `publication`, `attempt` and `context`. Only `attempt` and
`context` may cite unusable evidence (a refused method, a failed header recheck), and a
`coverage_gap` needs at least one `attempt`, `context`, `publication` or `derivation`
support, so cite a failed read as `{ "alias": "baseline_largest_0", "role": "attempt" }`,
never as a resolved-fact support. A `state_observation` needs a `state` or
`derivation` support that is RPC-derived state; an indexer or project page supports
only `source_analysis` (`document-as-runtime/state promotion forbidden`). Claims are
`state_observation`, `source_analysis`, `historical_execution`, `inference` and
`coverage_gap`; strengths `direct`, `corroborated`, `bounded` and `unresolved`.
Current sample IDs are expanded from dependency closure. Counterevidence uses the
same aliases. Explicit stability assertions still require unchanged fresh critical
rechecks.

Assign a pipeline finding without rewriting its text. The scaffold pre-fills each
assignment with `"signal": null` and the current `input_digests` of the facts the
finding cites; set the signal (and impact/concern for adverse signals). A stale digest
after a refresh is a field-specific compose error, never a silent carry-over:

```json
"signal_assignments": {
  "pipeline-controls": {
    "signal": "potential_risk",
    "impact": "high",
    "input_digests": {"auto-controls": "<current sha256 from facts>"},
    "concern": {
      "basis": "The captured mint records a retained mint authority.",
      "mechanism": "That authority can issue additional units under the observed program rules.",
      "consequence": "Additional issuance could dilute existing holders."
    }
  }
}
```

This is an illustrative shape, not a judgment to copy into a run without that
observation. Signals are `good`, `potential_risk`, `bad`, `unverified` or null while
unjudged. Strength is `direct`, `corroborated`, `bounded` or `unresolved`. Claims are
`state_observation`, `historical_execution`, `source_analysis`, `inference` or
`coverage_gap`. Pure gaps cannot become adverse allegations. Every completed finding
needs a signal: `good` when the fact affirms a checked property, `potential_risk` or
`bad` when it shows a concern, `unverified` when it is informational (an indexer
discovery, a publication) or leaves the property open. Ratings derive from signals and
actual coverage; unknowns never become passing ratings merely to finish.

Coverage rows carry `status` `not_checked`, `partial`, `checked`, `unavailable` or
`not_applicable`. `checked` and `not_applicable` need affirmative evidence and no
unresolved gap; `unavailable` pairs with an `evidenced_external_limit` closure whose
`attempt_ids` are the failed attempts among the ids the scaffold lists in that row's
`attempt_ids` (never invented); a `resolved` boundary needs `checked` or
`not_applicable` status, so a `partial` row can only close as an evidenced external
limit or stay `pending`; a completed report allows only `resolved` or
`evidenced_external_limit` boundaries and no `pending_work`. Finding and support
subjects are `{genesis_hash, kind, address}` with `kind` one of `mint`, `holding`,
`program`, `controller`, `pool`, `position`, `wallet` or `document` (a document
subject's address is the target mint). A surface is `checked` when its standard route ran and answered, even with a stated limit: current_concentration with an `observed` holders fact (exact largest-20, custody exclusions applied), canonical_lp_principal_custody with an `observed` pool fact whose sampled positions name their custodians, utility_redemption_rights with the policy captured and its execution route attempted. Rate such rows by the [rating rules](reporting-scenarios.md#rating-rules); do not leave them `partial` for a limit the text already states.

The coordinator copies the scaffold's `decision_template` into `decision` and completes
it: `verdict_kind` (`insufficient_evidence`, `conditional`, `favorable`, `adverse`),
`text`, `finding_ids`, `counterevidence_ids`, the four `axes` each with `text`,
`finding_ids` and `coverage_dimensions` (at least one of the two), `requirements` rows
whose `quote` is a verbatim substring of the request with `status` `met` (the evidence
satisfies that requirement), `not_met` (the evidence contradicts it) or `unverified`
(not established either way), `mitigations` rows `{"finding_id", "status" (unmitigated, partial,
mitigated), "text", "evidence_ids"}` and `actions` rows `{"kind" (user_choice,
risk_response), "text"}`. A `mitigated` row needs usable `evidence_ids`; a `met` or
`not_met` requirement needs a non-gap finding; every high or critical adverse finding
must appear in `summary_ids`, `decision.finding_ids`, its axis and the mitigations. When
all evidence is gaps the verdict must be `insufficient_evidence`.

An override has `finding_id`, `reason`, `evidence_ids`, `input_digests` (each ID maps
to its current digest in facts), and `changes`. Only text, signal, impact, confidence,
concern, limitations and assertion may change. Identity and source ownership cannot.
Overrides remain in the coordinator note during automatic rebuilding; changed
correction evidence requires explicit re-review. High/critical adverse findings are
always included in summary. The analyst must also retain them in the relevant
conclusion axis and mitigation review; composition will report omissions.

Each lane edits only `notes/liquidity.json` or `notes/project.json` and its assigned
capture directory. `scaffold --owner liquidity` or `--owner project` supplies its
complete pending checklist. A lane note has all checklist keys, `done`,
`external_limit` or `pending` with a concrete reason, and existing `evidence_ids`.
Findings use that owner's prefix. Lanes cannot assign pipeline signals, override
another finding or write a decision. Captures must already be registered through
the collection helper. `imports` specifies exact `path`, `sha256` and `evidence_id`
under the lane's capture directory or explicitly shared ownership; another lane's
capture can be cited by ID but never replaced. Self-check validates actual content,
not a trusted Boolean supplied by the writer.

Composition automatically includes existing lane notes. An explicit lane argument
must still name its fixed owned path. It records immutable content-addressed note
snapshots, so further edits do not invalidate a previous draft. Opposing signals
from different owners on shared subject/evidence become `coordinator_issues`.
Completed notes require `conflict_resolutions` with the pair of finding IDs, evidence
IDs and a reason; neither finding silently disappears.

`compose --check` validates without creating a lock, draft or evidence file. Errors
include paths for stale aliases, wrong claims/strength, missing concerns, invalid
coverage and decisions. Independent current-stage errors are returned together.
Successful compose serializes mutation, validates the prospective report, snapshots
lane notes and replaces the manifest/report pair with a rollback journal. An
interrupted pair is explicitly undeliverable until the next compose recovers it;
failed composition preserves the previous valid draft. A completed draft still
requires the separate frozen-delivery gate.
