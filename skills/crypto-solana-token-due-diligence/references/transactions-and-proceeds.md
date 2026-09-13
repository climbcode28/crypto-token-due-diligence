# Historical execution and proceeds

Use `solana_transactions.decode_transaction` on captured `getTransaction` and
matching historical `getBlock` packets. Legacy and version 0 need complete static
and returned loaded keys, exact requested first signature, successful metadata,
native/token balances and inner-instruction tables. Never fill historical keys
from today's address lookup table. Failed transactions retain their actual fee
and no persisted token effects. Missing interpretation stays a gap.

Each effect retains its transaction evidence ID, block evidence ID, slot, program,
mint where established, account roles, exact atomic quantity and outer/inner
locator. Token initialization, authority changes and protocol position units are
separate from transfers. Requested position ranges are not current ownership or
principal. Full evidence digests and network identity remain bundle obligations.
The wire semantics follow [Solana transaction structures](https://solana.com/docs/rpc/json-structures)
and [getTransaction](https://solana.com/docs/rpc/http/gettransaction); immutable
instruction source revisions/hashes are in `assets/layout-sources.json`.

`verify_sales` and `verify_rebuys` accept at most ten distinct historical receipts
(start's two plus the `pool_activity` presets'); a repeated signature is one execution
plus a row gap. A verified sample
requires one supported direct outer swap at the exact pool, two matching SPL inner
transfers, actual source/output ownership by the same observed key, matching token
balance deltas and instruction amount/thresholds. Fee payer and signer alone never
establish the seller. Nested/multihop routes, extra account movements, Token-2022
fee/hook routes and partial fills retain narrower effects. Supported instruction
roles cover the tested Raydium AMM v4/CPMM/CLMM, Orca and Meteora variants; unknown
versions and remaining-account layouts do not inherit those capabilities.

WSOL output is gross token consideration. Native proceeds additionally require
ordered account initialization/closure, observed ownership, actual seller native
delta, account funding/refunds, seller-paid network fee and other native transfers
to reconcile. Existing balances and rent refunds are not sale proceeds. An
unexplained native movement leaves net proceeds unknown without erasing a matched
swap. Cost basis is absent, so profit always remains unknown.

A router custody leg is verified when its input account is filled by exactly one transfer
from a wallet's account before the leg, or its output account drained by exactly one
transfer to a wallet's account after it, each at the leg's exact amount, with the other
side either the matching custody transfer of the same wallet or a hop into another decoded
leg. When the leg's own accounts are owned by a router (not the trader), that far-end
wallet is the beneficial trader and must have signed; it is reported as the seller (or
buyer) and the router authority as the `spending_owner`. When the trader owns and signed
for the leg's own accounts, the same-amount funding or forwarding transfer is a router
serving the trader, not a change of owner: the trader stays the seller and the funding
accounts are still recorded under `custody`. A router that keeps the proceeds, sells its
own inventory to a wallet, or hands a router-owned leg to an account whose owner did not
sign is not a wallet's sale. A pump.fun
curve trade is a supported swap at the curve: a v2 trade with a token quote is verified
exactly like a pool leg (the curve's base and quote holdings are its vaults; protocol,
buyback and creator quote accounts are fee sinks; the user's volume-accumulator account a
rebate), and a trade with a SOL quote (every legacy trade, and a v2 exact-input sell or
exact-output buy whose quote is wrapped SOL; an exact-quote-in native buy is not yet
supported) is reconciled from the lamport balance deltas of the curve, the fee
recipients and the trader, with the trader's own explicit native flows netted out
(`quote: native_sol`, proceeds under `native_proceeds`); its base leg is also checked
against both accounts' historical token balances. Proceeds the trader re-wraps into a
later decoded leg of the same route are reported as `converted_within_route`, otherwise
`native_lamports_to_wallet`. A lamport residual the reconciliation cannot itemize (for
example a cashback rebate paid inside the program) refuses the receipt and names the
residual; legacy layouts do not name a rebate account, so such receipts stay unverified
rather than mis-stated.

In an aggregated route, a hop into the leg's input account before the leg (bought
elsewhere, then sold at this pool) is tolerated and the sale at the exact pool still
verifies; a hop back into the input account after the leg is a round trip and is
rejected. An intermediate account is tolerated only for hops into or out of another
decoded swap's vaults; any other touch of the leg's accounts (a stray transfer, an
authority change) refuses the leg. This is a deliberate boundary, not a gap. Receipt sample count and indexed market activity are independent. The sale and rebuy
facts verify every sampled receipt at a known pool, start's two and up to four per
`pool_activity` preset, at most ten; a handful of receipts are neither the market's
entire sell count nor proof that everyone can exit.
Observed freeze, fee and other restrictions remain visible alongside activity.
