---
name: crypto-solana-token-due-diligence
description: Evidence-bounded diligence on an exact Solana token mint, including SPL and Token-2022 controls, liquidity custody, exits, launch, supply, treasury and holder rights. Use for focused token questions or broad diligence, including research routed from crypto-token-due-diligence; not native SOL price research or a full program exploit audit.
---

# Crypto Solana token due diligence

Answer the original decision question for one exact `(genesis hash, mint public key)`.
Keep addresses case sensitive. A mint, token account, wallet, pool, program and
transaction signature are distinct identities. Format alone never verifies a mint.

## Select the existing work and clock

1. **Fresh broad request:** read the [runbook](references/runbook.md), preserve the
   complete question/focus/URLs, resolve candidate identity and run standard start.
   V2 is the default; explicit `--profile solana-evidence-v2` examples remain valid.
   Use `--profile legacy-v1` for old bundles. Live rich-case parity remains unmet;
   public rate limits or unsupported state must remain explicit gaps.
2. **Active follow-up:** retain the investigation ID, original intake/deadline,
   evidence and consumed grants. Use only an applicable remaining preset. A follow-up,
   restart or fallback does not create a new ordinary budget.
3. **Focused request:** select relevant surfaces/dependencies at start, omit the
   research lanes, answer only that question and disclose limits. It cannot become
   completed broad research without executing the missing standard scope.
4. **Formatting/readback:** read an existing frozen bundle/checklist. Make zero new
   network requests. Use [trusted replay](references/report-replay.md) only when
   reproducing code behavior is requested and the frozen code is explicitly trusted.

Direct and routed ordinary work use the same original clock: target receipt +420
seconds, maximum receipt +600 seconds; honor shorter user deadlines. Preserve a
router's `received_at`, `target_at`, `deadline_at`, complete question, focus and URLs.
Stop collection at min(receipt +480, deadline −120), reserving two minutes for notes,
validation and delivery. Lanes stop at min(receipt +240, deadline −120). Delayed
routing/spawn/retries and helper/model latency consume this same wall-clock budget.

One session permits at most 120 actual sends and 64 MiB response bytes, RPC concurrency
three and public-web concurrency two per origin. Lanes each have fifteen reserved
attempts; final checks and contingency remain reserved. Redirects, retries, failures
and interrupted attempts count. Use the existing ledger; never refill by starting a
new process/session. The configured ceiling is not permission for paid services.

At cutoff preserve a partial/blocked checkpoint with actual facts and missing work.
Timeouts, missing evidence, unsupported decoding and budget exhaustion never become
passing checks or completed standard work. Seek at most one feasible source alternate
for a blocked fact within the existing budget. Do not retry until results look favorable.

## Resolve target and provider context

- Establish the expected network/mint from primary project/chain sources. If multiple
  plausible deployments remain, retain ambiguity and obtain the missing identity.
  Never select by ticker, suffix, scanner score, popularity or exchange listing.
- Verify the actual mint owner program/layout and `getGenesisHash`, independent of
  the endpoint label. Never silently substitute devnet/testnet for mainnet.
- Native SOL has no token mint. WSOL, liquid-staking tokens and bridged assets have
  different controls/dependencies. Native SOL price research stays outside this skill.
- Verified EVM targets use [EVM diligence](../crypto-evm-token-due-diligence/SKILL.md).
  The router only classifies candidate format; this specialist verifies identity.

Before the first provider check or RPC attempt, read applicable project guidance and
current provider policy. In this repository, read the top of `HANDOFF.md` and README
provider setup; source its documented private env with tracing disabled in the same
shell invocation where required. Never display credentials. The configured EVM dRPC
endpoint/authorization does not extend to Solana or another network.

Solana standard start uses credential-free public HTTPS RPC (`SOLANA_RPC_URL`, default
Solana mainnet public endpoint) and captured public web/API evidence. Custom Solana
dRPC setup is deferred. No key, payment, connection purchase or persistent endpoint
configuration is required. The transport/session are Solana-local standard-library
code with no EVM runtime dependency. Public preflight is local and makes zero requests;
start includes it, so do not add a second ceremonial provider check.

Respect public rate limits, preserve refusals and follow remaining authorized public
routes. A configuration failure is not a token finding. A successful preflight is not
a live endpoint test, identity verification or completed diligence. No wallet
connections, keys, signing, transaction broadcasts, test trades or service purchases.
Use background reads or hidden in-app browsing, not personal Chrome tabs/groups.

## Execute the standard workflow

Use only maintained commands in the runbook. Do not read helper source, write per-run
Python/assembly scripts, repeatedly inspect raw manifests or perform analyst arithmetic.
Use compact facts and named presets; raw evidence remains available for material disputes.

1. **Start:** one `solana_broad_collect.py start` creates the intake/work plan and
   shared session; verifies identity; collects discovery, related controls and material
   pool/transaction/quote dependencies; repeats consistency checks; builds facts,
   pipeline notes and an honest draft; returns two pointer briefs and diagnostics.
2. **Lanes:** dispatch two available generic subagents using the returned pointer
   prompts before a separate coordinator facts-reading step. Do not retype the briefs
   or create persistent personal agent definitions. Liquidity and project agents own
   only their files, grants, checklists and cutoff. They cannot run RPC, source
   credentials, create scripts, spawn agents, compose or change another owner's data.
3. **Facts/presets:** read the compact facts. Exact holder aggregates, pool reserves,
   position principal, custody controls and execution reconciliation are computed from
   typed evidence. The coordinator may execute at most two sequential named presets
   against the same draft/session. Refresh after new lane captures, then self-check
   notes. Reuse registered source captures; never overwrite another lane's evidence.
4. **Compose/scaffold:** analysts write judgment once in small owned notes. Pipeline
   findings have stable IDs and no selected signal. Assign signals without retyping
   facts; corrections need reason, current evidence and digests. Review contrary
   evidence and cross-lane conflicts. `compose --check` returns all current errors
   without changing the draft. A scaffold's TODOs never count as finished judgments.
5. **Finalize:** after all standard work is closed, finalize to a new directory.
   This composes, preflights, snapshots the entire engine/evidence, validates, renders
   and reproduces bytes before delivery. Failures preserve the previous draft/output.
6. **Answer:** read the returned report/checklist/citations in that same response.
   Lead with the conditional answer, material facts, strongest contrary evidence and
   unresolved limits. Keep the exact request and all material quantities/units,
   control/custody, economics, assurance and sample boundaries in the answer.

If a lane is absent/late, execute its feasible minimum checklist locally within the
same cutoff or retain explicit incomplete work. Do not mark a lane completed just
because it returned a note. Ordinary broad research requires both checked lane results
and all eleven [surfaces](references/surfaces.md), not a favorable-rating count.

## Evidence and claim boundaries

Retain raw requests/responses, errors, bytes, exact integer units, actual context slots,
commitment, UTC capture times and matching independent header/network checks. Each
separate RPC response has its own state. `minContextSlot` is a lower bound, not a query
for exact historical state. Atomic arithmetic requires the same actual response bank.
Finalized/header consistency does not prove RPC honesty or an account state-root proof.

Historical execution needs its own signature, slot/header, success, instruction roles
and account deltas. A fee payer, signer, source owner, seller and human are different
claims. A quote is an estimate/source quote; a receipt proves a bounded historical
flow. Rent, WSOL refunds, network fees, gross proceeds and profit are distinct amounts.

Keep SPL and Token-2022 layouts separate. Inventory all extensions and their authority
paths. Unknown TLV/layout/loader data retains observed base fields and explicit gaps;
it is never absence. Confidential balances stay unknown. Raw amounts never silently
use interest/scaled UI presentation. Validate every actual pool product/version,
vault mint/authority and position/custody path before drawing conclusions.

A PDA proves a seed relationship, not safety. Revoked mint/freeze authorities,
immutable metadata, a quote, burned LP labels or explorer verification cannot close
all token/program/controller risks. Inspect known upgrades, delegates, multisig
bypasses, spending limits, fee rights and withdrawals separately. Source publication,
third-party hash statements, deployed byte correspondence and independent reproducible
builds are distinct assurance levels.

Capture dated project claims, delivered work, actual audit scope and unresolved
findings, token-linked rights/economics, creator continuity and contrary evidence.
Keep launch allocations, transfers, sales, fees, withdrawals and rebuys separate.
A short history page is not archive coverage. Shared funders/deposits are not human
identity or personal cash-out. Indexer metrics are scoped context, not organic-use,
fraud, universal rank or future-return proof. Privilege or a price decline alone does
not establish malicious intent.

## Triggered references and maintenance

- Start/capture/presets/notes: [runbook](references/runbook.md),
  [compose](references/compose.md), [evidence tools](references/evidence-and-tools.md).
- Controls/source: [authorities](references/programs-and-authorities.md),
  [correspondence](references/source-correspondence.md).
- Pools/positions: [liquidity](references/liquidity-and-custody.md),
  [platforms](references/platforms.md), [quotes](references/exits-and-quotes.md).
- Transactions/creators: [proceeds](references/transactions-and-proceeds.md),
  [launch](references/launch-and-creator.md).
- Public claims/maturity: [project credibility](references/project-credibility.md),
  [adoption](references/adoption-and-assessment.md).
- Final judgments: [strict profile](references/strict-report-profile.md),
  [decision](references/decision-review.md), [completion](references/completion-and-delivery.md),
  [output](references/evidence-and-output.md), [scenarios](references/reporting-scenarios.md).

Validation proves internal consistency and evidence relationships, not economic truth,
complete knowledge or token safety. A valid partial report remains partial. Four
independent conclusions cover technical exposure, credibility/maturity, token economics
and research confidence. Never average away a critical finding or turn all gaps into
an affirmative verdict. Do not assign unfinished standard research as user homework.

Keep installed helpers and frozen evidence immutable during investigations. Bounded
operational feedback is nonblocking and stores no token facts or instructions.
[Memory](memories.md) defaults to no active lessons; separate reviewed maintenance
requires demonstrated recovery, applicability, version and expiry. See the
[improvement loop](references/improvement-loop.md) for tests, provenance and promotion.
