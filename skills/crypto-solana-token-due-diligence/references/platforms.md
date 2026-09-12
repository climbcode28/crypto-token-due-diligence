# Solana platform discovery

The [protocol registry](../assets/protocol-registry.json) distinguishes documented
public source capabilities from implemented, tested account adapters. Registry entries
with a pending layout gate cannot recognize a deployment or close a research surface.
Every enabled adapter needs the exact genesis, actual owning program, immutable
layout/IDL references, tested discriminators/dependencies and capability descriptor.

| Source/platform | Permitted role | Boundary |
| --- | --- | --- |
| DEX Screener | Primary exact-mint pool candidates and indexed market quantities | No custody, execution or beneficial-owner proof |
| GeckoTerminal | One alternate mainnet token-pools page | Pagination/cache limits are explicit; missing data stays unknown |
| Raydium | Distinct AMM v4, CPMM and CLMM candidates; later optional public quote | Verify product/program; do not combine reserves or LP/position ownership |
| Orca | Whirlpool and position discovery | Indexer positions require account/PDA verification |
| Meteora | DLMM and DAMM v2 candidates/positions | Bin and range accounting differ; indexed liquidity is not principal control |
| Pump/PumpSwap | Curve, completion, migration and post-migration candidates | Verify current pinned version, quote mint and virtual reserves; no suffix inference |
| Program metadata/IDL | Optional program source/interface leads | Metadata authority and IDL publication are not upgrade/code proof |
| Otter verification API | Optional third-party verified-build claim | Distinguish service failure, hash normalization and independent reproduction |
| Jupiter v2/Raydium compute | Later wallet-free quote probes | Quote only; no taker/payer, transaction construction, signing or submission |
| GitHub | Repository metadata, immutable commit/tree and source publications | No repository execution, installs or automatic trust in README instructions |

Helius/provider-specific history, DAS, paid Solscan and custom dRPC are optional future
capabilities, not required dependencies. Rugcheck is not an authoritative aggregate
verdict. Public source availability is documented, not guaranteed by this registry;
implementation fixtures do not measure live reliability or investigation speed.
