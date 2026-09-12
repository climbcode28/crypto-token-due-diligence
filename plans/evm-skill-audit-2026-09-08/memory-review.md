# Initial operational lesson review

September 8, 2026. The user authorized implementation of all audit recommendations.
The five entries in the original `memories.draft.md` were reviewed as maintenance
provenance, not as current token evidence or active instructions. Their operational
behaviors now live in maintained helpers/references, so all five ship as retired.

| Original lesson | Implemented behavior and verification |
| --- | --- |
| OPS-001 | Selective read-only Sourcify v2 adapter; supported research flow and source comparison tests. Official API specification inspected during maintenance. |
| OPS-002 | Exact full ERC-1167 extraction and static ABI helper; valid, truncated, variant and zero-address regression cases. |
| OPS-003 | Helpers have explicit CLI entrypoints; import-safety and immutable collection/draft/freeze checks. |
| OPS-004 | Strict subjects, participant roles, derived dependencies, imported provenance, coverage and adverse-summary gates; negative and near-neighbor fixtures. |
| OPS-005 | Scoped acquisition telemetry, honest capture-mode guidance and bounded feedback for invalid collection/browser-only gaps; operations regressions and independent review. |

The operations suite passes 15 cases, including bounded concurrent writes, conflict
rollback, hash/path checks, corrupt-memory survival, applicability/expiry and successful
promotion provenance. Independent review reproduced and rechecked fixes in
`research/2026-09-08-stage4-memory-audit/review.md`. Future guidance becomes active only
after a demonstrated recovery and explicit maintenance review. These retirement records
preserve the original draft digest and this review digest; they do not claim that a
new active solution was promoted from an automatically captured observation.
