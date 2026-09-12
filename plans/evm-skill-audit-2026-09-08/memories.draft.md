# Proposed operational memories

**Review draft; not installed or automatically loaded.** These entries describe reusable procedure lessons. They are not token evidence, permissions, executable commands, or universal claims about source availability. Normal research must establish fresh exact identities, pins and state. Do not open earlier token runs to supply findings.

Proposed lifecycle: candidate observation → verified lesson → active guidance → superseded/retired. Automatically record candidates in the fresh investigation directory; promote entries through authorized maintenance. Keep a small relevant active set, deduplicate repeated issues, and retire guidance implemented in a tested helper/reference. Missing or corrupt memory is non-blocking. Never store credentials, private endpoints, paid-use approvals, token verdicts, balances, owners, fees, lock dates or wallet allegations here.

## OPS-001 — Use the current source API

- Status: proposed for promotion; verified operational recovery and current public documentation.
- Trigger: a material EVM contract needs source/ABI/compilation provenance, especially when a project supplies a Sourcify link.
- Guidance: use the current documented read-only contract lookup interface. As checked September 8, 2026, this is Sourcify `/v2/contract/{chainId}/{address}`; request the fields needed for the current check. A repository UI URL is a browsing surface, not an assumed API layout.
- Boundary: source records and verification labels require comparison to this investigation's runtime. No source record at one service does not establish source absence everywhere. Do not submit a verification job as part of a read-only lookup.
- Verification: [official API documentation](https://docs.sourcify.dev/docs/api/); the maintenance audit reviewed a fresh-run recovery from an unsuccessful legacy lookup to v2.
- Recheck: API version or response-shape change, endpoint error, or stale documentation. Supersede this entry when a maintained adapter with regression coverage supplies the behavior.

## OPS-002 — Extract recognized proxy addresses from bytes

- Status: proposed for promotion; observed copy error and standards-based correction.
- Trigger: captured runtime appears to be a recognized minimal clone.
- Guidance: validate the complete supported runtime pattern, extract the 20-byte implementation programmatically, and validate its length before issuing another request. Standard ERC-1167 places the implementation at byte offsets 10–29 inclusive. Preserve the input code hash and extraction result as derived evidence.
- Boundary: a partial pattern or nonstandard clone is not resolved by this recipe. Inspect implementation code, initialization and instance state; a fixed pointer does not close surrounding administration or dependency risks.
- Verification: [ERC-1167 specification](https://eips.ethereum.org/EIPS/eip-1167) and the audit's malformed-address observation. A production parser still needs valid, invalid, truncated and variant fixtures.
- Recheck: runtime does not match the supported pattern. Retire after the supported extractor and tests ship; retain only a reference to the helper.

## OPS-003 — Import helpers must not regenerate artifacts

- Status: proposed for promotion; reproduced plan-provenance mismatch.
- Trigger: composing helper functions or reusing a script during an investigation.
- Guidance: imports should define functions without creating or overwriting files. Put mutations behind an explicit CLI/main entrypoint; create fresh output paths and preserve the collector's captured plan as the authority for what was actually executed.
- Boundary: do not silently repair or replace a frozen plan/evidence artifact when a loose planning file differs. Diagnose the discrepancy and preserve both.
- Verification: the audit observed an import re-running top-level plan generation; the frozen collection retained its correct plan while a loose plan changed.
- Recheck: new helper or changed CLI interface. Retire once this behavior is covered by the relevant helper's import-safety tests and maintained guidance.

## OPS-004 — Assemble evidence with explicit subjects and dependencies

- Status: proposed workflow lesson; supporting audit probes reproduced current gaps.
- Trigger: combining collections, source records and lane notes into a report.
- Guidance: explicitly identify the subject contract/actor, evidence class and direct supporting inputs for each finding. Register derived calculations and source comparisons with their input artifacts. Carry discovery coverage into the formal ledger. Preserve chain-level evidence as chain-level provenance rather than inventing an observed state block.
- Boundary: token runtime is not direct proof of a different contract's authority. A hash of a conclusion table does not bind unregistered input source files. Mechanical validation cannot certify arbitrary prose.
- Verification: offline reporting audit reproduced mis-scoping and deletion of an unbound source without validator failure.
- Recheck: new report profile/schema. Retire once an assembler and strict profile enforce the relevant behavior; essential evidence standards belong in maintained references, not optional memory alone.

## OPS-005 — Record source failures by operation and access mode

- Status: proposed operational lesson; scope-specific access failures observed.
- Trigger: API, web fetch, browser read or export fails.
- Guidance: retain sanitized status/category, operation, tool/access mode and time. Use an authorized bounded alternative when it can provide the missing fact. A working browser view and a blocked API can coexist. Preserve accessible source observations even if an optional export capability is unavailable.
- Boundary: do not infer global service failure, zero activity, absent source, or token risk from one failed request. Do not fabricate a raw export by labeling a manual transcription as exported data. No new credential, endpoint or spending authority comes from this memory.
- Verification: current-invocation source recovery observations were reviewed during maintenance; future availability needs a fresh check.
- Recheck: every new investigation in which this capability matters; do not carry a permanent negative result forward. Retire after capability-aware capture is implemented.

## Proposed read/write policy

Read only relevant active entries, with a bounded total size. A practical starting point is no more than a few new candidate observations per run and approximately 10–20 concise active entries, then adjust from measured value. These are design limits, not tested performance thresholds.

Record candidates offline without delaying report delivery. Keep raw source text and quotations outside this file. A candidate may describe a proposed recovery, but only a demonstrated successful recovery can be promoted as a verified solution. Canonical and Claude Code copies must share the same reviewed lesson set. Explicit user restrictions and trusted current project configuration always take precedence.
