# Broad diligence runbook (workflow 3.3.0)

The ordered command sequence for an ordinary broad review. Target **5–7 minutes**, cap
**10 minutes**, and **at most about 40 coordinator turns**: every turn costs 6–8 seconds of
model time whatever it does, so the run is fast when each step below is one turn. Every step
is one shell call (chain related helper commands with `;` inside it); the judgment lives in
the notes you write, not in scripts you author. `SKILL_DIR` is this skill's directory; `RUN`
is a new dated directory under the project's ignored `research/` folder.

| Step | Minute | One turn each | What you get |
| --- | --- | --- | --- |
| 0 | 0:00 | Read the provider policy excerpt (injected at load in Claude Code; `python3 "$SKILL_DIR/scripts/provider_context.py" --policy` in Codex). | Which RPC to use and with which flags. |
| 1 | 0:10 | `broad_collect.py start` (below). It runs discovery (Dexscreener, Sourcify, explorer creation/holders/transfers/counters), four pinned phases, the source match, the launch signer's explorer activity, writes `facts.json`, composes the **pipeline note** (its own factual findings), pre-charges both lanes, writes both briefs and prints two spawn prompts. | The whole standard collection and the factual half of the report in one process, usually 20–90 s. |
| 2 | 0:30–1:30 | Spawn **both** lanes in **one** message with the two printed one-line prompts (`Read the file …/lanes/<lane>/brief.md and follow it exactly …`). Do not paste or retype the brief and do not read the facts first; every minute the lanes start late is a minute added to the run. | Two lanes working from a self-contained brief; they self-validate their notes with `compose --check` before returning. |
| 3 | 1:30–3:30 | Read the printed summary (or `bundle_assemble.py facts "$RUN/draft"`). Decide the presets (up to four while at least 150 s remain before the deadline, custody first) and run them **in one shell call, sequentially** (they share the run's session and draft files; parallel processes would race). If the creation transaction is unknown and a lane reports it, the first preset is `receipts --tx`, the second `positions --ids` from that receipt. | Decoded controls, pools, quotes, balances, positions, receipts, actors with evidence aliases. |
| 4 | 4:00–4:30 | Lane notes land in `$RUN/notes/`. Compose **both** in one shell call, sequentially (joined with `;`, never as parallel tool calls: the notes share one draft file): `bundle_assemble.py compose "$RUN/draft" "$RUN/notes/liquidity.json" --lane liquidity` and the same for project. If a lane is absent at 4:30, run its minimum checklist yourself in one `web_capture.py --out "$RUN/lanes/<lane>"` batch, write `$RUN/notes/<lane>.json` with `"lane": "<lane>"` and compose it `--lane <lane>`. | Findings, coverage and scope merged; capture files registered as evidence. |
| 5 | 4:30–6:00 | `bundle_assemble.py scaffold "$RUN/draft"` writes `$RUN/notes/coordinator.json` with scope entries, a `signals` skeleton for every pipeline finding, all eleven coverage keys (lane results prefilled), the decision and text skeleton, alias hints and `TODO` markers. Edit it: give each pipeline finding its topic and signal, add your own findings (adverse concerns, lane conclusions), replace every `TODO`. Then `bundle_assemble.py finalize "$RUN/draft" --out "$RUN/report" --note "$RUN/notes/coordinator.json"`. | Compose → check → freeze → deliver in one process, or every note-level error at once. |
| 6 | 6:00–7:00 | Fix note errors once if needed (the error text names the field and the allowed values; it is the specification, never read `compose.py`); write the chat answer from `report.md`. `finalize` marks `composed` and `delivered` for you. | Completed report and a 300–600-word answer. |

## Network execution context

Before the first network-bearing shell call, read the host's declared network and
approval policy from the current tool/environment instructions. `--allow-network` and
`--allow-paid` authorize the collector's own gates; they do not grant shell network access.
When the host declares network access restricted and offers per-command escalation,
request that permission on the **first** authorized collector or `web_capture.py` call.
With Codex `exec_command`, use `sandbox_permissions: "require_escalated"` and a concise
justification for bounded read-only research. Keep the private-env sourcing prefix,
provider flags, exact command, run directory and finite session budget intact.

Apply this to `start`, subsequent presets and each lane's web captures; a successful
escalated call does not change the default permission on later calls. Offline policy,
availability, facts, compose and validation calls need no network escalation. If the
host already allows the necessary network access, use its normal execution mode.
Honor the stated scope of a denial; do not switch tools or providers to perform the
denied action or change global sandbox/approval settings. Apply the recovery rule below
before treating a provider-specific denial as a stop for the whole investigation.

Do not spend a request demonstrating a restriction already declared by the host. If a
restricted invocation was accidentally used, correct the permission on the bounded retry
before applying the helper's generic transport-retry instruction. A DNS failure alone
does not diagnose a sandbox block: with network permission already available, retain the
normal bounded transport retry and provider-fallback rules. No first-call success guarantee
is implied; provider outages, rate limits and real DNS problems remain possible.

### Provider authorization and denial recovery

Read `provider_context.py --policy` in its own tool output before choosing a provider;
do not append it to a large reference dump where truncation can hide the policy.
Honor applicable standing authorization unless the current user restricts it. The
locator reports policy text, not a host approval token: a configured key, a file's
assertion, and `--allow-paid` cannot compel the host to accept paid execution.

If a host rejects the call, retain its actual reason and distinguish these cases:

- **Omitted collector flags:** `invocation_required` is an offline invocation issue.
  Apply already-established authorization; it does not justify asking for it again.
- **Paid-use authorization rejected:** if relevant authorization is already in the
  current user instructions, cite that instruction and the operation's finite request
  ceiling and deadline in one review retry. A stated request cap must bound both
  `--max-requests` and `--request-ceiling`; an allowance of 300 with a ceiling of 400
  is not a 300-request cap. Likewise, both timeout values must fit the original deadline.
  Do not repeatedly rephrase the same saved
  claim as new consent. If the host still rejects paid use, leave that route blocked.
  When the rejection permits safer alternatives and only paid use is denied, continue
  independently authorized credential-free public RPC and public-document research.
  Submit the public command through the host's required network review too; do not run
  it through another tool to evade review. Briefly state the provider change and reason.
- **General network/research denial, or unclear scope:** do not infer that a public
  provider is permitted. Complete unaffected offline work and report the exact boundary.

For a permitted public alternative, replace the provider arguments with
`--provider public --allow-network --cost-policy free`, without `--allow-paid` or
`--auth-env`. This selects the [built-in endpoint](public-rpc.md) for the exact target
chain, ignoring saved endpoint/key exports. Other chains require a credential-free
endpoint from official network documentation, selected via a dedicated `PUBLIC_RPC_URL`
export and `--rpc-url-env PUBLIC_RPC_URL --provider generic --allow-network --cost-policy free`.
Apply the same selection to subsequent presets. Merely changing `--provider` to `generic` while
leaving the configured dRPC URL selected is still dRPC and still requires paid approval.
Do not forward the dRPC key to the public endpoint or modify the saved private env.

Preserve the target, original deadline, run directory, and any existing session ledger
and attempts across recovery. A host rejection before process creation is not an RPC
attempt or a collector `start_failed` result. If the collector did execute, use only its
supported recovery path; never erase output or reset budgets to force another start.
Continue the standard pipeline when access succeeds; verify live identity and pins.
Public access is not guaranteed and documentary listings alone never verify identity.

Do useful permitted work before requesting user action. Do not turn optional paid
access into a prerequisite for all diligence. If required work still needs rejected
access, explain the host rejection and ask only for the missing authorization under the
host's instructions. A repository edit cannot guarantee acceptance of saved consent.

## Step 1 in full

For a first-time user without configured, authorized dRPC, use public RPC directly;
no private env file, API key or paid-use question is needed. For an already configured,
authorized provider, use the variant below instead so its preference is preserved.

```sh
set +x
SKILL_DIR=…            # this skill's directory
RUN=research/<token>-$(date -u +%Y%m%dT%H%M%SZ)
python3 "$SKILL_DIR/scripts/broad_collect.py" start \
  --chain-id 4663 --address 0x… --run "$RUN" \
  --question 'General diligence on the exact token; no special acceptance requirements' \
  --provider public --allow-network --cost-policy free \
  --max-requests 300 --timeout 600 --request-ceiling 400 --timeout-ceiling 1500
```

**Configured provider variant:** with already-established paid dRPC authorization,
source `"$HOME/.config/crypto-research/env"` with tracing disabled and suppressed output
in the **same shell invocation** before `start` (stop that invocation if sourcing fails).
Replace the public arguments with `--provider drpc --allow-network --cost-policy paid
--allow-paid`. Use these flags on every later collection, reusing existing consent
within its bounds rather than asking again. For a configured free endpoint, use
`--provider generic --allow-network --cost-policy free` and its URL export.

The generic adapter also selects the built-in public default when no endpoint is
configured. It preserves configuration errors and paid-use gates when an endpoint is
configured; `public` deliberately selects the credential-free built-in endpoint.

For a routed request, retain its absolute `deadline_at` (Unix seconds). In the same
launch shell call, compute the remaining duration immediately before
`start` and replace **both** timeout values above; do not change provider flags or
request caps. This adds no network call or separate timing tool turn:

```sh
# ROUTED_DEADLINE is the already-recorded numeric handoff deadline, not a new clock.
REMAINING_SECONDS=$(python3 - "$ROUTED_DEADLINE" <<'CLOCK'
import math, sys, time
remaining = float(sys.argv[1]) - time.time()
if not math.isfinite(remaining) or remaining < 1:
    raise SystemExit(2)
print(math.floor(remaining))
CLOCK
) || exit 2
# start ... --timeout "$REMAINING_SECONDS" --timeout-ceiling "$REMAINING_SECONDS"
```

The user's shorter deadline controls; never reset it on retries. These are scheduling
limits, not a hard watchdog on model/tool execution. If it has elapsed, follow the
completion/checkpoint policy rather than starting collection. Existing absolute target
and deadline still govern composition and delivery after collection.

Only when the user asked for more than the address, add their words and links:

```sh
  --focus 'dig into the lore behind this coin and whether it is true or AI slop' \
  --url 'https://x.com/<account>/status/<id>'
```

`--question` carries the user's whole request. `--focus` is any ask beyond the address, in the
user's words; `--url` (repeatable, at most six) is each link they gave; omit both otherwise. Both are stored in `intake.json` and rendered into both lane briefs as **What the user
asked**: the project lane captures every user link first, the liquidity lane those about
pools, holders or trades, and each ask must end as a finding (inference for documentary
judgements) or a coverage attempt. The scaffold echoes `user_focus` so the verdict answers it.

Run it in the background when the host supports it, or in the foreground: it finishes in
about 15–90 s. It creates `$RUN/notes/`, `$RUN/lanes/liquidity/` and `$RUN/lanes/project/`,
charges 20 web requests to each lane, writes `$RUN/lanes/<lane>/brief.md`, and ends its
output with two `… lane -> Read the file … brief.md …` prompts. Those prompts are step 2,
verbatim. (`--no-lanes` skips the charges and briefs for a focused question;
`broad_collect.py brief --run "$RUN" --lane <lane>` rewrites and prints a brief if you need it.)

Use the provider flags the trusted policy authorizes (for a free verified endpoint:
`--provider generic --allow-network --cost-policy free`). Add `--pools 0x…` for a pool the
user named, `--holders label=0x…` for balances the user asked about, `--explorer none` to
skip explorer JSON, `--quote-sizes 100,10000,100000` to change the illustrative exits.

**Exit codes.** 3: the provider route is not ready (read the printed route; nothing was
created). 2 with a `{"status": "start_failed", …}` line: read `category`, `message` and
`next_step`. `dns_resolution`, `timeout`, `throttled`, `transport_error`, `server_error`,
`access_denied` mean the endpoint was not reached or refused: **re-run the identical start
command once, same `RUN`** (the directory accepts a restart because no block was pinned; the
failed artifacts are kept under `failed-attempt-1/`, while the same session retains all
attempts, limits and deadlines). Apply the Network execution context rule before this retry;
a declared restriction with omitted execution permission calls for a permission request,
not a second restricted call. `network_unavailable` means nothing answered at all: every web
discovery host that was captured and the RPC chain check failed before any response
(`transport_category` and `discovery` record the exact categories), which is the host denying
outbound network to this command; request network permission for the start command itself,
then re-run the identical command once, same `RUN`. A DNS failure on the RPC endpoint alone
does not prove a sandbox denial. Only `chain_mismatch` means the URL serves another chain; fix
the URL in the private env. Never debug by trying other environment-variable names, curling
the endpoint or reading helper source: the pipeline already retried transient failures once
and the diagnostic is exact.
Exit 2 after `facts.json` exists means a later phase was partial; continue.

What the pipeline reads, all at one pinned block (three blocks behind the reported head, so a
load-balanced public endpoint whose backends lag a block still answers; "unsupported block
number" replies are retried as node lag) with a fresh recheck: runtime, name/symbol/
decimals/totalSupply, `owner`/`paused`, three EIP-1967 slots, every zero-argument view
getter from the verified ABI (capped) plus common launch/control getters; for each indexed
pool (top six by liquidity) the v2/v3/v4 state and the token's balance; balances of the dead
address, pools, creator and every contract surfaced by getters; code, owner and
implementation slot for each of those contracts and for the quote assets; the creation
receipt at its own historical pin when the explorer exposes it; QuoterV2 quotes at three
sizes on the canonical v3 pool; NFPM position owner/approval/liquidity for positions minted
in the creation transaction; Safe owners/threshold for contract owners; code for every
actor named by receipts and positions. Sourcify source correspondence runs when sources
are published. A probe getter that **reverts** (`owner()` on a pool, `getOwners()` on a
non-Safe) is the chain's answer, recorded as `reverted` in `facts.json`
(`architecture[].reverted`, `owners[].reverted`, `controls.reverted_getters`) and printed as
`owner=reverted (owner unresolved)`; the revert itself is observed, but function existence and guarded behavior remain unresolved; it is never
retried. Transport or RPC failures are listed separately (`controls.failed_getters`,
operational feedback) and are gaps.

## What the pipeline now establishes on its own

The existing report renderer places native Markdown source citations beside summary findings.
Reuse them in step 6: every chat finding gets a supporting source link or the absolute
frozen report link. Let the client show company/product icons when supported; do not
add emoji to source labels. No additional fetch, helper call or agent turn
is permitted for link/icon formatting; the sequence and 5–7-minute target are unchanged.

Holder totals are computed from unique atomic balances in `holder_summary`, including
code-bearing accounts, with missing reads and sample exclusions explicit. Preserve the
computed aggregate and largest shares in the report and chat; do not mentally sum rounded
shares or call the selected sample a global top ten. The existing finalize response's
`reading_checklist` keeps non-summary findings and gaps visible during the usual report
read. Neither change adds a call, research lane, preset or agent turn.

When the explorer answers (Blockscout's API does, to the fetcher's browser-like agent), the
pipeline reads and decodes without any coordinator turn: the creation receipt at its own pin
(mint, pool seed, initial buy, position NFTs), the launch position's owner and its owner's
Safe signers and threshold, counter-asset reserves per pool, QuoterV2 quotes, the ten largest
indexed holders' balances with a code check each, up to two **receipt-verified sales** by
indexed wallet candidates (same-pool Swap direction and input amount matched to the token transfer), the launch signer's
transactions and token transfers, indexed holder and transfer counts, and the token's age. It
writes these as `notes/pipeline.json` (lane `pipeline`) and composes them: eight to ten
`strongly_supported` findings with no signal. **The coordinator's job is judgement**: in the
scaffold's `signals` block give each pipeline finding a topic and `Good` or `Potential Risk`
(or delete the entry), then add findings that only judgement produces: adverse concerns with
`concern {basis, mechanism, consequence}`, the lanes' documentary conclusions, and gaps that
remain after the automatic routes. `Unverified` is reserved for what the pipeline, both lanes
and any preset could not establish. Preserve supported observations alongside specific gaps; partial observations do not complete a surface.

**Report standard.** A completed ordinary review screens the six topics and preserves material supported
observations alongside specific gaps. Aim for 8–12 summary rows when evidence supports
them; never pad findings or turn partial observations into a pass. Include a maturity row (age, indexed holders and transfers, pools and liquidity) so an
established token reads as established. Popularity never changes a technical finding, and a
gap is still a gap; preserve a verified sale, identified custodian or matched source without hiding larger-exit,
withdrawal-authority or launch-history gaps.

## Presets (step 3)

```sh
python3 "$SKILL_DIR/scripts/broad_collect.py" collect --run "$RUN" --preset receipts --tx 0xhash1,0xhash2  …provider flags…
python3 "$SKILL_DIR/scripts/broad_collect.py" collect --run "$RUN" --preset positions --ids 109216,109300
python3 "$SKILL_DIR/scripts/broad_collect.py" collect --run "$RUN" --preset getters --contract 0x… --signatures 'unlockTime(),beneficiary()'
python3 "$SKILL_DIR/scripts/broad_collect.py" collect --run "$RUN" --preset balances --asset 0x… --holders creator=0x…,treasury=0x…
python3 "$SKILL_DIR/scripts/broad_collect.py" collect --run "$RUN" --preset architecture --contracts locker=0x…,vault=0x…
python3 "$SKILL_DIR/scripts/broad_collect.py" collect --run "$RUN" --preset logs --contract 0x… --topic 0x… --from-block N --to-block M
python3 "$SKILL_DIR/scripts/broad_collect.py" collect --run "$RUN" --preset pool --contract 0x… --version v3
```

Each `collect` call is a fresh shell: source the private env and pass the same provider
flags as `start`; every `collect` recomposes the pipeline note with new receipts. Other preset results
are printed and imported into the draft; use those aliases in coordinator findings to update the initial observations. Several presets go
in one shell call joined with `;`, never as parallel tool calls: they share the session
ledger and the draft. Each preset is one pinned collection at the
run's pin (receipts at their own historical pins), imported into the draft, with decoded rows
printed. Getter signatures must come from a verified ABI or specification; the selector is
derived deterministically. Use presets for conclusion-changing checks (a locker's withdrawal
path, a sale receipt a lane found, a second position), not for a second contextual sweep.

## Notes (steps 4–5)

The note schema and the expansion rules are in [compose.md](compose.md); the lane briefs
carry a worked example and the scaffold carries the structure. Cite evidence by alias
(`runtime`, `pool1-liquidity`, `quote-100`, `doc-liquidity-explorer-holders`); the `facts`
view and the scaffold's `alias_hints` list every alias. A completed report needs every
surface `checked`, `not_applicable` with affirmative evidence, or `partial`/`unavailable`
with real attempts and an external boundary. `finalize` prints the first blocking stage with
all of its errors; fix the note, not the validator, and never read `compose.py`: each error
names the field, the allowed values and the fix. Rules that notes trip on: an adverse
finding's `subject` is the contract that holds the power (the locker, the Safe), with one
successful RPC read there; a `not_applicable` surface still needs one neutral
`state_observation` finding at the target citing `runtime` or getter evidence; findings whose
only surface is `not_applicable` cannot carry a summary `topic`/`signal`; a `checked` surface
with open gap findings is downgraded to `partial` (keep a boundary and basis on it) or, in the
final note without a boundary, refused with the exact fix; `claim` names the kind of
observation (`state_observation`, `source_analysis`, `historical_execution`, `inference`,
`coverage_gap`) while `proven_fact`/`strongly_supported` are strengths; a
`historical_execution` finding needs its receipt alias in `evidence`, and compose fills
`receipt_evidence_id`, `result` and the target-token transfer `effects` from the receipt when
the parties are declared scopes. Use 8–12 summary rows when supported by the evidence.

**Focused questions** do not use lanes or `finalize`: run `broad_collect.py start --no-lanes`
with the focused `--question` (the cheapest way to get a session, pins and receipts), add
`collect --preset receipts|logs|balances|getters` for the question's dependencies, and answer
from `facts` in chat, labeling other surfaces out of scope. `finalize --checkpoint` saves the
evidence if a bundle is wanted; a focused run is never delivered as a completed broad report.
See the fee-origin example in `examples.md`.

## Timing, turns and cutoffs

Lanes return by minute 4 (their brief gives them 4 minutes from when they start reading it).
The coordinator note is written from `facts`, the lane notes and the scaffold, not from raw
JSON. After minute 8 start no new preset; go to finalize. The 10-minute cap includes finalize,
one repair round and the chat answer. Past 10 minutes: if every surface is bounded, finalize
and deliver; if surfaces remain open, continue only on a conclusion-changing trigger stated in
one line, otherwise `finalize --checkpoint` and say what remains. A third preset always needs a
trigger. Within the standard scope, `unavailable` or `exhausted` is an honest boundary when the
remaining route would need a third preset or work outside the lane checklists; name that route
in `next_check`. Phase timings are in `investigation.py status "$RUN/session.sqlite"` and in
the report; quote them when reporting elapsed time.

Turn budget for reference (a 12.7-minute live run spent 73 turns, 86% of them model time):
start 1, spawn 1, facts 1, presets 1–2, lane wait 1–2, composes 1, scaffold 1, note edit 1–2,
finalize 1–2, report read and answer 2. Anything that reads helper source, inspects raw
collection JSON, retypes a brief, or repairs a lane note by hand is a turn the run did not need.
