# Architecture v7 review and image prompts

Historical generation record. The main PNG was subsequently updated; see the
[v9 review and prompt](evm-diligence-architecture-v9.prompts.md) for its current contents.

Created 2026-09-10 using the built-in image_gen tool. Dark mode only.
Output: [main dark PNG](evm-diligence-architecture-dark.png).
Style reference: v6 dark PNG. Earlier diagram assets were removed at the user's request on 2026-09-10. This is a generated raster;
there is no corresponding v7 SVG or light asset.

## Why a new version was needed

- V6 depicted three specialists; workflow 3.0.0 has two brief-driven web lanes and
  coordinator-owned RPC verification, with lane launch before the coordinator reads facts.
- The one-process discovery / four pinned RPC phases / source-match / facts pipeline
  and bounded presets were absent.
- Compact note composition and preflight / freeze / delivery were absent.
- V6's raster called missing evidence Potential Risk. Pure gaps belong under Unverified.
- Shared session ceilings, phase timings, lane cutoff, completion cap and checkpoint
  behavior now need to be visible.

## Evidence reviewed

Canonical SKILL.md; references/runbook.md; both assets/lane-brief-*.md;
scripts/broad_collect.py phase orchestration; workflow/backend/reporting release manifests.
Versions are workflow 3.0.0, backend 3.2.0, reporting 2.6.0. The 5–7 minute label
is a target, not a measured clean-run result. This task did not rerun live acceptance.

## Review and improvement

Visually inspected both generated versions. Corrected the initial return connector:
coordinator and lane notes now flow into Compose + reconcile, before finalize.
Checked two lanes, source-versus-RPC separation, versions, time budgets, Unverified,
frozen report delivery, and focused/formal exceptions against the canonical runbook.
The diagram summarizes source families; it is not an exhaustive adapter inventory.
No executable skill changes were made; validation was visual and documentation-focused.

## Initial prompt

Subsequent user-requested label revision (built-in image_gen, visually inspected):
intake now reads `Token address + token name (optional)`; removed the visible version
subtitle; replaced `broad_collect.py start` with `Collect + verify evidence`.
Chain discovery and verification remain part of collection; the optional name is
an intake aid, not evidence of identity. The saved v7 dark PNG includes these edits.

### Label revision prompt

Edit this existing dark EVM architecture diagram with exactly THREE text changes. 1. In the top center intake box replace "Exact chain + token address" with exactly "Token address + token name (optional)". Fit on one line using a slightly smaller font if necessary, with comfortable padding. Preserve its second line "User question + actual requirements". 2. Completely remove the subtitle beneath the main title: "Architecture v7 · Workflow 3.0.0 · Backend 3.2.0 · Reporting 2.6.0". Fill that area seamlessly with existing dark background. Preserve main title and underline and all positions. 3. Replace the box title "broad_collect.py start" with exactly "Collect + verify evidence". Preserve its two description lines unchanged. Keep ALL other text verbatim, all boxes, arrows and routing, spacing, dimensions, dark navy background, mint outlines, hand-lettered typography, and all four assessment markers unchanged. In particular preserve return arrow into Compose + reconcile. No new text, no other changes.

### Original generation prompt

Create version 7 of this EVM token due diligence architecture diagram, DARK MODE ONLY. Reference image is the existing v6 diagram: retain its elegant dark navy/teal background, restrained mint outlines, white friendly hand-lettered text and roomy rounded boxes, but redesign the layout for the NEW architecture below. Landscape high resolution, preferably 2400x1600 or larger; all text crisp, readable and spelled exactly. This is a technical diagram, accuracy of labels and arrow direction matters more than ornament.

Title: "EVM token due diligence"
Subtitle: "Architecture v7 · Workflow 3.0.0 · Backend 3.2.0 · Reporting 2.6.0"

Use a spacious 3-column layout: evidence sources left, main pipeline center, parallel analyst work right. Main flow top to bottom, arrows only in the directions specified.
TOP CENTER intake box: "Exact chain + token address" / "User question + actual requirements"
arrow down to box: "Research coordinator" / "Scope · provider policy · time · budget"
arrow down to taller box: "broad_collect.py start" / "Discovery → four pinned RPC phases" / "Sourcify source match → facts.json"
arrow down to small hub: "Shared facts + evidence aliases" / "Pinned state · traceable provenance".
From this hub fork arrows RIGHT into BOTH a coordinator-work box and a two-lane group.
Coordinator work box text: "Coordinator judges facts" / "Controls · custody · exits · dependencies" / "At most two conclusion-changing presets".
Two-lane group title: "Two parallel web research lanes"
group subtitle: "Start when facts exist, before coordinator reads" / "Self-contained briefs · return by minute 4".
Exactly two boxes inside:
"Liquidity + market" / "LP custody · holders · sells · adoption"
"Project + creator" / "Delivery · economics · proceeds · prior launches"
group footer: "web_capture.py → captures + one note per lane" / "Pre-charged budgets · no RPC or credentials".
A thin dashed arrow from lane group back to coordinator-work box labeled "leads to verify"; don't imply lanes run RPC.
Both coordinator-work and lane group outputs flow into a lower center wide box: "Compose + reconcile" / "Lane notes + coordinator note → strict report" / "Eleven surfaces · four independent decision axes"
Below that wide box arrow to: "bundle_assemble.py finalize" / "Compose → preflight → freeze → deliver"
Below arrow to: "Frozen report.md → chat / formal report" / "Good · Potential Risk · Bad" / "Unverified = missing evidence, kept separate"
Use green/yellow/red small markers for the first three and gray marker for Unverified, never call gaps Potential Risk.

LEFT evidence-source panel, text:
"Evidence sources"
"RPC + discovery"
"Authorized dRPC first · public fallback"
"Dexscreener · Sourcify · explorer"
"Context + leads"
"RH Scan · Robinscan · Blockscout"
"Defined · Fomo · RH Trenches"
"Pons · Long · relevant launchpads"
"Website · docs · GitHub · X"
"Source candidates depend on chain"
"Web claims require onchain checks"
Arrow from RPC/discovery area into broad_collect box. A clearly labeled thin connector from context/leads area to the web lane group, routing without crossing text, if space permits. Do not route all web evidence into verified facts as automatically true.
Small support box below source panel:
"Deterministic backend"
"Chain registry · Keccak-256"
"Derived selectors + pool IDs"
"Bounded receipts · logs · reads"
"Block number + hash + UTC · recheck"

BOTTOM spanning guardrail bar:
"One session ledger: shared request ceilings + phase timeline"
"5–7 min target · 10 min cap · extra work needs a named trigger"
"Open scope at cutoff → internal checkpoint, not a completed report"
small footer:
"Focused question: facts + presets, no lanes  |  Formal report: render frozen evidence"
"Validation proves consistency, not token safety"

Do not include old three-specialist architecture. Do not claim a 7 minute measured completion. Preserve visual calm and comfortable padding. No light mode, no logos, no extraneous text. Adjust box sizes to text, keep connector lines outside boxes except at endpoints. All areas inside margins.

## Connector correction prompt

Edit this diagram with exactly one connector-routing correction. Preserve ALL text, boxes, positions, colors, dark theme, dimensions and every other arrow unchanged. The right-hand outputs from 'Coordinator judges facts' and the bottom of 'Two parallel web research lanes' currently merge into a line at y approximately 658 and point LEFT into 'bundle_assemble.py finalize'. They must instead both merge and point LEFT into the RIGHT EDGE of 'Compose + reconcile' (at y approximately 560), because notes are composed before finalization. Remove the old horizontal return segment and its arrow into finalize completely. Route the coordinator output along the far right margin down to y approximately 610, join the lane output from the bottom of its group, then route left to the empty gutter just to the right of Compose + reconcile, turn upward in that gutter and terminate with a leftward arrow at the right edge of Compose + reconcile at y approximately 560. Do not cross any text or any boxes. Leave the existing vertical arrow from Compose + reconcile DOWN to finalize intact. No other changes.
