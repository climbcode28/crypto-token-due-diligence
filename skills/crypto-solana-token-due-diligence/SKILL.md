---
name: crypto-solana-token-due-diligence
description: Evidence-bounded diligence on an exact Solana token mint, covering SPL and Token-2022 controls, pool and position custody on Raydium, Orca, Meteora and pump.fun/PumpSwap, exits, launch history, supply, treasury and holder rights. Use for focused questions, broad diligence or readback of a frozen report on an exact Solana mint, including research routed from crypto-token-due-diligence; not for EVM 0x addresses, native SOL price, trading or a full program exploit audit.
---

# Crypto Solana token due diligence

Answer the original decision question for one exact `(genesis hash, mint public key)`.
Keep addresses case sensitive. A mint, token account, wallet, pool, program and
transaction signature are distinct identities. Format alone never verifies a mint.

## Select the existing work and clock

1. **Fresh broad request:** read the [runbook](references/runbook.md), preserve the
   complete question/focus/URLs, resolve candidate identity and run standard start.
   V2 (`solana-evidence-v2`) is the default; `--profile legacy-v1` validates old bundles
   through their frozen contract. Public rate limits, refused methods or unsupported state stay explicit gaps.
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
validation and delivery. Lanes stop at min(receipt +300, deadline −120). Delayed
routing/spawn/retries and helper/model latency consume this same wall-clock budget.

One session permits at most 120 actual sends (160 on a keyed dRPC run) and 64 MiB, RPC concurrency
three and public-web concurrency two per origin. Lanes each have fifteen reserved
attempts; final checks and contingency remain reserved. Redirects, retries, failures
and interrupted attempts count. Use the existing ledger; never refill by starting a
new process/session. The configured ceiling is not permission for paid services.

At cutoff preserve a partial/blocked checkpoint with actual facts and missing work.
Timeouts, missing evidence, unsupported decoding and budget exhaustion never become
passing checks or completed standard work. Seek at most one feasible source alternate
for a blocked fact within the existing budget; a read that failed is never repeated in
the hope of a different answer.

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

Solana defaults to credential-free public mainnet RPC or `SOLANA_RPC_URL`; no key is needed.
Optional dRPC uses shared `DRPC_API_KEY` and credential-free `SOLANA_DRPC_URL` (default
`https://lb.drpc.org/solana`); source `"$HOME/.config/crypto-research/env"` with tracing disabled
in the same keyed collection invocation, never print it, and send the key only in `Drpc-Key`.
`--provider auto` uses dRPC only with a key and authorized `--cost-policy paid --allow-paid`;
`drpc` requires both. `public` ignores unused dRPC settings and sends no key. `provider.json`
locks later collections to the same provider/flags; read start's `diagnostics` per the runbook.
Paid use needs current-user authorization; reuse applicable standing consent within bounds.
Without it use public RPC directly, without a paid-use question. Per-command flags do not mean
repeat consent. Host rejection uses [denial recovery](references/runbook.md#provider-authorization-and-denial-recovery).

Respect public rate limits, preserve refusals and follow remaining authorized public
routes. A configuration failure is not a token finding. A successful preflight is not
a live endpoint test, identity verification or completed diligence. No wallet
connections, keys, signing, transaction broadcasts, test trades or service purchases.
Use background reads or hidden in-app browsing, not personal Chrome tabs/groups.

## Execute the standard workflow

`S` is this skill's directory (resolve symlinks; `${CLAUDE_SKILL_DIR}` in Claude Code);
`RUN` is a fresh `research/<mint>-<utc>` directory, never an earlier run. Use only
maintained runbook commands: no helper-source reading, per-run scripts, raw manifests or
analyst arithmetic. Use compact facts and named presets; raw evidence is for disputes.

1. **Start:** one `solana_broad_collect.py start` with the original `--received-at`
   and `--deadline-at` creates the intake, work plan and shared session; verifies
   identity; collects discovery, related controls and material pool/transaction/quote
   dependencies with consistency rechecks; builds facts, pipeline findings, an honest
   draft and three note scaffolds; prints a compact facts summary, `diagnostics` and
   two pointer prompts. Typical wall clock is one to two minutes. Collection commands
   need outbound network; in a sandboxed host request it for the exact command first
   (Codex: escalated permissions). A `blocked` start (`network_unavailable` or
   `identity_unavailable`) writes no lane pointers: follow its `next` action, retain its
   ledger/provider lock, and create no new run or budget. Never dispatch lanes from it.
2. **Lanes:** dispatch two general-purpose subagents (the default subagent type) with the two printed pointer prompts,
   verbatim, in the same turn that `start` returns and before reading facts yourself;
   the lane cutoff is receipt + 300 s whenever they are dispatched, so every minute
   spent first is taken from them. Do not retype the briefs or create persistent
   agent definitions. Liquidity and project agents own only their notes,
   grants, checklists and cutoff. They cannot run RPC, source credentials, create
   scripts, spawn agents, compose or change another owner's data.
3. **Facts/presets:** judge from the printed summary; run `solana_facts.py --category`
   only for an omitted material detail. Exact holder aggregates, pool reserves,
   position principal, custody controls and execution reconciliation are computed
   from typed evidence. Run the printed `recommended_presets` in order (request files
   under `$RUN/recommended-presets/`; up to four presets per run) while the cutoff and
   grant allow; add a preset only for a hash or address the user or a lane named, never a
   bare `pool` re-read. Lane self-checks import own captures; `refresh` only after outside captures.
4. **Note:** edit the scaffolded `$RUN/draft/notes/coordinator.json`: assign a signal
   to each pipeline finding, add your own findings for adverse concerns and lane
   conclusions, replace every `TODO`, resolve cross-lane conflicts, fill the eleven
   coverage rows, four axes and the literal original-request requirements
   ([compose](references/compose.md)). Cite the alias keys the scaffold lists, never
   the `fact-` display prefix. Assignments are pre-filled with fact digests: set only
   the signal. Corrections need reason, current evidence and digests.
5. **Finalize:** `solana_bundle.py finalize` composes, preflights, freezes, validates,
   renders and reproduces bytes in one step, listing every error at once; the error
   text is the specification. `compose --check` is the repair tool for a rejected note,
   not a routine step. Unfinished standard work goes to `checkpoint`, never delivery.
6. **Answer:** read the returned compact checklist and citations in that same response
   and write the chat answer below from them; open `facts_path` in the same turn only
   for a quantity no finding states, and `report_path` only for a disputed detail. No
   new fetch or extra turn for formatting.

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
fraud, universal rank or future-return proof; a RugCheck cluster claim is corroboration rated by the [rating rules](references/reporting-scenarios.md#rating-rules), its locker claims are leads. Privilege or a price decline alone does
not establish malicious intent.

## Deliver

Lead with a direct conditional verdict; when the user asked something beyond the mint,
answer it in the verdict or its own finding, labeled by evidence strength. Then 4–8
evidence-linked findings labeled **✅ Good / 🟡 Potential Risk / 🔴 Bad** (report signals
`good`, `potential_risk`, `bad`) across token and liquidity, adoption and maturity,
token economics, real work vs marketing, creator trading and proceeds, prior launches
and identity; group pure gaps (`unverified`) separately as **⚪ Unverified**. Good
needs affirmative evidence; Potential Risk needs an observed concern or adverse
inference; Bad needs a supported material adverse condition; Unverified is missing
research or an informational note, never a pass or an allegation; state its `gap_basis`; apply the [rating rules](references/reporting-scenarios.md#rating-rules). Use short bullets with **signal icon + label —
descriptive finding title**, selective bolding of key numbers, and an adjacent native
Markdown source link on **every finding**: the report's own citation or `answer_link`,
otherwise the absolute frozen report path as Evidence report. No emoji on source links,
no icon fetches, no extra calls or turns for presentation.

Keep exact quantities and units (showing an atomic figure also in decimal display is
presentation, not analyst arithmetic; keep the atomic figure), spending owner versus beneficial owner, sample
account/receipt counts, custody exclusions, LP principal versus fees, named
controllers and bypass paths, quote versus execution, economics/rights, assurance
levels and the original focus. Describe receipt counts as the verification sample,
never total market activity; lead with evidenced broad activity and its source.
Untested larger-trade price impact is a research limit, not evidence of selling
difficulty. Use computed holder totals, never mental addition.

Then a **Conclusions** block of exactly four bullets, one or two sentences each, never
merged: **Technical exposure**, **Credibility and maturity**, **Token economics**,
**Research confidence**. Market leadership never erases dangerous authority or replaces
custody and exit evidence; missing access limits confidence rather than adding risk.
Keep chat to 300–600 words, written from the frozen report, never a stronger
recommendation than the report's decision review, and no homework list. Full rules:
[output](references/evidence-and-output.md), [decision](references/decision-review.md).

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
  [completion](references/completion-and-delivery.md),
  [scenarios](references/reporting-scenarios.md).

Validation proves internal consistency and evidence relationships, not economic truth,
complete knowledge or token safety. A valid partial report remains partial. Never
average away a critical finding or turn all gaps into an affirmative verdict. Do not
assign unfinished standard research as user homework.

Keep installed helpers and frozen evidence immutable during investigations. Bounded
operational feedback is nonblocking and stores no token facts or instructions.
[Memory](memories.md) defaults to no active lessons; separate reviewed maintenance
requires demonstrated recovery, applicability, version and expiry. See the
[improvement loop](references/improvement-loop.md) for tests, provenance and promotion.
