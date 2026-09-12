These are conditional assessments of the supplied synthetic assertions in [scenarios.json](forward-scenarios.json), not current chain findings. Observation numbers below refer to each case's ordered observations. No web/RPC checks, credential access, signing or broadcasts were performed. Live RPC identity, block headers, timestamps and underlying raw evidence remain independently unverified; no live bundle or pins were created. Missing facts remain unresolved because this exercise permits only the supplied observations.

**HARBOR — general assessment**

Target: chain **4663**, `0x1234567890abcdef1234567890abcdef12345678`.

HARBOR has supported strengths in its inspected token controls, public accountability, product delivery and executed buybacks. The assessment is partial: canonical liquidity permanence and current exit capacity remain open, without evidence here of principal removal or a material adverse mechanism in the inspected token itself.

- **✅ Good — Token controls:** The supplied matched-source packet describes fixed supply with no mint, seizure, freeze, fee or upgrade entry point, and expired launch restrictions under the correct block semantics. This bounds those powers in the inspected token; it does not resolve the locker or other surrounding contracts. [HARBOR observation 1]
- **✅ Good — Historical exits:** Ordinary holders successfully sold $100 and $1,000 at the supplied historical states. Those executions establish historical access, not present sellability at every size. [Observation 4]
- **✅ Good — Accountability and delivery:** Independent public records link two named founders to this product, with eight months of executed use/releases and a documented incident response and reimbursement. That supports real delivery and accountability; it neither maps every admin key nor establishes market leadership or comprehensive security. [Observation 2]
- **✅ Good — Buyback execution:** The prior 30-day ledger reconciles the stated purchases and burn transfers. The published 80% protocol-fee buyback policy is discretionary: it supplies an observed token-benefit mechanism, with future performance dependent on continuation of that policy. No immutable payout or dividend was promised. [Observation 5]

**⚪ Unverified:** The LP NFT's locker ownership and runtime were captured, but withdrawal/approval permissions remained unresolved at the supplied collection deadline; “irreversibly locked” is therefore unestablished. Creator sales/proceeds, full holder unlock history and prior-launch history are not established by this packet. The missing $50,000 quote was an illustrative researcher probe, not your required exit size. Confidence is bounded to the supplied positive observations, with no complete current-state assessment. [Observations 3, 4, 6]

Useful next steps:

1. Match the locker runtime to source and resolve approvals, principal withdrawal, rescue, arbitrary-call, transfer and upgrade paths. Proving no reachable removal path would strengthen the custody claim; finding one would establish the specific exposure.
2. Reconstruct material creator sales/proceeds and holder unlocks from attributed allocations and transactions. Evidence of retained alignment or material exits/releases would qualify the economic assessment; missing history alone does neither.
3. If evaluating an actual trade size, obtain fresh route/depth evidence at that size. Favorable quotes would inform current depth, while failures require diagnosis; neither historical small sales nor a quote alone proves a future executed exit.

**MERIDIAN — general assessment**

Target: chain **4663**, `0x2234567890abcdef1234567890abcdef12345678`.

MERIDIAN has a material adverse technical finding: a current admin can seize an ordinary holder's balance without consent or delay. Its public team and substantial operating record deserve credit, but leave this executable exposure intact. The capability supports an unfavorable technical assessment even though no use of it or realized loss is supplied.

- **🔴 Bad — Reachable seizure authority:** Source-matched, reachable `forceTransfer` lets the admin move any ordinary holder's tokens to itself without allowance, delay or opt-out. Holders can lose their entire token balance through this administrative path. Disclosure and assurances of trust do not constrain the function. Likelihood of exercise and intent remain unknown. [MERIDIAN observations 1, 4]
- **✅ Good — Delivery and accountability:** Independently established public team identities, five years of operation, substantial measured product use and a completed prior public audit support credibility and maturity. The prior audit does not establish that the current seizure power is absent or harmless. [Observation 2]
- **✅ Good — Sampled canonical principal:** Matched locker code and pinned approvals establish no withdrawal path for the sampled canonical principal at the supplied state. This bounded finding does not extend to other pools or guarantee exit depth. [Observation 3]

**⚪ Unverified:** Material side pools are expressly unexamined. Token value capture, supply/unlocks, ordinary-holder exit capacity, creator trading/proceeds and prior launches are not established by this packet. The technical seizure conclusion is clear on the supplied premises; the broader economic and coverage assessment remains partial.

Useful next steps:

1. Treat tokens held under this design as exposed to administrative confiscation; limiting such exposure directly addresses the demonstrated mechanism. A changed assessment requires matched code and authority evidence showing the power has been removed and cannot be restored through remaining control paths. Additional reputation evidence alone would not resolve it.
2. Inspect custody and removal authority for material side pools. Bounded permissions would extend the favorable liquidity finding; reachable removal would identify a separate exposure.
3. Establish the exact token's benefit mechanism, dilution/unlocks and executed economics. Favorable evidence would support an economic thesis, while contradictions would weaken it; either result remains separate from the seizure finding.

**CINDER — general assessment**

Target address: `0x3234567890abcdef1234567890abcdef12345678`; **chain unresolved**.

**Blocked — target identity unverified.** The supplied evidence cannot support an overall assessment of CINDER. Exact-address discovery conflicts between mainnet and testnet, and the scenario reports that both authorized RPC identity attempts failed. This is an evidence limitation, not an adverse token finding. [CINDER observation 1]

**⚪ Unverified:** There is no verified chain/runtime/pin or readable project documentation, and ownership, liquidity, creator and team checks are unperformed. Consequently technical exposure, credibility/maturity and token economics are all unresolved. The aggregator's “popular” claim has neither authenticated target identity nor captured methodology, so it establishes no adoption strength. No Good, Potential Risk or Bad finding is warranted from these facts. [Observations 1–2]

Useful next steps:

1. Resolve the intended mainnet/testnet deployment through authenticated exact-address project evidence, then obtain matching `eth_chainId`, deployed runtime and a captured block header. Agreement would permit target-specific diligence; continuing conflict leaves identity blocked.
2. Once identity is resolved, obtain the exact deployment's control/custody evidence and authenticated project/economic documentation. These could support positive findings, specific concerns or narrower unknowns; the popularity label cannot substitute for them.

**HARBOR — explicit irreversible-liquidity requirement**

Target: chain **4663**, `0x1234567890abcdef1234567890abcdef12345678`.

**Your requirement is not established by the supplied evidence.** The NFT's presence at “Harbor Locker” does not resolve whether canonical principal is irreversibly locked. This is an unanswered requirement, not a demonstrated breach or observation of removal.

**✅ Good:** The supplied ownership read places the canonical LP NFT at the named locker, whose runtime was captured. That resolves the location of custody only. [HARBOR observation 3, inherited by `harbor_requirement`]

**⚪ Unverified:** Locker source correspondence and approval/removal permissions were unresolved when the supplied collection deadline ended. Token immutability, historical sales and founder credibility do not answer this specific custody question. Other diligence surfaces are outside this focused assessment.

Next step: Before treating the requirement as satisfied, match the locker runtime and inspect principal withdrawal/decrease, approvals/operators, rescue, arbitrary-call, position transfer, upgrades and any eventual unlock. Evidence that no present or future reachable path can release the canonical principal would support the requirement; a reachable release path would demonstrate that it is not met. If those paths remain unresolved, the answer remains unverified.

**LANTERN — general assessment**

Target: chain **4663**, `0x4234567890abcdef1234567890abcdef12345678`.

LANTERN has a specific, **low-confidence custody concern**: a reachable admin-controlled external-call branch may allow principal withdrawal. The partial decoding also permits a fee-collection-only interpretation, so principal removability remains unresolved. The supplied product-use and team evidence supports delivery and accountability. Overall coverage is partial; token economics are unestablished.

- **🟡 Potential Risk — Suspected withdrawal authority:** Bounded runtime analysis establishes the admin-controlled external-call branch. Partial decoding suggests a route to principal withdrawal, which, if confirmed, would let the admin remove liquidity supporting holders' exits. This is explicitly a low-confidence adverse inference. The called contract's semantics and target storage layout remain unresolved, the fee-only interpretation is a live alternative, and no withdrawal or loss was observed. [Additional supplied LANTERN observations]
- **✅ Good — Delivery and affiliation:** Independently documented public product use and named team affiliation support real activity and public accountability. They do not resolve what the external-call branch can do. [Additional supplied LANTERN observations]

**⚪ Unverified:** Full custody analysis and sale-size quotes were not supplied. The unknown storage layout and called-contract behavior limit the withdrawal inference; missing exit evidence limits claims about current depth. Public product use alone does not establish token value capture. Further checks were not performed because this is an offline exercise restricted to supplied assertions.

Useful next steps:

1. Resolve the branch's call target, calldata, storage layout, permissions and called-contract runtime/semantics. A reachable principal-removal path would support a stronger adverse finding; evidence that this branch can only collect fees would remove the present withdrawal concern for that branch.
2. Complete custody and approval analysis across canonical principal and material side pools. Bounded permissions would strengthen the custody assessment; another reachable removal path would establish its own exposure.
3. Obtain fresh exit quotes for a relevant intended size and route. These would inform executable depth, with any failure diagnosed on its actual cause; a quote alone would not prove an executed sale.
