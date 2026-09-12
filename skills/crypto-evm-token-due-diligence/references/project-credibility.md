# Project delivery, creator activity and prior launches

In broad diligence, perform a bounded first pass over team accountability, delivery,
creator activity and prior launches using the exact target packet. In focused mode,
load only the section needed for the question.
Use available primary project sources, deployed evidence and dated archives; inherited
research deadlines still apply. Follow leads only when they could change a material
conclusion. No public repository or inaccessible history is a coverage gap, not fraud.

## Team accountability and operating record

Use authenticated project links and voluntarily public professional records to assess
who publicly stands behind this exact project and what they have delivered. Verify the
connection among the public identity/profile, stated role and target project; a name,
photo, paid verification badge or "doxxed" claim alone does not establish that connection.
Record whether the identity/role is self-reported or corroborated and the dated basis.
Keep public affiliation distinct from control of a deployer, treasury or upgrade key;
apply [operational-attribution.md](operational-attribution.md) for the stronger claim.

Look for a concise, evidenced operating record: delivered products, duration under real
use, fulfilled commitments and, where incidents occurred, disclosure, remediation and
holder treatment. Attribute prior work to the evidenced person/team and project version;
do not inherit another project's record from a shared brand or employer. An incomplete
incident search cannot support "no incidents." Seek contrary evidence as well as successes.

Verified public accountability and demonstrated delivery earn bounded positive findings
and can inform the likelihood of intentional misconduct when the inference and its limits
are explained. They do not remove executable withdrawal, mint or upgrade powers, reduce
the consequence of their misuse, or establish a guarantee. Public identity alone is not
an assurance of honest future conduct. Unknown identity, pseudonymity and missing records
are not adverse behavior; record what is known without inventing either trust or suspicion.

**Stop:** the relevant public role and operating record have a bounded evidence basis,
or the relevant permitted routes reached a documented evidence boundary. A time-bound
lane handoff returns feasible remaining work as pending under the completion policy. Start this core credibility pass
alongside the first technical pass using existing project sources; do not leave it to an
unbounded tail of optional searches. Follow further leads only if decision-changing. Do
not search private PII, relatives, home addresses or unrelated personal accounts.

## Real work vs marketing

For each material promise, record the dated claim and source, exact implementation or
operator responsible, deployed correspondence, evidence of operation, holder impact and
remaining gap. Prioritize claims about fees, backing, payouts, redemption, audits and
"live" products; do not inventory every marketing sentence.

- **Delivery:** distinguish website/UI, repository implementation, deployed contracts,
  configured integrations and a completed economic cycle. Identify dependencies still
  undeployed, recipient configuration that points elsewhere, and operator-only steps.
  Capture source revision and deployed runtime/proxy correspondence before treating a
  source-level conclusion as deployed behavior.
- **Builds and tests:** record whether results were independently reproduced, reported by
  project CI, or merely asserted. Inspect test scope: unit/mocked versus fork/integration,
  failure paths, adversarial cases, operator behavior and exact deployment revision.
  Counts and passing builds are bounded positive evidence, not a security audit. Inspect
  untrusted repository scripts before running them; use an isolated writable workspace
  without credentials or access to private configuration. If that isolation is unavailable,
  inspect source and disclose that execution was not independently reproduced.
- **Audit claims:** check the actual auditor, date, scope/revision, findings and remediation
  evidence. Self-review is not independent assurance. "No independent audit found in the
  searched sources" is a coverage statement; a dated false audit claim requires evidence
  of the contradiction. Do not infer authorship from style or use AI-written code as a
  risk signal by itself. Authenticated co-author metadata supports only its recorded scope.
- **Operational proof:** inspect historical successful transactions and state changes for
  the claimed fee, reward, mint and redeem paths. Zero inventory/supply or no observed
  completed cycle means operation is unproven within the searched interval. Distinguish
  a disclosed prototype from a materially contradicted live-product claim. Source-matched
  reachable defects may be established before funds arrive; zero TVL does not refute them.
- **Fee path:** map accrual → entitled recipient → callable claim → forwarder → intended
  use. A contract credited with fees must be able to execute the required claim, including
  its caller checks. No forwarding observed is different from a verified unreachable
  claim. Establish alternative rescue/upgrade routes before saying funds are stranded.
- **Backing and redemption:** reconcile available reserves against circulating claims AND
  pending unpaid redemption liabilities in consistent units. Inspect request, burn,
  settlement, failure/cancellation, caps and repeated mint/redeem transitions. Burning
  supply does not extinguish an unpaid obligation. Distinguish a verified accounting
  defect, counterfactual exploit path and observed loss. Use
  [reward-accounting.md](reward-accounting.md) and
  [dependencies-redemption.md](dependencies-redemption.md) when triggered.

**Stop:** material claims are supported, contradicted or explicitly unresolved, and the
holder consequence is clear. Substantial exploit work belongs to a separate audit scope;
do not silently expand diligence or claim a comprehensive audit.

## Creator trading and proceeds

Start from the exact launch signer/direct allocation recipient and evidenced public
roles. Use [launch-cohort.md](launch-cohort.md) and
[fees-and-proceeds.md](fees-and-proceeds.md) for executed trades and reconciled flows.
Follow material proceeds to their defensible attribution boundary within the budget.

Record launch cost and allocation, supply denominator, elapsed time to sale, executed
amount and net receipt, fees/cost basis, transfers/bridges, downstream spending, rebuys
and residual inventory. In the answer use a short chronology only when sequence matters.
Round readable amounts while retaining atomic amounts, transaction IDs and calculations
in evidence. State incomplete cost basis instead of calling gross proceeds profit.

At commingling, stop exact tracing but retain defensible attribution bounds. For an
isolated interval with retained sale proceeds P, other available funds O and outflow X,
the sale-funded portion is between `max(0, X - O)` and `min(X, P)` if the full inventory
and all intervening flows are reconciled. With missing flows, weaken or omit that bound.
A payment to a labeled service wallet is an observed payment; vendor/service purpose
requires independent attribution and does not prove who ultimately benefited.

An early full exit may raise alignment concerns even if later spending funds promotion.
Show both observations. Promotion spending or rebuys do not erase the exit; a rapid sale
alone does not establish fraud, personal cash-out or a future rug. An exchange deposit
does not prove a sale or fiat withdrawal. Use neutral role labels when controller or
beneficiary is unresolved.

For Solana destination activity, use the sibling Solana diligence procedures only for
the needed evidence. Preserve exact mint/native-asset identity, genesis hash, signatures
and finalized slots in a separate packet; link it as external evidence in the EVM bundle.
Never invent an EVM chain ID, address or block pin for a Solana leg, and never treat an
EVM source bridge receipt as proof of destination execution.

**Stop:** the material sequence and net flows reconcile, or shared custody, missing
destination evidence or commingling bounds attribution after actual relevant attempts.
A deadline interruption preserves unfinished work; it cannot establish an external gap.

## Prior launches and identity

Keep four propositions separate: the same address signed deployments; the project
advertised earlier tokens; wallets likely share control; the same human operated them.
Evidence for one does not establish the others.

- Query exact launch-key/factory history over declared ranges/pages. Count only confirmed
  deployments with chain, token address and transaction evidence; distinguish migrations,
  relaunches, test deployments and unrelated same-symbol tokens. "One found in these
  factories and dates" does not mean "only ever launched one token."
- Follow authenticated project links and dated archived announcements to earlier exact
  contracts/mints. Preserve old and new claims and relevant version changes. Deleted
  content can document changed disclosure; it does not by itself prove deception.
- Assess earlier-holder treatment when material: disclosed migration, redemption or
  abandonment, retained liquidity, supply and outstanding obligations. Repetition alone
  is not a Bad finding. Verified undisclosed harmful behavior can be. Ambiguous continuity
  alone is Unverified; an adverse inference needs specific supporting observations,
  plausible alternatives and an explicit attribution limit.
- Separate cryptographic control, project affiliation and human identity using
  [operational-attribution.md](operational-attribution.md). Do not seek private personal
  information or request signatures. A brand, funding link, deployer service or exchange
  wallet is insufficient to identify a human or collapse several keys into one actor.

**Stop:** relevant project continuity and exact-key history are bounded, or further work
would be speculative identity hunting. State unsearched chains/platforms and unresolved
links explicitly. Map findings to historical_launch_integrity and/or development_disclosure;
these are additional investigation lenses, not extra machine risk dimensions.

## Assessment calibration

Use [adoption-and-assessment.md](adoption-and-assessment.md) for a bounded market-maturity
and token-economics screen alongside the project review. Verified public accountability,
delivery, actual use, token-linked benefits and resilience over time earn separate, scoped
credit. A missing audit search, inaccessible social history or unfinished creator trace
is Unverified, not
evidence of weak adoption, a nonexistent audit or adverse creator behavior. A source's
materially misleading disclosure, harmful authority or contradicted promise is assessed
on its own evidence. Keep observed deficiencies visible even for a widely used project.
