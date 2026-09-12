# Solana support and chain routing — 2026-09-06

## Authorized scope and starting state

The user requested Solana support in research and rug-check, a separate
`crypto-solana-token-due-diligence` skill, preservation of the EVM skill, and automatic
selection of the matching diligence skill for a researched token. This supersedes the
earlier Robinhood-only automatic integration. Verified EVM tokens (including Robinhood)
now route to EVM diligence; verified Solana mints route to Solana diligence. Native
assets stay on native-asset research; other chains have explicit unsupported coverage.

The working tree already contained the bounded research/quick-screen changes documented
in [fast-screen-and-research-budgets.md](fast-screen-and-research-budgets.md). Those changes
were preserved and extended. No commit/push was requested or run. Frozen history and
existing evidence were not edited. No paid RPC, keys, wallets or transactions were used.

## Implement

- New Solana skill: exact genesis/mint identity, SPL/Token-2022 procedures, eleven broad
  diligence dimensions, independent evidence ledger, validator and deterministic renderer.
- New standard-library collector: explicit network/cost gates using the existing EVM
  transport, dedicated Solana endpoint variable, request/response retention, mint byte
  decoding, separate finalized contexts, header/network rechecks, partial evidence and
  bounded process lifecycle. No pool decoding, trades, simulation or historical scans.
- Selected Token-2022 decoding: fees/epochs/caps, mint-close, default state,
  non-transferability, permanent delegate, transfer hook and pausable configuration.
  Unknown extensions keep hashes/types and unresolved coverage; no safety certification.
- Research chain-routing reference and offline identity-shape router; Solana market
  guidance; report/Pass 2/budget/documentation consistency. Numeric rubric v2.1 unchanged.
- Rug-check `--family solana` dispatch; existing EVM invocations remain compatible.
- Personal symlink installed at `~/.codex/skills/crypto-solana-token-due-diligence` to
  the canonical project skill. Linked offline availability returned zero requests.

Versions: research and EVM orchestration 1.1.0; rug-check dispatcher 1.1.0; Solana
collector/bundle/workflow 1.0.0 and its own schema 1. EVM backend remains 1.1.0 and EVM
packet schema remains unchanged. Solana packets are not EVM packets with renamed fields.

## Review and improve

Sequential implementation review focused on realistic boundary cases; no subagents used.

1. Enforced base58 32-byte identity with case/leading-zero preservation, mint account
   ownership/layout checks, COption distinction between absent authority and a present
   all-zero key, TLV bounds/duplicates/account-only extension rejection.
2. Kept distinct context slots and rechecked headers; `minContextSlot` never becomes an
   exact historical-state pin. Changing mint/program, stale/future/null timestamps,
   wrong networks/response IDs and errors cannot generate current observations.
3. Preserved unsupported extensions and raw top-account evidence without converting
   either to complete controls, a holder census, executable exit depth or LP custody.
4. Added a lock around the concurrent attempt budget and durable pre-request records;
   tested process termination, snapshots and retained partial output.
5. Bound bundle identity, artifacts, collection replay and report manifest hashes;
   independent RPC state rows require matching separately captured header evidence.
   Unknown/partial coverage cannot be no-issue/N/A or a completed report.
6. Verified Solana dispatch cannot implicitly reuse an EVM endpoint; rejected mixed
   EVM/Solana CLI arguments before network activity. Preserved paid-use fallback.
7. Removed obsolete Robinhood-only routing instructions from current guidance, retaining
   Robinhood network/platform safeguards and unchanged EVM investigative procedures.

## Validation

All **176 standard-library unittest cases passed**:

| Suite | Tests |
| --- | ---: |
| crypto-research | 31 |
| crypto-evm-token-due-diligence | 106 |
| crypto-rug-check | 17 |
| crypto-solana-token-due-diligence | 22 |

All four skills passed the bundled skill-creator `quick_validate.py`; all skill-relative
Markdown links resolve; `git diff --check` passed. The format checker used the existing
temporary PyYAML dependency at `/private/tmp/evm-dd-authoring-deps`. The default Python
lacked PyYAML and a temporary pip attempt could not resolve PyPI; no runtime dependency
was added to the skills or globally installed.

An end-to-end **synthetic**, offline rehearsal is saved in the ignored new directory
`runs/offline-solana-2026-09-06/`: nine fake RPC requests, an unknown Token-2022 extension,
preserved raw evidence/source snapshot, partial broad initialization, validation,
rendering and rendered-file comparison. It remained `insufficient_evidence`/`partial`.
Synthetic bundles require an explicit validation flag and are never presented as live.

No live Solana RPC collection, live end-to-end latency or labeled-token accuracy benchmark
was performed. Broad pool/program/launch/holder investigations still require additional
evidence beyond this collector. Validation checks consistency, not source truth, fraud
intent, discovery completeness, deployed-source correspondence or token safety.

## Final user preference

The user does not plan to connect dRPC for Solana. Guidance explicitly defaults to
public RPC/explorer/API sources with no dRPC key, account or persistent connection
required. A verified public endpoint may be supplied temporarily to the collector;
missing access uses bounded background-source fallback. No private EVM configuration
was changed. This clarification changed guidance only, not the tested code.

## Files changed in this update

New skill (all files under `skills/crypto-solana-token-due-diligence/`):

- `SKILL.md`, `agents/openai.yaml`, `assets/release.json`
- `references/surfaces.md`, `references/evidence-and-tools.md`
- `scripts/solana_common.py`, `scripts/solana_collect.py`, `scripts/solana_bundle.py`
- `tests/test_solana.py`

Research additions:

- `skills/crypto-research/references/chain-diligence.md`
- `skills/crypto-research/references/solana-research.md`
- `skills/crypto-research/scripts/route_diligence.py`
- `skills/crypto-research/tests/test_routing.py`

Research updates:

- `skills/crypto-research/SKILL.md`
- `skills/crypto-research/assets/report-template.md`, `assets/workflow-release.json`
- References: `backend-and-history.md`, `evidence-pull.md`, `output-and-validation.md`,
  `pass2-protocol.md`, `rating-rubric.md` (completion wording only),
  `robinhood-diligence.md`, `runtime-and-browser.md`

Rug-check updates/addition:

- `skills/crypto-rug-check/SKILL.md`, `assets/release.json`
- `references/collector.md`, new `references/solana.md`
- `scripts/rug_check.py`, `tests/test_rug_check.py`

EVM updates (routing/documentation only):

- `skills/crypto-evm-token-due-diligence/SKILL.md`
- `references/deterministic-backend.md`, `assets/workflow-release.json`

Project documentation: `AGENTS.md`, `README.md`, `HANDOFF.md`, and this record.
Earlier uncommitted budget/quick-screen files remain in the working tree as well.

Suggested commit message: `Add Solana token diligence and chain-aware research routing`
