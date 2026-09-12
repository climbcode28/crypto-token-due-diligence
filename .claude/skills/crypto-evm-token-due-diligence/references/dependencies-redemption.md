# External dependencies and underlying redemption

**Trigger:** advertised backing, vault/synthetic rewards, token utility, external collateral, or a dependency controls practical holder rights or exit.

**Scope first:** a routine quote asset calls for its exact chain/address, current proxy
and authority path, transfer restrictions and the exit exposure used in the assessment.
Start these reads with the architecture batch. Full issuer reserve, cross-chain finality
and offchain redemption audits are triggered by an actual backing/utility promise or
material discrepancy; they are not automatic lifetime sub-audits of every exchange pair.
Never describe an unexamined issuer as verified backing. A local matcher failure requires
review of supported correspondence alternatives, not a request that the user supply an audit.

**Minimum evidence for a triggered holder claim/backing route:** complete asset/claim chain, deployed contracts/control graph, balances and liabilities in their native units, eligibility/approval rules, caps/timing/fees, underlying asset and executable route. Treat offchain promises separately from contract-enforced rights.

Map `holder -> claim/share -> vault/issuer -> conversion -> underlying -> exit venue`. At each edge record who can exercise it, units/conversion rate, actual delivered asset, fees/caps/delay, admin intervention, liquidity and failure conditions. Distinguish a preview, accounting share price, inventory NAV, and a transferable/redeemable claim. Do not infer backing from a vault balance or ticker.

Verify whether inventory is pledged, lent, encumbered, reserved for other holders, administratively withdrawable, or only a synthetic representation. Reconcile total/circulating supply, claims, liabilities and available reserves without counting both backing and wrappers. Inspect material oracles (sources/staleness/control), bridges (custody/finality), APIs/keepers, collateral, lenders and issuer/custodian dependencies. Give other chains independent identities and pins.

Use pinned read-only calls/quotes first. A decisive local redemption simulation requires successful receipt plus intended **underlying** balance delta in an ordinary synthetic holder account, with fees and route accounted for. Receiving another synthetic token does not complete the underlying exit. Code-enforced payment rules and legal claims are different; legal enforceability may need separately scoped expertise/evidence.

**Stop:** the holder's actual enforceable route, realistic limits and material dependency failure modes are established, or a decisive missing edge is identified.

**If incomplete:** say which asset/exit/permission/backing remains unproven. Do not rate synthetic inventory as verified underlying backing; do not assign zero value merely because evidence is unavailable.
