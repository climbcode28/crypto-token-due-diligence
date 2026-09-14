# Size-dependent exits

`solana_quotes.size_policy` chooses three illustrative exact integer inputs.
Explicit user quantities take priority. Otherwise use $100/$1,000/$10,000 equivalents
only with exact mint/genesis-bound captured price (the earliest captured), decimals and
an explicit fresh timestamp, fresh as of the first quote capture once quotes were attempted
(so a later mint re-read never restates the sizes); disclose the source and rounding. Without that evidence use disclosed
token quantity probes. No schedule establishes affordability or the user's holding.

Local estimates currently support the pinned Raydium CPMM SPL configuration only:
one atomic full pool/config/mint/vault/Clock sample, recognized fees, enabled swap,
initialized vaults, passed opening time, and integer capacity checks. Input/output
creator-fee modes, ceiling fee deductions, floor output, and protocol/fund shares
follow the pinned implementation. Protocol/fund fees are components of the trade
fee, not extra deductions. Unknown fee state, Token-2022 execution controls and
missing concentrated tick/bin traversal refuse an estimate; vault balances never
substitute for executable concentrated depth.

Keep expected output, minimum output after slippage, modeled cost against the
pretrade reserve spot ratio, and individual fee components distinct. This model
includes curve/fee/rounding cost and excludes transaction execution and gas. A
modeled quote is not an observed sale or guarantee.

`start` captures the credential-free Jupiter lite quote (`GET
https://lite-api.jup.ag/swap/v1/quote`, no taker) once per illustrative size, selling the
mint into the leading pool's counter asset (WSOL for a launch curve); the importer types
each as a `public_quote` fact and derives one `quote_ladder` per source and output mint:
output per input unit at each size, each size's impact versus the smallest quoted size and
the largest size's impact, with a size the provider could not quote named as a gap. The
ladder compares quoted outputs; the provider's own `priceImpactPct` is retained verbatim and
separately. Rate it with the exit-depth rule in
[reporting-scenarios.md](reporting-scenarios.md#rating-rules).

Optional captured public GET routes:

- [Jupiter Swap V2 order](https://developers.jup.ag/docs/api-reference/swap/order):
  omit taker/wallet so no transaction is assembled. Preserve `outAmount`,
  `otherAmountThreshold`, route/fee claims, optional context and capture time.
  Current `priceImpact` is percentage points; convert to a rational fraction by
  dividing by 100. Pricing returned with an execution error retains that error.
- [Raydium Trade API](https://docs.raydium.io/sdk-api/trade-api):
  `GET /compute/swap-base-in` with `txVersion=V0`; validate the V1 envelope, BaseIn
  mode, exact mints/input/slippage and bounded connected route. Preserve its raw
  impact field without assuming an undocumented cross-version unit convention.

Use the shared retained capture/session path; never build, sign, simulate or send
a transaction. Documentation and synthetic schema fixtures establish parser
capability, not live service availability. Optional keyed/blocked endpoints remain
gaps and do not disable receipt observations. Quote-source claims are not on-chain
corroboration. Reuse includes the original context/time; do not present old quotes
as fresh executable offers.
