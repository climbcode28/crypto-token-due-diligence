# Compact notes and composition

Use the installed `scripts/solana_bundle.py`; `solana-evidence-v2` is the default.
Explicit profile flags remain valid. All paths below are within one run.

```sh
python3 skills/crypto-solana-token-due-diligence/scripts/solana_bundle.py facts RUN --profile solana-evidence-v2
python3 skills/crypto-solana-token-due-diligence/scripts/solana_bundle.py scaffold RUN --profile solana-evidence-v2
python3 skills/crypto-solana-token-due-diligence/scripts/solana_bundle.py compose RUN --profile solana-evidence-v2 --check
python3 skills/crypto-solana-token-due-diligence/scripts/solana_bundle.py compose RUN --profile solana-evidence-v2
```

`facts` checks raw input closure once and writes full `facts.json` plus
`notes/pipeline.json`. Its default display aims at 12 KiB. Material control and
coverage limits can exceed that soft target. The omitted-detail index names every
undisplayed category/typed record; `--category holders` selects a bounded view.
Exact totals, denominators, units and spending-owner limits are already computed.
Facts contain no assessment signal. Unsupported input invalidates its dependent
conclusion; it does not erase independent facts. Integrity failures must be repaired
from retained original evidence, never bypassed by changing a hash.

`scaffold` creates `notes/coordinator.json` only if absent. It preserves original
question, focus and URLs, supplies aliases and pending coverage, and leaves decisions
as TODO. Edit this JSON directly. No per-run script or helper-source read is needed.
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

Use a current exact evidence ID whenever an operation/category alias is ambiguous.
Support may instead be `{ "alias": "ID", "role": "execution", "effect_id": "ID",
"subject": { "genesis_hash": "...", "kind": "mint", "address": "..." } }`.
The actual role, subject and effect must pass the strict profile. A missing support
subject defaults to that observation's typed subject, not a fee payer or implied
human. Current sample IDs are expanded from dependency closure. Counterevidence
uses the same aliases. Explicit stability assertions still require unchanged fresh
critical rechecks.

Assign a pipeline finding without rewriting its text:

```json
"signal_assignments": {
  "pipeline-controls": {
    "signal": "potential_risk",
    "impact": "high",
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
needs a signal. Ratings derive from signals and actual coverage; unknowns never
become passing ratings merely to finish.

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
