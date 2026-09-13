# Compose: from analyst notes to the strict report

`bundle_assemble.py compose DRAFT NOTE.json [--lane NAME] [--checkpoint] [--check]` expands a
compact note into the strict `evm-evidence-v2` contract. `--check` validates and prints the
same result without writing anything (lanes run it on their own note before returning).
`bundle_assemble.py scaffold DRAFT` writes the coordinator note skeleton described below. It writes the plumbing the validator
demands (support roles, participant scopes, coverage closure, ratings, summary rows,
decision references) and refuses anything that would upgrade an unknown, invent evidence
or hide an adverse finding. All errors come back together with the field that caused each.
The draft is unchanged when any error exists.

## Note schema (version 1)

```json
{
  "note_schema_version": 1,
  "lane": "coordinator | liquidity | project",
  "requests_used": 12,
  "scope": [{"id": "locker", "address": "0x…", "roles": ["launch locker"], "material": true,
             "proxy": {"status": "none_found", "basis": "EIP-1967 slots are zero and the matched source has no delegatecall", "evidence": ["arch-locker-eip1967-implementation"]}}],
  "findings": [ … ],
  "coverage": { "<dimension>": { … } },
  "decision": { … },
  "text": { … }
}
```

### Finding fields

| Field | Values | Notes |
| --- | --- | --- |
| `id` | 1–60 chars `[A-Za-z0-9_-]` | Stable id; the same id in a later note replaces the finding. |
| `dimension` / `dimensions` | one of the eleven | Drives coverage, ratings and synthesis. |
| `claim` | `state_observation`, `source_analysis`, `historical_execution`, `inference`, `coverage_gap` | The kind of observation. `inference` forces strength `inference`; `coverage_gap` forces every strength/impact field to unknown. `proven_fact`/`strongly_supported` are strengths, and compose says so when they are used here. |
| `strength` | `proven_fact`, `strongly_supported`, `inference`, `unknown` | Resolved strengths need one successful RPC read of the subject at the finding pin (`direct`). |
| `confidence` | `high`, `medium`, `low`, `unknown` | Unknown only with unknown strength. |
| `impact` / `severity` | `benefit`, `adverse`, `neutral`, `unknown`; severity `low`…`critical` only for adverse | Adverse findings need `concern`. |
| `concern` | `{basis, mechanism, consequence}` | Basis `observed_behavior`, `reachable_capability`, `claim_mismatch`, `adverse_inference` (inference only), `user_requirement`. |
| `subject` | `target`, a scope id, or an address | Non-target subjects need a pinned evidence row at that address (code or getter). |
| `evidence` / `counterevidence` | aliases | `alias`, `alias@0xaddress`, `alias#role`, or `{id, address, pin, role}`. Lane captures under `lanes/<lane>/<alias>.json` are registered on first reference. |
| `topic` + `signal` | summary topics; `Good`, `Potential Risk`, `Bad`, `Unverified` | Only findings with a topic appear in the summary. Good needs benefit/neutral, resolved, high/medium and no failed evidence; Bad needs adverse, resolved, medium+ severity; Unverified needs `coverage_gap`. High/critical adverse findings are added to the summary automatically as Potential Risk if omitted. |
| `pin` | pin id or block number | Defaults to the current pin; historical executions default to the receipt's pin. |
| `text` | one or two sentences | Numbers, as-of basis, bounded proposition. Placeholders are rejected. |
| `basis`, `alternatives`, `coverage`, `time_basis`, `stale_when`, `discovery` | optional | Defaults are stated generically; override when the specific text matters. |
| `execution` | `{receipt_evidence_id, result, effects}` for `historical_execution` | Optional in the note: compose fills `receipt_evidence_id` from the finding's single receipt alias, `result` (`success`/`reverted`, `status` is accepted as an alias) from the receipt status, and derives `effects` from the receipt's target-token `Transfer` logs whose parties are `target` or declared/known scopes. Give `effects` yourself only to narrow them: `[{"kind": "erc20_transfer", "log_index": N, "asset_scope_id": "target", "from_scope_id": "…", "to_scope_id": "…", "amount_raw": "…", "units": "raw_token_units"}]`. A party with no pinned evidence row is reported, never invented. |

## Rating rules

Rows with a verified observation are rated; `Unverified` is reserved for a `coverage_gap` whose
route was not run or whose sources answered nothing.

- **Concentration:** the pipeline's custody-adjusted holder figures are observations. `Good` when
  the selected top holders hold at most 30% of supply and the largest non-custody address at most
  5%; `Potential Risk` above either bound; `Bad` when one non-custody address holds 50% or more.
  Beneficial ownership and wallet clusters stay a stated limit in the text.
- **Custody:** rate from the identified positions, their custodians and the pipeline's Safe
  (signers, threshold, modules, guard) and custodian getter reads. `Potential Risk` when
  identified custody covers a minority of the canonical pool's active liquidity or a custodian
  can withdraw, stating the covered share; `Good` when the sampled principal is locked with no
  reachable withdrawal path; `Bad` when a single unlocked owner can remove most of it. A
  custodian whose getters all reverted and whose source is unmatched keeps its withdrawal powers
  as the specific gap, not the whole row.
- **Listed LP holders (GoPlus):** the enumerated LP holders with lock flags are third-party claims;
  rate custody from the verified positions and state the listed shares and lock flags as the
  indexer's claim, naming the unread position ids the queue offers to verify. A listed LP holder
  that is not locked and holds a majority of the LP value GoPlus tallies is `Potential Risk` once
  its position is read; until then it is a specific gap, not the whole row.
- **Policies:** a documented discretionary buyback, burn or fee policy without reconciled
  execution is `Potential Risk` (discretion is the observed concern); verified receipts of the
  executed part may be `Good` for that part. `Unverified` only when the policy page was never
  captured.
- **Assurance:** audit or repository absence after the project's docs, site and repository
  links were checked is `Potential Risk`; a deployment-matched audit is `Good`.
- **Confidence axis, not rows:** team accountability, organic adoption, beneficial ownership
  and untested larger exits belong under Research confidence.

Support roles are derived: successful RPC at the subject and pin → `direct`; source
comparison → `source`; other derived → `calculation`; documents → `corroboration` (or
`source` for source lookups); RPC at another address → `identity` for code reads, else
`corroboration`; failed reads → `failed_attempt`; `counterevidence` entries keep that role.
Header and chain reads are never direct evidence. Every evidence address not already in
scope becomes a participant scope with its runtime status from the collected code read.

### Coverage fields

```json
"canonical_lp_principal_custody": {
  "status": "partial",
  "outcome": "Position 109216 is locker-owned with no approval; the remaining 80% of active liquidity is unattributed",
  "gap": "Owners of the other positions were not enumerable",
  "priority": "decision_critical",
  "decision_impact": "Cannot say whether most liquidity can be withdrawn",
  "attempts": [{"check": "Explorer position pages", "outcome": "Only the launch NFT listed", "evidence": ["doc-liquidity-nfpm-page"]}],
  "boundary": "unavailable",
  "basis": "No public index enumerates positions by pool and the subgraph requires authenticated access",
  "route_check": "A complete keyed position export",
  "route_evidence": ["doc-liquidity-nfpm-page"],
  "next_check": "Enumerate v3 Mint events for the pool with a bounded log preset",
  "rating": {"status": "unknown", "rationale": "…"}
}
```

`status` is `checked`, `partial`, `unavailable`, `not_checked` or `not_applicable`. Every
touched surface needs at least one finding (a `coverage_gap` finding for incomplete ones);
a checked or not-applicable surface needs at least one finding and no gap findings. A
`checked` surface that still has gap findings is downgraded to `partial` with a warning when
the entry carries a deliverable `boundary` (attempts default to the gap findings; lane notes
get a pending boundary); in the final note without one, compose refuses with the exact fix. A lane
finding with no coverage entry produces a `partial` surface with a `pending` route that the
coordinator's note must close; lane notes are never final, so this is a warning for them
and an error for the coordinator. The coordinator's (final) note also reports every
untouched surface and every leftover pending/budget/out-of-scope boundary up front.
Incomplete surfaces need `priority`, `decision_impact`, at least one attempt with evidence
(not for `not_checked`), and a `boundary`: `exhausted`, `unavailable` or
`not_yet_observable` for a completed report, or `pending`, `budget_exhausted`,
`out_of_scope` (checkpoint only; `finalize` rejects them). Route evidence defaults to the
attempts' evidence; give `route_evidence` only when a separate capture establishes the
boundary. A failed capture (403, shell) is fine as attempt evidence but never inside a
Good/Bad finding. Example for a token whose implementation source is unpublished: scope
`{"id": "target", "proxy": {"status": "resolved", "implementation": "0x…", "basis": "EIP-1967 slot points to an implementation whose source is unpublished", "evidence": ["token-eip1967-implementation"]}}`,
`token_controls` coverage `partial` with an attempt citing `sourcify-correspondence` and
boundary `unavailable`. Ratings are
derived: adverse finding → `concern` at the highest adverse severity; checked and all
findings resolved without failed reads → `pass`; not-applicable with resolved findings →
`not_applicable`; otherwise `unknown`. The optional `rating` block can downgrade a pass to
unknown or set likelihood/severity within the derived bounds; it cannot upgrade.

### Signals (coordinator note)

```json
"signals": {"pipeline-pool-depth": {"topic": "token_and_liquidity", "signal": "Good"},
            "pipeline-holder-distribution": {"topic": "token_economics", "signal": "Potential Risk"}}
```

`signals` gives an existing finding (typically one of the pipeline note's) a summary topic
and signal without restating it. The same Good/Bad/Unverified rules apply to the stored
finding: Good needs a resolved benefit/neutral finding with high/medium confidence and no
failed evidence; Bad needs an adverse resolved finding of medium+ severity (write an adverse
finding instead); Unverified only fits a `coverage_gap`. Unknown ids are errors.

### The pipeline note

`broad_collect.py start` (and every `collect`) writes `notes/pipeline.json` with lane
`pipeline` and composes it: deterministic `state_observation`, `source_analysis` and
`historical_execution` findings restating the pinned evidence (controls, launch execution,
position custody, pool depth and quotes, receipt-verified sales, holder distribution, side
pools, admin authority, quote-asset dependencies, maturity context, indexed creator
activity as an inference). They carry no topic or signal. Their ids are stable
(`pipeline-*`), so a coordinator note may also replace one by id when its judgement differs.

### Decision and text (coordinator note)

```json
"decision": {
  "requirements": [],
  "verdict": {"kind": "findings_with_limits", "scope": "General diligence on PONS at block 59578986", "findings": ["token-controls", "locked-position"]},
  "synthesis": {"technical_exposure": "…", "credibility_maturity": "…", "token_economics": "…", "research_confidence": "…"},
  "actions": [{"id": "m1", "kind": "mitigate", "action": "…", "reason": "…", "findings": ["seizure"], "changes_view_if": "…"}]
},
"text": {"verdict": "…", "main_reasons": "…", "strongest_contrary_evidence": "…", "unresolved_questions": "…", "change_evidence": "…"}
```

Note keys map to the report's expanded keys: `findings` → `finding_ids`, `dimensions` →
`coverage_dimensions`, `requirements` → `requirement_ids`. Verdict kinds:
`findings_with_limits` needs a resolved benefit/neutral finding among the selected ones;
`adverse_findings` is required whenever a high/critical adverse finding exists, and every
such finding must be referenced by some `mitigate` action (several may share one); `insufficient_evidence` for all-gap
packets; `requirement_unverified` needs an explicit user requirement with the user's
words. Synthesis axes default to their dimension groups (technical: controls, custody,
side pools, exits, admin, dependencies; credibility: disclosure, launch integrity;
economics: utility, rewards, concentration; confidence: all eleven) and take every finding
in those dimensions. `investigate` actions are rejected in a completed report. `text`
supplies the six report paragraphs; `conditions` defaults to the exact target and pin.

## Scaffold (coordinator note skeleton)

`bundle_assemble.py scaffold DRAFT [--out PATH] [--force]` reads `facts.json` and the draft
(with the lane notes already composed) and writes `<run>/notes/coordinator.json`:
`scope` entries for every pool, getter-named contract, owner, position owner and creator the
pipeline read (readable ids such as `pool1`, `launchFactory`, `owner-launchFactory`, with
proxy status from the EIP-1967 slot read); all eleven `coverage` keys, prefilled from the
lane coverage records (status, outcome, attempts, boundary, basis) and left as `TODO`
skeletons for untouched surfaces with suggested evidence aliases in a first attempt; an
empty `findings` list; the `decision` and `text` skeletons. Its printed result lists
`alias_hints` per dimension, the lane findings per dimension and `lane_leads`. Replace every
`TODO` and add findings; compose rejects any leftover placeholder by field name, so nothing
in the skeleton can reach the report unreviewed.

## Facts and finalize

`bundle_assemble.py facts DRAFT [--limit N] [--json]` prints every evidence alias grouped
by address with a decoded value (getters, balances, code size and keccak, storage slots,
receipts with ERC-20 transfers, documents with URLs). Read it instead of raw JSON.

`bundle_assemble.py finalize DRAFT --out REPORT [--note NOTE …] [--lane NAME] [--checkpoint]`
composes each note in order (capture registration follows each note's own `lane` field
unless `--lane` overrides it; lane captures must be plain `<id>.raw` files inside
`lanes/<lane>/`, and credential-like query parameters are stripped from recorded URLs),
runs the read-only preflight, freezes, and runs `deliver`. In `--checkpoint` mode untouched
surfaces receive an explicit not-checked review so the internal save validates.
`leads_for_coordinator` in any note is passed through and echoed in the compose result. Its
output names the failing stage and lists every error from that stage. A checkpoint freeze is
internal storage and prints that it is not deliverable.
