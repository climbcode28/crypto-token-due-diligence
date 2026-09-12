# Legacy schema-1 evidence — compatibility reader

For current v2 research use [evidence-and-tools.md](evidence-and-tools.md).
This retained contract describes schema-1 bundles, not the standard v2 workflow.

## Collector limits and interpretation

`scripts/solana_collect.py` defaults to 30 seconds, at most 24 attempts, no retries and
up to three concurrent final rechecks; maximum process budget is 55 seconds. Its fixed
sequence uses eight reads, nine with `--include-largest`. A killed process retains
completed evidence and durable pre-request attempt records. Startup/tool/model latency
is outside this process budget; these are limits, not a chat latency guarantee.

Require an independently established expected genesis hash and exact mint. The script
does not discover token identity, hardcode clusters, query ticker search, scan history,
simulate transactions or decode pools. It uses `SOLANA_RPC_URL` by default; use
`--rpc-url-env NAME` for another explicitly authorized endpoint. Availability checks are
offline. Prefer official public RPC and available explorer/API evidence for Solana;
no dRPC setup is required. A collector can receive a verified public endpoint via a
temporary environment variable, without saving a personal connection or credential.
Respect public rate limits and preserve incomplete evidence. Network and cost
declarations use the standalone Solana transport; dRPC access needs applicable paid-use authorization. Do not source or print unrelated credential files.
Availability schema 2 distinguishes `fallback` for configuration gaps from
`invocation_required / review_invocation_context` for omitted flags. Review applicable
current/standing authorization once, then apply it or continue authorized alternatives
if absent. EVM-only approval does not extend to Solana. Execute only on `ready`; every
availability result is offline with zero requests and `provider_tested: false`.

The packet stores `attempts/`, `evidence/`, an immutable `engine/` source snapshot and
`summary.json`. Summary binds every saved artifact by SHA-256, target by genesis/mint,
and final observations to exact RPC requests and matching response IDs. Failed/null,
redacted, malformed, mismatched, stale or changing evidence stays unknown. Summary
always says insufficient evidence: shallow mint reads do not establish complete exits,
liquidity custody, controller powers or launch behavior.

Raw base64 decoding covers initialized 82-byte SPL mints and Token-2022 mint padding,
account discriminator and TLV boundaries. Selected layouts: transfer-fee config (1),
mint-close authority (3), default account state (6), non-transferable (9), permanent
delegate (12), transfer hook (14), pausable (26). Unknown extensions preserve type,
length/hash and a critical gap. This is deliberately not a complete Token-2022 decoder.
The implementation basis is the official token-2022 interface `state.rs`, extension
enum/layouts and transfer-fee/pausable structures checked on 2026-09-06; refresh that
basis and add behavioral fixtures before extending decoding. Program ID matching does
not independently verify the deployed program build or all controller semantics.

Each mint response is finalized with its own context slot. The collector captures and
rechecks `getBlock` headers at both sampled slots and requires matching mint bytes and
owner program. It checks header age at capture (-60 to +300 seconds relative to local
clock). These are sampled consistency checks, not atomic historical-state reads, a
freshness promise after capture, or consensus verification. `minContextSlot` only sets
a lower bound. The optional largest-account response has its own context and is raw
discovery evidence; no holder concentration or current pin claim is produced from it.

## Broad bundle contract

Initialize in the collection directory with:

```sh
python3 "$SKILL_DIR/scripts/solana_bundle.py" init /path/to/run --from-collection --profile legacy-v1
```

Without collector access, initialize a new evidence folder using `--mint` and
`--genesis-hash` instead. This records the requested identity, not RPC verification.
Save web/explorer material and authorized raw RPC there; an unverified identity keeps
the result partial/blocked. Missing the optional collector itself is not a token finding.

`manifest.json` contains:

- `schema_version: 1`, `engine_version: "1.0.0"`, `target: {family: "solana", genesis_hash, mint}`;
- `synthetic` boolean and `safety: {no_real_keys: true, no_real_signing: true, no_broadcast: true}`;
- `collection_sha256`: hash of exact `summary.json` bytes, or null for independent evidence;
- `identity_evidence`: IDs of successful raw genesis and finalized base64 mint RPC evidence
  matching the requested target; these are necessary for a completed report;
- `limitations`: text array; `evidence`: rows as described below.

Each evidence row has unique `id`, `artifact` (relative, inside bundle), exact-byte
`sha256`, `kind: collector | rpc | document | derived | simulation`, `source` (URL,
revision or reproducible formula/input IDs), `subject: {family: "solana", genesis_hash,
address}` (or the exact target object), and a specific `time_basis` string. State evidence
time basis names commitment, context slot, header/hash evidence IDs and UTC time;
transaction evidence names signature, historical slot/header and success status. Document
evidence names capture/publication times and its limits. Additional networks need
their own identity verification, never the target's slot. External-chain evidence stays
in a separately identified packet and a hash-bound derived reconciliation here.

Successful independent state RPC rows (`getAccountInfo`, `getMultipleAccounts`,
`getTokenLargestAccounts`, `getTokenSupply`) also require `state: {slot, commitment:
"finalized", block_evidence_id, block_recheck_evidence_id}`. Both header IDs must refer
to raw `getBlock` evidence for that network/slot with finalized commitment,
`transactionDetails: "none"`, `rewards: false`, and matching blockhash/parent/time.
Collector rows use their bound collection's sampled-context checks instead. These
checks do not turn a response context into an exact-state historical query.

RPC artifacts preserve `{request, response}` (plus status/capture fields when present).
Keep failures as real error/transport artifacts, never fabricated success envelopes.
Collector-kind rows must refer to a hashed evidence file in the bound collection.
Simulation rows additionally declare `counterfactual`, `disposable_local_validator`, and
`synthetic_accounts_only` all true, and preserve isolation/configuration evidence in source.
Simulation declarations are auditable claims, not automatic verification of isolation.

`report.json` contains `schema_version: 1`, matching `target`, `synthetic`, `safety`,
`manifest_sha256` of final manifest bytes, `status: completed | partial | blocked`,
`question`, `verdict`, `strongest_contrary_evidence`, `change_evidence`,
`unresolved_questions` array, `findings` and eleven `ratings` from surfaces.md.

Findings: unique `id`, `class: fact | supported | inference | unknown`, `text`,
`time_basis`, `alternatives`, `coverage` (text) and `evidence_ids` array. All non-unknown
findings need evidence. Ratings: `dimension`, `status: unknown | concern |
no_issue_detected | not_applicable`, `coverage: complete | partial | unknown`, `severity`,
`likelihood`, `confidence`, `time_basis`, `basis` (text) and `evidence_ids`. Partial concerns
are allowed; no-issue/N/A needs complete stated coverage, rationale and evidence.
Completed requires all dimensions resolved with complete coverage and raw identity
evidence. It is a bounded investigation outcome, never a safety certificate.

After edits freeze the manifest, calculate SHA-256 over its exact bytes into
`report.manifest_sha256`, validate, render to a new `report.md`, then validate with
`--rendered /path/to/run/report.md`. Do not edit rendered output or raw evidence to
force a pass. For a revision use a new bundle. `--allow-synthetic` is only for explicitly
synthetic fixtures/offline exercises; never relabel them as live. Formatting validation
does not check substantive evidence sufficiency or prove that observed controls are safe.

## Maintenance verification

Run `python3 -m unittest discover -s "$SKILL_DIR/tests" -q` after changes. Keep engine,
schema and workflow versions explicit; preserve existing evidence/snapshots. Use new
synthetic fixtures for demonstrated defects and rerun the relevant sibling suites.
No installed helpers may be edited during a token investigation just to obtain a verdict.
