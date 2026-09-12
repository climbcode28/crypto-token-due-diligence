# Reward epochs and backlog

**Trigger:** distributions, accounting discrepancies, unfunded promises, duplicate payments, or processing liveness could change the verdict.

**Minimum evidence:** epoch/range rules and unit conversions, entitlement inputs or roots/proofs, caps and paid state, opening inventory, all material funding/transformation flows, successful claim/distribution receipts, closing balances and pending liabilities.

Recompute entitlement independently for sampled/material recipients and full epochs when discrepancies justify it. Distinguish cumulative entitlement from incremental claim, global from recipient caps, actual asset units from shares/synthetic units, and paid from scheduled. Check duplicate payments/identifiers, replay protection, resets/upgrades, rounding/dust and unpaid balances. An event or status flag is insufficient if the promised asset did not arrive.

Conservation: opening inventory + purchases + prefunding/donations/carryover + authorized minting/conversions + explained adjustments = distributed + other outflows + retained inventory + bounded unexplained delta. Distributions may exceed purchases legitimately; include other sources before finding an error. Liabilities can exceed spendable inventory even when the asset journal reconciles.

Model backlog with measured eligible arrival rate, processed recipients/units per transaction, observed cadence, gas limits, keeper funding, permissions and restart/cursor behavior. If service rate <= arrival rate, backlog will not clear under that scenario; if service exceeds arrival, bound clearance from backlog/(service-arrival), naming units and uncertainty. Do not treat historical cadence as guaranteed future automation. Test material failure isolation and whether one bad recipient stalls others using reads or permitted fork simulation.

**Stop:** material epoch conservation, entitlement/cap/payment behavior and feasible processing envelope are reconciled, or bounded unresolved liabilities/backlog are sufficient for the user's decision.

**If incomplete:** state unpaid amount/range, unavailable entitlement inputs, unknown recipients, unfunded liabilities, and operator/liveness dependencies. An accounting pass is not a redemption-rights pass.
