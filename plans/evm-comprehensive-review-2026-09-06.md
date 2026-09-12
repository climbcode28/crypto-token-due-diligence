# Comprehensive EVM diligence review — 2026-09-06

Outcome: reviewed and improved the canonical EVM skill, all its procedures, collector,
detectors, report validation/rendering and sibling routing interactions. Three independent
review lanes covered provider/runtime behavior, analysis/evidence correctness, and
source/risk coverage; the coordinator implemented instruction changes and reviewed the
combined result. A second independent collector review found a late-EOF timeout edge,
which was fixed and regression-tested before final verification.

This was maintenance, not an investigation of a particular coin. Existing uncommitted
provider/context changes were preserved. No historical evidence, engine snapshots or
frozen `history/` files were rewritten. No commits or pushes were performed.

## Provider-order conclusion

The skill selects the configured, already-authorized dRPC endpoint **first for its
matching network**. Current local policy maps the saved endpoint to Robinhood Chain
mainnet, chain 4663. It is not a universal endpoint for Base, Ethereum or Solana.
Public/other suitable RPC is fallback for genuinely absent matching configuration or
authorization, unsupported network/capability, or actual failed requests. Omitted flags
require context review; they are not provider failure. A request/deadline stop leads to
evidence review, not another provider with a fresh budget.

The collector reads the chosen environment variable and has no hardcoded public RPC
registry or silent endpoint switching. Its generic adapter default does not mean public
first: recognized dRPC hosts still receive dRPC authentication and paid-use gates. The
coordinator owns endpoint selection and fallback; every live investigation must verify
chain ID, runtime and fresh pins independently.

The current documented private exports were sourced with tracing disabled for the
authorized **offline** availability check. It returned `ready / run_collector`,
`provider_tested: false`, `network_requests: 0`. This confirms local invocation readiness,
not current endpoint health, archive support or token identity. No live paid calls were
needed for this maintenance review; credentials were not displayed or stored here.

## Findings and corrections

| Priority | Demonstrated issue or coverage gap | Correction and evidence |
| --- | --- | --- |
| P1 | Report log results could support a resolved finding despite wrong address/topic/block, removed events or duplicates. | Bind results to filters and known headers; validate receipt-log transaction identity. Adversarial bundle regressions reproduce rejection. |
| P1 | Redacted successful RPC payloads could remain cacheable or support detector/report positives. | Mark them unavailable, evict legacy redacted cache entries, preserve artifacts as gaps, and reject them as resolved detector/report support. Tests cover launch receipt/supply, fee predicate/runtime and positive summaries. |
| P1 | Source selection did not explicitly cover requested dashboards/social platforms; v2 fungible LP custody was absent. | Add source routing for onchain/explorers, Dexscreener, Defined.fi, Fomo, official website/X and linked GitHub; add v2 LP ownership/allowance/locker/fork checks. Primary documentation and independent scenarios reviewed. |
| P2 | Serial queries and no collection scheduling deadline threatened the research cutoff. | Up to four independent query reads, deterministic writes, receipt-before-trace barrier, scheduling/response timeout flags and final-pin time reserve. Barrier-based tests prove concurrent overlap without timing benchmarks. |
| P2 | Query budgets could consume required final pin checks; large log plans could spend on unusable headers. | Reserve recheck requests and preflight `1 + 2 × named pins` minimum before any RPC. Tests show usable partial evidence under an optional-query limit and zero attempts for impossible pin plans. |
| P2 | Duplicate failed reads could repeat across waves, and bounded stops could request fallback. | Memoize failed attempts within each run; later runs may retry under the original budget. Expose `limit_reached` and return `review_evidence` on deadline/request stops. |
| P2 | Malformed successful state values, contradictory same-height pins/block selectors and boolean-versus-integer response IDs could pass validation. | Validate wire shapes, exact ID types and pin/selector consistency. Failures stay failures; valid legacy rendering remains unchanged. |
| P2 | A response ending with a late EOF could bypass the response deadline. | Check monotonic time after every read before accepting EOF; regression uses complete JSON followed by a delayed EOF. |
| P2 | Parallel-agent instructions lacked query ownership and a shared budget/deadline. | One coordinator, up to three bounded lanes, shared packet/evidence, namespaced outputs, one repository-fetch owner and one final reconciler. Fewer lanes for short remaining windows. |
| P2 | Current supply screening omitted material vesting/unlocks/emissions; authority discovery omitted delegated accounts. | Check release/mint schedule and control without calling releases sales; conditionally inspect EIP-7702 delegate code plus authority storage/replacement power. |
| P3 | Holder-replay trigger invited unnecessary history scans; simulation reference incorrectly said all helpers never send RPC. | Start current concentration from candidates and pinned balances; reserve full replay for historical questions/discrepancies. Clarify offline helpers versus the authorized read-only collector. |

No justified arithmetic defect was found in the existing launch or fee rules. They use
integer atomic amounts, exact supply ratios, receipt deduplication, canonical boolean
decoding and explicit unknowns for missing historical supply. The review also retained
the v3 principal-versus-fee distinction, v4 PoolManager/PoolKey identity, creator-flow
commingling bounds, liability-aware reserve reconciliation and rate-based reward backlog
model. These are bounded calculations and procedures, not automatic protocol-wide audits.

## Source effectiveness and risk coverage

The new [source-routing reference](../skills/crypto-evm-token-due-diligence/references/source-routing-and-execution.md)
assigns each platform a fact it can supply and a stopping rule. It gives priority to exact
identity and material controls, custody, exit execution/depth, supply/unlocks, launch
allocations, proceeds/fees, rewards/backing/redemption, dependencies and project delivery.
Official claims and social/scanner leads must be reconciled with appropriate deployed
evidence. GitHub inspection starts with authenticated, commit-pinned relevant files;
builds and deep exploit work are conditional. No repository is a coverage gap, not fraud.

Dexscreener provides pool/quote-asset/indexed market discovery, not executable quotes.
Defined adds holder/maker/security leads when useful. Fomo supplies dated social/thesis
context only for supported, accessible exact-token pages. X/website evidence covers
announcements, continuity and material claims. Multiple dashboards can share upstream
data; redundant agreement is not automatically independent evidence. User-requested
sources receive an attempt or concrete access/applicability explanation. Login failures,
unsupported chains, missing APIs and timeouts never become passing checks.

Primary references reviewed:

- [Dexscreener API](https://docs.dexscreener.com/api/reference), [Defined holders](https://docs.defined.fi/defined-docs/defined-classic/defined-features/holders-summary), [Defined security scans](https://docs.defined.fi/defined-docs/defined-classic/defined-features/token-security-scan), [Fomo web](https://fomo.family/blog/announcing-fomo-web).
- [Uniswap v2 pools](https://developers.uniswap.org/docs/protocols/v2/concepts/pools), [v2 pair source](https://github.com/Uniswap/v2-core/blob/master/contracts/UniswapV2Pair.sol), [v3 manager source](https://github.com/Uniswap/v3-periphery/blob/main/contracts/NonfungiblePositionManager.sol), [v4 PoolId source](https://github.com/Uniswap/v4-core/blob/main/src/types/PoolId.sol).
- [OpenZeppelin vesting](https://docs.openzeppelin.com/contracts/5.x/api/finance), [EIP-7702](https://eips.ethereum.org/EIPS/eip-7702), [EIP-1898](https://eips.ethereum.org/EIPS/eip-1898), [Ethereum JSON-RPC](https://ethereum.org/developers/docs/apis/json-rpc/), [JSON-RPC specification](https://www.jsonrpc.org/specification).

## Independent forward tests

These are hypothetical reasoning exercises, not live token evidence.

1. Robinhood target with existing authorized dRPC and omitted flags: reviewer selected
   context review and corrected authorized invocation, with no premature public fallback.
   Unsupported Fomo and login-gated X remained explicit gaps; independent source work
   proceeded while identity/pins were prepared.
2. Base v2 token with a linked repo, vesting cliff, same-runtime lockers with different
   storage, 180 seconds and 40 total attempts left: reviewer did not reuse Robinhood's
   endpoint. It preserved 120 seconds for delivery, used fewer lanes and a sub-60-second
   collection window, kept a single shared request allowance and separate locker storage
   checks, and omitted full replay/build work. Unfinished broad surfaces remained unknown.

The forward pass identified imprecise Dexscreener “quotes” wording and possible duplicate
repository fetching. Both were corrected. It also checked that CLI timeout flags were
actually exposed and passed through after implementation.

## Verification and release

Final combined verification passed **242 tests**: EVM **170** (2.716 seconds), research
**31** (0.958 seconds), rug-check **18** (1.831 seconds), Solana **23** (1.827 seconds).
The EVM baseline had 133 tests; this review adds 37 net cases. The supplied skill validator
returned **Skill is valid!**; local links in 23 Markdown files resolved, release JSON and
code constants agreed, and `git diff --check` was clean. Temporary validation-only PyYAML was installed under `/tmp`
because the supplied skill validator requires it; project helpers/tests remain standard
library only and no project/system package configuration changed.

- EVM: `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s skills/crypto-evm-token-due-diligence/tests -q`.
- Research, rug-check and Solana: the three corresponding README suite commands.
- Supplied `skill-creator/scripts/quick_validate.py` against the canonical skill.
- Changed documentation links, JSON release metadata/constants and `git diff --check`.

Versions: workflow **1.3.0**, backend **2.1.0**, reporting **1.1.1**, launch/fee rules
**1.0.1**. The rule patches exclude redacted evidence; arithmetic semantics remain the
same. Availability schema 2 and collection/case/cache/bundle schema 1 remain compatible.
Malformed evidence previously accepted is now rejected; valid legacy Markdown remains
byte-identical. Old artifacts use their preserved engines for historical reproduction.

Limits: this establishes reviewed instruction coverage and implemented offline invariants.
It does not measure live detection accuracy, provider honesty, indexer completeness or
end-to-end research latency. Scheduling/socket checks cannot forcibly interrupt OS/DNS
stalls; numbered-pin acquisition/rechecks remain serial. Block-by-block history collection
is still expensive, so bounded discovery and targeted receipts are preferred. Validators
cannot authenticate source correspondence, economic truth or whether a researcher omitted
a material surface. A 5–10-minute run may correctly finish Partial when evidence is missing.

## Files changed by this review

- `README.md`, `HANDOFF.md`, this review record.
- `skills/crypto-evm-token-due-diligence/SKILL.md`.
- `assets/backend-release.json`, `assets/reporting-release.json`, `assets/workflow-release.json` under that skill.
- `references/source-routing-and-execution.md` (new), `core-surfaces.md`, `platforms.md`, `proxy-bytecode.md`, `holder-replay.md`, `simulation.md`, `deterministic-backend.md`, `bundle-format.md` under that skill.
- `scripts/backend_common.py`, `rpc_collect.py`, `detect.py`, `validate_bundle.py` under that skill.
- `tests/test_collector_runtime.py` (new), `test_optional_rpc.py`, `test_backend.py`, `test_bundle.py`, `test_reporting.py` under that skill.

Other entries already present in `git status` at review start belong to the earlier
provider repair, including `AGENTS.md`, provider-context helper/tests, sibling collector
edits and their release records. They were preserved; they are not new work attributed
to this review.

Suggested commit message: `Improve EVM diligence coverage, parallel execution, and evidence validation`
