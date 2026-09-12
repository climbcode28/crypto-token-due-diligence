# dRPC local setup and bounded live-test plan

> Historical setup record, superseded for current operation by [HANDOFF.md](../HANDOFF.md).
> The private configuration now exists, bounded paid read-only research is authorized,
> and a four-request authenticated collection succeeded. The no-flags availability
> example and pending-approval instructions below describe the earlier setup stage;
> do not use them as the current invocation or authorization policy.

Prepared 2026-09-06 from clean `main` at `6d8ea99`. **Draft; no live RPC or paid use
is authorized.** The user selected Robinhood Chain mainnet. Private environment setup
and offline verification are now complete; contract selection and dashboard tier/key
limit confirmation remain pending.

## Local configuration

The private configuration is `~/.config/crypto-research/env`,
outside this repository. Its directory is mode `700`; the file is mode `600`, owned
by the current user. It was created with setup comments and these blank exports:

```sh
export CRYPTO_RPC_URL=''
export DRPC_API_KEY=''
```

The user has now filled both values locally. Verification found a key-bearing URL;
removed only its final path segment exactly matching the separately saved API key.
The network and key were preserved. Local URL/header formats, permissions and ownership
passed, both variables loaded in the collector shell, and the network label was
consistent with Robinhood mainnet. No configured values were displayed. Actual provider
authentication and chain identity remain untested.

For future edits, change the values in a standalone local editor:

```sh
nano "$HOME/.config/crypto-research/env"
```

Save with Control-O, Return; exit with Control-X. Select Robinhood **mainnet** on the
existing dRPC key's endpoints page. Use its actual network slug, not a guessed slug.
The local adapter accepts a credential-free URL shaped like
`https://lb.drpc.live/?network=EXACT_NETWORK_SLUG` or
`https://lb.drpc.live/EXACT_NETWORK_SLUG`. Remove any `dkey` parameter or key-bearing
path segment. Put the key only in `DRPC_API_KEY`; the adapter supplies `Drpc-Key`.
Header authentication is documented by [dRPC](https://drpc.org/docs/gettingstarted/firstrequest).

A project `.env` is unnecessary and is not automatically loaded by this collector.
Explicit sourcing in the same shell invocation works for both this checkout and
the installed skill symlinks. No shell startup changes or authorization flags have
been added. Share the skill folders without this private machine configuration.

After editing, use the offline command below. It displays no configured values:

```sh
set +x
if source "$HOME/.config/crypto-research/env" >/dev/null 2>&1; then
  PYTHONDONTWRITEBYTECODE=1 python3 \
    skills/crypto-evm-token-due-diligence/scripts/rpc_collect.py \
    --check-availability --provider drpc
else
  printf '%s\n' 'Private config could not be loaded; check it in your local editor.'
fi
```

Run from the project directory. Blank values select `drpc_key_missing`. With both
values populated, the expected result is `fallback / network_disabled`,
`network_requests: 0`, `next_action: continue_standard_flow`. This is an offline
permission check, not complete URL validation or proof of authentication. Configured
credentials never authorize paid usage. Before live approval, separately inspect
the endpoint shape locally without displaying its value or constructing a client.

## Verified identity and remaining inputs

[Robinhood's official network documentation](https://docs.robinhood.com/chain/connecting/)
lists mainnet chain ID **4663** (`0x1237`); testnet is 46630. This is documented
identity, still to be verified against `eth_chainId` during an authorized test.
[dRPC announced mainnet support](https://blog.drpc.org/robinhood-mainnet-and-new-networks-drpc/)
and links to its [mainnet endpoint page](https://drpc.org/chainlist/robinhood-mainnet-rpc).
These pages do not establish this account's enabled network or endpoint slug.

Before requesting live-use approval, confirm the dashboard's exact mainnet selection,
tier and key-level daily limit, and select one known deployed contract with an
authoritative address source. The tier/limit and contract have not been confirmed.
Keep all key values and full dashboard
endpoint URLs out of chat and saved plans. No testnet substitution is permitted.

## Proposed live budget

One session, one endpoint, one contract, one numbered block, no automatic retries.
Stop between stages to inspect results; a failure prevents the next stage, a retry
invocation or a provider switch. The current collection may still perform its
budgeted header rechecks after a query failure. Count failed attempts against these caps.

| Stage | Requests | Attempt cap |
| --- | --- | ---: |
| Discovery | `eth_chainId`, then `eth_getBlockByNumber` with `["latest", false]` | 2 |
| First collection | `eth_chainId`, numbered header, `eth_getCode` at that number, numbered header recheck | 4 |
| Cache replay | `eth_chainId`, numbered header, cached code result, numbered header recheck | 3 |
| **Whole test** | **3 chain-ID reads, 5 header reads, 1 code read** | **9** |

`latest` is used only to discover a block number and capture its header. Freeze that
explicit number in the collection plan; compare its hash with the discovery header
and both runs. Token state is never read at `latest`. A reorg or mismatch ends the
test; do not replace the pin and silently repeat. During discovery, validate chain ID
4663 before requesting the header; a mismatch stops after the first attempt.

Proposed spending ceiling: **$0.01 total**, subject to explicit approval and
verification of this account's billing settings. Current published
[dRPC CU pricing](https://drpc.org/docs/pricing/compute-units) lists header/code reads
at 20 CU and chain-ID reads at 0 CU, giving 120 CU. Its general flat-rate description
would yield a conservative 180 CU if all nine calls cost 20 CU. At the published
$0.30 per million CU, that conservative estimate is **$0.000054**. This calculation
is not an invoice guarantee or authorization; verify applicable pricing, optional
provider features and limits before submitting the final approval request.

`--max-requests` caps attempts per invocation, not dollars or account-wide usage.
Maintain a total ledger across discovery and both collections. Review a dedicated
key's daily cap and other consumers; [dRPC documents daily key limits](https://drpc.org/docs/gettingstarted/createaccount).
If dashboard limits cannot enforce the proposed small ceiling, document that
limitation before approval. Do not buy, top up, enable auto-recharge or enlarge
limits as part of this test. A free tier does not bypass the existing local paid-use
guard; a strictly free-only adapter path would require separate review and tests.

## Plan and execution contract

The following is deliberately incomplete. Fill the same verified contract address
in both positions before approval; fill the block number from authorized discovery
after approval. Save the completed plan under a fresh ignored `runs/` directory.

```json
{
  "schema_version": 1,
  "target": {"chain_id": 4663, "address": null},
  "pins": [{"id": "smoke", "number": null}],
  "queries": [
    {"id": "runtime", "pin_id": "smoke", "method": "eth_getCode", "params": [null]}
  ]
}
```

Prepare and review the two-request discovery invocation before asking for approval.
It must use the existing credential-redacting transport, refuse redirects, retain
redacted responses or failure categories, cap attempts at two, and avoid retries.
Do not use a raw command that embeds the URL or key in process arguments.

Only after explicit approval, use `--provider drpc --allow-network --cost-policy paid
--allow-paid` with `--max-requests 4` for the first collection and
`--max-requests 3` for the replay. Run each once into a new output directory, using
one new SQLite cache shared by those two runs. The second cap intentionally leaves
no room for an extra code request plus a complete header recheck if the cache misses;
such a run fails acceptance and must not trigger an automatic retry. Offline
availability selection with those flags still makes zero requests, but the flags
must not be supplied before approval.

Accept only if both collections are `complete`, observed chain ID is 4663, discovery
and all captured/rechecked header hashes agree, code is valid nonempty hex, the first
run reports four attempts and zero cache hits, and replay reports three attempts
and one hit with identical runtime evidence. Review redaction and saved artifact
digests. Preserve all failure artifacts. Success establishes this small provider and
cache path only; historical state, traces, launch receipts, fee getters, proxy/source
correspondence and token diligence remain untested.

## Offline verification and review record

- Research suite: **21 passed**; diligence/backend suite: **106 passed**.
- Initial sourced blank configuration: `fallback / drpc_key_missing`, zero requests.
- After private value entry and removal of the matching key suffix from the URL:
  permissions/ownership and URL/header formats passed, both variables loaded in the
  actual collector shell, and CLI selection returned `fallback / network_disabled`,
  zero requests. No configured values were displayed or saved in the project.
- Synthetic environment checks: missing key, network disabled, unapproved paid use,
  and a generic provider alias all retain the expected fallback/gate; zero HTTP calls.
- One-pin synthetic rehearsal: first run uses four fake transport calls; replay uses
  three and one cache hit. Runtime evidence bytes match. HTTP and socket connection
  entry points were blocked during the rehearsal; zero live RPC requests occurred.
- Rehearsal artifacts: ignored `runs/offline-drpc-2026-09-06/`, including both frozen
  collections, their engine sources, SQLite cache and `verification.json`.
- Reviewed the current collector's uncached chain/header checks, attempt accounting,
  no-retry transport, provider alias gate, cache behavior and redaction tests.
- No production code correction was demonstrated or made. Engine remains **1.1.0**;
  schemas/rules, rubric, Robinhood-only research integration and no-key fallback are
  unchanged. Frozen `history/` is untouched. Future code changes require the existing
  implement-review-improve workflow, regression coverage and behavioral versioning.
- No live RPC, purchase, paid usage, commit or push was performed.
