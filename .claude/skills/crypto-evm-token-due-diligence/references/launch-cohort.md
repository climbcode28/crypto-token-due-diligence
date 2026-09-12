# Launch-cohort accounting

**Trigger:** early concentration, privileged allocations, exemptions, coordinated-looking flow, or alleged creator cash-out matters to the question.

**Minimum evidence:** exact launch/factory version, calldata and successful receipt, deployment sequence, allocation/exemption parameters, direct recipients, cohort definition and time bounds, material subsequent transfers and executed swaps.

Use [deterministic-backend.md](deterministic-backend.md) to collect and freeze the
declared receipts and calculate direct recipient flows/supply fractions. Its first
rules observe standard Transfer events and configured fee predicates; deployment
correspondence, actual buy recipients, intra-transaction exemptions and executed sales
still require the procedures below. Do not reinterpret gross flows as closing holdings.

Define the cohort **before measuring**: rule (for example direct buy recipients in the launch transaction), start/end blocks, evidence sources, exclusions, coverage, and any distinction between observed membership and inferred controller groups. Do not retrospectively choose only wallets that sold.

Build per-wallet/per-asset flow rows: initial allocation, purchases, received transfers, sent transfers, sales, rebuys, fees, proceeds, remaining inventory, and destination. Decode actual pool/curve direction and amounts from successful execution; router transfers alone can be intermediary settlement, liquidity provision, or failed intent. For Pons-style curves inspect the direct `recipient`, its tax/exemption, and delivered amount, not just the sender.

Trace material sale/rebuy chains to new recipients without equating recipients to the seller. Describe observed routing as **market-mediated redistribution** unless authenticated evidence independently supports stronger attribution. A wallet reaching zero may have transferred or bought for another recipient; it does not prove cash-out. Do not label proceeds profit without defensible cost basis, complete material flows, fees, and retained inventory.

Reconcile conservation per asset and conversion; retain downstream inventory instead of counting sales alone. If a route hits shared custodial infrastructure, stop exact attribution there. Avoid inferring common ownership from funding, timing, deterministic addresses, routers, exchanges, or settlement addresses.

**Stop:** requested cohort totals and material downstream flows reconcile over the declared interval, with dispositions classified as sale, transfer, retained, transformed, or unknown.

**If incomplete:** bound observed allocation/sales/inventory and disclose missing recipients, history, and cost basis. Human identity, coordination, intent, and ultimate beneficiary stay unresolved absent stronger evidence.
