# EVM skill implementation — September 8, 2026

The user authorized all four stages of the saved audit. Each stage receives its own implement, review, improve and verify cycle; subsequent stages are already authorized. The audit files predate this implementation and remain unchanged. No live provider requests, credentials, historical artifact edits, commits or pushes are needed.

## Execution record

| Stage | Status | Verification and review |
| --- | --- | --- |
| 1. Evidence and validation correctness | Complete | 196 EVM tests pass. Direct diff review and independent negative probes; fixes cover dependency taint, effect actor/duplicate binding, recheck aliasing, full header contradiction checks, and coverage-state consistency. |
| 2. Supported bootstrap and assembly | Complete | 206 EVM tests pass, including two-target CLI workflow and source-input replay. Independent controls review found executable-CBOR masking and zero-address ABI rejection; both fixed with regressions. Direct review also excluded escaping/unreferenced files from freeze. |
| 3. Workflow and measured performance | Complete | 216 EVM tests pass; independent review verified effective deadline, pending-response preservation on cache failure, and mandatory live API sessions. Synthetic full-collector median: rolling 0.099509 s versus wave 0.181871 s, same 11 attempts; no live claim. |
| 4. Memory, readability and replay | Complete | 240 EVM tests pass; independent memory/replay findings fixed and reverified; both copies synchronized; all release checks pass. |

Validation uses the README standard-library unittest suites plus new failure/near-neighbor fixtures, independent scenario review, canonical/Claude parity, and frozen research provenance checks. Synthetic timings will be labeled synthetic; no live speed or research-accuracy improvement will be claimed from them.

Explicitly deferred by the audit: JSON-RPC batching, Multicall, a new HTTP client, SQLite WAL, vector memory, and broad unpinned log scanning. These are evaluation ideas without demonstrated need, not required implementations.

## Final result

All four stages are implemented, reviewed and verified. Backend **3.0.0**, reporting
**2.0.0**, workflow **2.0.0**. Live Python/CLI collection and source lookup require a
shared investigation session; reporting CLIs require `evm-evidence-v2` by default.
Explicit `legacy-v1` preserves historical rendering. Collection/cache/bundle schemas
remain 1, cache keys use version 2, and detector rules remain 1.0.1.

Final suites: canonical EVM **240** on Python 3.14 and Python 3.10; Claude EVM **240**;
research **31**; rug **18**; Solana **23**, all passing. The EVM baseline was 172 tests;
68 new cases cover the behavioral changes. All four README suites and the mirrored
suite pass. `git diff --check`, local skill links, release-record paths, memory payloads,
project-only registration and canonical/Claude source parity pass. There are no
remaining actionable findings from the independent reviews.

Original GAGE/OURO manifests, report sources and outputs validate in explicit legacy
mode and render byte-for-byte identically. All 99 report evidence records, seven
original collections and 35 frozen collector source files retain their registered
hashes. See `release-verification.json`. Frozen history and
original research were not modified. No provider/RPC/token research was rerun; only
public technical documentation was fetched during maintenance. No credentials were
read, and nothing was committed or pushed.

## Review findings repaired

- Stage 1: failed derived-input taint, cross-chain/duplicate execution effects,
  receipt-log shape, inference labeling, distinct recheck evidence and coverage-state
  consistency; all successful chain/header observations are checked for contradictions.
- Stage 2: arbitrary executable CBOR masquerading as metadata, valid zero-address ABI
  encoding, and escaping/unreferenced file handling during freeze.
- Stage 3: reserve time against the effective shared deadline, preserve every started
  response after cache/start failure, and prevent live API callers omitting the session.
- Stage 4: persist review/observation hashes and enforce applicability; reject injection
  through alternate fields; survive deeply nested corrupt JSON; cap feedback across
  the session directory; stream bounded artifact hashes; tolerate unavailable POSIX
  locking; serialize conflicting ingestion and legacy feedback deduplication; use UTC
  expiry; isolate replay from unlisted import modules/bytecode; link supported source
  URL arrays and verify registered evidence integrity.

Independent review artifacts remain in ignored maintenance directories:
[controls stage 2](../../research/2026-09-08-evm-stage2-independent-controls/review.md),
[controls stage 3](../../research/2026-09-08-evm-stage3-independent-controls/review.md),
[memory stage 4](../../research/2026-09-08-stage4-memory-audit/review.md), and
[report replay stage 4](../../research/2026-09-08-stage4-report-replay-review/review.md).
The memory review includes independent before/after concurrent-write probes; the
report review includes a harmless unlisted-import reproduction and original report
comparisons. These are maintenance probes, not live token evidence.

## Acceptance reconciliation

Rows follow the original 34-row checklist (`acceptance.md`), which is preserved as the
pre-implementation test plan. “Guidance” below identifies a human/coordinator boundary;
mechanical validation cannot certify arbitrary financial prose or hidden tool behavior.

| # | Required scenario | Result and evidence |
| --- | --- | --- |
| 1 | Contradictory successful chain ID/header | Pass: strict profile/wire tests reject additional contradictions and preserve raw data. |
| 2 | Unavailable numbered recheck | Pass: no verified-current-state result; failed/reused rechecks rejected. |
| 3 | Canonical block-hash reads | Pass: explicit canonical profile accepts supported hash reads without invented numbered rechecks. |
| 4 | Critical finding hidden by unrelated Unknown | Pass: every high/critical adverse finding must appear in summary. |
| 5 | Wrong subject/runtime supports another contract | Pass: subject/participant/role gates and unrelated-anchor negative case. Claim meaning remains reviewed. |
| 6 | Removed/modified derived input | Pass: digest-bound dependency closure, taint/cycle tests and reproducible source comparison. |
| 7 | Incidental unreferenced note | Pass: allowed, not evidence; excluded from freeze. |
| 8 | Executable replacement masquerading as metadata | Pass: compiler-bound transforms; executable-CBOR and arbitrary-mask regressions. |
| 9 | Reverted transaction called successful sale | Pass: typed receipt status gates; revert remains evidence of failed execution. |
| 10 | Bundled transaction without target effects | Pass: success requires unique decoded target effects with bound actors/asset/units; no sender-as-seller default. |
| 11 | Missing broad discovery or generic gaps | Pass: nonempty bounded discovery and eleven specific coverage records; lane/intake guidance preserves distinct surfaces. |
| 12 | Malformed successful RPC data | Pass: preserved malformed-data gap; cannot enter reusable successful cache. |
| 13 | Valid empty code/revert/unsupported getter | Pass: valid wire observations retained, semantic limitation explicit. |
| 14 | Repeated identical pinned read | Pass: exact read reused within shared investigation with fresh final rechecks. |
| 15 | Address/caller/block/provider/mode differs | Pass: cache key separation regressions; runtime equivalence never supplies storage state. |
| 16 | New investigation | Pass: new session namespace/pins/fresh cache guidance; memory supplies no state. |
| 17 | Invalid bootstrap address/budget | Pass: offline failure before provider requests. |
| 18 | Import helper twice | Pass: no network/file creation from imports; mutations require entrypoints. |
| 19 | Second target resets budget | Pass: two-target CLI flow and multi-connection aggregate/deadline tests. |
| 20 | Mixed rolling requests | Pass: bounded in-flight work, deterministic rows, duplicate suppression and started-response preservation. |
| 21 | Exhaustion or missing receipt | Pass: shared reserves survive; dependent trace remains skipped/unavailable. |
| 22 | Browser works/API or export fails | Pass at supported boundary: scoped acquisition fields, browser-only candidate tests and explicit snapshot/transcription guidance. No new universal browser/export adapter claimed. |
| 23 | Repeated issue | Pass: idempotent ingestion, context-specific issues, distinct occurrences and run counts. |
| 24 | Huge/injected/secret-like/unsupported candidate | Pass: bounded schema/text guards and negative fixtures; semantic sanitization still requires review. |
| 25 | Initial chain/pin/browser failure | Pass: automatic bootstrap/invalid-collection capture and hash-bound browser artifacts without usable collection. |
| 26 | Never-successful proposed recovery | Pass: cannot promote; success, applicability and review provenance required. |
| 27 | Missing/corrupt/expired/irrelevant memory | Pass: empty non-blocking retrieval, including supported Python 3.10 recursion behavior. |
| 28 | Concurrent writes | Pass: locked atomic capture, serialized conflicting store imports and legacy dedup; independent before/after probes. |
| 29 | Approval or token fact offered as lesson | Pass at supported boundary: explicit exclusion policy, address/credential/approval-like text guards, no state/policy ingestion; human review remains necessary. |
| 30 | Fix moves into maintained helper | Pass: initial five lessons are retired, zero active entries; review and original draft hashes preserved. |
| 31 | Claude port | Pass: byte-identical code/tests/memories, only documented tool/path/release differences; 240 tests pass. |
| 32 | Reporting version changes | Pass: frozen dependency/profile replay ignores installed-version change; old reports reproduce exactly. |
| 33 | Malicious links/Markdown/HTML | Pass: safe text, allowlisted web links, confined artifact paths; injection/escape/import-shadow tests. |
| 34 | Faster synthetic benchmark | Pass: same 11 attempts; rolling median 0.099509 s versus waves 0.181871 s across three synthetic trials. No live claim. |

## Changed files and handoff

Canonical [SKILL.md](../../skills/crypto-evm-token-due-diligence/SKILL.md) now routes the
common path to [supported research flow](../../skills/crypto-evm-token-due-diligence/references/supported-research-flow.md),
[strict report profile](../../skills/crypto-evm-token-due-diligence/references/strict-report-profile.md),
[improvement lifecycle](../../skills/crypto-evm-token-due-diligence/references/improvement-loop.md)
and [replay](../../skills/crypto-evm-token-due-diligence/references/report-replay.md).
[Memories](../../skills/crypto-evm-token-due-diligence/memories.md), templates, release
metadata, source-routing, evidence/output, bundle/backend references and README are updated.

New scripts: `rpc_wire.py`, `report_profile.py`, `bootstrap.py`, `evm_decode.py`,
`source_lookup.py`, `bundle_assemble.py`, `investigation.py`, `operations.py`,
`render_legacy_v1.py`, `report_replay.py`. Updated scripts: `backend_common.py`,
`rpc_collect.py`, `validate_bundle.py`, `render_report.py`, `maintain.py`.
Six new test suites and a synthetic benchmark supplement updated backend/CLI fixtures.
The complete canonical changes are mirrored under `.claude/skills/` with documented
port differences; no new Codex registration exists. This implementation record,
benchmark results, memory review and release verification are new maintenance artifacts.
The original audit analysis, checklist and memory draft remain unchanged.

Remaining limits are deliberate: source comparison uses Sourcify-published compilation,
not independent local compilation; uncommon runtime transformations remain unresolved;
text/schema checks do not prove financial truth; external-tool charges conservatively
account for hidden internal requests; scheduling deadlines are not OS/DNS watchdogs;
replay opts into trusted local Python execution, not a hostile-code sandbox. Missing
feedback is non-blocking, and research never automatically modifies installed code or
active guidance. The audit's deferred batching/Multicall/HTTP-client/WAL/vector-memory
ideas remain deferred because no measured benefit justifies that complexity.

Suggested commit message: `Improve EVM diligence evidence, performance, operational memory and replay`
