# Solana tooling review — 2026-09-11

Requested scope: a five-minute research round to inform the ongoing parity
implementation, using public RPC for now. Research began **19:54:29 UTC**;
completion time is recorded below after the bounded synthesis. This is a primary
documentation/repository review, not a live RPC reliability test, token investigation,
tool installation or speed benchmark. All integration choices below are engineering
decisions, conditional on the relevant phase's schema and negative-fixture gates.

## Selected public capabilities

| Capability | Access and observed limits | Integration decision and evidence boundary |
| --- | --- | --- |
| Standard Solana JSON-RPC | Official public mainnet endpoint is documented as `https://api.mainnet.solana.com`. Published limits: 100 requests/10s/IP, 40 per method/10s, 40 concurrent connections and 100 MB/30s, explicitly subject to change. | Phase 3 primary raw evidence. Keep our stricter 3-request concurrency, byte ceiling and finite attempts; enforce lower advertised limits and backoff. Account batching preserves order, up to 100 per official method, with smaller local chunks. Verify genesis per run. [Cluster documentation](https://solana.com/docs/references/clusters), [multiple accounts](https://solana.com/docs/rpc/http/getmultipleaccounts). |
| PublicNode | Operator's public Solana page lists `https://solana-rpc.publicnode.com`, describes free access and separately offers archive access. Exact public method/rate/archive guarantees were not established. | Phase 6 registry: one permitted public RPC alternative after a genuine source failure, same ledger and new network verification. Do not infer archive entitlement or rotate endpoints to evade limits. [Operator page](https://solana.publicnode.com/). |
| DEX Screener | Exact network/token pools and exact pair routes; 300 requests/minute documented for those endpoints. Examples have no authentication header. Optional response fields and nulls are explicit. | Phase 6 primary indexed pool/activity discovery. Bind `chainId=solana`, exact mint and pair; use displayed volume/trades as attributed indexed activity, not verified executions or organic use. Missing fields remain missing. [API reference](https://docs.dexscreener.com/api/reference). |
| GeckoTerminal | CoinGecko explicitly documents a keyless public root. API docs say approximately 10 calls/minute and one-minute caching; an older support page says 30/minute, while current keyless guidance says dynamic IP throttling. | Phase 6 single market-data alternative: conservatively use at most 10/minute, captured source time and cache limits. Exact token→pool discovery and recent trade signatures can seed Phase 10 verification. Do not combine the conflicting rate statements into a higher allowance. [Keyless guide](https://docs.coingecko.com/docs/keyless-public-api), [API docs](https://api.geckoterminal.com/docs/index.html), [older support page](https://support.coingecko.com/hc/en-us/articles/22612838274841-Does-GeckoTerminal-have-an-API). |
| Raydium read and quote APIs | Current docs describe anonymous read APIs, 5–60s caches and separate quote GET endpoints; quote limit is 120/minute/IP. No wallet is required for the compute request. | Phases 6/7 pool leads; Phase 10 wallet-free `GET /compute/swap-base-in` estimates. Preserve route pools, exact mints/amounts, fees, output versus threshold and capture time. Validate raw account relationships independently. Do not call transaction-building, signing, forum-auth or sending paths. [Read API](https://docs.raydium.io/sdk-api/rest-api), [quote API](https://docs.raydium.io/sdk-api/trade-api). |
| Jupiter Swap v2 | Current rate documentation explicitly permits keyless 0.5 RPS (30/minute) on `api.jup.ag`. Detailed `/order` guide says omitting `taker` returns a quote without a transaction. The documentation index's “required taker” summary is less precise. | Phase 10 optional wallet-free quote route: GET `/swap/v2/order` without taker, payer, referral or key. At most one alternate route per quote need; bind route/fees/time and distinguish RFQ/API estimate from on-chain execution. No `/execute`, `/submit`, order creation or wallet fabrication. Keep API failure as unmeasured exit cost. [Rate limits](https://developers.jup.ag/docs/portal/rate-limits), [order guide](https://developers.jup.ag/docs/swap/order-and-execute). |
| Program Metadata / IDL Explorer | Official Solana-hosted docs expose HTTP IDL/latest metadata and security-txt reads, distinguishing canonical authority uploads, third-party uploads and legacy Anchor fallback. Hosted history can take up to 300s. Numerical rate/availability guarantee not found. | Phases 5/6 source/IDL/security-contact discovery, capped current revision only. Preserve program, metadata account, authority, source type and digest. Do not run history endpoint in ordinary mode, import generated code, equate IDL authority with upgrade authority, or treat publication as a verified build. [IDL API](https://idl.solana.com/docs). |
| OtterSec verification status | Public documented GET `/status/{program}` returns verification time, repository, on-chain and executable hashes. Repository describes update monitoring plus roughly five-minute refresh fallback. | Phases 5/6 optional third-party build-assurance record. Compare relevant current program identity/data where supported; disclose stale/missing/mismatched hashes. No verification-job submission or untrusted repository build. [Status API implementation/docs](https://github.com/otter-sec/solana-verified-programs-api), [Solana verification guide](https://solana.com/docs/programs/verified-builds). |
| Protocol-native pool/position data | Orca documents public pool/token analytics; Meteora's current DLMM Data API documents pool, position and wallet queries at 30 RPS. API data is indexed, not a coherent raw-account snapshot. | Phases 6/8/9 targeted pool/position leads that avoid full-program scans. Cap candidate pools and positions; derive custody and principal only from independently bound accounts. [Orca API](https://docs.orca.so/developers/api/overview), [Meteora DLMM API](https://docs.meteora.ag/developer-guides/dlmm/api-reference/overview). |

## Current source and decoder implications

Keep reviewed, immutable official interfaces as the runtime decoding premise.
The SPL monorepo has moved into program-specific repositories; use the current
[Token-2022 interface](https://github.com/solana-program/token-2022/tree/main/interface/src)
in Phase 4. Pin exact source revisions, layouts and licenses in that phase rather
than letting an unpinned main branch silently change the reader.

Raydium documents CPMM metadata via Program Metadata, CLMM via legacy Anchor and
AMM v4 via hand-maintained SDK layouts. It explicitly separates IDL update authority
from executable upgrade authority. Phases 5/7/8 must handle those paths independently;
an Anchor-only lookup failure is not evidence of unpublished source. [Raydium IDLs](https://docs.raydium.io/sdk-api/anchor-idl).

Pump's official current README describes appended PumpSwap virtual quote reserves
and new curve instructions/quote-mint fields. Phase 11 must pin and test these
versions, including nonzero virtual-quote fixtures and SOL-versus-other-quote
semantics. The README's rollout timing is a publication claim, not live deployment
proof. [Pump sources](https://github.com/pump-fun/pump-public-docs).

The Meteora `cp-amm` repository redirects to `damm-v2`; use the resolved official
repository for Phase 9 provenance. Orca's maintained program repository remains a
source for tick/position math and account relationships. [DAMM v2](https://github.com/MeteoraAg/damm-v2),
[Whirlpools](https://github.com/orca-so/whirlpools).

The Program Metadata repository declares Apache-2.0; the IDL-tools repository
declares MIT and Node/pnpm tooling. Its README still calls the security-txt package
scaffolded while hosted docs describe an API. Therefore treat that API as optional
and capability-test it in Phase 6; no mandatory SDK installation. [Metadata source](https://github.com/solana-program/program-metadata),
[IDL tool source](https://github.com/solana-foundation/idl).

## Useful tools kept optional or deferred

- **Helius enhanced/history RPC and DAS:** useful indexed transaction/account leads,
  but Helius examples require an API key; its enhanced methods are provider-specific.
  DAS also needs a supporting provider. Do not assume generic public RPC supports
  them or add setup/credit requirements. Retain as future explicitly authorized
  capability adapters. [Helius history](https://www.helius.dev/docs/rpc/gettransactionsforaddress),
  [enhanced parsing](https://www.helius.dev/docs/api-reference/enhanced-transactions/gettransactions),
  [DAS specification](https://github.com/metaplex-foundation/digital-asset-standard-api).
- **Solscan:** browser-visible exact transaction/account pages remain optional source
  leads. Current Pro API docs require keys/subscriptions; an old public-API landing
  page is not a proven anonymous API. No scraping/loading placeholder becomes a
  factual zero. [Current API docs](https://docs.solscan.io/api-access/solscan-pro-api-faq).
- **Carbon:** maintained Rust decoder/indexer framework with MIT licensing is useful
  for cross-checking known decoder edge cases, such as versioned instructions; it
  does not replace official pinned protocol sources. Do not add its runtime or
  Rust toolchain to this standard-library helper. [Repository guidance](https://github.com/sevenlabs-hq/carbon/blob/main/CONTRIBUTING.md),
  [release notes](https://github.com/sevenlabs-hq/carbon/releases).
- **Yellowstone/Geyser:** valuable streaming infrastructure, but ordinary bounded
  snapshots need neither an always-on stream nor gRPC dependencies. The project
  separates AGPL server licensing from Apache client/proto directories. Defer
  runtime integration, including paid stream access. [License boundaries](https://github.com/rpcpool/yellowstone-grpc/blob/master/LICENSING.md).
- **Rugcheck / wallet-cluster scores:** the public Swagger UI was a JavaScript shell
  in this read; current auth, schema and limits were not established. A tool's score
  or visual cluster cannot establish token safety or human common ownership. No
  mandatory score integration is selected. [Swagger entry](https://api.rugcheck.xyz/swagger/index.html).
- **Custom dRPC:** deferred by the user. No key lookup, configuration change or paid
  Solana call is part of this research or the current default workflow.

## Concrete follow-through and remaining checks

Phase 3: bounded standard RPC batching, original contexts and public rate windows.
Phase 4: pinned current token interfaces. Phase 5: metadata/IDL/build assurance
levels and authority separation. Phase 6: source capability registry, exact-mint
discovery, source ownership, one alternate, per-origin limits and explicit stale,
missing, denied or unsupported states. Phases 7–9: protocol-native discovery leads
plus independent account relationship/layout validation. Phase 10: optional Jupiter
v2 no-taker and Raydium compute quotes, with exact routes and no transaction paths.
Phase 11: updated Pump version/virtual-reserve/quote-asset fixtures.

For every integration, negative tests must cover wrong mint/network, missing and
zero values, changed schemas, stale observations, exhausted grants, 429/redirects,
and documentary claims promoted into raw execution. Public endpoint capability
smokes belong to the bounded later phase, not an unrecorded provider test here.
Exact software/license revisions will be checked before copying external code;
reading a public API specification does not install or vendor its SDK.

Several stale guessed documentation paths failed; canonical linked current pages
resolved the useful capabilities. No host-permission workaround, personal browser,
paid request, account creation, wallet or transaction was used. Tool choices improve
the planned evidence routes; they do not demonstrate rich live parity or latency.

Research synthesis completed **19:59:15 UTC**; elapsed **286.9 seconds**, against the requested 300-second research timebox.
