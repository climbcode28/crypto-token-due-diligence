# Standard Solana runbook

This is the default schema-2 (`solana-evidence-v2`) workflow: installed standard-library
Python helpers, no SDK install and no per-run script. `S` is this skill's directory
(resolve symlinks; `${CLAUDE_SKILL_DIR}` in Claude Code) and `RUN` is a fresh run
directory, for example `research/<mint>-<utc>`. The emitted lane context carries
absolute paths. Replace example values with the exact request and mint. Never paste
credentials into a command or artifact.

Solana uses credential-free public RPC: the default `https://api.mainnet-beta.solana.com`
or a public HTTPS root in `SOLANA_RPC_URL`. No policy file, private env, key or provider
check is involved; the helper refuses custom/dRPC endpoints and runs its zero-request
local preflight inside `start`. Host network permission is still enforced by the host;
a flag does not bypass a denial.

## 1. Start once with original timing

Record the actual original request receipt time, the complete question, focus, every
supplied URL and an absolute deadline. Ordinary target is receipt + 420 seconds,
maximum receipt + 600. Collection cutoff is min(receipt + 480, deadline − 120); lanes
stop at min(receipt + 240, deadline − 120). Routing delay counts. Respect a shorter
explicit user deadline. A new request creates a new run; continuation of an active
request keeps the existing run.

```sh
python3 "$S/scripts/solana_broad_collect.py" start "$RUN" \
  --mint EXACT_MINT --question 'The complete original request' \
  --received-at ORIGINAL_ISO_UTC --deadline-at ABSOLUTE_ISO_UTC \
  --focus 'Explicit requested emphasis' --url 'https://public.example/requested-source' \
  --allow-network --cost-policy free
```

`--mint`, `--question`, `--received-at` and `--deadline-at` are required; `--focus` and
`--url` repeat; `--genesis-hash` defaults to mainnet; `--rpc-url-env` names the public
root variable (default `SOLANA_RPC_URL`). For focused work add `--scope focused
--surface DIMENSION` (repeatable): only those dependencies are selected and the broad
lanes and final broad delivery are omitted.

Start performs identity/discovery, related accounts/controllers, material
pool/transaction/quote dependencies and consistency checks under one durable ledger:
initial mint/epoch/holder-discovery state, source candidates and project links, up to
two pool candidates, required account/configuration state, sampled LP holdings, up to
two recent pool receipts and known program authority metadata. When the public tier
refuses `getTokenLargestAccounts`, an SPL mint's holders are discovered with a bounded
account scan instead; Token-2022 holdings keep an explicit gap. The helper waits out
per-method rate windows itself. A curve PDA is only a candidate. All eight adapters
(`raydium_amm_v4`, `raydium_cpmm`, `raydium_clmm`, `orca_whirlpool`, `meteora_dlmm`,
`meteora_damm_v2`, `pump_curve`, `pumpswap`) remain distinct; unsupported layouts or
missing positions/locks stay explicit. Typical wall clock is one to two minutes.

Output: `research_status`, `facts_summary` (the compact facts), `diagnostics` (refused
methods, unsent reads, unresolved stages), `lane_pointers` and session totals. Read
`diagnostics` before judging: a refused method or an unsent read is a coverage limit,
not a token finding. A later failure retains earlier usable evidence. Identity failure
stops on-chain expansion and cannot create a completed report. Public source failures
do not turn unknowns into adverse claims. `start` repeated with identical intake
returns the existing result without new sends; `status "$RUN"` prints totals;
`brief "$RUN"` reprints the two pointers.

## 2. Dispatch the two pointers

Immediately dispatch each returned pointer to a generic subagent, before a separate
facts-reading step. Do not copy the briefs or install agent definitions. Each brief
carries the intake/cutoff, compact facts, captures, owner limits, exact commands, the
note contract with an example finding and the complete checklist.

Lanes own `notes/liquidity.json` and `notes/project.json`, which start scaffolded. They
may capture public sources within their grant, then self-check:

```sh
python3 "$S/scripts/solana_broad_collect.py" capture "$RUN" --owner liquidity \
  --url 'https://public.example/page' --allow-network --cost-policy free
python3 "$S/scripts/solana_broad_collect.py" lane-check "$RUN" --owner liquidity
```

Add `--dimension SURFACE` (one of the eleven surface names) to a capture made for one
coverage surface, for example `utility_redemption_rights` for a terms page, so that
surface records an attempt and can close as an evidenced external limit. `lane-check`
imports the lane's own new captures into the draft, validates the note and reports
whether the checklist is complete. Existing URLs keep their owner and are cited
by capture ID, never re-fetched. Lanes cannot run RPC, read credentials, write helper
scripts, spawn agents, compose or finalize. If subagents are unavailable or late,
execute the feasible owned checklist locally with the same grants, or retain pending
items. A missing lane or expired budget is never completed broad work.

## 3. Judge from facts, at most two presets

Judge from `facts_summary`. For an omitted material detail:

```sh
python3 "$S/scripts/solana_facts.py" "$RUN/draft" --check --category holders
```

Categories: `controls`, `pools`, `holders`, `quotes`, `transactions`, `programs`,
`creator`, `launch`, `maturity`, `source_assurance`. Do not open raw manifests, do
arithmetic by hand or fetch again to produce citations.

The coordinator may run at most two presets, each a small JSON file (data, not a
script) with a stable `id` of at most 12 characters, `kind` and `parameters`:

| Kind | Parameters |
| --- | --- |
| `pool` | `adapter`, `pool` (must appear in this run's exact-mint discovery or captured accounts), optional `lp_accounts` (at most six) |
| `positions` | `adapter`, `pool`, `positions` (at most six discovered supported leads) |
| `transactions` | `signatures` (at most two) |
| `pool_activity` | `pool` (captured), optional `limit` (1–25 signatures, default 10), `receipts` (0–4 sampled swap receipts, default 2) and `probes` (receipts–8 signatures classified, default 4) |
| `holders` | none: holder discovery (largest accounts or the bounded scan) plus the same-batch balance sample |
| `creator_history` | `keys` (at most two attributed keys), optional `before` cursors |
| `programs` | `addresses` (known program/controller dependencies) |
| `quote` | `adapter` = `raydium_cpmm`, exact `pool` |

Example: `{"id":"custody1","kind":"pool","parameters":{"adapter":"raydium_amm_v4","pool":"EXACT_POOL","lp_accounts":["EXACT_LP_ACCOUNT"]}}`

```sh
python3 "$S/scripts/solana_broad_collect.py" collect "$RUN" --request "$RUN/preset1.json" \
  --allow-network --cost-policy free
```

Presets run sequentially under the same deadline, attempt/byte ceiling and reserved
final capacity, and each refreshes facts (the draft becomes unjudged; analyst notes and
corrections are preserved). An identical named request resumes; a changed one is
refused; a third distinct preset is refused. Captures made outside a lane check need:

```sh
python3 "$S/scripts/solana_broad_collect.py" refresh "$RUN"
```

## 4. Compose the note and finalize

Edit the scaffolded `$RUN/draft/notes/coordinator.json` per [compose](compose.md):
signals for pipeline IDs, owned findings, conflict resolutions, eleven coverage rows,
four axes and the literal original-request requirements. Then:

```sh
python3 "$S/scripts/solana_bundle.py" finalize "$RUN/draft" --out "$RUN/final"
```

Finalize composes both lane notes and the coordinator note, preflights, freezes the
engine and evidence, validates, renders and reproduces bytes, and returns `report_path`,
`facts_path`, the compact reading checklist (verdict and axes, every finding with its
citation, the eleven coverage rows, typed-fact summaries, limits and attention rows with
`@aliases` for recurring addresses) and citations in one response. The typed-fact
detail tables with every quantity are frozen in `facts-compact.json` (`facts_path`),
keyed by evidence id as each entry's `details_ref` says. Answer from that checklist,
expanding aliases from its `addresses` table; open `facts_path` in the same turn only
for a quantity that no finding states, and `report_path` only for a disputed detail.
It lists every error at once;
repair the note and rerun. `compose --check` only validates a note without writing:

```sh
python3 "$S/scripts/solana_bundle.py" compose "$RUN/draft" --check
```

Finalize never overwrites the active draft or an existing output. Do not refresh or
fetch solely to format an existing report. Answer from the returned report per the
skill's Deliver section.

## Follow-ups, checkpoints and recovery

Active-run follow-ups use `collect`, `capture`, `refresh`, facts and finalize; they never
reset the clock or refill grants. If interrupted before a result was saved, `start`
resumes named captures in the same session. If standard work remains incomplete at
cutoff, preserve the actual draft:

```sh
python3 "$S/scripts/solana_bundle.py" checkpoint "$RUN/draft" --out "$RUN/checkpoint"
python3 "$S/scripts/solana_bundle.py" read "$RUN/checkpoint"
```

A checkpoint composes the coordinator and lane notes when they validate (its
`note_status` says so; an invalid note leaves the last composed draft in place) and is
explicitly undeliverable as completed broad research; describe its limits. `read "$RUN/final"` rereads a final report; code replay is in
[report-replay](report-replay.md). Old schema-1 bundles are validated with
`validate --profile legacy-v1`; they keep their original rendering.

Automatic activity sampling requests at most ten recent signatures per selected pool,
probes at most four of them and samples at most two receipts overall; `pool_activity`
classifies its probes the same way (skipping signatures already sampled or probed) and
can add up to four more receipts. Only
supported historical swap effects with exact pool/mint/owner and balance reconciliation
become sample sales. Empty/short history is not archive coverage or proof of no selling.
