# EVM social trading and launchpad sources

Requested workflow: implement-review-improve. Target: canonical EVM diligence skill
and its existing Excalidraw-style architecture diagram. This single scoped phase is
resolved from the user's explicit request; no earlier saved phase covers these additions.

## Phase 1 — Add sources, review the skill, then update the diagram

Implement Pump.fun social trading as an evidence source and Pons and Long as explicit
Token Launchpad sources, including the supplied X handles. Keep exact chain/address
identity, evidence provenance, provider policy, shared deadline and bounded parallel
ownership. Select relevant sources without expanding a focused question into a broad
investigation. Preserve pre-existing work and frozen evidence/history.

Sequence within this phase:

1. Update the skill's source routing and conditional platform guidance, version the
   instruction behavior, and add meaningful synthetic reasoning cases.
2. Review the final text and this phase's actual diff. Fix in-scope defects, run the
   relevant documented suites and skill validator, and review the synthetic cases.
3. After skill verification, extend the current native SVG diagram and render a PNG.
   Preserve the sketch style, muted cyan/teal/marine palette, "Coin to research", and
   green/yellow/red finding markers with explanatory text.

Acceptance criteria:

- Pump.fun social trading has an explicit source route; platform listing/feed evidence
  does not establish launch origin, executed trades, wallet control or token safety.
- Pons and Long have source entrypoints, target-linked launch/history/fee/rights checks,
  and conditional version/runtime verification. Inaccessible sources remain gaps.
- Same-symbol or cross-chain results cannot replace the exact EVM target; unrelated
  launchpads do not trigger deep work. Duplicate web/RPC requests share ownership and
  fit the original budget, with no new provider credentials or API assumptions.
- Matching configured authorized dRPC remains preferred before public RPC fallback;
  no collector, report schema, numeric research rubric or safety-label semantics change.
- The diagram shows Pump.fun under "Trading platforms" and Pons and Long under a new
  "Token Launchpad" category, with readable spacing and the existing architecture.

Validation from repository root:

- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s skills/crypto-evm-token-due-diligence/tests -q`
- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s skills/crypto-research/tests -q`
- Existing skill-creator `quick_validate.py`, using the already available temporary
  PyYAML dependency if needed; local reference/metadata checks and `git diff --check`.
- Direct review of synthetic source-routing cases. These are reasoning checks, not
  executed live diligence or automated end-to-end agent tests.
- Parse the SVG, inspect the rendered PNG and compare the diagram labels to the skill.

Pre-change snapshots are outside the repository at
`/tmp/evm-social-launchpad-before-20260907`. No commits or pushes are authorized.

## Source verification

Checked 2026-09-07 UTC:

- [Pump.fun landing page](https://pump.fun/landing) describes a social narrative feed
  and cross-chain trading. This supports discovery, not universal network coverage or
  proof that a listed EVM token originated on Pump.fun.
- [Pons documentation](https://docs.ponsfamily.com/) and its
  [contract repository](https://github.com/ponsdotdev/ponsfamily) distinguish versions;
  the repository cross-links [@ponsdotfamily](https://x.com/ponsdotfamily). Root ABI and
  deployment metadata describe V1 at inspection time; verify each deployed target.
- [Long's token directory](https://app.long.xyz/tokens) returned no readable content
  through the text fetch. It remains a conditional browser/discovery entrypoint.
- Direct text access to the user-supplied [Long](https://x.com/longdotxyz) and
  [Pons](https://x.com/ponsdotfamily) X profiles failed. Their post history was not
  verified. The instructions must preserve those access limits and authenticate links
  during actual research, rather than relying on mirrors or inventing platform behavior.

## Execution and review record

Skill implementation and direct review complete before diagram editing. Workflow is
1.4.0 (previously 1.3.0); backend 2.1.0 and reporting 1.1.1 are unchanged. The canonical
entrypoint routes to the expanded source matrix and conditional adapters; the installed
personal skill resolves to this same directory. No new API client or provider calls.

Review used the final source text, relevant entrypoint/reporting references and the
diff against this phase's snapshots, including the new plan. One minor wording fix:
source-routing-and-execution.md's documentation note now reports an empty text fetch
for Long instead of inferring a JavaScript requirement from that observation alone.
Conditional browser guidance remains appropriate. No remaining actionable findings.

Verification before diagram work:

- EVM suite: 170 tests passed; research suite: 31 tests passed (201 total).
- Existing skill-creator validator: `Skill is valid!` with its existing temporary
  dependency path. No validation tooling added to the project.
- 36 local Markdown references/fragments resolve; workflow metadata matches unchanged
  backend/reporting versions; review-record path and installed skill symlink resolve.
- `git diff --check` passed.
- Direct walkthrough of all eight new synthetic scenarios: listing/feed observations
  remain attributed; unresolved network support triggers bounded discovery; namesake
  mints are rejected; inaccessible history stays unknown; Pons ABI follows the matched
  generation; Long backing/rights claims require underlying evidence; unsupported
  surfaces stop early; shared evidence avoids duplicate lane requests at cutoff.
  These are manual reasoning checks, not independent or live agent executions.

Provider selection paragraphs and runtime/reporting code are unchanged from this
phase's baseline. Matching configured authorized dRPC remains preferred before public
fallback. No live RPC collection, token diligence or latency benchmark was performed.

Diagram completed after skill verification:

- Native SVG (superseded asset removed) and
  3600 × 2300 PNG (superseded asset removed).
- Source panel expanded to four categories. Pump.fun joins Trading platforms; the new
  Token Launchpad category contains Pons and Long. All prior source names are retained.
- SVG XML parsing and comparison verified unchanged architecture edges, palette and
  assessment label positions. The rendered PNG was visually inspected: source text is
  readable with no overlaps; green/yellow/red markers and context remain legible.
- Existing v2 artifacts are retained. No diagram code or output relies on remote fonts.

All phase acceptance criteria are satisfied. The source routing includes bounded
discovery, evidence gates, chain/version handling and shared ownership; metadata and
documented behavior retain provider/schema/reporting compatibility. No material plan
deviation, remaining actionable findings or required next phase. Changes are uncommitted.

## Files changed by this phase

- [Skill entrypoint](../skills/crypto-evm-token-due-diligence/SKILL.md)
- [Source routing and parallel ownership](../skills/crypto-evm-token-due-diligence/references/source-routing-and-execution.md)
- [Conditional platform adapters](../skills/crypto-evm-token-due-diligence/references/platforms.md)
- [Synthetic reasoning cases](../skills/crypto-evm-token-due-diligence/references/reporting-scenarios.md)
- [Workflow release metadata](../skills/crypto-evm-token-due-diligence/assets/workflow-release.json)
- [Repository README](../README.md)
- This plan and review record
- The v3 SVG and PNG linked above

Suggested commit: `feat(evm): add social trading and launchpad evidence sources`

Diagram cleanup, 2026-09-10: superseded assets were removed; the maintained
[dark architecture diagram](../docs/diagrams/evm-diligence-architecture-dark.png) reflects the current workflow.
