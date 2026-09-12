# Pool state and principal custody

Adapters recognize actual owning programs and pinned account layouts. An indexed DEX
label proposes a pool; it does not recognize a protocol. Each adapter exposes a versioned
capability descriptor, target/genesis requirements, dependencies, supported arithmetic and
unsupported quote/lock paths. The outer evidence bundle must bind the raw account packets
to genesis, headers, times and fresh critical rechecks. Adapter output alone is not a
validated broad report or proof that a published source revision is deployed.

Use `pool_sample` to assemble full pool, mint, vault, config/market and LP dependencies in
one bounded account batch. AMM v4 market discovery reveals its event queue; fetch that lead
before the final atomic batch. Separately read program/ProgramData controls. `minContextSlot`
is a floor; equal slots across separate calls do not establish one atomic reserve sample.

Raydium CPMM validates its PoolState discriminator/637-byte layout, mint order, token
programs, vault and LP PDAs, authority bump and AmmConfig discriminator/236-byte layout/PDA.
Base vault amounts minus protocol, fund and creator fee accruals produce public reserve
balances. Fee custody, confidential amounts, mint transfer controls and executable exit
outcomes remain distinct. Missing or unknown fee configuration prevents reserve arithmetic.
The pool may be created at a signed non-PDA address; the pool address itself is not required
to match a guessed deterministic seed.

AMM v4 has its own 752-byte layout and fee/PnL fields. Legacy status 1/5 enables the
OpenBook-dependent path. Only the pinned Raydium-maintained OpenBook program is supported;
Serum/other forks and permissioned market variants require another reviewed layout. Verify
OpenOrders market/authority, market mints and event-queue relationship before applying its
bounded ring of maker fills. Vault observations survive absent or invalid dependencies.

The current AMM source removed OpenBook while retaining the account layout. When legacy
and current reserve formulas disagree, emit both scoped candidates and leave the deployed
reserve total unresolved. Published layout/version compatibility cannot establish which
program implementation is deployed. When the formulas agree (including disabled order-book
states), their common account-balance result is usable with its evidence scope. Neither
formula proves order cancellation, route traversal or a successful sale.

LP mint supply and pool accounting supply are separate denominators. The pool's accounting
supply can include retained initial liquidity or historical differences not represented by
current minted LP tokens. Preserve each sampled account's owner, delegate, delegated amount,
close authority and state; pass those observed controller roots to the Phase 5 graph.
Missing or later-sample holdings do not contribute a custody numerator. Even all currently
minted LP tokens in a sample do not prove all principal inaccessible. Difference from the
accounting supply does not by itself prove burned or permanently locked liquidity.

No lock program is currently supported by these two adapters. Squads/program control facts
remain separate controller observations; labels, a pool PDA, a burn-like owner or an unknown
account cannot prove irreversible principal custody. There is no `all locked` or executable
exit default. Published program source/upgrade evidence cannot close unknown LP/locker paths.

Selection declares its indexed USD liquidity source and time. The primary source is
preferred over one alternate, with address tie-breaking. Preserve unpriced/conflicting
candidates and excluded pools at the cap. Ranking never establishes canonical pool status.
Layout references and licenses are recorded in `assets/layout-sources.json`; fixtures are
synthetic and test independently specified offsets/reserve expectations, not live behavior.

## Concentrated positions

Raydium CLMM and Orca Whirlpool are separate enabled adapters. Both use exact protocol
owners, full layouts and pool/position PDAs, actual pool mints/vaults, configuration,
position liquidity/ranges and boundary tick-array dependencies. Raydium permissioned
pool seed indices and Orca fee-tier seed indices are read from their stored fields;
Orca's fee-tier index is not assumed to equal tick spacing. Separate program control
observations remain necessary. Dynamic fees and Orca pool control/reward extensions
are retained as observations/hashes; these adapters do not implement dynamic quotes.

Pass up to six specifically discovered position leads, each with captured source IDs.
`position_sample` plans an atomic core/dependency batch per position, retaining the pool,
config, mints, vaults, position, boundary arrays and available NFT/bundle holding evidence.
It never issues an unbounded program-account scan. Multiple positions may share one
batch, but a shared slot across separate requests is insufficient for an atomic quantity.
No sampled position count is advertised as complete enumeration.

Each protocol has its own exact Q64 tick table and integer principal math. Positions
below or above range can own entirely one token even when their active liquidity is zero.
Boundary prices preserve the valid downward-crossing convention. An active-liquidity
fraction uses the pool's current active liquidity denominator; it is never a whole-pool
principal fraction. Missing boundary ticks, inconsistent pool/position associations,
insufficient boundary gross liquidity, unsupported layouts or integer overflow refuse
the affected principal calculation. Fees and rewards retain their stored checkpoints;
later uncollected growth is not silently added, nor are these checkpoints called live totals.

Orca supports verified SPL bundles (PDA, mint, active bitmap and index), fixed TickArray
and bounded DynamicTickArray tag/bitmap layouts. Standard SPL and Token-2022 position NFT
base ownership are observed for both protocols. Issuance must be revoked, mint supply one,
decimals zero and holding amount one. Mint extensions, freeze controls, holding delegate,
delegated amount and close authority remain separate evidence. Unknown extension semantics
remain gaps. Token-2022 bundle representations, unknown position account variants, Raydium
limit-order positions and lock configurations are explicitly unsupported. Frozen or
nontransferable position NFTs alone do not establish irreversible principal locking.

The current Orca repository uses the Orca License. Account layouts are independently
implemented wire observations; upstream programs are neither imported nor executed. The
numeric math table is also pinned to historical Apache-2.0 revision
`e528dd23bb41571f92cfdb49a2f15d4fa0b01bec`, verified identical to current numeric tables;
its notice is retained under `assets/licenses/`. Current and historical provenance are
recorded separately in the layout source inventory.

## Meteora DLMM and DAMM v2

The two adapters identify distinct owning programs and exact account discriminators.
DAMM v1, Dynamic Bonding Curve (DBC), expanded DLMM positions and neighboring products
are explicit unsupported candidates; an indexer label cannot substitute one for another.
Source revisions, file hashes and upstream license declarations are in
`assets/layout-sources.json`. DLMM is pinned at `576919e3e4368e542c402f000b4264724f7f23ec`;
DAMM v2 at `a85c926607433f23f0ea60f4ca7b1ae92f4156cb`. The latter source carries the
[Meteora Noncommercial Licence](https://github.com/MeteoraAg/damm-v2/blob/a85c926607433f23f0ea60f4ca7b1ae92f4156cb/license.md).
These local readers implement observed wire fields and integer relationships; no
upstream SDK or program code is installed or vendored, and no deployed-byte match is claimed.

DLMM supports the fixed 8,120-byte PositionV2 with at most 70 bins, in 10,136-byte
bin arrays. For each covered bin, gross MM principal is `floor(position_share *
bin_token_amount / bin_liquidity_supply)`, summed after per-bin rounding. Negative
bin IDs use floor division to select arrays. Missing bins retain the already decoded
bin observations but prevent a full position total. Vault balances, limit-order
inventory, protocol fees and the sampled MM principal remain separate. Embedded fee
parameters include function/collection modes, bin step, volatility controls and the
pinned fee cap; their sampled values do not establish a future dynamic fee or traversal.
No constant-product approximation or total market-depth assertion is supplied.

DLMM owner, operator and fee-owner fields are distinct controller leads. A captured
lock-release point may be compared only to a Clock sysvar from the same account batch;
operator permission and program controls remain separate from that time comparison.
Expanded positions and unknown layout versions refuse principal calculation.

DAMM v2 uses its actual 1,112-byte Pool and 408-byte Position. Current fee configuration
is embedded in Pool; it does not contain the initialization configuration address.
Fee modes 0/1 use the pool-wide price range with DAMM's liquidity units:
`A=floor(L*(upper-price)/(price*upper))`, `B=floor(L*(price-lower)/2^128)`.
Compounding mode 2 uses `floor(position_L * tracked_token_reserve / pool_L)`;
layout 0 does not yet track these reserves and is insufficient for this calculation.
The denominator includes the protocol's initialization dead liquidity. It is not a
fungible LP supply, position count, or unexplained burn percentage. Real vault balances
must back the modeled pool principal plus protocol fees. Reported amounts exclude
transfer fees, accrued claimable fees and rewards, and do not promise execution.

DAMM position NFTs use Token-2022, retain mint authority at the pool-authority PDA,
and retain the pool as freeze authority. Observed NFT holding ownership, token-transfer
allowance, protocol permission bits, and upgrade control are reported separately.
The protocol delegate path requires a delegate with **zero** token-transfer allowance.
For removal, fee claims and reward claims, unrestricted permission takes precedence
over the respective owner-ATA-only bit. A nonzero allowance is a separate NFT-transfer
control; it is not proof that a transfer or withdrawal will execute.

Unlocked, vested and permanently locked liquidity are separate quantities. Embedded
vesting refreshes on removal; explicitly captured external Vesting accounts require
refresh first. Their remaining schedules must reconcile the position's vested total
before a complete release amount is calculated. Slot/timestamp selection follows the
pool activation type and uses the same-bank [Clock layout](https://docs.rs/solana-clock/4.0.0/solana_clock/struct.Clock.html),
never local time. Missing Clock/vesting evidence leaves release quantities unknown
while retaining stored unlocked/permanent quantities. Permanent locking is a statement
about current program state/rules, not immutability, fee inaccessibility, or ownership.

Both adapters use at most six named leads and bounded atomic account batches including
actual mints/vaults, positions, arrays or NFTs, and optional external vestings. No global
position enumeration is attempted. A subset cannot prove all principal locked, total
custody, beneficial ownership, or executable exits.
