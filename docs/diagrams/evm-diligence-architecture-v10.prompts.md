# Architecture v10 — original palette and consolidated flow

Updated 2026-09-11 using built-in image_gen in edit mode.
Output: [main dark PNG](evm-diligence-architecture-dark.png).
Previous revision: [v9 record](evm-diligence-architecture-v9.prompts.md).

## User request and decisions

Restore the original reference's muted midnight-blue palette, soft off-white hand
lettering and fine desaturated outlines. Preserve the current source inventory and
substantive text, while consolidating the center and making the bottom note understandable
for both technical and nontechnical audiences.

- Five center boxes replace seven: collection is grouped with research coordination;
  validation and preservation are grouped with reconciliation. Both operations remain
  explicitly named. This is visual grouping, not an execution change.
- Detailed source and backend panels remain. The two removed source disclaimers stay
  removed, and the top box retains only the exact optional-name intake label.
- Exactly two parallel web lanes remain distinct from coordinator assessment.
- The approved Present findings box retains its full wording and four markers.
- The footer now reads: **Research limits — Read-only access · Fixed time and request
  limits · Findings and unknowns kept separate**. This replaces vague guardrail wording.
- Original reference used for aesthetics only: its outdated third lane and treatment
  of missing evidence as Potential Risk are not carried forward.

Workflow 3.2.4, backend 3.4.2 and reporting 2.6.2 remain unchanged. No executable
skill files, provider policy, registration, request budget or research evidence changed.
The skill/runbook remains authoritative for execution details and authorized exceptions.

## Review

Initial visual review verified all preserved labels, five center boxes, muted palette,
two lanes and clear footer. It identified a context arrow entering Shared evidence;
a connector-only edit redirects documentary context to the web research group and
clarifies its output junction with the coordinator return.
Final visual review confirmed the corrected context route, complete returns, retained
text and five-box flow. The selected PNG was copied to the stable project path;
PNG validity, documentation links and `git diff --check` passed. No runtime suites
were needed for this image/documentation-only edit. Changes remain uncommitted.

## Exact connector correction prompt

```text
Connector-only correction. Preserve every word, color, box, font, coordinate and all other content in this diagram exactly. Correct the Context + leads arrow: REMOVE its current straight segment from left source panel at x414,y388 into the LEFT edge of Shared evidence x554,y388. Replace with an elbow from source panel x414,y388 to x445,y388, DOWN to y442 (the empty gap below Shared evidence and above Reconcile assessments), RIGHT to x1095,y442, UP to y405, then RIGHT with arrowhead into the LEFT border of Parallel research at x1113,y405. Move the label "Context + leads" next to the first elbow in the left gutter if needed. Remove the old unlabeled extra line from Shared evidence right edge x982,y405 to Parallel research x1113,y405; retain the separate correct Shared evidence→Liquidity + market arrow at y370 and Shared evidence→Assess evidence path. The new context route must NOT touch or enter Shared evidence. Also ensure Parallel research output connects continuously from its left border x1113,y510 to the existing return junction x1097,y510 and then arrow left into Reconcile assessments x982,y510; add a tiny visible junction dot where the coordinator return joins that output. All return paths stay before the Present findings box. No other changes.
```

## Exact recreation prompt

Input 1: current diagram. Input 2: user-attached original-theme reference image.
Built-in image_gen edit mode.

```text
Recreate image 1's CURRENT EVM architecture with the ORIGINAL MUTED COLOR THEME of image 2. Image 1 is content/architecture truth. Image 2 is color, fine-line and handwritten-style reference ONLY: do not copy its obsolete three lanes or its incorrect assessment legend. User requests a clear principal-engineer presentation for technical and nontechnical readers, fewer center boxes, all existing substantive content retained, and a comprehensible footer.

STYLE: Exactly image 2's muted deep midnight blue background, subtle uniform texture (no green cloudy glow), slightly lighter dark blue-teal box interiors, thin desaturated pale blue-gray/mint borders and arrows, soft off-white hand-lettered typography. No neon cyan, heavy shadows, bright outlines, thick strokes or corporate bold font. Roomy landscape high resolution. Fine restrained underline below title. Text crisp enough for projection. Generous spacing.

LAYOUT: 3 columns. Left detailed sources/support. Center FIVE boxes instead of seven. Right coordinator judgment and EXACTLY TWO parallel web research lanes. Bottom shallow plain-language note. Purpose labels only, no filenames.

EXACT TEXT:
Title "EVM token due diligence"

LEFT sources panel:
"Evidence sources"
"RPC + discovery"
"Authorized dRPC first · public fallback"
"Dexscreener · Sourcify · explorer"
"Context + leads"
"RH Scan · Robinscan · Blockscout"
"Defined · Fomo · RH Trenches"
"Pons · Long · relevant launchpads"
"Website · docs · GitHub · X"
No qualification sentences beneath source list (these were intentionally removed).
LEFT support panel:
"Deterministic backend"
"Chain registry · Keccak-256"
"Derived selectors + pool IDs"
"Bounded receipts · logs · reads"
"Block number + hash + UTC · recheck"

CENTER only five aligned boxes:
1 "Token address + token name (optional)"
2 "Coordinate research"
   "Collect + verify evidence"
3 "Shared evidence"
   "Facts · automatic findings"
4 "Reconcile assessments"
   "Validate + preserve assessment"
5 Approved findings box preserve all these words:
   "Present findings from the preserved report"
   green check "Good", yellow exclamation "Potential Risk", red X "Bad", gray question "Unverified"
   "Unverified = missing evidence, kept separate"
   "Preserve concentration · custody/admin · economics/assurance"
   "Native source link per finding · four conclusions"
The first line in each merged box is heading, second is smaller supporting text. This combines collection with coordination and final validation with reconciliation without losing their meaning.

RIGHT:
"Assess evidence"
"Judgment · targeted verification"
Dashed group "Parallel research"
two boxes:
"Liquidity + market"
"Custody · exits · holders"
"Project + creator"
"Delivery · economics · history"
group footer "Web evidence only"
Dashed upward connector to Assess evidence labeled "Leads"

BOTTOM: replace vague Shared guardrails panel with shallow unobtrusive strip, heading:
"Research limits"
and ONE plain readable line:
"Read-only access · Fixed time and request limits · Findings and unknowns kept separate"
No more jargon or other footer sentences.

CONNECTORS IMPORTANT: Center vertical arrows 1→2→3→4→5. Left RPC/discovery feeds center Coordinate research / Collect + verify evidence box. Left Context + leads feeds ONLY Parallel research, labeled "Context + leads" and routed through empty gutter, not through center boxes. Shared evidence branches to BOTH Assess evidence and Parallel research (group input, so both lanes receive facts). Both right-side Assess evidence and Parallel research outputs merge into a single return arrow into RIGHT EDGE of Reconcile assessments, before Present findings. Coordinator return via outer right margin with visible continuous connection to shared return, no dangling lines. Dashed Leads arrow UP from research group to Assess evidence. Backend support is an annotation, no mandatory-stage arrow. Avoid crossing text, ambiguous junctions and unrelated branches. Use clean orthogonal routing. Do not add old coordinator execution instructions or timing paragraphs. Preserve the current source list and the four assessment categories exactly.
```
