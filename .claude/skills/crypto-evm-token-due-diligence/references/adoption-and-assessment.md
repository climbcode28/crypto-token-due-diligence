# Adoption, maturity and calibrated assessment

Load for broad diligence or a focused question about market establishment. This screen
shares the original request budget and deadline; reuse the existing liquidity and project
lanes. It does not start a price-prediction exercise or revive the retired market-scoring rubric.

## Four independent conclusions

Assess technical/custody exposure, credibility/maturity, token economics, and research
confidence separately. Use a concise qualitative synthesis in the verdict/main reasons
and evidence-linked summary findings; retain the eleven technical dimensions. No blended
score or count of colored flags should average a critical issue away.

- **Technical/custody exposure:** identify observed powers, defects and verified mitigations.
  Missing LP ownership or an unfinished history check is missing evidence, not a finding
  of removable liquidity or creator misconduct. A critical unknown may still prevent a
  conclusion under the user's requirements; state that dependency directly.
- **Credibility/maturity:** distinguish public team accountability, demonstrated delivery,
  measured traction, sustained use, and operating history. Use
  [project-credibility.md](project-credibility.md) for the team/record evidence.
  A token may be a leader in a young ecosystem while still having little time under stress.
  Qualifiers such as emerging or established need a declared peer group, interval and
  concrete basis. There is no universal age, volume or TVL cutoff for establishment; say
  what is established and relative to whom. No ranking or organic-use claim follows from
  a ticker or popularity alone. Credit verified accountability and sustained delivery
  without treating them as proof of technical safety or letting them erase adverse evidence.
- **Token economics:** determine how use can benefit this exact token, whether the mechanism
  operates, who can change it, dilution/unlocks, and what the observed valuation assumes.
  Platform success, token turnover and holder benefit are different propositions.
- **Research confidence:** state which decision-changing checks are resolved and which are
  unavailable, contradictory or not performed. Confidence attaches to claims and coverage;
  don't turn missing evidence into an adverse likelihood or fabricate a probability.

For example: "Adoption is supported by sustained measured use; token controls are bounded;
LP custody remains unverified; the assessment is partial." This can be more useful than
an overall score. Unknowns remain distinct even for obscure tokens; popularity is not the
condition for receiving neutral treatment.

## Bounded adoption screen

Use accessible exact-target market data, original indexer methodology, dated project
records and public discussion. Choose the few measures that answer the user's question.
Record retrieval time, measurement window, identity, denominator, source and limitations;
distinguish source-reported figures from independently reconciled results.

| Factor | Evidence that earns context | Limits and contrary evidence |
| --- | --- | --- |
| Valuation | Circulating market cap and FDV with explicit supply/burn convention and price time; compare with durable activity when meaningful | Market cap is a valuation, not deposited capital or executable liquidity. Higher valuation may price in more success. Conflicting supply conventions need reconciliation before ratios or ranks. |
| Market access and depth | Sustained trading, verified venues, size-dependent exit quotes, liquidity persistence and spread | A listing is a distribution observation, not an audit. Pool TVL and turnover do not establish LP custody or the ability to exit a particular size. |
| Product adoption | Active/returning users, executed usage, fees/revenue with definitions, integrations and consistent same-window peer comparisons | Wallets are not people. Incentives, bots, wash activity and common upstream indexers can distort counts. Platform fees are not automatically protocol revenue or holder cash flow. |
| Social participation | Distinct active authors, durable discussion, distribution across communities, disclosed promotion and conversion into product use | Raw followers, reposts and one viral week establish attention at most. Examine sampled duplication/incentives before asserting organic engagement; hype may also increase crowding. |
| Operating maturity | Age of this deployment/version, duration under meaningful use, adverse-market periods, withdrawals, incident handling and disclosed admin actions | Calendar age, absence of incidents in an incomplete search, brand age and current market rank do not demonstrate robustness. Changes of version/control can reset relevant assumptions. |

Good may label a bounded positive such as independently observed repeat use or a named
indexer's captured usage statistic, provided the proposition explicitly identifies that
measurement. An indexer capture can directly support "source reports X"; it does not
prove organic demand or source accuracy. Do not attach unrelated token runtime as the
direct proof of platform activity. A platform claim needs its actual contract/project
subject and participants; confirm the platform's association with the target token.

**Stop:** enough context to qualify traction/maturity, a material contradiction, or the
documented source-coverage boundary. A timed lane handoff leaves feasible required
checks pending for the coordinator. Lack of analytics or social access is Unverified,
not weak adoption. Do not expand the investigation merely to fill a scorecard.
Complete a bounded team/operating-history and adoption first pass using existing sources;
then rank technical and contextual follow-ups by their effect on the decision. A known
critical technical exposure takes priority; repeated inconclusive lookups must not consume
the entire credibility assessment. Record actual attempts and remaining gaps under
[stopping and escalation](stopping-and-escalation.md).

## Token benefits and expectations

Start from the actual investment premise and dated project claims. A token does not
automatically owe dividends, redemption, governance or an immutable revenue entitlement.
Affirmative evidence that a mechanism is not part of the product may justify neutral
not-applicable coverage. A skipped rights check cannot.

For relevant fee, buyback, burn, distribution or redemption claims, record:
claim → exact deployment/version → authority/configuration → observed execution → holder
effect. Separate an announced policy, discretionary operator practice, code-enforced
commitment, source-reported payout and independently reconciled payout. Buyback inventory
is not necessarily burned, and a burn-address balance alone does not prove buyback origin.
Use [fees-and-proceeds.md](fees-and-proceeds.md), [reward-accounting.md](reward-accounting.md)
and [dependencies-redemption.md](dependencies-redemption.md) when needed.

Disclosed discretionary buybacks are ordinary policy terms and an operator dependency,
not an automatic adverse finding. Explain how holders benefit if the policy continues,
who can change it, and what execution is or is not evidenced. Present neutral terms in
the synthesis without forcing them into Good or Potential Risk. Do not invent a user
requirement for immutable payouts or an entitlement the project never promised.

An adverse economics finding needs a concrete mechanism and holder consequence: observed
diversion or nonpayment, a reachable harmful capability over holder assets, a contradicted
commitment, or a mismatch with the user's explicit requirement. Discretion over future
voluntary buybacks is distinct from power to seize assets or redirect an enforceable
entitlement. A verified harmful capability can be material before it is exercised; a
public team or good record does not neutralize it. Separate missing payout reconciliation
from evidence of missed payouts. Rate the exact exposure or mismatch and show what would
change the assessment; do not mistake absent equity-like rights for fraud.

## Reporting and evidence contract

Use `adoption_and_maturity` and `token_economics` summary topics for these findings.
They are reading categories, not additional risk dimensions. Link adoption findings to
the relevant development/disclosure or dependency coverage, and token economics to the
specific utility, treasury, rewards, concentration or other dimension actually affected.
A bounded positive can coexist with an unknown broader dimension; do not manufacture a
dimension pass to display useful context.

Use **⚪ Unverified** only for a pure coverage gap: `claim_type: coverage_gap`,
`evidence_type: unknown`, `confidence: unknown`, `impact: unknown`,
`adverse_severity: unknown`. Keep observed concerns and adverse inferences in the assessed
findings section with their evidence/confidence. Split mixed propositions. Review prose:
the validator cannot detect a concealed adverse assertion mislabeled as missing research.

Every high/critical adverse finding remains visible regardless of valuation, social
traction or maturity. A generic technical unknown cannot substitute for a specific harm.
