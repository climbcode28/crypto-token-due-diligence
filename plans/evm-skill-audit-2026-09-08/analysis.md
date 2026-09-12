# EVM diligence skill: comprehensive audit and improvement plan

Date: September 8, 2026. Scope: workflow 1.7.0, backend 2.1.0, reporting 1.1.2, supporting procedures/tests, and the user-selected GAGE/OURO investigation. This is a maintenance analysis, not a new token investigation or a production implementation. Original research evidence and installed skills remain unchanged.

## Assessment

The skill has a strong research rubric and several valuable technical safeguards. Its largest weakness is the gap between those requirements and the work required to produce an evidence-complete report. More prose alone will not close that gap. The highest-return improvement is a supported path from discovery and collection to correctly scoped findings, complete evidence dependencies, explicit coverage, and a frozen report.

The GAGE/OURO round illustrates both strengths and weaknesses. Fresh identities and pins were established, source matching found useful token controls, main-pool custody was kept distinct from a side-pool lock, and historical sales were not presented as guaranteed current exits. However, report assembly defaulted unrelated findings to the token address, supporting source dependencies were not fully hash-bound, and several distinct unknown dimensions shared a generic explanation. The validator accepted those reports. That acceptance remains an internal-consistency result, not a certification of the analysis.

I recommend adding operational memory, but separating automatic observation capture from trusted, reusable guidance. Memory should prevent repeated procedure mistakes; it must not carry token conclusions, state, permissions, or permanent provider-failure assumptions into future investigations.

## Method and measured baseline

Reviewed the canonical entrypoint, all research procedure references, collector/cache/detector/maintenance/provider-context/reporting code, tests, release metadata, and Claude Code port conventions. Two independent audit lanes reviewed reporting quality and memory design. Performance analysis and synthetic probes ran locally. Only the selected latest investigation was opened as historical maintenance provenance. No paid RPC, credentials, transactions or new token research were used in this audit. Current technical recommendations were checked against primary documentation where relevant.

All existing README suites passed: EVM 172, research 31, rug check 18, Solana 23; the Claude EVM mirror also passed 172. That is **244 canonical tests, plus 172 mirrored executions**, not 416 independent test cases. The independent reporting audit reran a 94-test subset. Passing existing tests did not prevent the new probes below from exposing gaps.

Latest-run measurements:

| Measurement | Result | Interpretation |
| --- | ---: | --- |
| Recorded RPC attempts, including head discovery | 91 | 89 collector requests plus two discovery attempts; not a dollar cost |
| Collector invocations | 7 | Per-invocation caps worked; total orchestration was manual |
| Chain-ID reads | 7 | Repeated verification across separate collections |
| Block-header reads/rechecks | 18 | Necessary safeguards, with potential consolidation under a shared session |
| Other state/transaction requests | 64 | All 64 were distinct; zero cache hits was expected |
| Feedback rows | 0 in both caches | Operational problems remained in lane notes |
| Registered discovery records | 0 in both reports | Discovery work did not survive in the formal discovery ledger |
| Unbound copied evidence files | 216 per report | Not every extra file is a defect, but some were essential source dependencies |
| Risk dimensions | 10 Unknown, 1 Concern per report | Conservative grading, but insufficient dimension-specific explanation |
| Rendered report sizes | 55,516 / 46,301 bytes | Large appendices with limited clickable navigation |
| Timing | Collection stopped within eight minutes; delivery overran ten minutes | Report assembly, review and validation needed a larger or better-used reserve |

Metrics and scripts are in [run-metrics.json](../../research/2026-09-08-evm-skill-audit-1356/run-metrics.json), [performance-results.json](../../research/2026-09-08-evm-skill-audit-1356/performance-results.json), and [suite-results.json](../../research/2026-09-08-evm-skill-audit-1356/suite-results.json). Synthetic timings are not a live provider or end-to-end performance benchmark.

## Priorities

P1 means fix before relying on stronger automated assurance or scaling the workflow. P2 means a valuable next improvement. These are maintenance priorities, not token finding labels.

| Priority | Area | Finding / action | Evidence class |
| --- | --- | --- | --- |
| P1 | Validation | Check every captured successful header and chain-ID observation | Reproduced validator defect |
| P1 | Reporting | Make material adverse findings individually mandatory in summaries | Reproduced guard weakness |
| P1 | Evidence | Require explicit subjects and support roles; bind derived-source dependencies | Observed assembly omissions; missing structured contract |
| P1 | Coverage | Require a specific record for each applicable surface and bounded discovery | Observed workflow omission |
| P1 | Collection | Validate RPC wire shapes before marking/cacheing results successful | Reproduced collector/loader inconsistency |
| P1 | Workflow | Add supported bootstrap and incremental bundle assembly | Demonstrated manual-work bottleneck; proposed implementation |
| P2 | Reproducibility | Freeze reporting tools/profile as well as collector tools | Reproduced replay gap |
| P2 | Performance | Prioritize unresolved decision-changing checks; share investigation setup | Observed orchestration cost; proposed improvement |
| P2 | Performance | Replace blocking request waves with a bounded rolling scheduler | Measured synthetic opportunity |
| P2 | Sources | Add explicit Sourcify v2 and capability-aware fallback records | Successful run recovery and current official documentation |
| P2 | Clarity | Preserve product-specific risks and distinguish observations from inference | Observed summary weakness |
| P2 | Learning | Add bounded operational-memory intake, review and retirement | Existing feedback design lacks a lifecycle |

## 1. Research quality and clarity

### 1.1 Correct finding subjects and supporting evidence

GAGE's vault activity, fee administration, seed locker, and creator transfer were all represented as findings about the token address. Some findings appended the token's runtime evidence to satisfy the validator's requirement that at least one evidence item share the finding's identity. That meets the current schema while missing the intended attribution.

The skill already says related-contract findings must use their own scope identity. The missing piece is an assembly interface that makes the right representation easy. Require explicit subject scope IDs, evidence class, and support roles when creating a finding. Do not default to `proven_fact`, medium confidence, or the token address. For a cross-contract proposition, list its participant scopes or split it into atomic observations and a clearly labeled synthesis.

Useful support roles are direct observation, identity binding, source correspondence, calculation input, corroboration, counterevidence, and failed attempt. An unrelated token code read must not stand in for direct evidence of another contract's owner or withdrawal path. Do not require every supporting artifact to have the same address: legitimate cross-contract claims need multiple identities.

Relevant code: [validate_bundle.py](../../skills/crypto-evm-token-due-diligence/scripts/validate_bundle.py), especially the finding support check around line 533; run-local [build_reports.py](../../research/2026-09-08-gage-ouro-1249/build_reports.py), around lines 54–61. The actual reports' generic actor roles should become precise roles such as FeeSink, seed locker, operations recipient, PositionManager, or fee hook.

### 1.2 Bind the complete source-comparison chain

The controls lane did meaningful source work: it compared fresh RPC runtime with Sourcify deployed and recompiled bytecode, accounting for published immutable/metadata substitutions. The lane correctly disclosed that it did not run a local compiler.

The report reduced that work to a derived boolean comparison table labeled as a document. Several raw source/API inputs supporting the seed-lock and fee-control findings were copied but not registered in the evidence ledger. Deleting the seed contract source from an isolated synthetic copy still allowed validation. The defect is not that every incidental file must be hashed; it is that a material derived conclusion lacks its complete supporting dependency chain.

Introduce structured derived evidence with `input_evidence_ids`, derivation/tool version, exact source URL and capture time, compiler/version/settings provenance, transformation details, output hash, and limitations. Validate missing inputs, cycles and changed hashes. An offline source-correspondence helper should reproduce byte comparisons and validate permitted substitution locations against compiler artifacts. Arbitrary replacement masks must not turn executable differences into a match.

Keep distinct outcomes: published verification assertion; captured deployed-bytecode match; independently reproduced transformation comparison; local compiler reproduction. A source hash alone is not proof of compiler honesty or reachable behavior.

Package the transitive supporting files rather than copying every lane into both reports. This improves integrity, reviewability and file size together.

### 1.3 Make coverage specific and useful

Both reports used the generic LP/quotes/holder gap to support reward liveness and external-dependency Unknown ratings. Ten dimensions received the same rationale. Unknown is often the correct outcome, but that does not explain what was investigated or why a conclusion is missing.

Each applicable dimension needs a compact coverage record containing: relevance, observed checks, attempted evidence, unresolved question, access/technical limitation, deliberate skip or deadline stop, and the next check capable of changing the conclusion. Distinguish:

- Observed concern.
- Unknown after an attempted check.
- Not checked within budget.
- Outside the selected scope.
- Not applicable, with an affirmative basis.

For this round, examples include unverified main-pool position ownership, missing current size quotes, unclassified large-holder custody, unproven complete loan settlement, unresolved payout conservation, and incomplete exact-key prior-launch history. Those are different gaps and should remain separate.

Discovery must also survive assembly: source/factory universe, query, pages or ranges, exclusions, timestamp, outcome and completeness. Neither report had discovery records despite limited holder tables, last-25 transaction pages and exact-address searches. Largest-indexed-holder discovery should identify its indexer/sample; no-result searches should remain bounded negatives, not absent-history claims.

### 1.4 Allocate effort to the most consequential unknowns

The skill has extensive coverage instructions but less concrete support for deciding what to do next. Broad work can become a source checklist while canonical liquidity control, current exits or reward enforceability remain unknown.

Use a small priority queue based on holder consequence, whether the answer could change the verdict, dependencies and likely time/request cost. Exact identity and runtime come first. Then pursue material control paths, canonical LP principal authority, ordinary-holder execution/depth, and material holder/treasury rights. Explore additional websites or side mechanisms when they can resolve a remaining important question. This is a proposed scheduling heuristic, not a numerical risk score or permission to suppress dangerous powers below a monetary threshold.

Keep the distinction between specific favorable observations and overall coverage. A source-verified side-pool lock is useful, but must not consume the entire liquidity lane while the canonical pool remains unexplained. No fixed priority order overrides a user-focused question or an already demonstrated critical problem.

For multiple tokens, establish a shared deadline and per-target coverage allocation at intake. Give each exact target its own packet and verdict; share only compatible infrastructure/source work. Do not silently treat the ordinary single-investigation time target as ten minutes per token, or imply two comprehensive investigations will always fit ten minutes total. State the bounded scope and deliver Partial when required.

### 1.5 Improve holder-facing language

The strongest summary improvement is selection and precision, not length:

- “The vault reports 26 deals and 15 bids” is a direct observation. “A functioning lending system” is a broader inference until a funded→settled/defaulted→withdrawn cycle is established.
- “No transfer tax in the token runtime” and “5% fee on this pool route” can both be true. Always say which layer charges the fee and whether the value is configured, quoted, or historically realized.
- Preserve concrete product risks. OURO's report captured a claim about sealed trading venues alongside a roadmap acknowledging untaxed secondary pools and proposed migration; the final chat omitted that distinct risk.
- Explain a concentration denominator and custody category. A manager's inventory is not one pool's LP ownership, nor one beneficial holder.
- A successful bundled transaction does not by itself establish the target holder's successful trade. Distinguish bundler, smart account, token sender, router, recipient and economic beneficiary.
- A documented audit absence is different from an unsuccessful audit search. A project-run bug bounty is a useful disclosure, not an independent audit.

Add safe clickable evidence anchors, local artifact links and exact source links to the renderer. Its current findings/evidence IDs are largely escaped text, which protects against injection but makes auditing cumbersome. Preserve escaping, restrict URL schemes and keep file links within the bundle.

### 1.6 Introduce typed checks without pretending to validate prose

A synthetic reverted receipt can currently support a free-text claim of a successful sale. This is a documented semantic limitation, not evidence that the actual sampled sales reverted. Reverted receipts must remain valid evidence of failure.

An additive `historical_execution` claim type could require a successful receipt, the relevant historical pin, decoded target interaction and asset effects, asset units, and explicit actor roles. Similar bounded types could cover metadata, direct balances, configured fee values and source-runtime comparisons. Complex economic or control conclusions still require review. Avoid a validator that assumes any receipt, getter, selector or source badge establishes a safe trade or absent authority.

## 2. Concrete validation and replay defects

### 2.1 Recheck contradictions are not comprehensively validated

The collector itself performs final live pin checks. The broad bundle validator validates each pin's selected header but does not bind every other successful captured header response to that pin. A synthetic same-height recheck with a different hash passes. Repeated chain-ID evidence likewise needs consistency checks, not just the designated chain-ID row.

Validate all successful chain/header observations, including explicit request parameters, returned number/hash/time and assigned chain/pin. Failed observations can remain coverage evidence; successful contradictions must invalidate the affected state. A strict new report profile should require explicit recheck provenance for numbered state reads, or record supported canonical block-hash reads. Do not weaken existing pin requirements to obtain performance savings.

No conflicting header was demonstrated in the original GAGE/OURO evidence. This is a reproduced gap in what a future assembled bundle can get past validation.

### 2.2 A critical finding can be hidden by an unrelated Unknown

The summary guard checks whether any non-Good finding intersects a high/critical dimension's findings. A synthetic supported seizure finding can be omitted while an unrelated generic Unknown from that dimension satisfies the guard.

Attach material adverse status/impact to the actual finding, or explicitly identify the rating's required adverse findings separately from evidence gaps and mitigating observations. Require each material adverse proposition to appear in the summary. Confidence still determines whether it is presented as Potential Risk or Bad; do not force allegations or unknowns into Bad.

This requires more structure than checking the presence of a colored summary row. The current example tests cover simple omission, not mixed adverse/coverage references.

### 2.3 Collector success can include malformed reusable state

An offline mocked `eth_getBalance` response of `not-a-hex-quantity` was accepted as a complete collection, accepted by `load_collection`, and reused from cache on the next same-target collection. The broad report validator is stricter and rejects malformed balance quantities. The result therefore demonstrates inconsistent enforcement across layers, not a demonstrated false broad-report pass.

Centralize lightweight method-specific wire validation before declaring a record successful or inserting it into reusable cache. Keep semantic decoding separate. Treat malformed responses as explicit protocol/data errors and preserve raw evidence. Validate legacy cache entries on read or version the validation assumptions; do not silently wipe all cache history. Align strict JSON-RPC ID type handling and error shape checks across collector, collection loader and broad validator.

Relevant code: `rpc_collect.py` fetch/store path around lines 326–355 and `backend_common.py` collection loading around lines 124–137. Nearby regressions should cover empty valid code, standard revert responses, invalid hex/widths, nulls, mismatched IDs, and cache replays.

### 2.4 Freeze the reporting engine needed to replay reports

Collector snapshots include `validate_bundle.py` but omit `render_report.py`; neither selected report includes a frozen renderer. The renderer inserts its currently imported reporting version into the output. A version-only monkeypatch changed both report outputs even though their frozen JSON sources stayed identical.

This is a reproducibility gap, not an actual change to the saved reports. Freeze the required reporting tool files and a profile/version manifest with each report, or provide an explicit compatible replay mechanism. Test both kinds of compatibility: validation of old supported data and byte-identical reproduction of old rendering with its original engine. Preserving no-summary legacy fixtures alone is insufficient for existing summary-bearing reports.

Use strict current-profile validation for newly assembled reports while retaining documented legacy paths. Engine/profile/schema changes must be versioned independently and mirrored to Claude Code after acceptance.

## 3. Performance and source access

### 3.1 Eliminate repeated ad hoc bootstrap and report code

The last run wrote custom code to discover the head, generate plans, compute selectors, extract a proxy address, combine evidence and build reports. A hand-copied proxy address was malformed and rejected. Later, importing the plan helper ran its top-level code again and rewrote a loose OURO plan with the wrong address. The collector's frozen plan retained the correct address, so its original evidence was preserved; nevertheless, the loose reproduction plan no longer matched it.

Add small supported helpers with no import-time file writes:

1. A bounded bootstrap operation using the existing provider gates: chain verification, head discovery, explicit pin capture, target code and metadata, and plan/capability output.
2. Exact runtime classification/extraction for recognized proxy forms, with unsupported variants left unresolved.
3. ABI-derived calldata/decoding support for the small common read set; prefer available compiler method identifiers or a verified implementation. Do not write a new cryptographic primitive during time-limited diligence.
4. An incremental collection-to-bundle assembler that preserves artifacts, remaps IDs deterministically, binds sources/derived inputs, and requires explicit finding semantics.
5. An early draft/coverage skeleton, followed by one final freeze, validate, render and rendered-file check.

The initial collector-to-report conversion failed because collection-level chain evidence has `pin_id: null` while report evidence requires a valid pin. A supported importer must distinguish chain-level provenance from observed state; it must not invent a block at which chain-ID discovery happened merely to fill a field. Existing schemas may need an explicit chain-level evidence representation or a documented contextual association.

### 3.2 Interpret caching accurately

All 64 non-header/non-chain queries in the run were unique. Therefore zero cache hits does not establish a broken cache. The existing tests and audit probe show that an identical pinned read under the same target is reused, with fresh chain/header checks retained.

However, cache keys also include the report target. The same read of the same surrounding address at the same pin misses when the report target changes. Separate a run-scoped transport read identity from target-specific report provenance if cross-target deduplication is added. Retain chain, queried address, method, canonical parameters/caller, block hash, provider namespace and synthetic/live separation. Never reuse source analysis as another instance's storage/authority state. Do not enable cross-investigation state reuse in conflict with the fresh-run requirement.

Seven invocations caused 25 chain/header control reads. A coordinator-owned session can consolidate some setup across compatible work, but the exact savings are unmeasured and not all 25 reads are redundant. Preserve fresh checks at appropriate acquisition/reorg boundaries. Global request/time accounting should cover bootstrap, failures, capabilities, state reads, traces and rechecks across all calls. A request cap remains distinct from a financial cap.

### 3.3 Keep workers busy without losing evidence order

`request_many` waits for each wave of up to four requests before launching another. One slow request leaves the other slots idle.

An eight-request synthetic workload with two 150ms responses and six 10ms responses took approximately **0.324s** through the current collector. A scheduling-only rolling executor comparison took **0.168s**. That comparison excludes collector packaging work and is not a validated replacement or a live speedup claim. The timelines do demonstrate unused worker capacity.

A production change would require bounded in-flight work, a coordinator-owned request budget, prompt failure validation, stable request/result identities, deterministic output ordering, bounded buffering, final recheck reserves and receipt-before-trace dependency barriers. Simply yielding `as_completed` results into the existing ordered `zip` would misbind responses. Do not add a faster loop without those regressions.

### 3.4 Route sources by demonstrated capabilities

The run tried several blocked explorer/API routes before finding useful hidden pages and Sourcify source data. The lesson is to maintain a cheap, scoped capability record, not permanently blacklist a service after one 403 or assume a browser and API fail together.

Record HTTP status, sanitized failure category, endpoint operation, tool/access mode, retrieval time, request duration, bytes and outcome. Current generic `HTTPError`/`URLError` records cannot reliably distinguish authentication, throttling, missing records or sandbox DNS failure. Never log private URLs, headers or arbitrary exception bodies to improve diagnostics.

Add a first-class Sourcify lookup adapter, particularly when the project supplies a verified-source link. Official documentation now specifies v2 contract lookup and says the v1 API was retired on July 7, 2026. This is a confirmed current API change, not a timeless inference from one 404. Use selective fields when supported and expand to required source/compiler/bytecode data only for material contracts. [Sourcify API documentation](https://docs.sourcify.dev/docs/api/).

Recognized ERC-1167 runtime has an exact address location; parse and validate the bytes rather than copying hex manually. Still inspect the pointed-to implementation and instance initialization. Variant or custom runtimes need separate classification. [ERC-1167](https://eips.ethereum.org/EIPS/eip-1167).

Preserve background/hidden access, source ownership, fresh reads, API permission boundaries and bounded fallbacks. A new host authorization decision, paid-provider configuration or source authentication cannot come from the capability cache or memory.

### 3.5 Avoid optimizations without a demonstrated need

- **JSON-RPC batches:** potentially reduce HTTP overhead, but count individual method attempts, map response IDs independent of order, handle partial errors, enforce byte/capability limits and preserve pins. Provider support and latency benefits are unverified here; concurrency already exists.
- **Multicall:** changes call context for target contracts and may change getter behavior. It is not automatically equivalent to separate `eth_call` reads.
- **HTTP connection reuse:** benchmark before adding a dependency or custom transport. Preserve redirect refusal, authentication and redaction.
- **SQLite WAL or writer threads:** the current design has one SQLite writer on the coordinator thread. WAL does not create multiple simultaneous writers and is not an obvious fix for this workload. Transaction batching can be evaluated later against crash durability. [SQLite WAL documentation](https://www.sqlite.org/wal.html).
- **Log collection:** per-block hash reads have strong provenance but can be expensive. Keep narrow transaction/indexer discovery as the default. For explicit historical work, consider bounded range adapters with pagination, truncation handling, event-block/header reconciliation and reorg checks; do not replace pinned reads with unconstrained `latest` or unverified range summaries. Block-hash read support must be checked per provider. [EIP-1898](https://eips.ethereum.org/EIPS/eip-1898).
- **Detector loops:** current transfer accounting uses integer arithmetic and hash/set aggregation over supplied receipts; no quadratic bottleneck was demonstrated. Optimize source acquisition, useful coverage and assembly before these small loops.
- **Prompt loading:** entrypoint is 2,231 words; all procedure references total about 20,836 words. Broad startup should load the common essentials once and select platform/trigger sections progressively. The last run repeatedly dumped long references and suffered tool-output truncation. Reduce duplicated provider prose while preserving the actual policy checks; do not turn memory into another always-loaded manual.

## 4. Operational memory design

### 4.1 What already exists

`maintain.py` already appends evidence-linked feedback to SQLite. It verifies collection/evidence references and preserves synthetic gates. It does not edit detection rules. This is a useful foundation.

It lacks deduplication, review status, applicability/version context, resolution, retirement and bounded retrieval. Offline tests accepted duplicate identical feedback and a 41,000-character note. `list` returns the entire feedback table. Both latest-run caches contained zero feedback records despite useful operational lessons in Markdown.

There is also a documentation mismatch: the improvement loop describes shared SQLite history, while the research workflow requires a fresh cache per investigation. A separate feedback DB can technically be supplied today, but that distinction is not designed into the workflow. Separate persistent operational history from fresh RPC evidence caches explicitly.

### 4.2 Recommended two-stage lifecycle

**Automatic capture:** each investigation may write a small `operational-feedback.json` in its own run directory. Capture only material observed failures/recoveries, decoding issues, omitted checks, or assembly problems. Include what actually happened and whether a proposed recovery actually worked. Do not require the run to become a valid collection before recording an operational failure; identity failures and browser-only problems need their own artifact provenance. Keep recording offline and within the delivery reserve.

**Reviewed reusable guidance:** promote a narrow, reproduced lesson into canonical `memories.md` through the existing maintenance workflow. A future skill reads only relevant active entries. Mirror the same reviewed entries to Claude Code; do not let each copy learn divergent policies. Retire a memory once a tested helper/reference implements it, leaving a small pointer or archive entry instead of duplicate instructions.

This is deliberately more reliable than automatically appending arbitrary prose to the skill and treating it as truth. It still learns: runs capture experience automatically; maintenance converts demonstrated patterns into tested procedures. If full automatic cross-run retrieval is desired, a separate schema-validated operations store can supply untrusted hints, but it adds concurrency, redaction, retrieval and lifecycle complexity. It should not be the first implementation.

### 4.3 Minimal observation and memory fields

Observation: schema version, ID, component/operation, category, relevant tool/provider mode and version, observed time, symptom, exact observed outcome, proposed recovery, recovery status, source artifact path/hash, optional collection digest, and bounded impact such as repeated requests or lost coverage.

Promoted memory: stable ID, status, relevance trigger, applicability/version scope, concise action, limitations, verification/test provenance, last reviewed date, recheck/expiry condition and supersession link. Keep occurrences separate from the deduplicated lesson. A content key alone must not merge different authentication modes, network contexts or tool versions.

Suggested initial bounds are at most a few new observations per run and roughly 10–20 concise active memories, with bounded per-entry and total read sizes. These are proposed operating limits, not measured optima. Deterministic metadata filtering is sufficient initially; embeddings, a vector database, or a separate model call are not justified by this small corpus.

### 4.4 Trust and freshness rules

Allowed: generic source-access procedures, parser/decoder corrections, tool capability handling, evidence-assembly lessons and regression identifiers. These help choose a method, then fresh evidence must establish the target facts.

Excluded: token verdicts, balances, holder percentages, owners, fees, lock dates, creator allegations, assumed liquidity, private endpoints, credentials, paid-use approval, account budgets and instructions copied from retrieved sites. Public infrastructure addresses, if needed, belong in a versioned chain adapter and still require fresh identity/runtime verification; they should not be remembered as universal truth.

A candidate is untrusted data, even when generated by an agent. It cannot authorize actions, alter thresholds, remove unknowns, skip validation or execute a command. An HTTP 403 is scoped evidence about one request, not “this source never works.” Failure to load, validate or write memory should not stop research or turn a token check into a pass/fail.

The current freshness rule should explicitly allow reviewed generic operational lessons while continuing to prohibit opening old token run directories as research evidence. Historical run references can remain maintenance provenance; normal research should not follow them to recover token facts.

### 4.5 Concrete initial lessons

A [draft memories file](memories.draft.md) is included for review, outside the installed skill. It contains candidates for current Sourcify lookup, exact proxy extraction, import-safe helpers, evidence-aware assembly and scoped access recovery. Methodology such as bundler attribution and principal-versus-fee custody belongs in the main maintained procedures; do not make essential diligence rules depend on optional memory.

The next step after adoption is to measure whether entries prevent repeated mistakes. Track recurring issue rate, successful recovery, requests/time avoided, irrelevant memory reads, stale entries and any new false certainty. A profitable token call does not validate the memory system.

## 5. Implementation order and acceptance criteria

### Stage 1: Evidence and validation correctness

Add regressions for contradictory rechecks/repeated chain IDs, hidden critical findings, malformed reusable RPC, explicit subjects and missing derived-source dependencies. Implement narrow fixes and a strict current-report profile. Keep old valid artifact replay paths explicit and preserve original evidence bytes. Do not downgrade checks merely to make existing incomplete bundles pass a stronger profile.

Acceptance: all mechanically detectable contradictions are rejected; failed/null/reverted evidence remains usable for truthful unknown/failure findings; a critical concern cannot disappear behind a generic gap; changing a required source input invalidates its derived proof; cross-contract claims retain correct actors.

### Stage 2: Supported bootstrap and assembly

Implement small reusable helpers rather than a general autonomous research engine. Create report/coverage structure at intake, import collections with provenance, collect exact source dependencies and require structured lane handoffs. Add validated clone extraction and source-correspondence support. Generated helpers must have no import-time mutations and must preserve raw inputs.

Acceptance: a two-token synthetic scenario completes using supported commands without writing throwaway cryptography, head-discovery or report builders; no malformed address reaches HTTP/RPC; no invented metadata/pin/approval; each surface has a specific outcome; source IDs and timestamps survive handoff and report rendering.

### Stage 3: Workflow and measured performance

Add session-level request/deadline accounting, per-target coverage priorities, source capability records and detailed timing. Evaluate rolling scheduling under mixed latency, errors, duplicates, deadline exhaustion and receipt dependencies. Consider shared exact-read reuse within one investigation after transport provenance is separated from report identity.

Acceptance: critical checks gain measured coverage within the same budget; aggregate limits cannot reset through another collector invocation; duplicates map to the correct evidence; no stale cross-run state reuse; no unbounded scheduling, response buffering or retries. Compare repeatable fixture outputs and several explicitly authorized fresh runs before claiming live speed or accuracy improvements.

### Stage 4: Memory, readability and replay

Enable bounded run-local operational feedback, deduplication and reviewed promotion to `memories.md`. Add safe navigation and frozen reporting tools. Keep optional memory independent from provider configuration.

Acceptance: duplicate/oversized/malicious observations do not become instructions; concurrent candidates do not overwrite one another; corrupt/missing memory is non-blocking; temporary source failures can recover; no token state or permission is reused; canonical and Claude memories stay consistent; old reports render with their saved engine.

### Verification and release boundaries

Run the four README unittest suites, the Claude mirror suite, new failure regressions and independent scenario reviews. Add end-to-end fixture tests that go from discovery artifacts through collection/import to report, because isolated validator tests cannot demonstrate research quality. Include near-neighbor non-error cases to prevent overfitting the GAGE/OURO example.

Use workflow version changes for instruction/memory policy changes, backend changes for collection/cache/maintenance behavior, reporting changes for validation/rendering, and a new schema/profile where required. Choose exact version numbers after implementation scope is settled. Preserve code/evidence snapshots; canonical changes precede the documented Claude port transformation. Do not create a second Codex or Personal EVM registration.

No live token rerun is needed just to format or mechanically replay the audit. A live performance benchmark should have explicit scope, a fresh investigation, bounded authorization and stated measurement limits.

## Deliverables and limits of this audit

This analysis, the proposed memory file and an acceptance checklist are review artifacts. Independent reporting and memory reviewers accepted the final analysis and design with no material corrections. Local Markdown links were checked, and the audited skill source fingerprint remained unchanged. No production skill changes, commits or pushes were made. Existing tests passing and synthetic probes are not a live performance benchmark or a complete proof of the skill's financial reasoning. The findings identify concrete gaps and a practical implementation order without changing the research rubric, optional dRPC policy, fresh-evidence rule, or cautious treatment of unknowns.

Reproduction material: [reporting audit](../../research/2026-09-08-evm-skill-audit-1356/independent-reporting-audit.md), [reporting probes](../../research/2026-09-08-evm-skill-audit-1356/reporting-repro.py), [performance harness](../../research/2026-09-08-evm-skill-audit-1356/performance_repro.py), [replay probe](../../research/2026-09-08-evm-skill-audit-1356/replay_probe.py), [memory audit](../../research/2026-09-08-evm-skill-audit-1356/independent-memory-audit.md).
