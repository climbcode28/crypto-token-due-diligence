# Provider setup and operating policy

## Current provider policy

Both specialists work with public RPC by default. This repository ships no credentials.

- Optional private configuration belongs in `~/.config/crypto-research/env`, outside
  the checkout. Copy `env.example`, set file mode `600`, and source it with tracing
  disabled in the same shell invocation as a configured provider check or collection.
- A dRPC key in that file is the configuring user's standing authorization for bounded
  read-only research on that key: whenever the key is present the skills use dRPC for its
  matching network (EVM within the run's request ceiling, 400 by default; Solana within
  the 160-send session ceiling) and otherwise fall back to public RPC. No per-run consent
  flag or question is needed; remove the key from the file to stop. Nothing here permits
  purchases, top-ups or plan changes, and never reuse someone else's key.
- To opt out on one command, ask for the credential-free route explicitly: on Solana
  `--cost-policy free` (or `--provider public`), on EVM `--provider public --cost-policy
  free` (a free policy on the configured dRPC endpoint is refused by name). Removing the
  key from the file opts out: a credential-free dRPC URL left behind selects the chain's
  built-in public endpoint under the default provider on a registered chain, while an
  explicit `--provider drpc` or a custom endpoint variable stops with `drpc_key_missing`.
  `--cost-policy paid --allow-paid` are accepted for compatibility.
- An optional, ignored `HANDOFF.local.md` at the repository root can record machine-local
  provider notes. Its first second-level section takes precedence for EVM;
  `provider_context.py --policy` identifies the source. Never publish that file.
- Respect host network permissions and each run's request, byte, and time limits.
  Missing access or evidence remains a gap, never a passing check.

## Endpoint configuration

| Variable | Purpose |
| --- | --- |
| `ROBINHOOD_DRPC_URL` | EVM public or credential-free dRPC HTTPS endpoint; automatic public selection works without it. |
| `SOLANA_RPC_URL` | Optional override for Solana's public endpoint. |
| `SOLANA_DRPC_URL` | Optional dRPC endpoint for Solana; defaults to `https://lb.drpc.org/solana`. |
| `DRPC_API_KEY` | Shared dRPC authentication key, sent as a header rather than embedded in URLs. |

EVM dRPC use needs the configured endpoint and the key; Solana dRPC use needs the key (and
optionally `SOLANA_DRPC_URL`); public use needs no private configuration. Never print the
private env file or place keys in captured URLs.

The configured key is the authorization on every command; nothing asks for consent again.
Host approval rules still apply to every network command; if the host denies a
configured-provider command, complete permitted public research under the specialist's
recovery rules and state the boundary.

EVM has [built-in public endpoints](../skills/crypto-evm-token-due-diligence/references/public-rpc.md)
for its seven registered mainnets. `--provider public` ignores the configuration; `generic`
(or `auto`) uses the configured dRPC endpoint when its key is set and the chain's public
default otherwise. All live commands still require `--allow-network` and host network permission.

## Research and maintenance

Start each investigation in a new ignored `research/` directory. Preserve the original
request deadline when routing between skills. Verify chain or mint identity and evidence
pins; never substitute testnet for mainnet. Completed reports must pass their specialist's
validation and delivery checks. Preserve evidence bytes and frozen replay engines.

See the [EVM runbook](../skills/crypto-evm-token-due-diligence/references/runbook.md),
[Solana runbook](../skills/crypto-solana-token-due-diligence/references/runbook.md), and
[project guidance](../AGENTS.md). Maintained review records are in [docs/reviews/](reviews/);
older setup records are described in the [provenance index](development-history.md).
