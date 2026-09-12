# dRPC workflow reliability repair

Implemented and reviewed 2026-09-06 from clean working-tree base `9952b02`.
No commit or push. This is workflow maintenance, not a completed BOW investigation.

## Observed failure and cause

The user reported exact-address BOW discovery on Robinhood mainnet, followed by public
RPC DNS/403 failures. The assistant loaded private dRPC configuration but used the
no-flags availability example. The helper returned `fallback / network_disabled /
continue_standard_flow`, so the assistant issued a premature blocked-identity answer.
The subsequent authorized check returned ready with zero requests. No live dRPC
request, verified BOW pin or validated broad report existed in that chat.

Code and instruction review found four contributing defects:

1. The EVM skill described RPC identity verification before its optional-provider
   guidance, without an explicit entry-point lookup of saved local authorization.
   An installed symlink invoked outside the project did not automatically expose the
   checkout's README/HANDOFF guidance.
2. The first backend example omitted all network/cost/paid flags even for configured
   authorized users. Another paragraph advised the right flags, but the executable
   example and helper action encouraged fallback first.
3. One fallback result conflated missing process credentials, malformed configuration
   and omitted invocation flags. `network_disabled` also masked other omitted flags
   and skipped full local configuration validation. Python cannot know whether the
   user has granted standing permission from those flags alone.
4. HANDOFF appended new authorization above old imperative no-approval/setup instructions
   and an outdated starter prompt. Those statements described different stages, but
   remained easy to interpret as current restrictions.

The user-provided conversation is the failure provenance. No collector evidence IDs
were fabricated or appended through `maintain.py` for a collection that never ran.
The earlier successful dRPC evidence remains in
`research/drpc-config-check-2026-09-06/collection` and was checked read-only for integrity.

## Implement

- Added a required pre-RPC context step to the portable EVM skill. The small offline
  `provider_context.py` locator resolves installed symlinks and lists existing trusted
  workspace/canonical-checkout AGENTS/README/HANDOFF paths. It reads no credentials or
  approval text and makes no permission decision. Shared standalone skills work without
  these project files; no personal authorization is embedded in the skill.
- Added an explicit AGENTS pointer and rewrote HANDOFF as a current policy with a compact
  historical section. The original setup plan has a supersession notice. Standing
  authorization is scoped to this user's configured provider/network and bounded paid
  read-only research. Current user restrictions override it.
- Put the complete already-authorized check in the maintained examples, with `set +x`
  and private-file sourcing in the same invocation. A source failure stops that command.
  Keys, endpoint values and environment contents are never printed.
- Prefer matching configured authorized dRPC before public RPC. After offline ready,
  research proceeds to finite-budget live collection and fresh chain/runtime/pin checks.
  Discovery, failures and header rechecks count against the total attempt/time budget.
- Split configuration validation from execution guards. Availability schema 2 returns
  `invocation_required / review_invocation_context` for missing flags, with all
  `blocking_reasons`, `reason_category: invocation`, zero requests and `provider_tested:
  false`. Missing/invalid configuration retains `fallback / continue_standard_flow`.
  Review trusted permission once; if actually absent or revoked, use authorized
  alternatives without an optional setup/payment prompt. The helper never grants flags.
- Updated all three CLI entrypoints to execute only when `status == ready`. Collection
  returns exit 3 with no artifacts for either non-ready state. Direct transport setup
  independently enforces networking and paid-use gates, including generic dRPC aliases.

## Review and improve

Reviewed the actual source diff, every `provider_availability` caller, configuration
redaction, direct transport gates, schema consumers, frozen evidence compatibility,
provider ordering, current versus historical policy, and sharing boundaries.

Review-driven corrections:

- Updated rug-check and Solana dispatch handling so the additional non-ready state
  cannot fall through into collection. Added regressions for EVM and Solana paths.
- Updated the shared collector guides' old fallback wording and preserved Solana's
  separate endpoint/authorization scope. No EVM credential loading was added to Solana.
- Strengthened preflight tests to reject even constructing a transport client, rather
  than only detecting calls. Added a subprocess test demonstrating that exports must
  be sourced again in each fresh shell.
- Resolved platform path aliases in the linked-install fixture so the test compares
  physical paths consistently on macOS.
- An initial replay comparison against saved engine 1.0.0 output differed; that output
  predates existing fixes. Replayed the identical frozen synthetic collection/case with
  the pre-change HEAD engine 1.1.0 and candidate 2.0.0. All three findings and every
  non-engine metadata field match exactly. Only expected engine version/source digests
  differ. The prior authenticated engine 1.1.0 collection also validates under current
  code, including evidence hashes and the chain 4663 pin.

Versioning: backend **2.0.0** and availability response schema **2** explicitly version
its changed machine-readable action/status contract. EVM instruction workflow is
**1.2.1**. Rug/Solana dependency metadata records the new provider workflow separately.
Collection/case/cache schema v1, detector rules, reporting engine, rubric, screen packet
semantics, research deadlines and spending gates are unchanged. No historical engine
snapshot, cache or evidence bytes were rewritten.

## Regression and acceptance results

Before implementation, five availability assertions failed on the old fallback behavior
and two discovery tests failed because the locator did not exist. The synthetic bounded
collection neighbor already passed and remains covered. Nine new tests cover the
recurrence and adjacent safe cases; existing fallback, pin and reporting tests remain.

All README commands passed:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s skills/crypto-research/tests -q
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s skills/crypto-evm-token-due-diligence/tests -q
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s skills/crypto-rug-check/tests -q
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s skills/crypto-solana-token-due-diligence/tests -q
```

Results: **31 research + 133 EVM + 18 rug-check + 23 Solana = 205 passing tests**.
The EVM suite includes source-loading subprocess checks, no-artifact invocation gates,
redaction, a synthetic four-attempt chain/header/runtime/header-recheck collection,
provider failure packets, wrong-chain invalidation and legacy report rendering.

Additional checks:

- The real configured environment, separately sourced with tracing disabled in each
  invocation, gives `invocation_required` without flags and `ready` with existing
  authorization flags. Both report zero requests and `provider_tested: false`.
- Invoking the actual installed skill symlink from `/private/tmp` returns this project's
  three context paths. The synthetic standalone-copy test returns no personal paths.
- The skill-format validator passed using pre-existing temporary PyYAML; Python's
  default environment lacked that authoring-only dependency. Nothing was installed.
- The unchanged historic synthetic case replays identically against pre-change HEAD
  after excluding engine metadata. The saved authenticated dRPC collection validates.
- Markdown relative-file links and Git whitespace checks pass. `history/` has no diff.

No live provider request or paid usage occurred in this maintenance task. Synthetic
requests are labeled and do not establish BOW identity, authentication today, archive
coverage, or real-token accuracy. These are executable routing/discovery regressions
and a manual instruction review, not a measured fresh-model end-to-end benchmark.

## Changed files

- [AGENTS.md](../AGENTS.md)
- [HANDOFF.md](../HANDOFF.md)
- [README.md](../README.md)
- [plans/drpc-local-setup-and-live-test.md](../plans/drpc-local-setup-and-live-test.md)
- [plans/drpc-workflow-reliability.md](../plans/drpc-workflow-reliability.md)
- [skills/crypto-evm-token-due-diligence/SKILL.md](../skills/crypto-evm-token-due-diligence/SKILL.md)
- [skills/crypto-evm-token-due-diligence/assets/backend-release.json](../skills/crypto-evm-token-due-diligence/assets/backend-release.json)
- [skills/crypto-evm-token-due-diligence/assets/workflow-release.json](../skills/crypto-evm-token-due-diligence/assets/workflow-release.json)
- [skills/crypto-evm-token-due-diligence/references/deterministic-backend.md](../skills/crypto-evm-token-due-diligence/references/deterministic-backend.md)
- [skills/crypto-evm-token-due-diligence/references/examples.md](../skills/crypto-evm-token-due-diligence/references/examples.md)
- [skills/crypto-evm-token-due-diligence/scripts/backend_common.py](../skills/crypto-evm-token-due-diligence/scripts/backend_common.py)
- [skills/crypto-evm-token-due-diligence/scripts/provider_context.py](../skills/crypto-evm-token-due-diligence/scripts/provider_context.py)
- [skills/crypto-evm-token-due-diligence/scripts/rpc_collect.py](../skills/crypto-evm-token-due-diligence/scripts/rpc_collect.py)
- [skills/crypto-evm-token-due-diligence/tests/test_optional_rpc.py](../skills/crypto-evm-token-due-diligence/tests/test_optional_rpc.py)
- [skills/crypto-evm-token-due-diligence/tests/test_provider_context.py](../skills/crypto-evm-token-due-diligence/tests/test_provider_context.py)
- [skills/crypto-rug-check/assets/release.json](../skills/crypto-rug-check/assets/release.json)
- [skills/crypto-rug-check/references/collector.md](../skills/crypto-rug-check/references/collector.md)
- [skills/crypto-rug-check/scripts/rug_check.py](../skills/crypto-rug-check/scripts/rug_check.py)
- [skills/crypto-rug-check/tests/test_rug_check.py](../skills/crypto-rug-check/tests/test_rug_check.py)
- [skills/crypto-solana-token-due-diligence/assets/release.json](../skills/crypto-solana-token-due-diligence/assets/release.json)
- [skills/crypto-solana-token-due-diligence/references/evidence-and-tools.md](../skills/crypto-solana-token-due-diligence/references/evidence-and-tools.md)
- [skills/crypto-solana-token-due-diligence/scripts/solana_collect.py](../skills/crypto-solana-token-due-diligence/scripts/solana_collect.py)
- [skills/crypto-solana-token-due-diligence/tests/test_solana.py](../skills/crypto-solana-token-due-diligence/tests/test_solana.py)

Suggested commit message (not executed): `Fix dRPC context discovery and invocation routing`
