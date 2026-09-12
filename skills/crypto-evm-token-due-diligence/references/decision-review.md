# From evidence to a useful decision

Read at broad intake and again before freeze. This is an assessment contract, not a
new score, risk dimension, research budget or requirement for trustless design.

## Preserve the question

A ticker/address with no narrower question means general diligence: assess observed
exposure, credibility, maturity and holder economics, then deliver a completed assessment with specific evidence limits.
It does **not** mean “prove impossible to rug”, “require immutable buybacks” or “approve
my position size”. Record explicit user requirements with the user's actual words.
Default to an empty requirement list. Label analyst-selected exit sizes illustrative;
they are research probes, not user acceptance conditions.

Keep three questions separate: what harmful behavior or capability is evidenced; what
credible delivery/accountability is evidenced; and what the investigation could establish.
A shortfall in the third is not an answer to the first. Per-surface partial coverage describes what evidence is established. Research completion
is separate: finish feasible scoped work before delivery, while retaining documented
externally unavailable facts. See [completion and delivery](completion-and-delivery.md).

## Calibrate the conclusion in both directions

- **Supported findings with stated limits:** affirmative, bounded findings exist. Say
  which strengths matter and which conclusions remain open. “No material adverse
  mechanism identified in the inspected token code” requires that actual inspection;
  it cannot describe unchecked lockers or the whole project.
- **Evidence-backed concerns:** name the observed or inferred mechanism and holder
  consequence. Keep capability, likelihood, intent and realized loss separate. Severe
  powers remain prominent even when the team is public and the product widely used.
- **Insufficient evidence:** an honest abstention when available evidence cannot support
  an overall assessment. A packet of gaps supports neither “clean” nor “avoid”.
- **User requirement not established:** an explicit condition cannot yet be evaluated.
  Say which condition and why. A proven breach instead belongs in assessed concerns.

Do not issue a global “avoid”, “hold off”, “not rug-resistant” or position-sizing
recommendation solely because a source failed or the research window ended. A specific
claim may remain unestablished without an adverse token verdict. Conversely, failure to
find an adverse mechanism is no guarantee, and popularity does not fill evidence gaps.
Do not force balance, a favorable label or a target count of positive findings.

Every adverse finding must explain **mechanism → holder consequence**, with its basis:
observed behavior, reachable harmful capability, contradicted claim, adverse inference,
or mismatch with an explicit user requirement. Ordinary discretionary buybacks, absence
of unpromised dividends, nonzero administration and an unfinished audit search do not
by themselves earn adverse severity. Describe ordinary operating terms neutrally in the
economics synthesis; mark a concern only when a particular exposure or mismatch warrants
it. A disclosed power to seize holder funds can still be materially adverse.

A public identity can support accountability and a relevant track record can inform
judgment about likely behavior. Neither removes executable powers. An anonymous team
with identical technical evidence receives the same technical findings; credibility
and maturity may differ on their own evidence. See [project credibility](project-credibility.md).

## Write the reading layer first

Lead with a concise answer to the actual question and the strongest evidence behind it.
Show four independent conclusions before the appendix as four separate bullets, one or
two sentences each: technical (token/liquidity) exposure; credibility and maturity; token
economics; research confidence. Never run them together as one paragraph. Name confirmed
strengths as directly as concerns. Do not bury all favorable evidence under “contrary”.

A completed report needs **no action list** by default. Perform feasible research before
delivery; describe truly unavailable evidence and its consequence in coverage. At most
three actions may address observed concerns, explicit user requirements or use of the
completed findings. Do not append a research backlog or a request for ordinary exports.
The full coverage/stopping ledger still retains every surface and severe finding.

| Basis | Appropriate action | Boundary |
| --- | --- | --- |
| Unfinished locker review | Verify withdrawal/approval paths to answer whether this position is irreversibly locked; bounded paths strengthen that claim, reachable removal qualifies it | No assertion of removable liquidity and no automatic investment veto |
| Demonstrated seizure power | Explain the exposure and a proportionate mitigation; removal of that power would change the assessment | Doxxing and adoption cannot erase the power |
| User explicitly requires a $50k exit | Obtain that quote/execution evidence before answering the user's size condition | Missing quote does not establish a honeypot |
| Historical sale verified, large quotes missing | Credit the historical execution; distinguish the unmeasured current size limit | Neither “currently sellable at any size” nor “cannot sell” |
| Declared scope fully resolved | State how to use the bounded result and what change would invalidate it | Do not invent additional missing research or issue a blanket safety certificate |

Summarize shared access failures once. Preserve separate coverage records without making
one unavailable source look like several independent adverse signals. Rank follow-ups
by how likely they are to change this decision, not merely by ease of collection.

## Versioned decision review

New assembly requires `decision_review_version: 2` and a `decision_review` handoff.
Older reports remain readable without a retrospective claim. Keep these fields concise:

- `requirements`: array of `{id, text, user_quote}`; empty by default. Source quotation
  must support the actual requirement; an analyst assumption is not a user quotation.
- `verdict`: `{kind, scope, finding_ids, requirement_ids}`. Kind is
  `findings_with_limits`, `adverse_findings`, `insufficient_evidence` or
  `requirement_unverified`. Scope names the bounded question. `report_text.verdict`
  supplies the matching plain-language answer; the renderer also displays a fixed label.
- `synthesis`: exactly four `{axis, conclusion, finding_ids, coverage_dimensions}`
  entries. Axes: `technical_exposure`, `credibility_maturity`, `token_economics`,
  `research_confidence`. References must belong to the named coverage dimensions.
  Unknown axes stay explicit; runtime identity is not proof of public team credibility.
- `actions`: zero to three ordered `{id, kind, action, reason, finding_ids,
  coverage_dimensions, requirement_ids, changes_view_if}` entries. `investigate` is permitted only in an internal unfinished checkpoint, never in a
  completed report; feasible investigation must be executed first. Empty actions are
  valid, while serious adverse findings still require mitigation. `mitigate` references an adverse
  finding and concern rating; `requirement_gate` additionally requires an explicit user
  requirement. `use_within_scope` needs affirmative findings and complete declared
  coverage for that action. `changes_view_if` names the resolving evidence and the
  consequence of favorable/adverse results or changed state. Empty requirement lists
  are valid except for requirement-based gates.

Under this version, every adverse finding also carries
`concern: {basis, mechanism, consequence, requirement_ids}`. Basis is `observed_behavior`,
`reachable_capability`, `claim_mismatch`, `adverse_inference` or `user_requirement`.
The last requires explicit requirement references; inference retains its evidence class
and inference basis. Even an adverse inference needs a direct observed lead at its
subject; identity-only evidence and failed requests cannot supply that lead.
Missing evidence cannot be promoted to adverse evidence by adding this object.
All high/critical adverse findings remain in the verdict basis, synthesis, assessed
summary and mitigation actions. Several severe findings may share a coherent action.

The validator checks structure, source links and declared decision/evidence consistency.
It cannot authenticate user quotations, infer causal truth from prose or determine whether
an operator's discretion is economically material. Review those judgments yourself.
No phrase blacklist is a substitute for that review.

## Final semantic check, including chat

Before freeze ask: Did I answer the user's question? Which exact observation earns each
concern? Did I impose an unrequested standard? Did I credit public accountability and
actual delivery only to the extent verified? Does each gap limit a named claim? Would the
same technical evidence earn the same result for an obscure token? What finding could
reverse the conclusion? Are any severe issues obscured by the positive context?

Write chat from the frozen decision review. Preserve its verdict kind, evidence strength
and action basis. Do not add a stronger “hold off”, “avoid”, sizing, safety or rug claim
when shortening the report. A readable report can be strongly negative when the evidence
warrants it; trust comes from warranted conclusions, not a positive response rate.

Version 1 remains readable with its original one-to-three-action requirement. Version 2
removes compulsory homework without weakening adverse-finding visibility or gap labels.
