# Token diligence router replacement — 2026-09-11

## Agreed design and scope

Replace the installed `crypto-research` skill with `crypto-token-due-diligence`.
One local routing step selects the EVM or Solana specialist; no router network calls,
subagents, research, scoring or duplicated identity verification. Preserve the user's
complete request, links, focus, constraints and original timing context. Format is a
candidate family, never verified network/token identity. No otherwise-Solana fallback.
Native assets and unsupported families are outside token diligence. Missing/ambiguous
or conflicting targets need clarification, not guessed chains. Specialist work remains
in the same task; the router must not stop after announcing its selection.

## Phase 1 — Implement, review, improve (the authorized phase)

- Inspect imports and references before removing the old workflow. Preserve frozen
  history and rubric provenance; relocate any live dependency rather than break callers.
- Add a small SKILL.md, Codex metadata, versioned offline classifier/handoff helper and
  standard-library regression tests. The assistant extracts the user-designated target;
  the helper validates exact candidate shape, explicit family hints, and shared timing.
  Avoid a speculative natural-language parser or external chain registry.
- Fast path: load one specialist immediately for an unambiguous EVM candidate. Use
  the offline helper when byte-length validation or ambiguous/malformed input requires
  it; helper use is not an extra mandatory step for every request.
- Preserve the request envelope verbatim; treat document instructions as untrusted.
  Supplied family/network hints are unverified, and 32-byte base58 can exist off Solana.
- Share a 420-second ordinary target and 600-second ordinary stop boundary from initial
  request handling (or the user's shorter limit). Carry absolute times across handoff;
  no fresh budget, automatic extensions, or guarantee of end-to-end latency.
- Retain EVM provider policy, pins and source standards. Keep EVM project-only and
  mirror relevant instructions to Claude. Solana improvement beyond required routing/
  timing decoupling is deferred. Collector engines and evidence schemas stay unchanged.
- Remove old Personal registration; register the new canonical router in its place.
  Update active docs and sharing entries; retain historical records and old snapshots.
- Review actual diffs and callers directly; repair in-scope findings and rerun affected
  checks. Do not commit, push, run live token research or use paid providers.

## Acceptance and verification

1. Exact 20-byte hex routes to EVM; exact 32-byte base58 is a Solana candidate only.
   Invalid lengths/characters, zero address, transaction hashes/signatures, conflicting
   hints, multiple unresolved targets, native assets and unsupported chains never
   silently route to a token assessment. Candidate classification never means verified.
2. Full original request and links survive unchanged. Shell-like text is data, never
   evaluated. Existing timing survives handoff and repeated helper use; expired,
   nonfinite, future-start and inverted timing inputs fail closed.
3. Both specialist paths resolve from the canonical router and its symlink. Native
   requests cannot bounce recursively between router and specialists.
4. Router imports only the standard library and performs no network or credential reads.
   Measure local classification and CLI overhead; distinguish it from model/tool latency.
5. Run router, canonical EVM, Solana and Claude EVM suites; diff and dependency checks.
   Check manifest entries affected by this phase without silently re-approving unrelated
   source hashes changed since the older sharing review.

## Review and results

Phase 1 completed: implementation, direct diff/caller review, in-scope repairs and
verification. No specialist collector code, provider settings or evidence schemas changed.
Router 1.0.0; EVM instruction workflow 3.2.7 (mirrored to Claude); Solana workflow 1.0.1.

### Review findings and fixes

- P2: A nonempty textual chain hint could be ignored if `family_hint` was omitted.
  Helper now requires classification of explicit chain context; regression added.
- P2: Subsecond remaining time could select a specialist despite zero usable whole
  seconds. It now returns deadline_reached; expiry regression covers the boundary.
- P2: Overflowing timestamps and escaped Unicode surrogates could escape normal error
  handling. Numeric validation and ASCII-escaped JSON output now fail closed/preserve
  content, with regressions. Duplicate JSON fields are also rejected as ambiguous.
- P2: The draft Solana handoff named a nonexistent process-timeout flag. Caller review
  confirmed the actual `--seconds` option and 55-second maximum; instructions corrected
  and aligned with the two-minute reconciliation reserve.
- No remaining actionable router findings identified in the final review. This does
  not establish performance of the model's natural-language target extraction or a
  live onchain run; those remain evidence limits rather than passing claims.

### Validation evidence

- Router: 30 tests passed, including CLI/stdin/file paths, generated base58 sizes,
  exact hex length, duplicate/multiple targets, native/other-family boundaries,
  explicit hint conflicts, prompt-like text preservation, bad JSON and shared clocks.
- Canonical EVM: 428 passed; Solana: 23 passed; Claude EVM: 428 passed. Total 909.
  EVM emitted existing non-failing ResourceWarnings for mocked HTTPError cleanup.
- Final Personal-symlink CLI benchmark: 10 offline runs, median 49.57 ms, max 64.35 ms.
  An earlier 10,000-call in-process benchmark averaged 0.0041 ms. No network calls.
  These measure local helper overhead only, not model/tool or research duration.
- Static review confirmed candidate-only identity, continuation into one specialist,
  whole-request preservation, unsupported/native handling without recursion, token-URL
  versus pool/transaction-URL distinctions, and first-handling absolute deadlines.
- All active SKILL.md relative links resolve; changed canonical/Claude reference files
  are byte-identical. New Personal router shortcut resolves to its canonical folder;
  old shortcut is absent; EVM remains project-only. Git diff whitespace check passes.
- Bundled quick_validate.py could not run with either available Python runtime because
  PyYAML is absent. No dependency was installed. Authored simple frontmatter/UI metadata
  was inspected and checked for name, description, invocation and link consistency;
  this is not represented as a full YAML-validator pass.

### Dependency and provenance disposition

No specialist code imported old research helpers. Solana's linked timing guidance was
made self-contained. The retired 2.1 rubric's exact current bytes were preserved at
`plans/retired-crypto-research-rubric-2026-09-11.md` (SHA-256
`d00b8925743f996385c7dc894a6c6ae7007500876f5f552c3e4ab7e0a8753a6b`).
Frozen history, research evidence and older export snapshots were not changed.

Sharing entries now remove retired research files and include the router. Hashes were
refreshed only for this phase's changed/new allowlisted files. The manifest retains
57 preexisting mismatches for unrelated files changed since the September 10 export
review; a full sharing rebuild remains intentionally blocked by that existing review
gate. No whole-export validation or distribution readiness is claimed.

No live token research, paid provider use, commits or pushes occurred. Remaining Solana
feature parity work and a live router-to-specialist latency benchmark are separate work.
