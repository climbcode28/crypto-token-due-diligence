# Complete pool and position history

**Trigger:** principal-lock claims, side-pool risk, migration, past removal, or fee/principal ambiguity can change the verdict.

**Minimum evidence:** searched factory/manager universe, creation/initialization logs, chain/version, exact pool addresses/keys, position identities, pinned owners/approvals/liquidity, and relevant custody code/state.

1. Search relevant factory events and known deployments with declared block ranges and pagination. Use directories/indexers for candidate discovery, then match onchain. Include user-specified pools even below financial thresholds. “Complete” means complete within a named universe; permissionless pools elsewhere may remain undiscovered.
2. Bind v4 pool identity to full key, derived PoolId and PoolManager; use pool-specific events/state. Resolve v3 manager NFTs or native core positions, and v4 manager NFTs or owner/range/salt positions without conflating these namespaces.
3. Follow mint/increase/decrease/collect/burn/transfer history. Recover approvals/operators now, locker permissions/beneficiary/unlock rules, rescue/arbitrary-call routes, upgrades, and delegated control. Reconcile liquidity and fees; a zero-liquidity position or a destroyed NFT needs history, not assumptions.
4. Map who can remove **principal**, collect fees, transfer the position, change a fee destination, or change the code. For timelocks include who changes the delay. Verify locked tick range and whether it currently supplies useful depth.
5. Separate canonical LP and side pools, quantify material side liquidity under the same state, and connect removal rights to tested exits. State custody per position instead of a single “LP locked” boolean.

**Stop:** material positions in the stated universe reconcile, each removal/control path is resolved or explicitly unknown, and historical scope requested is covered.

**When an export/index is missing:** test a permitted event route before calling custody
unavailable. Discover native v3 `Mint`/`Burn` owner/range positions as well as manager
NFT positions; for v4 retain owner/range/salt and exact PoolId. Use creation anchors,
indexed topic filters, pagination and adaptive provider-sized log ranges, then batch
current liquidity/owner/approval reads. Reconcile the covered position liquidity against
the pinned pool state; distinguish active-liquidity units from USD inventory. An empty
initial NFT says nothing about later positions. Do not blindly scan a whole chain or
repeat a rejected oversized range. Record the actual history/coverage/access constraint
if a bounded reconstruction cannot cover the material universe; lack of a UI export alone
is insufficient. Use already captured logs locally before issuing more requests.

**If incomplete:** say “No current executable removal path found at the pinned block” only for inspected paths/positions. Unknown approvals, unverified locker code, missing historical positions, and undiscovered pools remain separate coverage gaps.
