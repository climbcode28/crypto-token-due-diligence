# Launch stage and attributed-key activity

The Pump adapters use immutable official IDL revision
`9c82f61cb711b044a17f770ab8ce9f9bdf78f333`. File hashes are in
`assets/layout-sources.json`. Each owning program's own IDL governs its accounts;
older copies of another program's types embedded in the fee/AMM IDLs are not
interchangeable. These are interface facts, not deployed bytecode verification.

Current curve layouts distinguish real and virtual token/quote reserves, completion,
creator, mayhem/cashback flags and quote mint. The stored default pubkey represents
native SOL; the instruction interface uses WSOL's mint while native transfers still
use SOL. Non-native quote holdings are separate ATAs with their actual token program.
See the [pinned Pump interface notes](https://github.com/pump-fun/pump-public-docs/blob/9c82f61cb711b044a17f770ab8ce9f9bdf78f333/README.md).
These published capabilities do not establish which new products are live today.

PumpSwap binds its pool PDA, base/quote mints, actual vault ATAs, Token-2022 LP mint,
global controls and fee configuration. Actual vault balances remain separate from
pricing reserves that add the signed virtual quote adjustment. Sampled LP units use
both mint and pool-accounting denominators. Their difference is not lock/burn proof.
Pool creator, coin creator, mutable creator setters, cashback and sharing beneficiaries
remain separate roles. The [pinned pool specification](https://github.com/pump-fun/pump-public-docs/blob/9c82f61cb711b044a17f770ab8ce9f9bdf78f333/docs/PUMP_SWAP_README.md)
documents these state distinctions.

Stored flat/native/stable fee tables and admin roles are decoded. The documented
native normal-mode selection uses canonical creator derivation and a reserve/supply
market-cap ratio; noncanonical pools use flat fees. Curve applicable components are
protocol and creator fees. Special mayhem/cashback/boost/buyback and non-native fee
selection remain unresolved when their extra runtime semantics are not established.
No local Pump quote is advertised. See the [pinned fee-selection document](https://github.com/pump-fun/pump-public-docs/blob/9c82f61cb711b044a17f770ab8ce9f9bdf78f333/docs/FEE_PROGRAM_README.md).

`solana_launch.launch_facts` distinguishes:

- Pre-migration curve observed.
- Completed curve with migration unverified.
- Verified migration receipt, exact destination initialization CPI/funding, and
  current matching pool/mints/vaults/LP custody observed after that receipt.

An earliest fetched signature, mint suffix, completion flag or pool's canonical
creator PDA alone does not prove launch time or migration. A Pump initialization
time requires matching successful launch and inner token-mint initialization effects.
Legacy and v2 migration interfaces bind their actual quote assets. Unknown older
layouts retain an explicit unsupported-layout gap.

`launch_leads` accepts at most two retained exact-mint publications. A matching
publication or derived curve address is a lead to verify. Neighboring LaunchLab/DBC
products remain distinct unsupported automated semantics, not exhausted research.

Creator/treasury work starts with up to two exact-mint attributed keys and source
evidence. Keep the declared `(start_slot, end_slot]` window, at most two 25-entry
signature pages per named address, and at most eight selected receipts. Paginated
responses must bind their exact address and cursor. A short/empty page does not
establish archive coverage or absence of activity. An owner-address history is not
the history of every token account it controls.

`creator_activity` preserves allocation mints, transfer directions, verified sale
inputs, verified rebuy outputs, liquidity-withdrawal receipts and fee-operation
receipts separately. Swap intentions alone do not become sales. Claimed sales and
rebuys are recomputed from the supplied historical effects. Counter-asset receipts,
network fees/refunds and unknown profit remain scoped to their underlying receipts.
An exchange label, shared funding or transfer out is not personal cash-out.

`reconcile_inventory` can prove arithmetic conservation only for explicitly listed,
unchanged token accounts with atomic opening/closing batches, spanning per-account
history, every indexed receipt, complete interpreted effects and stable observed
ownership. Missing windows/receipts leave the result unresolved; a difference stays
a mismatch. It never claims exhaustive beneficial-owner inventory.

Prior launch links distinguish actual signer continuity from a recorded creator
argument. Neither establishes project affiliation, common control or a human
identity. Failed/partial history never becomes “no prior launches” or “no creator
sales.” Preserve material contrary state and capability gaps in later synthesis.
