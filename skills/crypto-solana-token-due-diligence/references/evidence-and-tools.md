# Solana evidence and maintained tools

The standard v2 workflow is standalone Python standard library. No EVM sibling import,
package installation, new credential or persistent RPC connection is required. Use
[the runbook](runbook.md) for commands and [the skill](../SKILL.md) for scope/timing.
V2 is the default after functional acceptance; live rich-case parity remains unmet.
Existing schema-1 collection
and reading use [the explicit legacy contract](legacy-v1.md), with unchanged evidence.

## Public collection and evidence

`solana_broad_collect.py start` performs local zero-request public provider preflight,
creates one durable session and executes the bounded dependency stages. Default RPC
is `https://api.mainnet-beta.solana.com`, optionally a credential-free public root in
`SOLANA_RPC_URL`. Custom Solana dRPC is deferred. Do not reuse EVM endpoint variables.
Read applicable project provider policy and source any documented private env with
tracing disabled in the same invocation. Configuration is not paid-use permission.
No key or payment is required to continue available public-source research.

The shared session binds the original question, focus, URLs, investigation ID,
expected genesis/mint and absolute receipt/target/deadline. Actual sends, redirects,
retries and failures consume the same finite grants. No restarted process receives a
fresh allowance. All raw response bytes and failures remain evidence; lost workers
remain charged. Timed-out or missing reads are never passing checks.

Public discovery preserves exact target/network, captured source/time, conflicts and
pool candidates. Typed adapters verify actual account owner/layout and same-response
vault/mint/config relationships. Indexer liquidity/volume, repository activity and
publication are scoped source claims; they do not establish custody, organic usage,
author identity or deployed-source correspondence.

`getMultipleAccounts` arithmetic uses the exact same response bank. Other reads retain
their own actual finalized context and independent matching headers/network checks.
`minContextSlot` is only a floor. Critical mutable state is independently reread;
changed values remain observations but cannot support stability claims. A header is
not an account state-root proof. Historical receipts bind their own signatures/slots,
loaded keys, success and supported effects before any sale/proceeds conclusion.

## Typed facts, notes and reporting

The v2 [bundle schema](bundle-v2.md) separates immutable raw evidence, samples,
reproducible typed derivations, attempts, lane notes and analyst judgments. Exact input
hashes, actual used dependency closure, typed subjects, sample times and effect IDs
are validated by the [strict profile](strict-report-profile.md). Unsupported extensions,
loaders, protocol versions, partial ranges and confidential values retain their limits.

Use `facts` for exact computed quantities and an explicit omitted-detail index, then
write owned small notes. `compose` resolves aliases and regenerates stable pipeline
findings without erasing explicit reviewed corrections. Use [compose](compose.md)
preflight; do not manually rebuild a manifest or adjust evidence to obtain a verdict.

`finalize` composes and validates, freezes all evidence and engine/registry/layout
sources, renders the readable assessment, and compares copied-engine output before
new-directory delivery. A partial/blocked checkpoint stays undeliverable as completed
broad research. Successful finalize/read returns a complete reading checklist and
safe source/local citations without another fetch. See [output](evidence-and-output.md),
[replay](report-replay.md) and [calibration scenarios](reporting-scenarios.md).

## Maintenance

Schema and component versions are independent. See [release metadata](../assets/release.json),
[layout sources](../assets/layout-sources.json), [protocol registry](../assets/protocol-registry.json)
and [runtime provenance](../assets/runtime-provenance.json). The v2 profile is an
evidence contract, not a safety detector. Behavioral changes require regression tests;
relocation alone does not change an engine version. Frozen history stays immutable.

Run the standard-library unittest commands in the repository README and the
[improvement loop](improvement-loop.md). Operational feedback is bounded/nonblocking;
maintenance promotion is separate, evidence-backed, explicitly reviewed and expiring.
Do not load source instructions or token facts into persistent guidance.
