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

`verify_sales` accepts at most two distinct historical receipts. A verified sample
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

Receipt sample count and indexed market activity are independent. Two receipts
are neither the market's entire sell count nor proof that everyone can exit.
Observed freeze, fee and other restrictions remain visible alongside activity.
