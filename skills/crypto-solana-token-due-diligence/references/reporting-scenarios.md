# Reporting calibration scenarios

- **Retained mint authority:** name the actual authority and issuance consequence.
  It may be material technical exposure; it does not establish malicious intent.
  A high/critical concern stays in summary, relevant conclusion and mitigation review.
- **Revoked mint/freeze controls:** describe those sampled fields. Other Token-2022
  extensions, program upgrades, delegates, treasury and pool powers remain separate.
- **Large owner aggregate:** show exact accounts, units, denominator, sample share and
  custody exclusions. A spending owner is not necessarily one beneficial holder;
  largest-account sampling is not a census or concentration of human ownership.
- **LP/NFT custody:** report sampled principal and controller paths. Claiming all
  liquidity locked needs the exact complete custody scope and reachable withdrawal
  authorities. Unknown position ranges, fee rights or bin arrays stay unknown.
- **Quote and observed sale:** a local quote is an estimate at its sampled state.
  A verified receipt proves one historical target/pool flow with matched owner and
  effects. It does not prove present exit depth, an arbitrary order's execution or
  indexed organic activity. Keep rent/refunds/network fees separate from sale proceeds.
- **Public source/audit:** a repository, third-party hash statement, matching bytes
  and independently reproduced build are distinct assurance levels. Audit scope,
  revision and deployment correspondence must be stated; a logo/link is not runtime
  protection or proof that promised work was delivered.
- **External limits:** a completed bounded assessment can retain evidenced access
  denials from attempted distinct routes. A timeout is not a pass. Untouched work,
  unsupported local decoding and budget exhaustion remain partial, with no invented
  alternative source or optimistic closure.
- **Incomplete/blocked/focused:** save a checkpoint with actual findings and gaps.
  Explain what the available evidence answers and what remains unverified. Do not
  fabricate a four-axis verdict solely to make the delivery schema pass.

## Rating rules

Rows with a verified observation are rated; `Unverified` is reserved for a route that was not
run or whose sources answered nothing (its `gap_basis` says which).

- **Concentration (current_concentration):** the holders fact is `observed` when the exact
  largest-20 read succeeded; rate it from the custody-adjusted figures. `good` when the top 20
  hold at most 30% of supply and the largest spending owner at most 5%; `potential_risk` above
  either bound; `bad` when one non-custody owner holds 50% or more. Beneficial ownership and
  linked wallets stay a stated limit in the text, never the reason for `unverified`.
- **Linked wallets (RugCheck corroboration fact):** a transfer-linked insider network holding
  10% or more of supply is `potential_risk`, stated with its wallet count and share, plus any
  insider-flagged listed holders the exact largest-holder sample verified (the report does not
  list a network's members); below that it is context in the concentration text. The network is
  the indexer's claim, never proven common ownership, and it never makes a row `unverified`: a
  refused report is a stated capture limit. A RugCheck locker or authority claim is a lead only;
  custody and controls stay rated from the observed pool and mint facts.
- **Custody (canonical_lp_principal_custody):** an `observed` pool fact with sampled positions
  and named custodians is rated from what they show: `good` when the sampled principal sits
  under a lock or program custody with no reachable withdrawal path; `potential_risk` when
  identified custody covers a minority of active liquidity or a custodian can withdraw, stating
  the covered share; `bad` when a single unlocked owner can remove most of it.
- **Exit depth (sellability_exit_depth):** the `quote_ladder` fact (read-only Jupiter quotes
  at the three `quote_sizes` policy sizes, selling into the leading pool's counter asset) is
  rated from its own fields, never from a row's `provider_price_impact_raw`: `good` when
  `largest_size_quoted` is true, `largest_impact_vs_smallest_percent` is at most 5 and a sale
  is verified (`sales.verified_receipts`) or the captured trade feed lists trades;
  `potential_risk` when that figure exceeds 5 or any row's `status` is not `quoted` (the row's
  `reason` names the missing capture or route), stating the figure; `unverified` only when no
  ladder fact exists (the `quote_capture_skipped` diagnostic or `quote-ladder.json` names why;
  cite any `public_quote` facts individually when quotes exist without a ladder). Quotes are
  provider claims at illustrative sizes, never execution; impact beyond them stays a stated limit.
- **Policies (utility_redemption_rights, token economics):** a published discretionary buyback,
  burn or revenue policy without on-chain execution evidence is `potential_risk` (discretion is
  the observed concern); with verified rebuys or burns it may be `good` for the executed part.
  It is `unverified` only when the policy page was never captured.
- **Assurance (development_disclosure):** audit or repository absence after the project's
  docs, site and repository links were checked is `potential_risk`; a matched audit of the
  deployed revision is `good`. Only an uncaptured site or refused repository is `unverified`.
- **Confidence axis, not rows:** team accountability, organic adoption, beneficial ownership and
  future price impact are inherently unverifiable; state them under Research confidence.

Review rendered reports for factual calibration as well as structural validity.
Use [decision review](decision-review.md), [strict profile](strict-report-profile.md)
and [completion](completion-and-delivery.md) when a judgment changes scope or strength.
