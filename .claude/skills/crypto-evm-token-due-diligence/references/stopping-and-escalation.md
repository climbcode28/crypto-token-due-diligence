# Investigate unknowns and justify stopping

Load when planning material unknowns and before finalizing Unverified findings.
For broad completion and timing, apply [completion-and-delivery.md](completion-and-delivery.md). Apply
the reasoning to focused/chat answers too; a narrow answer needs no broad bundle.
Seek an evidence-backed answer, including a confirmed concern where warranted.

## Prioritize and follow up

At intake and after material discoveries, rank open checks by their decision consequence:

- **decision_critical:** a favorable conclusion under the user's requirement depends
  on this evidence. Unresolved mint/seizure/upgrade powers, principal withdrawal authority
  and the required exit commonly belong here. Preserve the authority-discovery floor.
- **material:** the result could meaningfully qualify the conclusion or exposure.
- **context:** useful background with limited effect on the stated decision.

`decision_critical` is a research scheduling priority. Bind it to the specific claim or
explicit user requirement it could change (for example irreversible custody), not to an
invented overall investment standard. The renderer must not turn the number of these gaps
into a favorable/adverse verdict. Use [decision-review.md](decision-review.md) to choose
an investigation action, a supported mitigation or a requirement-specific gate.

Write the consequence, not just the priority. Market leadership never lowers the priority
of consequential control or custody unknowns. An established adverse condition may
already justify an unfavorable answer while other checks remain open.

Choose the next check capable of changing the answer. For unclear LP custody, locate
the actual pool/position, trace its owner and inspect the lock/withdrawal powers. For
an inaccessible source, use the best permitted alternate with independent evidence
value. Another dashboard repeating the same indexer is not independent verification.
Source analysis may require a runtime match; a historical claim may need a historical
pin. A check may yield a positive finding, a concern or a narrower unknown.

Perform useful authorized next checks and review their remaining request/time estimates.
Reallocate optional social/history expansion before leaving critical
checks untouched. Preserve the one-alternate-source limit, pin rechecks and explicit hard limits.
The ordinary progress target is not a stopping boundary for broad diligence. Never retry identical failures, open a second session, buy access or bypass a
limit. Use explicit same-session `review/replan` inside the finite ceilings when an
operational allowance is inadequate; this is a recorded revision, not a bypass. Plan
sufficient room at intake instead of setting a premature cutoff. There is no mandatory attempt
count: one decisive read may resolve a claim; irrelevant reads earn no coverage. Fix
invocation omissions within existing permission before calling a provider unavailable.

## Review each remaining gap

Record actual checks and outcomes with captured evidence, including errors and
contradictions. A runtime identity anchor is not an attempt to verify LP ownership.
Identify the best next route and why it cannot proceed in this investigation:

| Disposition | Required basis |
| --- | --- |
| `pending` | A useful authorized route remains feasible. Continue before finalizing; only explicit checkpoint freezes permit this status. |
| `exhausted` | Relevant permitted routes were tried up to the bounded source limit. Link attempts and explain what remains unanswered; this is not a global completeness claim. |
| `unavailable` | Captured failure, documented access/support limit or a truthful capability observation prevents the route. Check the permitted alternate; one failed API operation never proves a whole service unavailable. |
| `budget_exhausted` | Internal checkpoint only: identify the operational allowance versus actual ceiling and its provenance, used attempts/time, remaining work, and the next budget-review action. An analyst estimate cannot establish an external evidence boundary. Replan inside existing ceilings; preserve the same session ledger. |
| `out_of_scope` | Name the user's scope boundary and why this background question is unnecessary. Use a not-checked surface; a decision-critical gap cannot be dismissed this way. |
| `not_yet_observable` | Link the dated claim/release and observation window establishing why the evidence does not yet exist. Failure to find an event alone does not prove it never happened. |

If nothing was attempted, say so and explain the actual boundary. A skipped check is
not exhausted research. Preserve a truthful capability/session note when no remote
response exists; never manufacture failures, attempts or future evidence. Missing
authorization permits only already-authorized alternatives.

For every final Unverified item, state **what was checked and found, what remains missing,
why work stopped, the decision consequence, and the exact evidence that would resolve
it**. Link a shared surface review instead of repeating one failed-source story. Show
critical gaps in the reading layer even when omitted from the short findings selection;
they limit the named claim or evaluation of the explicit requirement, without implying
an observed defect or an overall investment recommendation. A budget stop earns
an internal checkpoint, not a final answer to an ordinary broad request. Continue
feasible authorized work before final delivery; a completed review can retain externally
bounded unknowns. Keep feasible next checks in the active queue, not a list for a later
user-requested continuation. Replanning inside authorized ceilings needs no repeat
approval. Actual scope/authorization limits follow the completion policy; do not start
unsolicited background work or silently change spending authority.

## Structured review

New assembly emits `closure_review_version: 1` in `report.json`. Every `partial`,
`unavailable` or `not_checked` coverage record includes `closure`:

- `priority`: one of the priorities above, and nonempty `decision_impact`.
- `attempts`: a list of `{check, outcome, evidence_ids}`. References must also occur in
  that surface's coverage evidence. A `not_checked` surface has an empty list;
  partial/unavailable coverage requires actual captured attempts.
- `next_route`: `{check, disposition, basis, evidence_ids}`. `basis` explains the
  disposition. Exhausted/unavailable/not-yet-observable routes require captured basis
  evidence; exhaustion references must belong to recorded attempts. Budget and scope
  boundaries allow empty references with an explicit explanation.

Keep `gap`, `stop_reason` and `next_check` on the coverage row; the last names the precise
evidence needed to resolve the question. Replace intake placeholders. Completed or
not-applicable surfaces remove stale closure records and cannot retain unknown-evidence
findings. Handoffs carry the whole updated row; the coordinator reconciles before freeze.
This adds no risk dimension or collection budget.

The helper checks structure, references, consistency and declared pending work. Human
review still checks priority, relevance, authenticity of boundaries, viable alternatives
and verdict consistency. It cannot detect all invented prose or prove every useful
source was searched. Older strict sources without the marker remain readable and do
not acquire a retrospective stopping-review claim.
