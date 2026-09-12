# Standard Solana runbook

This is the default schema-2 workflow. Run the installed
standard-library Python helpers. No SDK install or per-run script is required.
Commands below use repository-relative helper paths and a chosen fresh `RUN` directory;
the emitted lane context supplies absolute command arguments. Replace example values
with the exact request and mint. Never paste credentials into a command or artifact.

Before any actual provider check/collection, read this checkout's current HANDOFF.md
policy and README provider section. Source its private env with tracing disabled in
the same invocation, without displaying values. Its EVM endpoint is for Robinhood
4663; Solana uses public RPC. Existing EVM paid authorization does not select a paid
Solana provider. Custom Solana dRPC configuration is deferred. The start helper does
its zero-request public configuration preflight internally; no second provider check.

## 1. Start once with original timing

The coordinator records the actual original user request receipt time, its complete
question, focus, every supplied URL, and an absolute deadline. Ordinary target is
receipt + 420 seconds, maximum end-to-end receipt + 600 seconds. Collection cutoff
is min(receipt + 480, deadline − 120); lanes stop at min(receipt + 240, deadline − 120).
Routing delay counts. Respect a shorter explicit user deadline. A new request creates
a new run; continuation of an active request keeps the existing run.

```sh
set +x
if [ -r "$HOME/.config/crypto-research/env" ]; then
  source "$HOME/.config/crypto-research/env" >/dev/null 2>&1 || exit 2
fi
python3 skills/crypto-solana-token-due-diligence/scripts/solana_broad_collect.py start RUN \
  --mint EXACT_MINT --question 'The complete original request' \
  --received-at ORIGINAL_ISO_UTC --deadline-at ABSOLUTE_ISO_UTC \
  --focus 'Explicit requested emphasis' --url 'https://public.example/requested-source' \
  --allow-network --cost-policy free
```

Default RPC is `https://api.mainnet-beta.solana.com`; an optional `SOLANA_RPC_URL`
selects a credential-free public HTTPS root. Values stay out of artifacts. The helper
rejects authenticated/custom dRPC configuration on this path. Network permission is
still enforced by the host. A flag does not bypass a host denial.

Start performs identity/discovery, related accounts/controllers, material
pool/transaction/quote dependencies and consistency checks using one durable ledger.
It captures initial mint/epoch/top-account state, source candidates and project links,
up to two pool candidates, required account/configuration state, sampled fungible LP
holdings, and known program authority metadata where feasible. A curve PDA is only a
candidate. All eight supported adapters remain distinct; detected unsupported layouts
or missing positions/locks stay explicit. Read-only quote estimates require actual
supported dependencies. Start is automatic collection, not an analyst verdict.

Outputs: intake/work plan, actual attempts and stage resource totals, retained RPC/web
captures, `draft/facts.json`, machine note, partial `draft/report.json`, three note
scaffolds, diagnostics and two pointer prompts. A later failure retains earlier
usable evidence. Identity failure stops further on-chain expansion and cannot create
a completed report. Public source failures do not turn unknowns into adverse claims.

## 2. Dispatch the two pointers

Immediately dispatch each returned pointer to an available generic subagent before
a separate coordinator facts-reading step. Do not copy/retype the full briefs or
install personal agent definitions. Each brief includes original intake/cutoff,
known facts, captures, owner limits, exact commands and a complete checklist.

Lanes own `notes/liquidity.json` and `notes/project.json`. They can perform public
source research/capture within their existing grant, but cannot run RPC, read
credentials, write helper scripts, spawn agents, compose or finalize. New captures
are imported by coordinator `refresh`. They then self-check with:

```sh
python3 skills/crypto-solana-token-due-diligence/scripts/solana_broad_collect.py lane-check RUN --owner liquidity
python3 skills/crypto-solana-token-due-diligence/scripts/solana_broad_collect.py lane-check RUN --owner project
```

If subagents are unavailable or late, execute a feasible owned checklist locally
using those same notes/capture grants, or retain its pending items. A missing lane,
unsupported helper or expired budget cannot be converted into completed broad work.

## 3. Facts and at most two targeted presets

```sh
python3 skills/crypto-solana-token-due-diligence/scripts/solana_bundle.py facts RUN/draft --profile solana-evidence-v2
```

Use `--category holders`, `--category pools`, etc. when the omitted-detail index calls
for a specific material detail. Do not repeatedly read raw manifests, do arithmetic
by hand, or fetch again solely to produce citations.

The coordinator may create up to two small preset JSON requests; these are data,
not scripts. Each contains a stable `id` of at most 12 characters, `kind`, and
`parameters`. Supported kinds:

| Kind | Parameters |
| --- | --- |
| `pool` | `adapter`, `pool`, optional `lp_accounts` (at most six) |
| `positions` | `adapter`, `pool`, `positions` (at most six already discovered supported leads) |
| `transactions` | `signatures` (at most two) |
| `creator_history` | `keys` (at most two attributed keys), optional `before` cursors |
| `programs` | `addresses` (known program/controller dependencies, bounded batch) |
| `quote` | `adapter` = `raydium_cpmm`, exact `pool` |

Example shape: `{"id":"custody1","kind":"pool","parameters":{"adapter":
"raydium_cpmm","pool":"EXACT_POOL","lp_accounts":["EXACT_LP_ACCOUNT"]}}`.

In the same env-sourcing invocation shown at start, run:

```sh
python3 skills/crypto-solana-token-due-diligence/scripts/solana_broad_collect.py collect RUN \
  --request PRESET.json --allow-network --cost-policy free
```

Calls are sequential under the same original deadline, attempt/byte ceiling and
reserved final capacity. Identical named requests resume; changed requests cannot
replace them or receive new grants. A third distinct preset is refused. A refresh
rebuilds affected facts, marks the updated draft unjudged, and preserves editable
analyst notes/corrections for compose. Recheck changed-evidence corrections explicitly.

For one public-source batch:

```sh
python3 skills/crypto-solana-token-due-diligence/scripts/solana_broad_collect.py capture RUN --owner project \
  --url 'https://public.example/audit' --url 'https://public.example/docs' --allow-network --cost-policy free
python3 skills/crypto-solana-token-due-diligence/scripts/solana_broad_collect.py refresh RUN
```

Existing URLs retain ownership and are reused; same-owner retries follow the original
finite retry/backoff rules. A lane cites another owner's capture instead of resending.
The source cap/remaining grant is enforced by helpers, without a per-page accounting
ceremony. Unattempted sources remain visible limits. Current-run evidence only.

## 4. Compose the coordinator note

Follow [compose.md](compose.md). Assign signals to pipeline IDs, add scoped findings,
resolve cross-lane issues, and fill all eleven coverage rows, four decision axes and
literal original-request requirements. Preserve material concerns, affirmative
maturity/delivery evidence, sample counts and exact limits. Run:

```sh
python3 skills/crypto-solana-token-due-diligence/scripts/solana_bundle.py compose RUN/draft --profile solana-evidence-v2 --check
python3 skills/crypto-solana-token-due-diligence/scripts/solana_bundle.py compose RUN/draft --profile solana-evidence-v2
```

Existing lane notes are automatically included. `--check` writes nothing. Successful
compose retains immutable note snapshots; editing a note does not invalidate the
previous draft. Partial work may remain unjudged. Complete bounded research can retain
externally unavailable facts only after actual primary/alternate attempts and all
required work. Budget-only or implementation-only boundaries remain partial.

## Follow-ups and recovery

`start` repeated with identical original intake returns the existing result and
current ledger without resetting edited notes or collected evidence. If interrupted
before its result was saved, it resumes named captures in the same session. Active-run
follow-ups use `collect`, `capture`, `refresh`, facts and compose. They never reset the
clock or refill grants. Use `status RUN` for resource totals. An interrupted composition
is explicitly undeliverable; the next compose restores its last valid pair first.

For focused work, add `--scope focused --surface DIMENSION` (repeat as needed).
Only those dependencies are selected; broad lanes and final broad delivery are
omitted. State exactly what the focused answer established. A formatting/replay
request uses frozen report data and performs no new research. Final freeze/delivery
and safe replay are documented in [report-replay.md](report-replay.md).

Automatic activity sampling requests at most ten recent signatures per selected pool
and at most two distinct receipts overall. The receipt stage repeats network and
critical mint checks even for an empty candidate set. Only supported historical
swap effects with exact pool/mint/owner and balance reconciliation become sample
sales. Empty/short history is not archive coverage or proof of no selling.

## Freeze and answer (offline)

After notes and standard lane checks are complete:

```sh
python3 "$S/scripts/solana_bundle.py" compose "$RUN/draft" --profile solana-evidence-v2 --check
python3 "$S/scripts/solana_bundle.py" finalize "$RUN/draft" --profile solana-evidence-v2 --out "$RUN/final"
```

Finalize returns the readable report, complete reading checklist and source/local
citations in one response. Read them and answer the exact question, preserving all
material quantities, sample boundaries, named control/custody, economics, assurance
and focus limits. Finalize does not overwrite the active draft or an existing output.
Do not refresh/fetch solely to format an existing report.

If standard work remains incomplete, preserve the actual draft as a checkpoint:

```sh
python3 "$S/scripts/solana_bundle.py" checkpoint "$RUN/draft" --profile solana-evidence-v2 --out "$RUN/checkpoint"
python3 "$S/scripts/solana_bundle.py" read "$RUN/checkpoint" --profile solana-evidence-v2
```

The checkpoint is explicitly undeliverable as completed broad research. Describe its
actual limits. For an existing final report use `read "$RUN/final"`; for code replay
see [report-replay.md](report-replay.md). No new network grants are created.
