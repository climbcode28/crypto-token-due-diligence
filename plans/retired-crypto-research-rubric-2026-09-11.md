# Rating Rubric (v2.1) — Crypto Research

This is the canonical grading reference for Crypto Research, adapted from the supplied
v2.1 rubric. Evidence comes before grades; scenarios are pre-registered;
Pass 2 is adversarial; missing data lowers confidence rather than inviting fabrication.

## 1. Identity first

Accept name, ticker, chain, contract/mint, or any combination. Contract/mint is the
primary anchor when one exists. Verify name, ticker and chain against the canonical
contract/mint before DEX analysis. Native assets may be identified as native rather
than by contract. Never merge assets that share a ticker.

**Unresolved identity = no grade.**

Record:
- canonical name and ticker
- chain
- contract/mint or `native asset`
- primary market/pair used for price and liquidity
- asset class A / B / C
- data timestamp

## 2. Asset classes

- **A** — BTC/ETH or a large, liquid, perp-enabled major.
- **B** — liquid alt/protocol token with meaningful CEX/DEX/on-chain data.
- **C** — new, DEX-native, micro-cap or memecoin.

Missing derivatives for Class C is **N/A, not a penalty**.

## 3. Market-regime pass

Run before asset conclusions. Check BTC/ETH trend and relative strength, alt
breadth/rotation, leverage/crowding, liquidation asymmetry, spot/DEX liquidity and
volume, on-chain/cycle context, sentiment, and dated catalysts.

Signal speed matters:
- funding/OI/liquidations, price-volume structure, DEX flows and fresh sentiment:
  mainly 1–3D / 1–3W
- breadth, narrative rotation, unlocks, listings, governance/protocol catalysts and
  chain flows: mainly 1–3W / 1–3M
- MVRV/Rainbow: slow BTC context only
- Alt Season: breadth context, not an intraday trigger
- Fear & Greed: sentiment, not automatically contrarian
- liquidation heatmaps: possible liquidity concentrations, not guaranteed levels
- OI dominance: interpret only with price, funding, liquidations and volume

For Class C, BTC is a background shock variable at 1–3D. Token-specific evidence may
reduce regime weight toward ~5%. Regime influence rises at 1–3W and 1–3M, and during
severe BTC/liquidity shocks.

## 4. Six score components

Score each 0–4 before assigning horizon letters:

1. **Regime alignment**
2. **Price / volume / relative strength**
3. **Derivatives positioning** — N/A where genuinely inapplicable (e.g. no meaningful
   derivatives market), especially Class C; inaccessible applicable data is an unknown
4. **Liquidity / market quality**
5. **Catalyst / narrative velocity**
6. **On-chain / tokenomics / fundamental support**

Default weights:

| Class | Regime | Price/Vol/RS | Derivatives | Liquidity | Catalyst | On-chain/Tokenomics |
|---|---:|---:|---:|---:|---:|---:|
| A | 20% | 25% | 20% | 15% | 10% | 10% |
| B | 15% | 20% | 15% | 15% | 15% | 20% |
| C | 10% | 20% | 0% | 30% | 20% | 20% |

Reweight N/A components proportionally. For Class C at 1–3D, regime may be reduced to
~5% only when token-specific evidence is unusually strong; redistribute the removed
weight across the remaining applicable components.

Unavailable applicable inputs do not automatically become N/A, zero or neutral scores.
Score a component only if remaining evidence supports it; otherwise withhold the affected
horizon and Overall grades. Missing slow data for Class C can coexist with a supported
component score and lower confidence under the Provisional high-grade rule below.

These are default class weights across all three tactical horizons. Horizon sensitivity
comes primarily from the horizon-appropriate evidence scored inside each component,
not from ad hoc weight changes. Do not change component weights by horizon except for
the explicit Class-C 1–3D regime adjustment or a separately documented methodology
revision. When N/A reweighting is material, disclose the missing component and effective
weight shift.

## 5. Grade bands

Weighted component score is on a 0–4 scale:

| Score | Grade |
|---:|:---|
| ≥3.75 | A+ |
| ≥3.50 and <3.75 | A |
| ≥3.25 and <3.50 | A- |
| ≥3.00 and <3.25 | B+ |
| ≥2.75 and <3.00 | B |
| ≥2.50 and <2.75 | B- |
| ≥2.25 and <2.50 | C+ |
| ≥2.00 and <2.25 | C |
| ≥1.75 and <2.00 | C- |
| ≥1.50 and <1.75 | D+ |
| ≥1.25 and <1.50 | D |
| ≥0.75 and <1.25 | D- |
| <0.75 | F |

These bands are calibration aids, not a substitute for the evidence. Horizon grades
must be computed independently from horizon-appropriate inputs.

Overall horizon weights:
- 1–3D: 25%
- 1–3W: 45%
- 1–3M: 30%

## 6. Scenario pre-registration

Before grades, write bear / base / bull scenarios for each horizon.

Default probabilities: **30% / 45% / 25%**. Deviate only when dated technical,
derivatives, sentiment, catalyst, liquidity or on-chain evidence supports the change.
Do not reverse-engineer scenarios to reach a grade.

Ranges generally widen with horizon. Illiquid/new tokens need wider ranges and lower
confidence. State the assumptions carrying each scenario.

After scoring, run a scenario/grade coherence check. If the mechanical grade materially
conflicts with the pre-registered scenario distribution or ranges, revisit the evidence
scores or explain the conflict; do not rewrite scenarios after the fact merely to fit
the grade.

## 7. Class-specific evidence

### Class C / new tokens
Inspect the deepest legitimate pool(s), pair age, liquidity, 1h/6h/24h
price-volume-transactions, FDV vs circulating cap, supply/unlocks/emissions,
holder/wallet concentration when verifiable, LP/market-maker concentration,
contract/admin/bridge/governance risks, official links, exchange dependence, and
organic vs promotional attention. Flag volume that looks suspicious relative to
liquidity, transactions or wallet activity.

Absence of an observed red flag is not proof of safety.

### L1/L2/DeFi/protocol tokens
Add TVL direction, stablecoin liquidity, DEX/perps volume, fees/revenue, token-holder
value capture, credible usage, emissions/unlocks, governance, treasury/incentives and
competitive share.

Protocol success does not automatically imply token value capture.

## 8. Provisional high grades

A new/Class C token may receive a **Provisional A-range** grade despite incomplete
holder/supply/unlock/history data only when:
- identity is verified;
- at least two independent non-social market signals are unusually strong; and
- one additional confirming lens supports them.

Social strength alone cannot create an A-range grade. Confidence remains below High.
State what remains unverified and what would downgrade or invalidate the setup.
Confirmed A-range requires Pass 2.

## 9. Confidence discipline

Use High / Medium / Low.

- stale or unverified short-term price/liquidity: no A-range 1–3D
- missing critical inputs lowers confidence
- conflicting high-quality sources must be surfaced
- inaccessible/paywalled dynamic data is marked unavailable or replaced with a
  transparent fallback

For A/B assets, do not normally exceed broad regime by more than two notches on
1–3D/1–3W without idiosyncratic evidence. Do not mechanically apply that cap to
Class C at 1–3D.

## 10. Pass 2 and revisions

Pass 2 attempts to break Pass 1. Verify supply/unlocks, holders, announcements,
governance, token economics, exploit/bridge/admin risk, listings, wallet anomalies,
market-maker dependence, sentiment reversal and technical invalidation.

Write the strongest bear case. If evidence changes an input or scenario, revise it
and state the diff. Otherwise mark **Confirmed**. End with unresolved/conflicting
evidence.

Pass 1 should be labeled **Provisional** unless a Pass 2 adversarial verification has
already been completed. Reserve **Confirmed** and **Revised** for Pass 2 outcomes.
Confirmed A-range always requires Pass 2.

An incomplete Pass 2 remains Provisional. Partial or blocked required chain-specific
diligence also keeps the integrated report Provisional, with coverage limitations stated.

## 11. Output contract

Multi-asset:
`Rank | Asset | Overall | 1–3D | 1–3W | 1–3M | Setup | Catalyst | Risk | Confidence`

Single asset:
identity + compact scorecard, horizon views, scenarios, catalysts, risks and
invalidation.

Every report carries:
- market-sensitive data timestamp
- Pass status: Provisional / Confirmed / Revised
- facts separated from inference
- unresolved/conflicting evidence
- no directive buy/sell/hold language
- no guarantees or personalized financial advice
