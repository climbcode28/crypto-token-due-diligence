# Crypto research handoff

Current operating policy, updated 2026-09-11. Read this section before provider selection;
a personal `HANDOFF.local.md` (untracked) takes precedence when present.

## Current provider policy

This repository ships no credentials, no private endpoint and no standing permission to
spend money on a paid RPC provider. The EVM skill reads this section before any RPC
attempt; it applies to whoever is running the skill from this checkout.

- Configure a JSON-RPC endpoint in `~/.config/crypto-research/env` (copy `env.example`,
  `chmod 600`). The free public Robinhood Chain mainnet endpoint works with the flags
  `--provider generic --allow-network --cost-policy free`; the collector verifies
  `eth_chainId` and pins every read to a block. Source that file with tracing disabled in
  the same shell invocation as every check and collection; never display it.
- A paid provider is used only if **you** configured it and **you** authorize it in the
  conversation. A configured key alone is never permission to spend, and nothing here
  buys, tops up or changes a plan.
- Personal, machine-local standing authorizations belong in `HANDOFF.local.md` next to
  this file. It is ignored by git, and when present its first section replaces this one
  as the policy the skill reads (`provider_context.py --policy` names its source).
- Every run is a fresh investigation in a new `research/<token>-<timestamp>/` folder;
  earlier runs are never reused as evidence. Missing or unreachable sources are recorded
  as gaps, never as passing checks.

## Project and research operation

- Canonical editable skills are the three folders under `skills/`. Codex EVM diligence
  is project-only via `.agents/skills/crypto-evm-token-due-diligence`, a symlink to its
  canonical folder; the other two skills retain Personal symlinks. Follow `AGENTS.md`
  and the README regression commands. The private env location is documented above;
  personal standing authorizations live in the untracked `HANDOFF.local.md`.
- Verified EVM tokens use EVM diligence; exact Solana mints use Solana diligence. Native
  assets remain native-asset research. Address shape, ticker and brokerage listings
  alone do not verify a deployment. Never substitute testnet for mainnet.
- Solana defaults to the public RPC/explorer/API sources and can use a personal dRPC
  endpoint when a run authorizes paid use (`--cost-policy paid --allow-paid`): the shared
  `DRPC_API_KEY` plus an optional credential-free `SOLANA_DRPC_URL` (default
  `https://lb.drpc.org/solana`). `SOLANA_RPC_URL` only overrides the public root. A key
  alone is not authorization to spend.
- Solana v2 workflow 2.0.0 is the default after functional acceptance. The 2026-09-11 review
  found and fixed the public-endpoint failure that had kept every live run partial; see
  `plans/solana-review-fixes-2026-09-11.md` for the live evidence. The Solana skill needs no
  private env for the public tier; dRPC use reads the shared `DRPC_API_KEY`/`SOLANA_DRPC_URL`
  from the documented env file. One broad start shares
  original receipt/deadline and 120-attempt/64-MiB grants across typed controls,
  supported pools/positions, two bounded lanes and at most two coordinator presets.
  Compose/finalize returns a frozen readable report/checklist/citations; partial work
  remains an undeliverable checkpoint. Direct/routed ordinary timing targets seven
  minutes and stops by ten, reserving two for delivery. Timing is a target, not a
  measured live-performance claim. See the [implementation record](plans/solana-evm-parity-2026-09-11/implementation.md)
  and [Solana runbook](skills/crypto-solana-token-due-diligence/references/runbook.md).
  The README suites include operational-feedback and guidance validation.
- Standalone broad EVM diligence runs the standard pipeline (`broad_collect.py start`,
  two brief-driven lanes, presets, `bundle_assemble.py compose`/`finalize`) and targets
  5–7 minutes end to end, 10 at most, including report validation. A completed ordinary
  review is the standard scope executed to its stopping rules; work beyond it needs a
  named conclusion-changing trigger stated before continuing. The pipeline fills the
  eleven-surface plan and reviews the session; ceilings and user/provider limits still
  control, and replanning stays inside the same ledger. A checkpoint is an internal save;
  completed reports must pass `deliver` (run by `finalize`). See the skill's runbook and
  completion-and-delivery references. Quick screens and ordinary market/Solana research
  retain their own budgets. Background reads through `web_capture.py` are the default;
  Robinhood Blockscout returned 403 to scripted requests on 2026-09-10, so RH Scan and
  Robinscan are the lane alternates.
- Missing evidence and timeouts remain unknown; every pin, source correspondence and
  broad report validation requirement remains in force. A collector packet is not a
  completed broad diligence report.
- Preserve saved collections, engine snapshots and evidence bytes. `history/` is kept only on
  the local `archive/pre-publish` branch (ignored on the published branch); do not rerun its
  historical installers. New local investigation output belongs in ignored
  `research/`, `runs/` or `cache/` directories; credentials stay outside the project.
- Never commit or push unless explicitly requested in the current conversation.

## Historical context (superseded status, not current instructions)

Initial setup notes described an absent private file, pending chain verification and
no paid-use authorization. Those were true **before** configuration, the successful
four-request collection and the standing authorization now recorded in `HANDOFF.local.md`. Later notes reported
purchased credits but still preceded that approval. They are no longer action items.
The original nine-attempt test and $0.01 proposal were not an approved spending ceiling;
current bounded-use authority comes from the quoted user instruction.

Prior records remain in [the original setup plan](plans/drpc-local-setup-and-live-test.md),
[project migration](plans/project-migration.md),
[bounded research and quick screening](plans/fast-screen-and-research-budgets.md) and
[Solana routing](plans/solana-support-and-routing.md). Their test totals and account
status describe those runs. Use this handoff's current policy rather than old starter
prompts or historical no-approval statements. Earlier tasks: `01a07528-8ea5-79e2-a248-b8dde3596d5a`
and `01a0754d-3f56-7ed0-8ff5-ee688e28d887`.

## New-chat starter

```text
Continue research in this checkout (the directory that holds this HANDOFF.md). Read AGENTS.md,
README.md and the current policy at the top of HANDOFF.md before choosing an RPC provider.
Apply the policy `provider_context.py --policy` prints (the personal HANDOFF.local.md when
present, otherwise the tracked policy); source the private env with tracing disabled in
every check/collection invocation. Keep credentials private, verify fresh identity/pins,
respect the research budget, and produce the required validated report when evidence
allows. Do not purchase, top up, change plans, commit or push. Historical setup notes
are provenance; do not repeat setup or ask again for already-granted permission.
```
