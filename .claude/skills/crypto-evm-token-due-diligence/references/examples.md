# Behavioral examples (all hypothetical)

These are reasoning fixtures, not live findings or authenticated evidence. Do not use them to fill an actual target packet. Assume stated observations only for the conditional answer; missing identity/header/receipt evidence remains unresolved.

For concise Good / Potential Risk / Bad findings with separate Unverified gaps, project-delivery checks, creator
proceeds and prior-launch attribution, see [reporting-scenarios.md](reporting-scenarios.md).

| Scenario | Expected behavior |
| --- | --- |
| Fresh chat invokes an installed skill symlink from another workspace | Run `provider_context.py` before any RPC, read the returned trusted workspace/canonical-checkout guidance, and honor the current user's scoped authorization. The locator does not read credentials or grant permission. |
| Exact-address discovery selects Robinhood mainnet; the private env file configures the matching dRPC endpoint and key | Source private exports in the same invocation, check with `--provider auto --allow-network` (the key is the authorization), then collect chain ID, explicit header, runtime and final header recheck within a finite budget. Prefer this endpoint before public RPC. Prior successful evidence is not a new target pin. |
| Configured dRPC check returns `invocation_required` with `network_disabled` | Add `--allow-network` and rerun. No network request occurred, so this is not a provider failure. |
| Public RPC fails DNS/403 while matching authorized dRPC remains untried | The public failure does not establish dRPC unavailability. Try the configured authorized endpoint within the remaining budget before declaring RPC identity evidence unavailable. |
| Current user says no paid requests despite a configured key | Pass `--provider public --allow-network --cost-policy free` on every collector and do not source the private env; the current restriction overrides the configuration. |
| Availability returns ready but no live collection has run | Configuration is locally valid; identity, authentication and pin remain unverified. During research proceed to a bounded collection, not a completed or blocked diligence conclusion based only on preflight. |
| Current process lacks dRPC variables but the user already saved the documented private env file | Load that file without printing values in the same invocation as the check/collector; the configured key is the authorization. Do not ask for the key again or label saved configuration missing. |
| No documented private configuration exists, or its exports remain unavailable after loading | Report the actual configuration gap, continue public-source fallback, and do not manufacture credentials or assume paid authorization. |
| User supplies an exact address without a chain; exact-address launch and exchange pages identify Robinhood mainnet without conflicting evidence | State the inferred network and proceed without confirmation. Resolve provider context first; prefer matching configured authorized RPC, or discover an alternative endpoint if needed. Verify `eth_chainId` and capture code at the exact address. Discovery alone does not resolve deployed identity. |
| Only the symbol matches Robinhood, exact-address sources disagree between networks, or the user explicitly requested another chain | Do not substitute Robinhood. Preserve the explicit network or clarify the unresolved ambiguity; a failed RPC is not permission to switch networks. |
| Exact-address discovery identifies Robinhood but its RPC is inaccessible or target code is empty | Continue available evidence collection on that target and report the identity gap. Do not call identity verified or ask the user to certify an onchain fact. |
| Canonical position has no observed principal-removal path; a material side position is removable | Rate canonical principal and side-pool removal separately. Do not say all liquidity is locked. State inspected positions, authority paths, block pin and discovery coverage. |
| Supply is fixed, small sells quote successfully, a holder-size exit gets 70% worse output per token | Separate supply controls from exit depth. Report tested sizes, route, quote asset, per-unit degradation, fees and state; do not equate fixed supply with a realistic exit. Quotes remain previews. |
| Token runtime is immutable but its reward vault is upgradeable by one key | Keep token controls separate from reward/admin custody. Resolve implementation and upgrade power and describe how replacing the reward layer can change payouts/rights. |
| Launch wallets execute sells, use proceeds to rebuy for new recipients, and reach zero token balance | Reconcile sales, rebuys, downstream inventory, costs and transfers. Describe market-mediated redistribution; neither zero balance nor routing proves cash-out, profit, common ownership or intent. |
| Vault holds synthetic claims; preview returns another synthetic token, no underlying exit is proven | Separate holdings from liabilities and enforceable backing. Mark underlying redemption unknown; require successful local-fork receipt and underlying balance delta for a decisive simulation. |
| Historical RPC request fails because state is pruned | Record method/params, endpoint label, requested pin/range and error. Retry a bounded alternative if available; keep historical check unknown and record a coverage limitation, not a token defect or pass. |

## Focused fee-origin example

Supplied synthetic observations: opening balance 20 WETH with unspecified provenance, donation 30, v3 collection 70 of which 20 is previously decreased principal and 50 accrued fees, commingled outflow 20, closing balance 100.

Answer the fee-origin question only. The journal reconciles `20 + 30 + 20 + 50 - 20 - 100 = 0`. The identified interval's fee contribution retained at closing is bounded at **30–50 WETH**. If the opening 20 could itself have come from older fees, total possible fee origin is **30–70 WETH**, rather than a single exact attribution. Do not call all 70 collected WETH fees or all 100 closing WETH LP-fee holdings. The arithmetic is conditional on supplied assertions; without captured headers/receipts and asset identity this is not a live validated finding.

## Example invocations

- Focused: `$crypto-evm-token-due-diligence On chain <chain ID>, token <exact address>, did vault <exact address>'s <asset> holdings come from LP fees between <start block> and <end block>? Reconcile collections, principal, forwarding and closing inventory; keep the answer focused.`
- Broad: `$crypto-evm-token-due-diligence Perform broad diligence on chain <chain ID>, token <exact address>. My requirement is resistance to privileged asset removal and an exit of <amount tokens>. Pin current state, screen all core surfaces, deepen on material evidence triggers, and produce a validated evidence bundle with separate risk dimensions.`
- Formal: `$crypto-evm-token-due-diligence Turn this completed diligence bundle into a formal report with custody and fee-flow visuals. Reuse reconciled evidence, keep exact target/pin labels, validate the source, and identify any stale claims before rendering.`

Angle-bracket fields in these invocation examples are user-supplied inputs, never acceptable manifest values or pins.
