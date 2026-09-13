# Built-in public RPC candidates

The collector resolves a default by the exact target chain ID when no endpoint is
configured. Explicit `--provider public --cost-policy free` selects that default even
if paid configuration exists. This mode ignores saved endpoint/key exports and rejects
custom authentication headers. `generic` retains explicit endpoint configuration and
its authorization gates; a configured dRPC URL cannot be relabeled as free.

| Chain ID | Network | Public endpoint | Primary source checked 2026-09-13 |
| --- | --- | --- | --- |
| 1 | Ethereum | `https://ethereum-rpc.publicnode.com` | [PublicNode](https://ethereum.publicnode.com/) |
| 10 | OP Mainnet | `https://mainnet.optimism.io` | [Network information](https://docs.optimism.io/op-mainnet/network-information/connecting-to-op) |
| 56 | BNB Smart Chain | `https://bsc-dataseed-public.bnbchain.org` | [BNB RPC endpoints](https://docs.bnbchain.org/bnb-smart-chain/developers/json_rpc/json-rpc-endpoint/) |
| 137 | Polygon PoS | `https://polygon.publicnode.com` | [Polygon RPC endpoints](https://docs.polygon.technology/pos/reference/rpc-endpoints) |
| 4663 | Robinhood Chain | `https://rpc.mainnet.chain.robinhood.com` | [Network information](https://docs.robinhood.com/chain/connecting/) |
| 8453 | Base | `https://mainnet.base.org` | [Base RPC overview](https://docs.base.org/base-chain/api-reference/rpc-overview) |
| 42161 | Arbitrum One | `https://arb1.arbitrum.io/rpc` | [Chain information](https://docs.arbitrum.io/for-devs/dev-tools-and-resources/chain-info) |

These are endpoint candidates, not verified identity or availability. Every live run
still verifies `eth_chainId`, deployed runtime and fresh block pins. Public providers
may throttle or lack historical/trace methods; failures remain coverage gaps. There
is no automatic endpoint rotation after failure or bypass of a host denial.

Other chains require an explicitly selected endpoint; never substitute a supported
chain or testnet. For a custom endpoint use `--provider generic --rpc-url-env NAME`
with the appropriate cost/auth flags. A missing custom export stays a configuration
gap. The low-level offline `--check-availability` accepts `--chain-id`; broad start,
bootstrap and subsequent presets derive it from their exact target.
