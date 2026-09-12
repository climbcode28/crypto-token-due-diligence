# Proposed implementation acceptance checklist

This is an implementation test plan, not a claim that proposed improvements have shipped. Existing tests pass; the audit's negative probes demonstrate current gaps.

| Area | Scenario | Required outcome |
| --- | --- | --- |
| Chain/pins | Additional successful chain-ID or same-height recheck contradicts the selected observation | Reject the affected identity/state; preserve raw contradiction |
| Chain/pins | Recheck is unavailable; numbered state lacks required completed recheck | Preserve evidence gap; no verified-current-state pass |
| Chain/pins | Canonical block-hash read is explicitly supported and recorded | Apply its documented profile without inventing numbered rechecks |
| Summary | Critical adverse finding and unrelated Unknown share a dimension | Actual adverse proposition remains mandatory in summary |
| Finding scope | FeeSink owner or seed-lock claim uses unrelated token code as support | Require explicit subject/participant and direct evidence roles |
| Evidence chain | Required source input removed or modified after derivation | Derived proof validation fails |
| Evidence chain | Incidental unreferenced note is present | Allowed without treating it as evidence; no need to hash every unrelated file |
| Source match | Arbitrary executable-byte replacement masquerades as metadata/immutable substitution | Reject the claimed match; preserve mismatch |
| Executions | Reverted receipt claims a successful sale | Typed successful-execution check fails; receipt can still prove a revert |
| Executions | Successful bundled transaction lacks decoded target effects | Target sale stays unproven; bundler is not assumed seller |
| Coverage | Broad report has no bounded discovery records or uses LP uncertainty for rewards | Specific discovery/surface accounting required |
| Collector | Malformed code/balance/storage result has a successful RPC envelope | Explicit malformed-data gap; no reusable successful cache entry |
| Collector | Standard revert, empty valid code or unsupported getter | Preserve correct wire-level observation and semantic limitation |
| Cache | Identical pinned read repeated in one investigation | Reuse permitted result with correct identity and provenance |
| Cache | Same runtime but different address, caller, block, provider or synthetic/live mode | No invalid state reuse |
| Cache | New investigation | Fresh state/pins/cache; operational memory supplies no token facts |
| Bootstrap | Invalid address or insufficient budget | Fail offline before provider request |
| Helpers | Module imported twice | No generated/overwritten artifacts or network calls |
| Multi-target | Second collector is launched after partial use of shared cap | Aggregate cap/deadline cannot reset; preserve per-target evidence |
| Scheduling | Slow, fast, duplicate, failing requests mixed under rolling execution | Bounded in-flight work; stable identities/order; complete started-attempt records |
| Scheduling | Budget/deadline exhausted or receipt unavailable | Reserve/attempt checks survive; dependent trace skipped without invented evidence |
| Capture | API blocked but browser view works; browser export unavailable | Scoped outcome and honest snapshot/transcription provenance |
| Memory | Identical issue recurs | Deduplicate lesson, retain distinct occurrences and context |
| Memory | Huge note, injected instruction, secret-like data or unsupported schema | Reject/quarantine candidate; never promote verbatim or expose credentials |
| Memory | Initial chain/pin failure or browser-only problem | Record operational artifacts without fabricating a usable collection |
| Memory | Proposed solution has never succeeded | Remains unverified; not promoted as a solution |
| Memory | Missing, corrupt, expired or irrelevant file | Research continues normally; no passing token check inferred |
| Memory | Concurrent writes | No lost/corrupt entries; one coordinator or atomic conflict handling |
| Memory | Paid authorization or token-specific fact is offered as a lesson | Exclude; current trusted policy and fresh evidence remain authoritative |
| Memory | Fix moves into tested helper/reference | Supersede/retire redundant memory |
| Port | Canonical update accepted | Apply documented Claude differences and rerun both suites; no new registration |
| Replay | Reporting version changes with old report JSON unchanged | Original rendering reproducible using frozen reporting engine/profile |
| Links | Malicious URL/Markdown/HTML in metadata or evidence | Safe text/allowed links only; local links confined to bundle |
| Benchmark | Synthetic scheduler result is faster | Report synthetic scope; no unmeasured live speed/accuracy claim |

Release checks: all four README suites; Claude EVM suite; new regression fixtures and near-neighbor non-error cases; independent scenario evaluation; original evidence immutability check; source/port diff review; version/profile/schema compatibility assessment. Run a live benchmark only as a separately scoped, bounded fresh investigation when authorized.
