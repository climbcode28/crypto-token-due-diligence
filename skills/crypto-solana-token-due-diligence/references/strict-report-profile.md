# Strict Solana evidence profile

Use the explicit `solana-evidence-v2` profile for schema-2 reading. Default activation
is a later release gate; schema-1 keeps its isolated `legacy-v1` rules and bytes.
`solana_profile.validate` is offline/read-only and returns field-path errors. It
checks necessary evidence relationships, not the economic truth of arbitrary prose.

`manifest.json` contains `schema_version`, `profile`, `target`, `investigation_id`,
`synthetic`, full `intake`, `artifacts`, `observations`, `samples`, `derivations`,
`attempts`, `lanes`, optional `network_checks` and `header_checks`. Each artifact
has `path`, `sha256`, `bytes`. Paths must be relative regular files with no symlink
components; inventory/observation hashes bind exact bytes. JSON rejects duplicate
keys, non-finite values and implicit schema-version coercion. Synthetic use is
explicit. Root manifest/report hashes cannot be made self-referential inventory rows.

RPC artifacts retain the request/response/status and actual numeric start/completion
timestamps. Evidence `captured_at` is UTC ISO and matches completion. `source.namespace`
identifies the original provider. Document artifacts retain raw bodies; their
`source.capture` metadata includes exact URL/final URL, status, HTTP status, timestamp,
byte count and hash. Document bytes and the capture record must agree. Observations
may be unusable without disappearing from the inventory.

Every successful contextual RPC has a sample with the raw address mapping, slot,
encoding, capture time, explicit `status` (`pinned` or `partial`), `critical` flag
and optional `recheck_of`. Pinned samples require a same-provider genesis pair
bracketing collection, their matching independently rechecked finalized header,
and fresh current context. Partial samples can preserve evidence without supporting
resolved state. Critical original samples need a later independent account recheck.
All successful network/header/account observations are checked for contradictions,
including uncited responses. A changed later account is a transition; a finding with
`time_basis.stability = required` additionally needs unchanged rechecked values.

`network_checks` and each `header_checks` row name `initial_evidence_id` and
`recheck_evidence_id`. Historical headers use their actual slot/time without applying
a current-state age test. Historical transactions resolve through the `transaction`
derivation, which recomputes full keys, execution status and indexed effects from
the exact transaction/header inputs. Other execution derivations consume that output.
Failed transactions have no persisted token effects; quotes never supply such effects.

Each derived observation has the same ID as its operation record. Operations use
the explicit installed registry in `solana_derivations.py`; no downloaded code,
dynamic plugin, Python expression or arbitrary operation is executed. Inputs have
IDs and exact hashes; the transitive set must be complete and acyclic. Every actual
input is declared, every declared input is used, and outputs recompute byte-for-byte
under canonical JSON. Subject/address parameters bind the operation's output subject.
Source publications and provider quote/discovery claims retain a publication category.

Typed support names exact subjects and roles. Main substantive support must match
the finding subject; separately declared participants do not silently replace it.
State must use a pinned actual account or tested typed derivation. Pool, position
and controller semantics require their adapter/graph derivation. Documentary support
establishes publication, with no invented runtime corroboration. Execution support
names a recomputed exact effect ID involving the claimed subject. All state sample
dependencies must appear in the finding's time basis.

Optional `assertion` narrows stronger claims: `verified_sale` and `net_proceeds`
require their actual recomputed sale outcomes. `executable_capability` requires
state, observed controller paths and source correspondence as necessary conditions;
those checks alone still do not establish financial truth or guarantee execution.
Independent build reproduction is not an enabled assertion from supplied bytes.
See [source correspondence](source-correspondence.md) and
[transaction scope](transactions-and-proceeds.md).
