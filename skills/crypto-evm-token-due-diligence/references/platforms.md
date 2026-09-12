# Conditional platform adapters

Read only adapters implicated by the frozen target. These links are discovery starting points, not attestations about a target or permanent deployment registries. Fetch current documentation, record its date/version, then verify chain, runtime, state, factory, and deployment evidence. No helper depends on a public endpoint remaining available.

## Uniswap v2 and compatible forks

Confirm pair/factory runtime and creation event, `token0`, `token1`, reserves and LP-token
total supply at the pin. Inspect material LP balances, allowances, lockers, beneficiaries,
unlock time, upgrades and rescue/arbitrary-call paths. Fungible LP tokens confer principal
redemption; canonical minimum liquidity burned at initialization covers only that amount.
Check fork-specific mint/burn, reserve synchronization and privileged behavior rather than
assuming upstream semantics. Treat reserve ratios as spot observations, not executable
holder-size exits; fee-on-transfer/rebasing assets and actual route fees require their
own accounting and quotes. Separate pool LP ownership from beneficial token holdings.

Discovery: [v2 pools](https://developers.uniswap.org/docs/protocols/v2/concepts/pools)
and [canonical pair source](https://github.com/Uniswap/v2-core/blob/master/contracts/UniswapV2Pair.sol).
Match the deployed fork/version before applying the reference behavior.

## Uniswap v3

Confirm factory, pool tokens/fee/tick spacing, deployed runtime, and factory event. Resolve NonfungiblePositionManager `positions(tokenId)`, `ownerOf`, `getApproved`, `isApprovedForAll`, and surrounding locker powers at the same pin. For non-NFT core positions resolve owner/range/position key separately; do not invent a token ID. Track liquidity decreases, collections, burns and transfers. `tokensOwed` and `Collect` alone do not distinguish fees from principal previously decreased. Reconcile decrease amounts and collections before claiming fee origin. Position asset amounts depend on ticks/current price; pool token balances are not an executable quote.

Discovery: [Uniswap v3 position management](https://developers.uniswap.org/docs/protocols/v3/guides/managing-liquidity/getting-started) and [canonical periphery source](https://github.com/Uniswap/v3-periphery/blob/main/contracts/NonfungiblePositionManager.sol). Match the actual chain's deployment and build to the source.

## Uniswap v4

Record chain, PoolManager, sorted `currency0`, `currency1` (including native-currency sentinel where applicable), uint24 `fee`, int24 `tickSpacing`, and `hooks`. Derive `PoolId = keccak256(abi.encode(PoolKey))` with correct ABI types, signed tick spacing, and Ethereum Keccak, then compare against initialized pool evidence. PoolId alone is not globally unique: retain chain and PoolManager. Record hook permissions, dynamic fees, custom accounting, upgrade/external dependencies and authorization. Do not infer behavior from hook-address flags alone.

The singleton holds assets for multiple pools. Never use its token balance as a pool's reserves. Read pool-specific state/liquidity/ticks and quote the exact route. Distinguish core positions (owner, tick bounds, salt) from periphery NFT positions; inspect manager approvals/operators, locker paths and hook-mediated economic changes. A nominal fee may be a dynamic-fee indicator; verify realized and applicable hook fees.

Discovery: [v4 overview](https://developers.uniswap.org/docs/protocols/v4/overview), [PoolKey source](https://github.com/Uniswap/v4-core/blob/main/src/types/PoolKey.sol), [PoolId source](https://github.com/Uniswap/v4-core/blob/main/src/types/PoolId.sol). Pin a source revision for an actual decoding basis.

## Pump.fun social trading

Start at [Pump.fun](https://pump.fun/landing) and follow its current trading/feed links.
Distinguish a social trading listing from a token's actual launch venue. Check live
network support and exact contract/mint identity; neither the platform's historical
association with Solana nor cross-chain marketing settles support for this EVM target.
Capture relevant dated posts, promotion disclosures, visible trade records and linked
profiles as attributed platform evidence. Verify material trading claims against exact
transactions/receipts and amounts; displayed P&L is not realized creator profit.

Do not substitute a same-symbol Solana mint. If the requested target itself is Solana,
use the sibling Solana diligence skill; a relevant Solana prior launch stays in a
separate identity packet. A feed author/profile does not establish control of a wallet.
If an exact-token page or feed is missing, login-gated or inaccessible, record the
specific search/access limit and use the shared bounded fallback. Do not infer no
activity, no risk, a public API, or a particular launch mechanism from an empty page.

## RH Trenches tracked-wallet activity

Use [RH Trenches](https://rhtrenches.com/) as a supplementary, unofficial aggregator of
tracked Fomo wallet activity for Robinhood Chain mainnet (4663). The supplied
[robinhoodtrenches.com](https://robinhoodtrenches.com/) redirected there when inspected
on 2026-09-08. Confirm the current destination, network and target before using rows.
Follow the source-routing lookup budget; no new collector, API or login is assumed.
A text-only fetch may expose just the page shell; use permitted background/hidden
browsing when available, otherwise record the access gap under the shared fallback.

- **Find the exact token:** try an exact-address lookup if supported. In the inspected
  UI, a full-address filter missed known rows returned by a symbol search. If this
  occurs, use symbol/handle only for discovery, then match the full contract address
  and chain on each candidate. A shortened address, ticker or token-name match alone
  cannot resolve identity. Empty search results are not evidence of no trading.
- **Capture coverage:** save source URL, retrieval UTC, observation date/time and its
  timezone (or unresolved), displayed history start/window, tracked-wallet coverage,
  filters and feed freshness. Inspect with warning-hiding `clean` filtering off and
  include stock-token rows when relevant to the target or a material quote/proceeds
  leg. Record the actual filters; do not silently expand into unrelated stock research.
  Missing dates, stale feeds, excluded wallets and unindexed intervals remain gaps.
- **Capture leads:** retain the persona/profile URL, full observed wallet and token
  addresses, side, token quantity, displayed cash amount/unit, estimate/warning labels
  and transaction hash/link where available. A "first buy" or "closed position" is
  bounded by the site's wallet/history/accounting coverage, not a lifetime statement.
- **Verify material claims:** the coordinator follows the existing provider policy,
  preferring matching authorized dRPC with authorized fallback when unavailable, for
  successful receipts, historical pins and decoded asset flows; reuse
  matching evidence already captured in this investigation. Confirm actual sender,
  recipient, token/quote assets and amounts rather than equating transfers or a linked
  hash with a successful swap. Failed/mismatched transactions cannot support a trade.
- **Bound accounting and labels:** price-feed estimates without a readable cash leg,
  displayed sell/open-position P&L, returns and hit rates are attributed calculations.
  Reconcile cost basis, fees, transfers, gifts/airdrops and retained inventory before
  claiming realized profit. "Planted", "honeypot", "drained" and similar automated
  warnings are leads; many buys and few sells alone do not prove blocked sales or fraud.
- **Bound attribution:** a Fomo persona or popularity rank does not prove wallet control,
  creator status, coordination or organic demand. Establish the relevant role under
  [operational-attribution.md](operational-attribution.md) before connecting observed
  sales to a creator or comparing them with dated public claims. Share the captured
  lead with the project/creator lane; RH Trenches and Fomo may share upstream evidence.

Stop once relevant candidate trades are captured or the lookup/access limit is reached.
Report only what was found among the covered wallets and interval. Missing activity
never certifies clean history, continued holding, sellability or absent creator sales.
No site observation replaces the existing token-control, LP-custody or exit-size checks.

## Pons-style launches

For launchpad discovery, use [Pons](https://www.ponsfamily.com/) and
[@ponsdotfamily](https://x.com/ponsdotfamily), with authenticated site/docs/repository
cross-links. Capture the exact-token launch page, dated launch/migration announcements,
creator/recipient links and disclosed fees/allocations. A profile's launch history is a
lead until tied to exact token addresses and execution keys; platform-wide statements
do not establish an individual token's current configuration.

Start from the target's creation receipt and exact factory runtime/version; do not apply the current website's mechanism or fee split to every generation. Determine whether the launch used a direct pool, a curve, or migration; follow the observed sequence. On a curve launch decode caller, funder, `recipient`, quote asset/input, minimum output, configuration and exemptions. Check the **recipient's** applicable tax at execution, actual tokens delivered, and how an initial buy differs from defaults. Follow graduation into exact pool/position custody, fee escrow, payout and buyback/treasury contracts. A later fee policy is not evidence of an earlier realized rate.

Discovery: [Pons documentation](https://docs.ponsfamily.com/), [versioned v2 documentation](https://docs.ponsfamily.com/v2), and [project contract repository](https://github.com/ponsdotdev/ponsfamily). These are project claims until matched. The repository publishes multiple generations; its root ABI/metadata described V1 when checked on 2026-09-07. Select the target-matched generation and pin the relevant commit rather than applying the root ABI to every launch. Inaccessible versioned documentation is a coverage limit, not a token finding; do not bypass restrictions or infer missing behavior.

## Long

Use [Long's token directory](https://app.long.xyz/tokens) and
[@longdotxyz](https://x.com/longdotxyz) as launchpad discovery entrypoints. Authenticate
current site/account cross-links and capture the exact token page, chain, contract,
linked factory, deployment transaction and relevant documentation/source. Inspect dated
launch/funding/migration announcements, creator links, initial allocations, vesting and
fee/holder-rights claims. Follow relevant prior launches by exact keys, separating
platform listing history from proven common control.

The directory may require a browser; an empty fetch is not “no token.” Do not infer a
universal launch mechanism, vesting rule, fee policy, holder right, or locked LP from
branding. Resolve each from target-linked onchain evidence. Follow surrounding
funding/vesting/treasury/reward contracts when actually present. Claimed asset backing
or revenue sharing triggers [dependencies-redemption.md](dependencies-redemption.md)
and [reward-accounting.md](reward-accounting.md) as relevant; a listing or promotional
announcement alone establishes neither backing nor an enforceable holder claim. If
the page lacks authenticated deployment mappings, leave platform association unresolved
and continue exact-address chain evidence within the existing cutoff.

## RH Scan explorer

Use [RH Scan](https://rh-scan.com/) as a supplementary explorer for Robinhood Chain
mainnet (4663), under the existing chain-explorer source category. Its
[about page](https://rh-scan.com/about) describes an independent community indexer,
unaffiliated with Robinhood or Etherscan. At inspection on 2026-09-08,
[official connection documentation](https://docs.robinhood.com/chain/connecting/)
listed [Blockscout](https://robinhoodchain.blockscout.com/) for mainnet. Confirm current
network support and entrypoints; an explorer listing does not replace RPC identity.
Use a matching-chain alternate within the shared fallback limit when a needed fact is
inaccessible. Never substitute mainnet evidence for testnet or another requested chain.

- **Wait for actual records within the lookup budget:** sampled pages initially showed
  "Unknown Token", zero holders or empty tables, then populated. A text-only shell,
  403, loading placeholder or unavailable record is an access gap, not a zero balance,
  absent history or adverse token fact. Use background reads and only the browsing
  tools permitted by the host's execution conventions; stop at the existing cutoff.
- **Capture exact evidence and coverage:** retain the full chain/address or transaction
  hash, source URL, retrieval UTC, source block/hash/time where exposed, filters,
  pages/range, units and raw artifacts. Record unavailable pins explicitly. The
  inspected holder view exposed the top 1,000, not the complete reported holder set;
  counts such as `>10,000` are lower bounds. Record current limits rather than assuming
  those caps are permanent. A page-data download or CSV control does not establish a
  complete export; inspect its scope if used. The provider's full-history claim does
  not prove complete discovery, an absence of sales or a clean launch history.
- **Check source correspondence and proxies:** capture source files, ABI, compiler and
  optimization metadata when supplied. An "Exact match" badge is the explorer's
  verification claim, not an audit. Match deployed runtime and resolve the current
  implementation, beacon/admin and upgrade powers under [proxy-bytecode.md](proxy-bytecode.md).
  Verified proxy source alone does not verify its implementation or token behavior.
  Explorer Read Contract output with no usable pin cannot replace pinned state.
- **Reconcile transaction meaning:** use status, timestamp, calldata, internal-transfer
  and event views to locate relevant evidence. Verify material execution through the
  coordinator's existing provider policy: matching authorized dRPC first, with authorized
  fallback when unavailable. Match successful receipts, block hashes, emitting contracts,
  topics/log indices and correctly decoded atomic amounts; preserve trace provenance
  for internal calls. A method label, transfer row or rounded dollar value does not
  establish a swap, realized profit or current sellability. Sequencer confirmation is
  not proof of settlement finality or completed delivery to another chain; keep each
  required chain's evidence and pins separate.
- **Bound labels and balances:** contract-creator, pool and named-wallet labels are
  discovery leads. Establish factory/caller/recipient roles and public attribution under
  [operational-attribution.md](operational-attribution.md) before alleging creator sales
  or common control. Pool custody is not beneficial holder ownership; a v4 singleton's
  balance is not one pool's liquidity. Verify controls and exit-size evidence separately.
  Price, market-cap and portfolio estimates do not establish backing or redemption rights.
- **Share work and keep API assumptions explicit:** use the assigned existing lane and
  reuse exact RH Trenches transaction references and already captured evidence within
  this investigation. Explorer presentation of the same transaction adds context, not
  an independent underlying event. The [API page](https://rh-scan.com/api-docs) had not
  finalized endpoint references, keys, rate limits or stability guarantees at inspection.
  Do not assume an Etherscan-compatible API or build a collector around undocumented
  internal/export endpoints. Use current documented interfaces only if available and
  authorized; missing API access does not block other permitted sources.

## Robinscan explorer

Use [Robinscan](https://robinscan.io/) alongside RH Scan as an optional explorer for
Robinhood Chain mainnet (4663). Its [documentation](https://docs.robinscan.io/) presents
mainnet data, not testnet 46630; the explorer describes itself as unaffiliated with
Robinhood Markets. Confirm current coverage and exact chain/address/hash. Follow the
existing source-routing ownership, lookup cutoff and shared one-alternate allowance.
Use the host's permitted background/browser tools; a readable overview does not establish
that a detail table has loaded. Missing records, loading rows and access failures remain gaps.

- **Capture the evidence basis:** save URL/query, retrieval UTC, source block/hash/time,
  filters, pages/range, units and raw records. Read current [coverage limits](https://docs.robinscan.io/data-coverage).
  Indexed history, current balance/holder snapshots, derived analytics and external
  market data have different time bases. The documented full-history index is a provider
  claim; inspect actual coverage and freshness. An empty account can mean unseen by this
  index. Some list totals are navigation bounds rather than global counts; page CSV
  exports contain loaded rows, not necessarily complete history. Omission cannot prove
  no balance, no creator sales or clean history. Missing source pins remain explicit.
- **Bound holder analytics:** [Token Intelligence](https://docs.robinscan.io/api-intelligence)
  documents up to 100 ranked holders, `basis.coverage` for observed supply and
  `basis.sampleCompleteness` as a collection ratio (1 means all required top-N rows).
  Complete sampling is not complete ownership coverage or a historical snapshot.
  A null `basis.asOfBlock` stays unpinned; do not substitute the current chain tip.
  Gini is over observed top-N only. Preserve raw and adjusted concentration,
  listed infrastructure exclusions and each risk signal; curated exclusions and other
  labels still need custody/role verification. Permissionless names cannot lower risk.
  `insufficient_data`, null scores and missing prices stay unknown. An available risk
  score is neither an audit nor evidence of absent powers, safe custody or sellability.
- **Verify contracts and transactions:** [verified-contract reads](https://docs.robinscan.io/api-contracts)
  are Beta and may expose source, ABI, compiler/constructor metadata and a resolved
  proxy implementation. Capture match type; an empty verification record or HTTP 200
  does not establish verified source. Apply [source/proxy checks](proxy-bytecode.md)
  to runtime correspondence and current implementation/upgrade authority. There are no
  documented Read/Write Contract forms. Traces are source-dependent, and unavailable
  traces do not prove no internal calls. Calldata decoding needs an agreeing verified
  ABI; method labels are leads. Reconcile material execution with successful receipts,
  exact emitter/assets/atomic amounts, trace provenance and historical pins through the
  coordinator's existing matching-authorized-dRPC-first policy and authorized fallback.
- **Interpret rollup context narrowly:** [batch records](https://docs.robinscan.io/blocks-and-batches)
  link L2 ranges to indexed Ethereum publication transactions when available. A block's
  L1-height field is not batch membership. A batch Finalized label describes the indexed
  L1 commitment transaction, not a standalone fraud-proof/challenge-period analysis or
  completed bridge delivery. Pin and verify material settlement/destination evidence separately.
- **Separate two PnL sources:** the [Top Traders leaderboard](https://robinscan.io/leaderboard)
  uses Fomo account-wide PnL, trades and volume across all chains; only Top Holdings is
  filtered to this chain. Do not assign these totals to Robinhood or the target token.
  Fomo-derived rankings/trending data are platform context, not independent confirmation
  of Fomo/RH Trenches observations or proof of persona control. Robinscan's own
  [wallet PnL Beta](https://docs.robinscan.io/api-wallet-pnl) is different: it recognizes
  clean single-token/WETH swaps with weighted-average
  ETH cost basis from capped transfer history (documented 50–2000 transfers and at most
  20 unrealized positions). `basis.complete=false` signals capped history; even `true`
  does not repair unsupported multi-token/non-swap flows or historical USD conversion.
  Incoming non-swap quantity can enter at zero cost (`hasNonSwapFlows`), inflating later
  estimates. Current USD rates are not historical proceeds. Coverage docs describe
  narrower web sell badges; verify live availability. Apply existing cost-basis, fee,
  transfer, attribution and inventory checks
  before claiming realized creator profit; a displayed return never suffices.
- **Keep structured access optional:** the documented read-only [partner API](https://docs.robinscan.io/api-reference)
  requires a separately provisioned base URL and partner key; do not infer a public
  endpoint or Etherscan compatibility. The [MCP server](https://docs.robinscan.io/mcp)
  uses that API and currently requires repository-source installation and Bun, not a
  published standalone package or hosted endpoint. Documentation does not establish
  that either is installed, connected or authorized here. If already available and
  authorized, follow current docs, deployment limits, Beta semantics and shared budgets;
  keep credentials in private configuration outside the project and evidence artifacts.
  No API setup or purchase is required for diligence. Do not extract internal site
  credentials or treat existing dRPC authorization as Robinscan partner access. Public
  page evidence and other authorized sources remain usable without these integrations.

Reuse existing target evidence across lanes and explorers. Matching transaction hashes
describe one event; shared upstream Fomo data is one source lineage. Robinscan's UI,
API and MCP are access paths to the same service, not three independent witnesses.

## Robinhood Chain

Use [official connection documentation](https://docs.robinhood.com/chain/connecting/) to discover current mainnet/testnet infrastructure. When exact-address discovery unambiguously identifies Robinhood Chain and the user omitted the network, disclose that inference and proceed without manual confirmation. Verify the inferred or explicitly requested network with `eth_chainId` and capture the target's deployed code; never substitute testnet or another chain with the same address. Conflicting or ambiguous network evidence requires clarification. Verify archive, log-range, trace, supported block-tag and EIP-1898 capabilities before relying on them. Document explorer/API/RPC failures and bounded retries. Pin the relevant settlement/destination chain separately when examining bridging or finality. Examine sequencer, bridge, upgrade and external-asset dependencies when material; EVM compatibility does not prove an asset is backed or redeemable.

For indexed mainnet discovery, select the [RH Scan](#rh-scan-explorer) or
[Robinscan](#robinscan-explorer) adapter within the existing source-routing budget.
Their network numbers and links are discovery
context, not trusted identity or permanent infrastructure constants; live chain/runtime
verification remains required.
