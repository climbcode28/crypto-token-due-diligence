# Evidence packet and layered output

## Frozen target packet

Record the requested chain name/ID and address, RPC-observed chain ID and target, decision question, selected mode, relevant holder/exit sizes, materiality, and known coverage limits. Resolve name, symbol, decimals and atomic total supply from the token at a pinned current block; preserve failed/nonstandard calls and explicitly unresolved fields. Capture the header with number, hash and UTC time. Never supply invented metadata or a zero/placeholder pin to complete a form.

Capture runtime and its hash, source-correspondence status, proxy/implementation/beacon graph and authority scope. Add deployment/launch transaction if available with its own historical pin, and candidate pools/related contracts with provenance. Give additional chains distinct chain-ID evidence and headers. A contract address is not chain-independent; a v4 PoolId also needs its PoolManager and chain. Code hashes can identify common runtimes but not shared storage, permissions, or controllers.

Preserve raw inputs, outputs and errors. Include raw RPC method/params, calldata, receipt status, original logs, ABI/source revision or bytecode decoding basis, and artifact checksum. Redact endpoint keys, authorization headers, query credentials, personal secrets and environment dumps **before saving**. Keep a nonsensitive endpoint label and independently usable method/parameters. Never alter an original evidentiary value merely to reconcile a report; retain raw and derived artifacts separately.

Use integer atomic values for balances, shares and flows. Record each asset's chain/address/decimals and conversion rules; explicitly distinguish native currency, wrapped token, synthetic claim and LP/share units. Do not invent a token contract address for native currency. Keep an asset-unit table alongside the manifest when several assets are material.

Cache keys include target chain/address, queried contract, block hash or exact historical transaction, method and canonical parameters. Historical range evidence records both bounds. Pin historical transactions to their captured block headers. Verify receipt/log identity, emitter, execution status and topic decoding. On numbered-block reads recheck the header after the batch; if a reorg changes the hash, invalidate and repeat affected reads. Do not replace errors with empty results or `latest`.

For user-supplied offline/synthetic scenarios, reason conditionally over supplied assertions and explicitly leave RPC identity, headers and missing raw artifacts unresolved. Never turn such an exercise into a validated live bundle. Generated fixtures carry `synthetic: true`; the validator rejects them by default. A blocked real investigation may deliver a clearly labeled coverage-limited answer without claiming broad validation passed.

## Finding ledger

Every finding has: ID, exact proposition, chain, address, pin and/or transaction, artifact/query references, decoding basis, evidence class, confidence, alternatives, coverage, time basis and staleness conditions. One finding may use several evidence rows; each evidence row is bound to the frozen target and its actual queried chain/address. Link related-contract findings to their own scope identity, not the token address merely for convenience.

Evidence classes:

- **Proven fact:** directly reproducible observation under declared assumptions (for example code bytes at a pin).
- **Strongly supported:** reconciled independent observations close material alternatives; explain remaining assumptions.
- **Inference:** plausible interpretation with unresolved alternatives; do not present as direct observation.
- **Unknown:** missing, inaccessible, contradictory or skipped evidence. Name the gap; never score it as a pass.

For discovery claims record search universe (factories, indexers, event filters, wallets, deployments), range/page coverage, inclusion/exclusion rules, financial materiality and discovery limitations. A completed search of one factory is not global completeness. No discovery monetary threshold applies to dangerous authority paths. Track failures and unsearched segments explicitly.

## Focused answer

Lead with the answer conditional on scope/state, followed by the minimum reconciled evidence, strongest contrary evidence, uncertainty and what would resolve it. Use the finding labels below for the relevant checks; keep unrelated risk surfaces outside scope. For fee-origin answers show the asset journal and attribution bounds; distinguish the identified interval's fee contribution from total closing fee origin when opening provenance is unknown. Do not force a full report schema onto one narrow question.

## Plain-language finding signals

Use **✅ Good**, **🟡 Potential Risk**, and **🔴 Bad** for assessed findings, with
**⚪ Unverified** in a separate research-gap section, including Partial/Blocked answers.
Machine `summary.signal` values are `Good`, `Potential Risk`, `Bad`, and `Unverified`;
emojis are presentation only. Missing research lowers confidence, not a token's risk score.

| Signal | Evidence needed | Meaning and boundary |
| --- | --- | --- |
| **✅ Good** | Affirmative proven or strongly supported finding, high/medium confidence, with its stated bounded check resolved | A specific favorable observation. Say exactly what was checked and at what state; it is neither an overall pass nor proof of safety. |
| **🟡 Potential Risk** | An observed concern, adverse inference, or material conflicting evidence | Name the concern, confidence and consequence. Uncertain attribution does not erase an observed issue, but missing RPC/history/audit evidence alone does not qualify. |
| **🔴 Bad** | Proven or strongly supported material adverse condition, high/medium confidence and explicit holder consequence | A demonstrated defect, reachable harmful authority, reconciled harmful activity or material contradiction. Distinguish capability from exercise and observed loss. An allegation, low-confidence attribution or scanner flag alone cannot qualify. |
| **⚪ Unverified** | A pure coverage gap: missing, inaccessible or unperformed evidence | State actual attempts/results, missing evidence, the reason for stopping, decision consequence and resolution evidence. It is neither an observed defect nor a passing check. |

Assess atomic propositions: "the inspected release builds" can be Good while "the
deployed fee recipient cannot claim" is Bad. Do not combine them into one averaged label.
Good requires resolution of the stated observation, not every project risk. Broad
dimension passes still require their stronger complete-coverage gate below. Bad does
not mean scam, intent, a proven exploit or inevitable loss. Not-applicable and out-of-scope
items remain neutral in the detailed coverage record; never count them as Good.

Use **Unverified** for pure missing research, separately from assessed findings. Do not
count unavailable checks as risk points, infer that an obscure token is worse because
less data was accessible, or repeat one missing source as several apparent warnings.
Keep distinct coverage records for all eleven surfaces. An observed contradiction or
adverse inference stays Potential Risk; split it from accompanying coverage gaps.
If exact chain/token
identity is unresolved, identify that blocker plainly. For broad work, separate completed
research with specific unavailable facts from unfinished execution under
[completion-and-delivery.md](completion-and-delivery.md); continue feasible required checks. Rate only conditional or established
findings; do not present a verified token verdict or fabricate a bundle.

## Concise reading layer

Apply [decision-review.md](decision-review.md). General diligence defaults to no special
acceptance requirements. Missing research limits the claims it touches; it does not
make an observed technical, team or economic strength disappear. An adverse verdict
needs a specific evidenced concern. A research-priority label cannot create a global veto.

1. One or two sentences answering the decision question, identifying the main adverse
   condition and the strongest mitigating evidence when material. Never make a color
   count, average score or overall Good label substitute for the verdict.
2. A **Conclusions** block of exactly four bullets, one or two sentences each, in this order:
   **Technical exposure** (controls, custody, exits), **Credibility and maturity**, **Token
   economics**, **Research confidence**; judge each independently using
   [adoption-and-assessment.md](adoption-and-assessment.md). Never merge them into one
   paragraph. No blended safety score or popularity override. Give exact chain/address and current block/time, scope/completion limits and exit-size
   context. Historical executions and current quotes keep their distinct time/evidence
   labels; quotes alone never justify "currently sellable."
3. Usually 4–8 short findings, each with a signal, concrete observation, why it matters
   and a source link. Cover token/liquidity, real work vs marketing, creator trading and
   proceeds, prior launches/identity, adoption/maturity and token economics in broad work.
   Group pure gaps in a separate Unverified section; state missing coverage briefly.
   Put conclusion-changing findings first. Add rows when needed to avoid hiding severe
   problems; never force equal numbers of labels or let market positives hide a critical issue.
4. Finish with the completed assessment and link the full evidence report. Actions are
   optional: include only justified mitigation, an explicit user requirement or use of the
   verified scope. Execute feasible investigations before delivery; record externally
   unavailable facts in coverage without a closing list of useful additions. Preserve the
   frozen decision's evidence strength when writing chat.

`bundle_assemble.py finalize` runs `deliver` on the completed frozen source before the final
research answer; run `deliver BUNDLE` yourself only after a manual freeze. Successful
checkpoint storage/validation does not authorize delivery; its unfinished work stays active
under the completion policy.

End completed reviews with the supported conclusion and what would change it, not a
generic partial-investigation or validator-status footer. Keep ordinary broad chat delivery around 300–600 words, and focused answers shorter;
honor the user's requested depth. Prefer one compact table or short topic bullets, not
both repeating the same claims. Use familiar words; explain necessary technical terms
by their effect on holders. Give readable amounts/percentages, preserve exact values in
evidence and avoid precision beyond the data. Do not repeat full wallet addresses or
transaction hashes in the prose when an exact linked role is already established.

For new machine-backed reports, write findings, coverage, decision and texts as a compact
note and expand it with `bundle_assemble.py compose` ([compose.md](compose.md)); read evidence
through `bundle_assemble.py facts`. The expanded `summary` entries follow [bundle-format.md](bundle-format.md). The
renderer reuses their exact text and evidence references above the technical appendix;
there is no separate unbound summary prose. Each proposition must itself state a bounded
observation and consequence. Every chat finding ends with an adjacent native
Markdown citation to its supporting source/transaction or the local report; document
claims retain dated source/revision provenance. The existing renderer surfaces up to two
already-cited document URLs beside each assessed summary finding and always retains its
frozen evidence link. Reuse those links in the existing report-read/answer step. Select
the link that supports the actual sentence; a documentary label never upgrades evidence
strength. For composite claims, prefer the frozen finding or retain both needed sources.

Chat layout: direct verdict, exact network/address and pin, then short bullets beginning
with **✅ Good / 🟡 Potential Risk / 🔴 Bad — descriptive title**. Bold a few material
numbers, not whole paragraphs. Use Market snapshot, Transaction or Source, Repository,
and Evidence report or Pool evidence as readable source-link labels. Company/product
logos belong to the client's native link rendering when available; do not replace them
with emoji, Unicode pictograms, remote image embeds or hand-built logo assets. Plain
Markdown cannot guarantee a brand icon in every client: use a plain text link when no
native decoration appears. Preserve the ✅/🟡/🔴 assessment and ⚪ gap markers, which are
separate from source branding. Finish grouped **⚪ Unverified** text with a Detailed
findings link, then the existing four-bullet Conclusions block. Use standard Markdown
links to actual destinations, never bare URLs or internal citation IDs.

Use only URLs already collected and tied to the finding. When no suitable direct link is
available (including RPC-only findings or failed captures), link the absolute frozen
`report.md` path returned by finalize; use a specific location only if already available.
Resolve report-relative anchors against that path, not against the chat. A single global
report link is not a substitute for adjacent citations. Prefer a human-facing official source URL when it is already collected and supports
the claim; do not substitute an invented product URL merely to obtain its logo.
Do not construct an explorer URL,
fetch a favicon, open/recheck a page, read additional evidence, call another tool or add
an agent turn just for presentation. This is formatting inside the existing final answer,
with unchanged research steps, request budgets, 5–7-minute target and word limit.

Before delivery, review label meaning against the actual evidence, including raw
support and counterevidence. The helper enforces structural label gates, not semantic
truth, materiality or the absence of omitted issues. A positive finding cannot stand in
for a negative one just because they support the same machine dimension. Use
[reporting-scenarios.md](reporting-scenarios.md) for synthetic acceptance examples.

Preserve findings when shortening the frozen report into chat. The existing `deliver`
response includes a compact `reading_checklist` of coverage, finding IDs and gaps,
including findings without optional summary signals; use it during the same report-read
and answer step, without an additional tool call or agent turn. Keep sampled holder
count/aggregate/largest shares and ownership limits, named LP custodian/admin plus what
withdrawal power is unproven, and holder-right/source/audit/team/adoption limits explicit.
Use `holder_summary`'s sum of unique atomic RPC balances, not mental arithmetic or summed
rounded percentages. Name sample exclusions; code-bearing or delegated accounts are not
automatically protocol custody, single beneficial owners or evidence of coordinated control.
Concentration earns Potential Risk only with an explained exposure; incomplete ownership
classification and absent unpromised payouts remain neutral gaps. When comparing runs,
reconcile pins, sampled addresses, raw sums and denominators before calling a change real.

Complete the [stopping review](stopping-and-escalation.md) for each incomplete surface.
Resolve feasible consequential checks before optional context expansion. Disclose
not-attempted checks distinctly from exhausted research, and show decision-critical
gaps in the reading layer even when not selected as summary findings. New assembly
requires the review; the validator cannot establish that its prose earns the boundary.

## Sellability in plain language

Separate observed trading activity, the analyst's receipt-verification sample, and
size-dependent execution costs. A sample of two verified sales means two transactions
were inspected, not that only two sales happened or only small sales are possible.
When broader buy/sell activity is evidenced, lead with that activity and attribute
indexer metrics as reported; retain receipt amounts, sender and proceeds limitations
in supporting detail rather than a redundant headline Good finding. When activity is
sparse or sellability is the user's actual question, a sampled sale can be a useful
headline, explicitly labeled as a sample at its historical state.

Describe an unmeasured large exit as "I did not independently measure price impact and
execution costs for larger trades." Missing size tests alone earn no Potential Risk
or implication of blocked selling. A demonstrated restriction, failed execution or
measured adverse price impact remains a separate evidence-backed concern. Do not
upgrade indexer activity or one wallet's success into universal sellability.

A user's report of completed buys/sells is relevant user-reported experience; acknowledge
it without representing it as an independently verified receipt or proof for all wallets,
sizes or future states. Example with corroborated market activity: "Active buying and
selling is evident from the indexed market activity; sampled receipts corroborate it.
I did not independently measure execution costs for larger trades."

## Broad and formal broad reports

Use the concise reading layer above, preserving the user's conditional verdict and requirement, for example “A stated immutable-custody requirement is contradicted by the verified withdrawal path,” “No current executable removal path found within the inspected scope at the pinned block,” or “Exit quotes available at the tested sizes; execution remains unproven.” Unknown historical state is “Unknown because historical state was unavailable.” An unfavorable technical condition can be established despite coverage gaps; avoid pretending all work must finish to communicate it.

Rate these separately; do not average a critical condition away:

| Machine dimension | Meaning |
| --- | --- |
| token_controls | Current token powers and upgrade exposure |
| canonical_lp_principal_custody | Canonical principal withdrawal control |
| side_pool_removal_risk | Material other pool/position custody |
| sellability_exit_depth | Ordinary-holder transfers/exits at relevant sizes |
| current_concentration | Current balances with denominators and custody categories |
| historical_launch_integrity | Allocations, exceptions, launch-cohort evidence |
| admin_treasury_reward_custody | Surrounding key, vault, fee and admin controls |
| reward_accounting_liveness | Entitlements, conservation, caps and processing |
| utility_redemption_rights | Live token-linked utility and actual enforceable exits |
| external_dependencies | Assets, oracles, bridges, custodians and operators |
| development_disclosure | Source/builds, releases, tests, audit scope and accuracy |

Each dimension states severity, likelihood, confidence, coverage and time basis. Status `pass` means only the stated bounded condition was fully examined with resolved evidence; it is not a general safety judgment. Partial coverage with no observed issue remains `unknown`; a proven issue with partial coverage may remain `concern`. `not_applicable` needs affirmative evidence and rationale, not a skipped check. Distinguish observed likelihood from a future estimate; do not manufacture percentages.

Give main reasons, strongest contrary evidence, unresolved questions, specific evidence that would change the conclusion, and recommendations tied to observed deficiencies. Keep current/historical and canonical/side/system-layer distinctions visible in prose and visuals. Do not promise returns or issue unconditional safety conclusions.

Finalize raw evidence and reconciliations once; freeze `manifest.json`, calculate its SHA-256 into `report.json`, validate, then render. The rendered report includes source hashes, evidence/query ledger, dimensions, pins and limitations. For any requested custom/PDF/slides/visual output, preserve the source identity, evidence IDs and units and inspect the final artifact; the bundled validator can compare its own deterministic Markdown only, not arbitrarily edited prose or charts. This is a diligence workflow, not a full protocol exploit audit.

## Strict assembly and navigation

New broad reports use [incremental assembly](supported-research-flow.md), the
[strict report profile](strict-report-profile.md) and the versioned
[decision review](decision-review.md). Findings identify their subject,
participants, claim class, adverse severity and direct/source/calculation evidence.
Hash-bind every derived input; unrelated runtime is no substitute for the claimed
contract's authority. Report a successful sale only with successful receipt status and
decoded target effects; transaction sender may be a bundler, not the seller. Distinct
surface gaps cannot be replaced with generic LP uncertainty. Summary selection keeps
every high/critical adverse proposition visible. Safe links connect the summary to the
finding, its inputs, raw artifacts and sources. Frozen [report replay](report-replay.md)
separates historical reproducibility from current validation. Human review still owns
prose meaning, causal attribution, rights, valuation and research completeness.

Completed reports do not require next steps. Execute feasible follow-ups during research;
keep externally unavailable evidence in coverage, without a closing homework list.
