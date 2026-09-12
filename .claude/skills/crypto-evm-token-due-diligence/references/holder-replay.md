# Full holder or Transfer replay

**Trigger:** historical holders are requested, material balances disagree, or nonstandard
accounting requires reconstruction. Current concentration starts with indexed candidates
and pinned material balance snapshots; relevance alone does not require full replay.

**Minimum evidence:** exact target/runtime and accounting model; deployment or defensible starting state; pinned ending header; raw logs with query ranges/pages; supply/balance snapshots; exclusions and units. Archive absence is explicit.

1. Determine whether mint, burn, rebase, reflection, shares, migration, or direct storage changes alter balances without normal events. Use balances/shares/index histories appropriate to that mechanism; Transfer replay alone may be insufficient.
2. Backfill bounded contiguous ranges from deployment/start snapshot through the pin. Persist range coverage, pagination tokens and errors. Dedupe by chain/block hash/transaction hash/log index, reject removed logs, sort by block/transaction/log index, and handle reorgs.
3. Use integer atomic units. Reconcile mint/burn and supply; do not automatically call the zero address or a labeled burn balance burned supply. Prove whether the balance is spendable and whether totalSupply changed.
4. Verify material reconstructed balances against pinned `balanceOf` or the appropriate unit conversion. Record unexplained differences; never normalize them away. If all balances are unavailable, bound covered supply and unclassified residual.
5. Classify custody separately from investor-like balances and any inferred controller grouping. Report top-N and cohort percentages with total/circulating/investor-like denominators and explicit exclusions. Do not count both a wrapper's underlying custody and its beneficiaries as independent assets.

**Stop:** the requested snapshot/history reconciles within an explicit rounding/accounting bound, and material ownership categories plus residual coverage are stated. Full chain replay is unnecessary if a defensible snapshot answers the question.

**If incomplete:** report known balances and lower/upper concentration bounds where defensible; ownership of undiscovered/non-replayed balances remains unknown. Indexer coverage and beneficial identity remain separate uncertainties.
