# Offline bundle contract and helpers

## Current and legacy profiles

New reports require `validation_profile: "evm-evidence-v2"` in both JSON files.
[Strict profile](strict-report-profile.md) adds explicit finding subjects/support,
derivation dependencies, pin rechecks, per-surface coverage and adverse-summary rules
to the v1 base fields below. Use [compose](compose.md) over [supported incremental assembly](supported-research-flow.md)
to build drafts; hand-copying templates is a fallback. Validator and renderer CLIs
require the current profile by default. Existing bundles are inspected with explicit
`--profile legacy-v1`; legacy output uses the preserved 1.1.2 renderer. Never strip the
new profile to make a report pass. Collection schema remains1; report profile and
reporting engine 2.2.0 are versioned separately.

## Files and dependencies

Use any writable investigation directory, independent of skill installation location:

```text
bundle/
  manifest.json       Frozen target, pins, scope, evidence, discovery, execution declarations
  report.json         Reconciled report source bound to the manifest's exact bytes
  evidence/           Raw RPC envelopes, receipts, sources, derived journals, failure records
  report.md           Deterministic output of render_report.py
  reporting-engine/   Frozen renderer, validator, dependencies and snapshot hashes
```

Python 3.10+ standard library is the only helper dependency. The validator and renderer described here never open network connections, sign, or broadcast. `tests/fixtures.py` generates only labeled synthetic data; tests use temporary directories. No credentials, package installation or paid service are required for validation. The separately enabled [collector and detectors](deterministic-backend.md) produce an evidence packet to reconcile into the strict profile over this base contract. Real diligence requires suitable RPC and optional archive/trace, ABI and Keccak tools; unavailable infrastructure narrows coverage.

Resolve `SKILL_DIR` as the directory of the loaded `SKILL.md`. Copy [manifest.template.json](../assets/manifest.template.json) and [report.template.json](../assets/report.template.json) into the bundle. They intentionally contain null identity/pin/evidence fields and **must fail** until completed with actual evidence. Do not replace missing facts with fixture values. Use `tests/fixtures.py` to inspect a complete structural example, exclusively as synthetic data.

## Manifest v1

The actual validator is `scripts/validate_bundle.py`; this contract describes its accepted broad-report format. Required IDs are unique nonempty strings. Chain IDs and block numbers are positive JSON integers, addresses are nonzero 20-byte hex strings (comparison ignores case), and block/transaction hashes are 32-byte hex strings prefixed `0x`. Address checksum correctness is not verified. Header hashes with a single repeated hex character are rejected as placeholders. Atomic supply is a decimal **string**, not a JSON float. UTC timestamps use `YYYY-MM-DDTHH:MM:SSZ`.

- `schema_version: 1`, `synthetic: boolean`, `mode: broad | formal_broad`, `question`, `materiality`, `limitations: [text]`.
- `target.requested` and `target.observed`: `{chain_id, address}`. Keep human-requested chain names in context; RPC ID is authoritative for the observed chain.
- `target.metadata`: exactly `name`, `symbol`, `decimals`, `total_supply`. Each is `{status: resolved | unresolved, value, evidence_ids: [...], reason}`. Resolved standard ABI strings/uint8/uint256 are compared against the first referenced target `eth_call` result at the current pin. Unresolved fields require `value: null` and a reason; preserve attempted-evidence references when attempts exist. The strict profile permits an explicit not-attempted gap without invented requests. For nonstandard encodings preserve the raw value and a tentative decode in a separate artifact while this standard field stays unresolved. Empty but correctly encoded strings are recorded literally, not replaced with a familiar symbol.
- `context`: investigation notes, requested chain label, exit sizes, deployment/launch `{status, chain_id, tx_hash, pin_id, evidence_ids}` or unresolved reason, candidate pools and links to unit/architecture/reconciliation tables. Context must be an object and is included in the deterministic Markdown. Context is human-reviewed; the helper does not semantically validate arbitrary context text. Place material addresses in `scope` too.
- `chains`: objects `{chain_id, label, chain_id_evidence, current_pin, pins}`. Each pin: `{id, number, hash, timestamp_utc, header_evidence}`. Capture a successful `eth_chainId` for every chain and an explicit-number/hash block query for each pin. The full raw returned header must be preserved; the validator compares number/hash/time and checks parent/state-root formatting. It does not recompute consensus block hashes or authenticate an RPC. Historical transactions need their historical block pin; the chain's `current_pin` remains separate.
- `scope`: `{id, chain_id, address, roles: [text], material: boolean, pin_id, provenance: [evidence_id], runtime, proxy}`. Combine roles for the same chain/address rather than duplicating identity. Include the current material target and every material actor/contract. Authority edges across chains require an explicit bridge/dependency model, not a cross-chain proxy implementation link.
- `runtime`: `status: captured | no_code | unavailable`. Captured/no-code requires `evidence_id` referencing scoped pinned `eth_getCode`, plus `sha256` of decoded runtime **bytes**, not the hex string. This portable integrity digest is explicitly SHA-256. Optional `keccak256` records an Ethereum code hash; its format is checked but its computation is not validated by this helper. Compute Ethereum Keccak using a verified tool, never NIST SHA3. Unavailable requires `reason` and `evidence_ids` of attempts. `no_code` is not by itself proof of an EOA, absence of special chain behavior, or safety.
- `proxy`: `{status: none_found | resolved | unresolved | not_applicable, basis, evidence_ids, implementation_scope_ids: [...], authority_scope_ids: [...]}`. `resolved` requires implementation scope; other statuses still need evidence and a bounded basis. The validator checks references/chains, not completeness of proxy reconstruction or source correspondence.
- `safety`: `no_real_keys`, `no_real_signing`, `no_broadcast` all true; `simulation: {used: false}` when absent. For used simulations include `verified_disposable_local_fork`, `synthetic_accounts_only`, `counterfactual`, `no_transaction_forwarding` all true; loopback `endpoint`, `process_provenance`, `snapshot_id`, `source_pin_id`, distinct `local_chain_id`, `verification_evidence_ids`, and `overrides: []` (explicit even if empty). Include simulation evidence. Declarations are auditable assertions, not enforcement of other tools. A loopback URL alone never verifies fork isolation.

## Evidence rows

Each row requires `{id, target: {chain_id,address}, chain_id, address, pin_id, tx_hash, kind, artifact, sha256, query, endpoint_label, captured_at_utc, decoding_basis, coverage}`. `target` binds the investigation; the row's chain/address identify the contract/actor actually queried. Use its own pin for another chain. `tx_hash` may be null. `kind` is `rpc`, `document`, `derived`, or `simulation`.

`artifact` is a bundle-relative existing file, no absolute path or traversal/symlink outside the bundle. `sha256` is the digest of its exact saved bytes. Preserve originals and put normalizations/decoded tables in additional derived files. Do not store a credential-bearing URL in `endpoint_label`; use a nonsensitive infrastructure alias. Redaction is an investigator obligation, not something the validator can guarantee.

For `rpc`, save this exact envelope, including failures:

```json
{
  "request": {"jsonrpc": "2.0", "id": "unique-id", "method": "eth_chainId", "params": []},
  "response": {"jsonrpc": "2.0", "id": "unique-id", "result": "0x7a69"}
}
```

This example is a shape illustration, not live chain verification. `query` must equal `request`. Store a real error response for a real failed request; for transport failure (no RPC response), save a `document` failure artifact with attempted method/params, transport error category, endpoint label and coverage. Do not fabricate a JSON-RPC response to stand in for a network error.

The allowlist supports chain/header/code/storage/balance/call/log/transaction/receipt reads plus `debug_traceTransaction` and `trace_transaction`. Pin code/balance/storage/calls to explicit block quantities or supported `{blockHash, requireCanonical: true}`. For `eth_call`, only the standard two parameters and optional null/empty override objects are accepted as `rpc` evidence. Nonempty state/block overrides describe a counterfactual: preserve the original envelope as a `derived` scenario artifact with explicit overrides and limitations, never as resolved target metadata or proof of unmodified deployed behavior. Match target addresses in call/read params; log queries require addresses and explicit bounds/hash. Transaction/receipt rows require matching tx hash and historical pin. Successful `debug_traceTransaction`/`trace_transaction` rows additionally require a successful RPC transaction or receipt lookup for the same transaction, chain, and pin; a trace request alone does not establish its block. A receipt lookup may describe a reverted transaction: RPC success is not transaction success. Failed/null traces may remain coverage evidence without that lookup. Return bytes and inner receipt status are not a generic verdict: manually decode intended effects, successful execution and asset deltas. Unknown ABI calldata, routed token identities, trace semantics and derived arithmetic are not automatically authenticated.

For document/derived/simulation artifacts, `query` is a nonempty object with reproducible provenance (source URL/revision, formula/input artifact IDs, or local scenario configuration). These files are hash-bound but their semantics require review. Every material conclusion needs onchain supporting evidence appropriate to its claim; a hashed marketing page is still only marketing evidence.

`discoveries` is a list of `{id, chain_id, universe, block_ranges: [[start,end]], pagination, inclusion_rules, exclusions, materiality, coverage, evidence_ids}`. Empty ranges are allowed for purely page-based discovery, with complete page bounds in `pagination`. Every finding marked `discovery_claim: true` must reference one or more discovery IDs. Do not mark it false to bypass coverage requirements.

## Report source v1

Reporting 2.6.0 emits `decision_review_version: 2` and `decision_review` in new assembly;
version 1 retains its historical validation. Version 2 allows no actions and rejects
research actions in completed reports.
The exact [decision contract](decision-review.md#versioned-decision-review) binds verdict
kind, explicit user requirements, four-axis synthesis and ordered actions to findings
and coverage; adverse findings also explain their mechanism and holder consequence.
Older reports without the extension remain readable and replay with their frozen engine.
It does not change the eleven dimensions, evidence profile or financial truth guarantees.

Required: `schema_version: 1`, matching `synthetic`, `target`, `metadata` and `safety`; `manifest_sha256` of the exact final manifest bytes; text fields `verdict`, `conditions`, `main_reasons`, `strongest_contrary_evidence`, `unresolved_questions`, `change_evidence`; `findings` and eleven `ratings`. Recommendations can be placed in reasons/change-evidence text or a separate human-reviewed artifact; tie them to deficiencies.

New assembly also supplies `closure_review_version: 1`. Incomplete coverage rows require
the `closure` fields in [stopping-and-escalation.md](stopping-and-escalation.md): priority,
decision impact, captured attempts and the next route's disposition/basis. Validation
rejects missing reviews and pending follow-up; rendering exposes stopping details and
critical gaps. Historical strict sources without this extension remain readable.

Each finding: `{id, proposition, chain_id, address, pin_id, evidence_ids, decoding_basis, evidence_type, confidence, alternatives, coverage, time_basis, stale_when, discovery_claim, discovery_ids}`. Its chain/address must be in scope and supporting evidence must include that scope/pin. Transaction and artifact/query details are linked through evidence IDs. Evidence types: `proven_fact`, `strongly_supported`, `inference`, `unknown`; confidence: `high`, `medium`, `low`, `unknown`. Unknown findings require unknown confidence. Cross-chain propositions reference additional evidence but retain a clear primary scope identity.

Each rating: `{id, status, severity, likelihood, confidence, coverage, time_basis, finding_ids, rationale}` with the eleven IDs in the output reference. Status: `pass | concern | unknown | not_applicable`. Severity: `critical | high | medium | low | none | unknown`. Likelihood: `observed | likely | possible | unlikely | unknown | not_applicable`. Coverage: `complete | partial | unavailable | not_applicable`.

A pass requires complete **declared** coverage, high/medium confidence at both rating and finding levels, severity none, resolved likelihood and no unknown/inference finding references or failed/null RPC support. It does not establish that a search actually found all contracts. Unknown requires unknown severity/confidence. Resolved finding classes cannot have unknown confidence. Not-applicable requires affirmative resolved evidence, no failed RPC support and matching coverage. Concern requires nonzero explicit severity. The helper cannot detect an investigator dishonestly labeling an unknown as a fact or misdescribing a search; evidence review remains essential.

### Concise summary (additive v1 extension)

New reports include `summary`, a nonempty ordered array of objects containing exactly
`finding_id`, `topic` and `signal`. The template's empty array intentionally fails until
actual findings are selected. Existing v1 reports without this field retain their prior
validation and byte-identical Markdown rendering; never rewrite a frozen report to add it.

- `finding_id`: one existing finding, selected once. Use a concise proposition that states
  the bounded observation and holder consequence; supporting details stay in the ledger.
- `topic`: `token_and_liquidity`, `real_work_vs_marketing`, `creator_trading_and_proceeds`,
  `prior_launches_and_identity`, `adoption_and_maturity` or `token_economics`.
  These are display groups, not new risk dimensions; the last two require the strict profile.
- `signal`: exactly `Good`, `Potential Risk`, `Bad` or `Unverified`, following the
  [reporting rules](evidence-and-output.md). Usually select 4–8 rows across applicable
  topics in materiality order; include explicit gaps and material contrary evidence.

Each selected finding must support at least one applicable rating. Good and Bad require
proven/strongly-supported evidence, high/medium finding confidence and no failed/null RPC
in that finding's support. Bad additionally requires a linked concern of medium/high/critical
severity, high/medium rating confidence and complete/partial coverage. Every high/critical
concern rating must have a referenced finding selected as Bad or Potential Risk. These
are necessary structural conditions, not a semantic completeness check: selecting an
unrelated unknown from the same rating does not disclose its actual defect. Manually
review the actual propositions and all conclusion-changing problems before delivery.

Potential Risk retains Inference, Unknown or Low confidence qualifiers for observed
concerns, conflicting evidence and adverse hypotheses. Pure gaps use Unverified and
require `claim_type: coverage_gap`, `evidence_type: unknown`, `confidence: unknown`,
`impact: unknown`, `adverse_severity: unknown`. They render in a separate neutral section
and cannot satisfy high/critical concern visibility. Older strict summaries that used
Potential Risk for a pure gap remain valid; current rendering separates them without
mutating source, and new assembly normalizes them to Unverified. Good/Bad mistakes are
rejected, not silently downgraded. Unverified is unavailable in legacy-v1.

The renderer links every summary row to its finding and its raw evidence ledger,
shows current pins and each finding's time basis,
and preserves all eleven detailed ratings. It never derives an overall grade or turns
an unknown/not-applicable rating into a pass. Custom chat prose still requires review.

Legacy reporting engine 1.1.2 was versioned separately in
[reporting-release.json](../assets/reporting-release.json); RPC collection, detectors,
cache and bundle schema remain unchanged. Older helper versions do not validate this
extension: use the current validator for new summaries and the preserved engine for
historical report replay.

Version 1.1.2 changes only rendering: summary rows use ✅ Good, 🟡 Potential Risk and 🔴 Bad.
Version 1.1.1 also validates successful state-result wire shapes, binds returned logs to
address/topic/block filters and captured hashes, rejects removed/duplicate logs, checks
receipt-log transaction/block consistency, and rejects conflicting same-height chain
pins. RPC response IDs must match both value and type. RPC evidence marked `redacted`
may document a gap but cannot support resolved metadata/runtime, trace bindings, passes
or Good/Bad summaries. These are consistency checks:
they do not authenticate a provider, prove log completeness or establish economic meaning.
Legacy valid reports retain byte-identical rendering; malformed evidence that previously
slipped through is rejected. Preserve old engine snapshots for historical reproduction.

Bind after all evidence is finalized:

```python
from pathlib import Path
import hashlib, json
bundle = Path("/path/to/bundle")
report = json.loads((bundle / "report.json").read_text())
report["manifest_sha256"] = hashlib.sha256((bundle / "manifest.json").read_bytes()).hexdigest()
(bundle / "report.json").write_text(json.dumps(report, indent=2) + "\n")
```

Prefer assembler freeze, which also saves the [reporting snapshot](report-replay.md). For manual assembly execute validator, renderer, validator with `--rendered`, then `report_replay.py freeze`. All return nonzero on invalid inputs; successful broad consistency can coexist with all eleven risk ratings unknown. `--rendered` compares exact deterministic Markdown, including source digest and identity. It rejects manual changes; edit the reconciled JSON source and rerender. Custom prose/PDF/visuals require separate human/agent inspection. Never equate a successful command with protocol safety.

## Reproduce offline tests

```sh
python3 -m unittest discover -s "$SKILL_DIR/tests" -v
python3 "$SKILL_DIR/tests/fixtures.py" /path/to/empty-synthetic-demo
python3 "$SKILL_DIR/scripts/render_report.py" /path/to/empty-synthetic-demo --allow-synthetic
python3 "$SKILL_DIR/scripts/validate_bundle.py" /path/to/empty-synthetic-demo --allow-synthetic --rendered /path/to/empty-synthetic-demo/report.md
```

Fixtures explicitly label themselves synthetic and use no network. Tests reject chain/token substitution, wrong report identity, inconsistent/placeholder pins, unknown-as-pass, changed/missing artifacts, mismatched metadata, scope chains, unsafe simulation declarations and unbound rendered output. Passing demonstrates these implemented invariants only.
