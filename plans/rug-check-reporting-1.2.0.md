# Rug-check reporting workflow 1.2.0

## Demonstrated coverage gap

The FRIES screen on 2026-09-06 led with “Insufficient evidence” despite valid mint
observations. The user then reported a successful Jupiter buy and sell. The prior
instructions required a blanket verdict and prohibited transaction reads. Desired
behavior: retain independently established findings, attribute the user's sale claim,
and allow bounded verification of exact supplied transactions. Original evidence in
runs/fries-20260906T175240Z is unchanged; no historical snapshots were edited.

## Implementation and review

Changed skill reporting and references, added sale-evidence guidance, and versioned
the reporting workflow separately. Raw collector engines, schemas, compatibility
verdicts, routing, paid-use gates and research rubric remain unchanged. No automated
transaction fetcher/decoder is introduced: the skill uses available read-only tools.
Reviewed the diff for contradictory blanket-verdict requirements and sale evidence
promotion. Confirmation requires matching finalized swap semantics and participant
asset changes, not receipt success alone. Missing route attribution stays explicit.

## Retained behavioral regression cases

These are manual instruction-level review cases, not automated execution benchmarks.
Inputs beyond the original FRIES mint packet/user claim are synthetic scenarios.

| Scenario | Required outcome | Review |
| --- | --- | --- |
| FRIES mint authorities absent + user says Jupiter round trip, no signatures | Report authority findings and user-reported sale; custody/concentration unchecked | Pass |
| Exact matching finalized sell, resolved participant debit/credit and swap | Sell confirmed with size, output, wallet and time; no token-wide safety claim | Pass |
| Verified sell, unverified buy | Sell confirmed only; no buy/sell confirmed claim | Pass |
| Quote or aggregator sell count only | Route available or reported activity; no execution confirmation | Pass |
| Successful transfer/burn/LP deposit with token debit | No confirmed sale without matching swap and output | Pass |
| Wrong network/mint, missing owner mapping, pending transaction, RPC timeout | Verification incomplete; no pass or honeypot inference | Pass |
| Verified sale plus separately evidenced material control risk | Lead with risk and retain scoped sale result | Pass |
| Known mint but provider unavailable | Checks unavailable; no identity-unresolved claim | Pass |
| Revoked authorities but unsupported extensions | Report revocation plus unresolved extensions; no complete control pass | Pass |

## Validation

Standard-library regression suites: research 31, EVM diligence 106, rug-check 17,
Solana diligence 22; all 176 tests passed.
No new Python behavior or wording-matching unit tests were introduced. Existing tests
retain collector safety, identity, deadline and paid-use regression coverage.
Skill quick_validate.py could not run in system Python because PyYAML is unavailable;
frontmatter and local reference targets were reviewed directly. No dependency installed.
No live transaction verification or latency benchmark was performed. No commit/push.
