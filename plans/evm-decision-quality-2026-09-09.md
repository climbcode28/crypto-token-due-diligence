# EVM decision-quality repair

## Request and finding

The user challenged a PONS report whose headline advised holding off on treating the
token as rug-resistant, although the run established favorable token controls and no
material adverse rug mechanism. The user requested a deep skill correction that produces
clear, actionable, trustworthy reports without manufacturing favorable conclusions, and
requires the Claude Code copy to receive the same changes.

This maintenance review diagnoses an **assessment and communication failure**. It does
not establish that PONS is safe, verify the user's public-team claim, or rewrite a live
token assessment. The frozen PONS evidence/report is preserved as development provenance.
No new token investigation, provider request, credential access or paid usage occurred.

## Why the prior safeguards failed

1. `render_report.py` automatically turned every analyst-assigned decision-critical gap
   into “A favorable conclusion still depends…” without binding it to a user requirement.
   A research priority became a global verdict gate.
2. `main_reasons` contained useful independent conclusions, but appeared only after the
   technical-detail boundary. The reading layer emphasized unresolved checks and placed
   positives under “strongest contrary evidence”.
3. Typed findings constrained colors and severity, while `verdict` and recommendations
   were unconstrained prose. Independent review reproduced acceptance of an all-gap
   synthetic bundle with a verdict saying to avoid the token because the locker was not
   checked. Existing validation did not earn the apparent recommendation.
4. The PONS output treated disclosed mutable buybacks as medium adverse economics without
   establishing a contradicted promise, explicit user requirement or specific harmful
   consequence. Existing guidance already said discretion was not automatically a defect;
   the failure was at the evidence-to-decision boundary.
5. Chat strengthened “does not establish” into “I would hold off”. Summarization introduced
   a recommendation absent a supported frozen action basis.
6. Public engineering artifacts received attention, but the credibility procedure did not
   ensure a bounded affirmative check of public roles, relevant operating record and
   accountability. Commits became a weak substitute for that broader context.

The remedy is not a lower evidence standard or a positive-response target. It is a better
connection between the actual question, findings, coverage, conclusions and actions.

## Implemented behavior

Workflow and reporting engine **2.3.0**; backend **3.0.0** unchanged. Existing bundle,
collection and strict-profile identifiers remain compatible. New assembly emits and
requires `decision_review_version: 1`; older sources do not acquire a retrospective claim.

- Default broad diligence has **no additional user acceptance requirements**. Explicit
  requirements retain actual user wording. Illustrative exit probes do not become mandates.
- New decision review binds a declared verdict kind to findings and requirements. A
  packet of gaps cannot support a typed adverse or affirmative verdict. A specific
  requirement can remain unestablished without alleging that it failed.
- The reading layer shows four separate, evidence-linked conclusions: technical exposure,
  credibility/maturity, token economics and research confidence. There is no blended score.
- Each adverse finding states a mechanism, holder consequence and evidentiary basis.
  Unknown evidence cannot supply a concern; even adverse inference needs a direct observed
  lead at its subject and must retain its inference classification.
- One to three ordered actions distinguish investigating uncertainty, mitigating an
  assessed concern, checking an explicit requirement and using a completed bounded result.
  Each explains what evidence or change would alter the assessment. No generic DYOR list.
- High/critical adverse findings remain visible in the verdict basis, synthesis, summary
  and mitigation actions. Public teams or popularity cannot erase demonstrated powers.
- Discretionary buybacks and absent unpromised rights are ordinary terms unless a specific
  exposure, contradicted commitment or user requirement earns a concern. They need not be
  forced into positive or negative labels.
- Public credibility receives a bounded first pass: authenticated project role, relevant
  delivery/operating history and incident response. Identity does not prove control of
  every key, and private personal information is unnecessary.
- Chat must preserve the frozen decision kind, certainty and action basis. It cannot add
  an unsupported avoid/hold-off/size/safety recommendation while shortening the report.

All eleven coverage dimensions, strong pin/runtime/source/receipt standards, provider
selection and standing authorization, source/time limits, frozen histories and project-only
Codex registration are preserved. References direct the coordinator to draft the review
incrementally so it does not become a second research pass at the delivery cutoff.

## Implement-review-improve record

An independent reviewer first located the actual renderer/validator bypass and reproduced
it using supplied synthetic evidence. A separate author improved the two credibility and
adoption references. The coordinator implemented the decision contract, renderer, assembly,
documentation and tests in the canonical skill.

Independent review of the implementation found that `use_within_scope` could cherry-pick a
positive finding from a completed dimension containing a medium adverse finding. Fixed:
its entire declared coverage must have pass/not-applicable ratings and no adverse finding.
A new regression reproduces the rejected near-neighbor. The reviewer also caught an
inference test whose action overstated a “demonstrated” path; the accepted fixture now
uses conditional language. The report template now explicitly declares the review marker
and an incomplete value instead of silently omitting the new contract.

A final local review strengthened inferred concerns against another loophole: an
identity-only evidence anchor cannot become a harmful-authority inference, and an
inference cannot relabel its basis as demonstrated capability. These are structural gates;
semantic relevance and prose remain investigator responsibilities.

## Independent forward evaluation

A separate agent with no conversation fork received the revised skill and only synthetic
requests/observations, not the intended answers or diagnosed defects. It produced conditional
user-facing answers without live tools or fabricated bundles. The supplied inputs and
outputs are retained in [scenarios](evm-decision-quality-2026-09-09/forward-scenarios.json)
and [responses](evm-decision-quality-2026-09-09/forward-responses.md).

| Scenario | Observed outcome |
| --- | --- |
| HARBOR: constrained code, verified public roles/delivery, executed discretionary buybacks, unresolved locker | Credited strengths; qualified custody specifically; no blanket hold-off, immutable-payout norm or inferred rug allegation |
| MERIDIAN: established public team plus reachable holder seizure | Prominent Bad finding and mechanism-specific exposure mitigation; reputation did not remove the power; no claim of realized loss |
| CINDER: conflicting identity and failed research | Blocked/inconclusive; neither a passing finding nor an adverse token verdict |
| HARBOR with explicit irreversible-liquidity requirement | Requirement not established; no allegation that liquidity had been removed or that a breach was proved |
| LANTERN: low-confidence withdrawal inference with fee-only alternative | Potential Risk retained inference/alternative and conditional next steps; no promotion to demonstrated withdrawal or loss |

The last case was supplied in a follow-up to the same isolated evaluator. This is a small
behavioral exercise, not a blinded population study, live performance benchmark or measured
false-positive/false-negative rate. Claims about actual token identity and safety still
require fresh real evidence.

## Validation

- Canonical EVM suite: **288 tests passed**, including **18 new decision-review tests**.
- Claude EVM suite: **288 tests passed**.
- Crypto research: **31 passed**; rug check: **18 passed**; Solana diligence: **23 passed**.
- Total across five suites: **648 passing test executions**; canonical and Claude tests
  intentionally exercise the mirrored implementation separately.
- New assembly/freeze tests reject absent reviews, verify handoff preservation, render
  evidence-linked assessments/actions, reject modified output and replay the frozen engine.
- The original PONS report replayed byte-for-byte under its frozen **2.2.0** engine, with
  report digest `251382daaac5e5226dbfe574537f3972a69db719cec5e96d1dbb318a13805a29`.
- Canonical/Claude scripts, tests and shared references are byte-identical; only documented
  tool wording, sibling paths, release-record paths and port notes differ.
- `git diff --check`, simple frontmatter/release checks, local reference checks and the
  project registration check passed. The optional skill-creator `quick_validate.py` was
  attempted but unavailable because PyYAML is absent in both Python runtimes; unchanged
  simple frontmatter was checked using the standard library. No dependency was installed.

## Changed files and remaining limitations

Changes are in the canonical skill's `SKILL.md`, decision/assessment/project/output/source/
stop/format references, `bundle_assemble.py`, `report_profile.py`, `render_report.py`,
`validate_bundle.py`, report/release assets and regression tests. Matching changes are in
the Claude Code copy, with its port notes updated. README records the current versions and
this review; this plan and the synthetic forward artifacts preserve the review evidence.
No unrelated skill implementation, personal registration, historical run, or credential
file was modified. Changes are left uncommitted.

The validator cannot authenticate a quoted user statement, recognize every misleading
sentence or establish that a referenced source semantically proves a claim. Its checks
make several structural contradictions impossible in new freezes and keep the decision
basis visible. Independent semantic review and honest reporting remain necessary. The
new procedures improve calibration; they do not guarantee a correct investment judgment.

Suggested commit message: `Improve EVM diligence decision quality and actionable reporting`
