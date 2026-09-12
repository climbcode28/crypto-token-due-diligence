# Fee-wallet and cross-chain reconciliation

**Trigger:** fee destination, claimed LP-fee origin, treasury spending, buybacks, or material bridge/proceeds flow is decision-relevant.

**Minimum evidence:** opening and closing balances at explicit pins; raw executed receipts/logs and calldata for material flows; asset identities/decimals; fee configuration/version history; claim/forwarding authority. For native/internal flows use traces or equivalent reconciled evidence and disclose unavailable traces.

1. Define wallet/contract cohort and interval from the question and observed leads. General
   diligence verifies current fee rights, material launch flows and a representative recent
   policy execution; it does not assert lifetime adherence from a sample. Expand to a full
   ledger for an explicit claim/question or a material unexplained delta, not because an
   all-time ledger would always be nice to have. Map basis and denomination: a 30% share of a 1% fee bucket is 0.3% of gross only if that gross and fee basis actually apply. Reconstruct historical configurations at execution; current settings are not historical realized rates.
2. Maintain integer per-asset journal: opening + inflows + explained adjustments - outflows - closing = unexplained delta. State signs, bounds, dust/rounding, and sources. Reverted transfers/events do not count; reverted transactions may still consume sender gas. Include refunds and relevant execution/L1 fees without charging gas to the wrong account.
3. For LP-fee origin, link pool/position accrual and collection receipts to forwarding and final holdings. In v3, collection may include previously decreased principal; reconcile decrease and collect history. In v4 inspect actual accounting/actions and settlements. An event called “fees” or an inflow from a manager is insufficient alone. Separate pool inventory, unclaimed fees, vault holdings, donations and prefunding. Attribute only the portion supported by the journal.
4. Treat wraps/unwraps, burns/mints and bridges as linked transformations with separate asset legs; do not count each leg as fresh revenue. For bridges match source success, message/nonce/identifier, source token/amount, destination chain and recipient, fees, delivered asset/amount and destination execution. Pin both chains. Pending delivery is a receivable/unknown, not destination inventory.
5. Follow material subsequent use until the requested endpoint or commingling. At commingling, report observable flows and bounds; do not assert exact coin-level origin, final beneficiary, exchange sale, or fiat withdrawal. A fungible inventory attribution may be a range, not a unique answer.

**Stop:** each material asset reconciles within justified bounds, source-vs-transformation distinctions are clear, and requested fee-origin/destination attribution is established to its defensible boundary.

**If incomplete:** report unexplained delta by asset, unavailable trace/history/destination evidence, and the fraction proven to originate from fees. Do not claim the entire closing balance came from LP fees when only some inflows are proven.
