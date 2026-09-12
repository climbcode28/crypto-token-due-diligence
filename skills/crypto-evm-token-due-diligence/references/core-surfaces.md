# Core screening surfaces

For each applicable surface record observation, execution path, controlling actor, evidence IDs, coverage, time basis, and the next check capable of changing the verdict. An omitted or inaccessible check remains unknown. In broad mode screen all sections; focused mode does not inherit a full-audit obligation.

## A. Token code and control

Inspect mint/burn/rebase, balance rewrites/seizure, pause, blacklist/whitelist, taxes and exemptions, cooldowns, transaction limits, trading gates, external calls, delegatecall, and upgrades. Trace reachable paths, not selector presence alone. Resolve current owners and roles, role admins, multisig signers/threshold/modules/guards, timelock delays/proposers/executors/cancellers, and who can change each. Distinguish currently executable behavior from behavior an administrator could introduce by replacing code. “No owner” or “renounced” does not close role, proxy, locker, hook, router, treasury, or reward authority.

## B. Liquidity custody

Identify each material pool by chain/address or full v4 key and PoolManager. For every v3/v4 position resolve manager, NFT/position ID or native position identity, range, liquidity, owner, approvals, operators, locker/hook authority, and fee recipient. Inspect decrease, withdrawal, burn, rescue, arbitrary-call, approval, upgrade, and position-transfer paths. An NFT lock does not prove the owner lacks another removal path. Fee collection and principal removal require separate analysis; owed amounts can include previously decreased principal. Separate canonical LP principal from side pools and disclose the search universe/ranges/thresholds. Locked principal does not guarantee price support, adequate exit depth, or in-range liquidity.

For v2-style pools, inspect the fungible LP token's total supply, balances, allowances,
custody and locker escape paths; no position NFT is required. Resolve the proportion of
principal each holder can redeem and any privileged pair/factory behavior. Burned minimum
liquidity is not proof that the remaining LP supply is locked. See [platforms.md](platforms.md).

## C. Sellability and executable depth

Seek a successful historical sale and pinned current read-only quotes for a small amount plus holder-relevant sizes. Inspect recipient exemptions and sender assumptions; one privileged seller does not establish ordinary-holder access. Record route contracts/pools, atomic input, quote asset and decimals, output, protocol/token/hook fees, gas assumptions, and failure reason. For sizes x and small baseline s, compare `(output(x)/x)/(output(s)/s) - 1`, using the same quote asset and units. Report whether quote fees are included; do not subtract them twice.

Separate spot price, price impact from size, slippage tolerance (execution limit), gas cost, and executable depth. Historical execution proves that historical state; quotes/previews do not prove a realized exit. For decisive local simulations require a successful receipt AND the intended underlying-asset balance delta, including costs. An emitted event or success boolean is insufficient. Simulation follows the isolated-fork reference.

## D. Supply and concentration

Reconcile total supply and material balances using the actual accounting model. Classify pool/protocol custody, lockers, treasury, burns, creator allocations, and investor-like balances separately; custody is not beneficial ownership. State denominators/exclusions and unclassified balances; avoid double-counting wrapped claims and their backing. Separate raw assets, rebasing units, synthetic claims, bond/NFT shares, LP shares, custody, total supply, and circulating float. Snapshot material `balanceOf` values where possible. Replay all Transfers only for historical questions or discrepancies, and investigate non-Transfer balance changes.

Screen vesting, unlocks, emissions, mint caps and treasury releases: allocation, released
and currently releasable amounts, cliff/end times, beneficiary/transferable control,
revocability/acceleration and who can change the schedule. Separate escrowed
existing supply becoming liquid from newly minted dilution; record the relevant horizon
and denominator. Compare material releases with observed float/depth without predicting
a sale. An advertised schedule needs matching contract/state or remains a project claim.
[OpenZeppelin vesting documentation](https://docs.openzeppelin.com/contracts/5.x/api/finance)
is a reference only when the inspected implementation corresponds to that version.

## E. Launch integrity

Decode exact factory/version, deployment sequence, deterministic-address inputs, launch parameters, supply allocation, exemptions, direct-buy recipients, funding, early transfers and sales. Separate platform defaults from caller-supplied exceptions; verify deployed behavior. Define any cohort before counting it, including time bounds, sources, exclusions, and coverage. Track initial allocations, transfers, sales, rebuys, downstream inventory, proceeds, fees, and retained assets. Zero balance does not prove cash-out. Establish sales with successful receipts and pool/curve mechanics, not transfers into a router. For Pons-style curve buys, resolve the direct recipient and recipient-specific tax treatment.

## F. Fees, treasury, proceeds

Map fee basis, denomination, splits, escrow, claim authority, recipients, configurable routing, and use. Separate percent of gross trade value from percent of a fee bucket, and configuration now from realized historical rates. Per asset reconcile opening + inflows + explained adjustments = outflows + closing + bounded unexplained delta. Account for wraps, burns, bridge legs, gas and reverts without double-counting transformations. Bridges require source execution/identifier, destination chain/recipient/delivery, and destination evidence. Exact attribution stops at commingling. An exchange deposit alone proves neither sale, fiat withdrawal, nor beneficiary.

## G. Rewards, vaults, backing, redemption

Separate inventory, liabilities, and promises. Determine who can claim, what asset arrives, conversion units, fees, caps, timing, approvals, administrator dependencies, and the actual exit route. Vault holdings are not necessarily available backing; synthetic rewards need an independently proven underlying exit. LP-fee-origin questions reconcile receipt-level collections/forwarding to balances and separate pool inventory, vault holdings, and unclaimed fees. Test material distributions for conservation, entitlements, cumulative caps, duplicate payments, unpaid amounts, retained inventory, and liveness. Distributions can exceed purchases with prefunding, carryover, donations, or minting; reconcile all sources first.

## H. Utility, dependencies, development

In broad work, apply [adoption-and-assessment.md](adoption-and-assessment.md) to give
measured adoption, market/social context and operating maturity their own assessment.
Credit supported use without turning valuation, popularity or age into contract safety.
Evaluate the actual token-benefit premise; absent unpromised dividends/redemption are not
automatic defects. Distinguish discretionary policy, enforceable commitment and observed
performance. Missing research belongs in neutral coverage, not adverse-risk counts.

Verify whether advertised utility is live, token-linked, and enforceable. Examine external assets, oracles, bridges, APIs, keepers, lenders, collateral, and redemption dependencies that can affect holders. Inspect source correspondence, reproducible builds, tests, audit scope/version, release controls, governance, disclosure accuracy, and observed operations. Distinguish code-enforced rights from administrator discretion or offchain contractual claims; legal enforceability may remain unresolved. Marketing polish, copied templates, and awkward code prove neither safety, fraud, nor AI authorship.

Use [project-credibility.md](project-credibility.md) to compare material promises with
the deployed path and observed use, including zero-state systems, fee forwarding and
pending redemption liabilities. A clean build or many tests does not establish economic
correctness. Report verified strengths alongside operational gaps and demonstrated defects.

## I. Prior launches and public project continuity

Screen exact launch-key history and dated official project references to earlier tokens.
Distinguish repeated launches by the same key, project/brand migrations, inferred wallet
links and verified human identity. Preserve chain/address and archive provenance for each
iteration, search bounds and earlier-holder outcomes when evidenced. Repeated branding or
shared funding does not establish common control or misconduct. Deepen only when a
material relaunch/disclosure question remains; use [project-credibility.md](project-credibility.md)
and [operational-attribution.md](operational-attribution.md). An unavailable history is an
unknown, never a clean-history finding.
