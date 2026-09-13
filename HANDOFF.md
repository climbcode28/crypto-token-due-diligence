# Provider setup and operating policy

## Current provider policy

Both specialists work with public RPC by default. This repository ships no credentials
and grants no standing permission to spend money on a paid provider.

- Optional private configuration belongs in `~/.config/crypto-research/env`, outside
  the checkout. Copy `env.example`, set file mode `600`, and source it with tracing
  disabled in the same shell invocation as a configured provider check or collection.
- A configured key alone is not authorization for paid use. The current user must
  authorize it; nothing here permits purchases, top-ups, or plan changes.
- An optional, ignored `HANDOFF.local.md` next to this file can record the current
  user's machine-local provider policy and bounded standing authorization. Its first
  second-level section takes precedence for EVM; `provider_context.py --policy`
  identifies the source. Never publish that file or reuse someone else's authorization.
- Respect host network permissions and each run's request, byte, and time limits.
  Missing access or evidence remains a gap, never a passing check.

## Endpoint configuration

| Variable | Purpose |
| --- | --- |
| `ROBINHOOD_DRPC_URL` | EVM public or credential-free dRPC HTTPS endpoint; automatic public selection works without it. |
| `SOLANA_RPC_URL` | Optional override for Solana's public endpoint. |
| `SOLANA_DRPC_URL` | Optional dRPC endpoint for Solana; defaults to `https://lb.drpc.org/solana`. |
| `DRPC_API_KEY` | Shared dRPC authentication key, sent as a header rather than embedded in URLs. |

EVM dRPC use requires the configured endpoint and the authorized invocation flags.
Solana dRPC use requires `--cost-policy paid --allow-paid`; public use needs no private
configuration. Never print the private env file or place keys in captured URLs.

## Research and maintenance

Start each investigation in a new ignored `research/` directory. Preserve the original
request deadline when routing between skills. Verify chain or mint identity and evidence
pins; never substitute testnet for mainnet. Completed reports must pass their specialist's
validation and delivery checks. Preserve evidence bytes and frozen replay engines.

See the [EVM runbook](skills/crypto-evm-token-due-diligence/references/runbook.md),
[Solana runbook](skills/crypto-solana-token-due-diligence/references/runbook.md), and
[project guidance](AGENTS.md). Maintained review records are in [plans/](plans/);
older setup records are described in the [provenance index](docs/development-history.md).
