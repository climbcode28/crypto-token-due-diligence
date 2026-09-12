# Solana diligence surfaces

In broad mode assess all eleven dimensions below. For each record the exact target or
related account/program, evidence IDs, controlling path, severity, likelihood, confidence,
coverage, time basis and the next conclusion-changing check. Focused mode uses only
relevant dimensions. Unknown/skipped/inaccessible is never no-issue or N/A.

| Dimension | Required investigation |
| --- | --- |
| token_controls | Mint owner program and initialized state; mint/freeze authority, currently frozen relevant accounts, delegates; Token-2022 extension inventory and all material configuration/change authorities; custom hook program and upgrade authority. |
| canonical_lp_principal_custody | Exact canonical pool program/version, mints and vaults; LP share or position ownership and delegates; withdrawal, position transfer, rescue, lock/vesting and program upgrade paths. |
| side_pool_removal_risk | Other material pools/curve stages/positions with separate ownership and withdrawal paths; search universe and limits. |
| sellability_exit_depth | Ordinary-holder execution evidence and current quotes at disclosed sizes, exact routes/mints, token/DEX/hook fees, net output and SOL transaction costs. A quote is not execution; a failed quote is not proof of a honeypot. |
| current_concentration | Integer mint supply versus custody-adjusted holdings, owners of token accounts, mint/program matches, denominators and exclusions; unresolved beneficial ownership and linked-wallet hypotheses. |
| historical_launch_integrity | Exact launch platform/version, mint initialization/authority changes, creator allocations, curve buys, migration, early cohort, transfers and confirmed sales; bounded signature history and pagination. |
| admin_treasury_reward_custody | Mint, hook, pool, locker, vault, treasury and reward controllers; multisig threshold/signers/modules, timelocks, upgrade authority, emergency paths and fee recipients. |
| reward_accounting_liveness | Entitlements, funding, accumulated liabilities, caps, payout processing and conservation; prove actual reward asset and availability. |
| utility_redemption_rights | Live token-linked utility; claim/redeem instructions, underlying asset, fees, caps, timings and discretion; backing inventory is not an enforceable holder entitlement. |
| external_dependencies | SOL/WSOL, quote assets, stablecoin controls, LST/bridge custody and redemption, oracles and external operators; each deployment has its own identity/evidence. |
| development_disclosure | Source-to-deployed-program/build correspondence, loader and ProgramData/upgrade configuration where applicable, release/audit scope and disclosure accuracy. An explorer verified label is corroboration until correspondence is established. |

## Token-2022 and controller review

Inventory every extension, including those a scanner omits. Check transfer fee config
and withdrawal authorities, current versus scheduled epoch fees/caps, permanent delegate,
default frozen state, non-transferability, pausable state/authority, transfer hook address
and change authority. Resolve hook code, extra-account dependencies and program upgrades.
Interest/scaled UI amounts affect presentation: use raw atomic balances and explain the
conversion. Confidential features can limit observable supply/flows; do not invent a
reconciliation. Metadata/group pointers and close authority require their own bounded
interpretation; metadata mutability is not itself arbitrary balance control.

No single revocation closes every control path. Existing frozen token accounts can remain
frozen after freeze authority removal. A permanent delegate can transfer/burn across token
accounts; a holder cannot revoke that mint-level delegate. Present these as evidenced
capabilities, with legitimate use cases and controller uncertainties distinct from intent.
Unsupported extensions or loaders stay unknown; do not call them absent or immutable.

The opt-in v2 account decoder pins interface revisions in
[`layout-sources.json`](../assets/layout-sources.json). Base fields and extension
coverage are independent: invalid/truncated TLV retains valid base observations and
records an extension error. Supported account extensions include withheld fees,
immutable owner, memo/CPI guard, nontransferability, hook and pausable markers;
encrypted withheld amounts stay unknown. Unknown tags retain their length and digest.
The newer permissioned-burn mint authority is inventoried separately. Extension
metadata/group pointers describe metadata relationships, not arbitrary token powers.

Current/scheduled transfer fees require an epoch observation whose epoch interval
contains the mint context. Atomic supply never uses interest or scaled UI multipliers.
PDA derivation follows pinned official vectors and only establishes a seed relationship;
it does not establish controlling authority or signing capability.

## Pools and launch stages

For Raydium distinguish legacy AMM, CPMM, CLMM and launch products; for Orca distinguish
Whirlpool positions; for Meteora distinguish the actual AMM/DLMM/curve product. Verify
program IDs and layouts from current official documentation and match actual accounts.
For Pump.fun or another launchpad distinguish pre-migration curve reserves, completion,
migration transaction and destination AMM. Never infer pool custody from a mint suffix.

Fungible LP shares and concentrated/bin-based positions need different ownership checks.
Burn/lock evidence applies only to the identified principal and actual controlling paths.
LP fee collection is distinct from principal withdrawal. Virtual curve reserves, vault
balances, quoted prices and displayed TVL are not interchangeable with executable exits.
Do not assume Raydium or launchpad defaults establish this deployment's configuration.

## Distribution, launch and proceeds

`getTokenLargestAccounts` returns up to 20 token holding accounts, not 20 people or a
full holder census. Resolve token-account owners and account mint/program; aggregate
accounts by owner without calling that beneficial ownership. Classify pool vaults,
lockers, treasury, exchanges and burns only with evidence; disclose unclassified amounts.
Different responses have different context slots. Do not divide mixed-state balances
into a mint snapshot without measuring/disclosing the mismatch.

The v2 holder preset samples discovered accounts and the mint in one bounded
`getMultipleAccounts` response. Owner aggregates preserve discovery rank/amount,
actual sample balances, the integer mint-supply denominator, missing/mismatched
accounts, separately evidenced custody exclusions and exact fraction inputs. Rounded
percentages are display strings. Withheld fees remain separate from spending-owner
balances; encrypted/unsupported quantities are explicit gaps. A labeled address is
never subtracted as a burn; proving a supply reduction requires transaction evidence.

For launch questions define the time/slot cohort before counting. Capture successful
transactions with `meta.err == null`, resolve versioned message keys and loaded addresses,
inner instructions and pre/post token balances. Preserve absent fields as gaps. A wallet
transfer or common funder is not proof of a sale, shared control or fraud. Separate token
dumps from principal withdrawal; reconcile opening balances + inflows - outflows with
closing balances per asset, including WSOL wrapping, rent, fees and commingling limits.

## Primary references

Checked 2026-09-06; resolve current deployed versions during each investigation.

- [Solana tokens and account ownership](https://solana.com/docs/tokens)
- [Token extensions](https://solana.com/docs/tokens/extensions)
- [Transfer hooks](https://solana.com/docs/tokens/extensions/transfer-hook)
- [Permanent delegate](https://solana.com/docs/tokens/extensions/permanent-delegate)
- [Token-2022 interface layouts](https://github.com/solana-program/token-2022/tree/main/interface/src)
- [Solana RPC methods](https://solana.com/docs/rpc/http)


## Maintained capability and completion boundaries

The [platform matrix](platforms.md) and [protocol registry](../assets/protocol-registry.json)
name the eight required product families and their pinned layouts. A family being
supported does not mean every deployment, old version, fee mode, lock or withdrawal
path is understood. [Liquidity custody](liquidity-and-custody.md) separates principal,
fees and controller powers; [launch](launch-and-creator.md) separates Pump stages and
actual migration receipts. Retain unsupported paths as explicit gaps.

The standard [runbook](runbook.md) records work on each surface, both owned lane
checklists, current evidence dependencies and the original focus. `checked` requires
affirmative scoped evidence; `unavailable` completion requires actual bounded external
attempts and an evidenced limit. Budget exhaustion, unsupported implementation and
pending research do not satisfy that condition. Use an undeliverable checkpoint when
required work remains. See [output](evidence-and-output.md) and
[completion](completion-and-delivery.md) before making a completed-report claim.
