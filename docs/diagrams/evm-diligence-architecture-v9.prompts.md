# Architecture v9 — presentation review

Historical revision. The stable PNG now uses the original muted theme and consolidated
[v10 presentation](evm-diligence-architecture-v10.prompts.md).

Updated 2026-09-11 with the built-in image_gen tool in edit mode.
Output: [main dark PNG](evm-diligence-architecture-dark.png).
Previous detailed revision: [v8 record](evm-diligence-architecture-v8.prompts.md).

## Presentation intent

The user requested a principal-architect review view with much less text, especially
in the center pipeline and bottom guardrail panel. The approved Present findings box
retains its complete wording and assessment markers. Stage headings communicate purpose,
without filenames or command names. Following user review, the final revision restores
the earlier hand-lettered blackboard style and detailed source/backend panels on the left.
The simplified center, right-hand research lanes and compact guardrails remain; the
approved findings box retains its full text. The earlier sans-serif prompts below are
historical steps in this same revision.

The architecture still represents workflow 3.2.4, backend 3.4.2 and reporting 2.6.2.
No skill behavior, versions, budgets, registrations or research evidence changed.

## Abstraction decisions

- Center stages use headings with brief scope/evidence subtitles only where necessary.
- Two parallel web lanes remain distinct from coordinator judgment and verification.
- Both assessment outputs converge at reconciliation before validation and preservation.
- Named source candidates are retained on the left. At the user's request, the two
  source-panel footer qualifications were removed from the image; chain-dependent
  source selection and onchain verification remain requirements in the skill/runbook.
  The source list does not promise every source is applicable or accessible in every run.
- Shared guardrails condense access authorization, budgets and explicit evidence gaps.
- Detailed provider gates, source correspondence, computed holder aggregation, lane
  timing, preset limits, retry accounting, checkpoints, focused/formal exceptions and
  delivery rules remain authoritative in SKILL.md and references/runbook.md.
- The diagram is a broad-review architecture view, not an execution runbook or a claim
  that validation establishes token safety. The preserved report retains explicit gaps.

## Review

Final intake-label edit: the top box contains only `Token address + token name (optional)`.
The earlier scope heading and decision-question subtitle were removed. Built-in image_gen
was used; visual inspection confirmed the single line and preserved layout.

```text
Make exactly one local text edit to this existing blackboard architecture diagram. In the TOP CENTER intake box, remove BOTH current lines "Define research scope" and "Token address · decision question". Replace them with just ONE centered line, exactly: "Token address + token name (optional)". Use the same white handwritten blackboard typeface, modestly smaller to fit on one line with comfortable padding, vertically centered in the existing box. Keep the box dimensions and position unchanged. Preserve EVERY other text, box, border, arrow, source name, symbol, color, background, layout and image dimensions unchanged. No subtitle in this box. No other changes.
```

Latest local edit: removed the two source-panel footer sentences and their divider,
preserving the panel size and remaining diagram. Built-in image_gen was used; visual
review confirmed the removal and retained source list, stages, arrows and findings box.

```text
Precisely edit this latest blackboard architecture diagram. In the upper-left Evidence sources panel ONLY, erase the two bottom text lines "Source candidates depend on chain" and "Web claims require onchain checks". Also remove the thin horizontal divider immediately above those two lines, because that footer section is being removed. Fill that small area seamlessly with the existing dark chalkboard background. Keep the panel border at its existing position and size, leaving clean empty space below the source list. Preserve EVERY other text, source name, box, line, arrow, marker, color, handwritten typography, canvas dimensions and layout exactly unchanged. Do not reword, rearrange or add anything. This is a local removal only.
```

The first generated revision was visually inspected for all stage names, compact text,
exactly two lanes and preserved findings text. Two connector errors were identified:
a spurious context-to-reconciliation branch and an unfinished coordinator return.
A targeted connector-only correction was requested before selecting the final asset.
The final image was visually verified: the unwanted context branch is gone, the
coordinator return joins the lane output before reconciliation, and the stage sequence
and approved findings text are preserved. The PNG was saved at the stable project path.
Documentation links and PNG validity were checked; `git diff --check` passed.
No executable changes were made, so runtime suites were not rerun.

## Exact connector correction prompt

## Final blackboard and source-detail revision

Built-in image_gen used the simplified diagram as edit target and the earlier v8
blackboard image as the style and source-panel reference. Visual review confirmed the
restored named sources and backend details, hand lettering, simplified center/right/bottom,
unchanged findings text, and complete return connector into reconciliation.

```text
Edit image 1, the current simplified architecture. Image 2 is the BLACKBOARD STYLE AND DETAILED LEFT PANEL reference only.
User wants a hybrid: keep image 1's simplified center/right/bottom wording and correct arrows, restore image 2's hand-lettered blackboard aesthetic and full detailed LEFT panel.

STYLE: image 2's elegant dark navy/teal chalkboard texture, warm white handwritten lettering, thin pale mint rounded outlines, hand-drawn underlines, no bold corporate sans-serif. Keep high legibility and spacious presentation. Preserve image 1 center/right box coordinates and routing as much as practical. Left panels can grow to image 2's heights. No connector crossing text.

LEFT SIDE: replace image 1's simplified Evidence sources and Evidence integrity panels with image 2's full two panels, exact text:
"Evidence sources"
"RPC + discovery"
"Authorized dRPC first · public fallback"
"Dexscreener · Sourcify · explorer"
"Context + leads"
"RH Scan · Robinscan · Blockscout"
"Defined · Fomo · RH Trenches"
"Pons · Long · relevant launchpads"
"Website · docs · GitHub · X"
divider
"Source candidates depend on chain"
"Web claims require onchain checks"

Separate left lower support panel:
"Deterministic backend"
"Chain registry · Keccak-256"
"Derived selectors + pool IDs"
"Bounded receipts · logs · reads"
"Block number + hash + UTC · recheck"

CENTER retain image 1 text EXACTLY, no extra descriptions:
"Define research scope" / "Token address · decision question"
"Coordinate research"
"Collect + verify evidence"
"Shared evidence" / "Facts · automatic findings"
"Reconcile assessments"
"Validate + preserve assessment"
Approved final box exact:
"Present findings from the preserved report"
Good / Potential Risk / Bad / Unverified with existing four colored symbols
"Unverified = missing evidence, kept separate"
"Preserve concentration · custody/admin · economics/assurance"
"Native source link per finding · four conclusions"

RIGHT retain simplified image 1 text:
"Assess evidence" / "Judgment · targeted verification"
"Parallel research"
"Liquidity + market" / "Custody · exits · holders"
"Project + creator" / "Delivery · economics · history"
"Web evidence only"
Dashed upwards "Leads" arrow to Assess evidence.

BOTTOM retain image 1 compact strip ONLY:
"Shared guardrails"
"Authorized access · bounded budget · explicit evidence gaps"

Title remains "EVM token due diligence".
CONNECTORS: center arrows downward. Left RPC/discovery feeds Collect + verify. Left Context + leads feeds Parallel research ONLY; route this horizontal line through empty gutter BETWEEN Shared evidence and Reconcile, not through the center boxes. Shared evidence branches into Assess evidence and Parallel research. Assess evidence outer-right return and Parallel research output converge into RIGHT EDGE of Reconcile before Validate. Preserve completed return path from image 1, no dangling lines. Backend support has no mandatory-stage arrow. No extra text, filenames, command flags, detailed timers or large ledger box. This restores left detail and blackboard style while preserving the successful simplification elsewhere.
```

### Earlier connector correction prompt

```text
Precise connector-only correction to this architecture diagram. Keep EVERY text label, box, position, font, color, size and icon EXACTLY unchanged. Fix two connector errors:
1 REMOVE the erroneous downward branch from the "Context" horizontal line at approximately x=485,y=410 to the LEFT edge of "Reconcile assessments". Project context must feed ONLY Parallel research, never directly Reconcile assessments. Keep the Context connector across into Parallel research.
2 The output from RIGHT edge of "Assess evidence" currently descends along far right x=1498 and fades out at y=580. Complete this return path: from that right edge route down the far-right gutter to y=560, then left to x=1075 (in empty whitespace BELOW Parallel research), then up that gutter to y=482, then LEFT with an arrow into the RIGHT edge of "Reconcile assessments" at x=983,y=482. Join the existing short Parallel research→Reconcile output at x=1075,y=482 with a small visible junction dot. This makes BOTH Assess evidence and Parallel research feed Reconcile. Do not cross any box or text. Remove any dangling tail. All other arrows preserved, especially the center vertical sequence and dashed Leads arrow. The final output must have no stray connector and no new text.
```

## Exact overhaul prompt

Edit target: the v8 contents of the stable main PNG. Built-in image_gen.

```text
Use case: infographic-diagram edit. Overhaul the attached EVM diligence architecture for a principal-engineer architecture review. It is currently far too text-heavy. Deliver a polished, spacious, presentation-ready architecture view with dramatically fewer words. Preserve the dark navy/teal palette and mint outlines, but use clean professional sans-serif typography instead of hand lettering. Landscape high-resolution, precise alignment and generous whitespace. No file names, CLI commands, numbered implementation phases or operational instructions. The user explicitly approves the existing bottom-center "Present findings" box: preserve its exact text and four colored assessment markers; other boxes are simplified as below. Retain meaning and directed flow; this is architectural abstraction, not a changed workflow.

EXACT CONTENT — no additional prose:
Title: "EVM token due diligence"

LEFT column, one restrained panel titled "Evidence sources" with two sections:
"Onchain evidence"
"RPC · explorers · verified source"
"Project context"
"Markets · launchpads · websites · repositories"
Small supporting box below:
"Evidence integrity"
"Pinned state · provenance · rechecks"

CENTER vertical flow: compact equally aligned boxes with headings and only the specified short subtitle, most heading-only:
"Define research scope"
"Token address · decision question"
↓
"Coordinate research"
↓
"Collect + verify evidence"
↓
"Shared evidence"
"Facts · automatic findings"
↓
"Reconcile assessments"
↓
"Validate + preserve assessment"
↓
PRESERVE approved findings box EXACTLY (resize neatly but same words):
"Present findings from the preserved report"
colored marks "Good" / "Potential Risk" / "Bad" / "Unverified"
"Unverified = missing evidence, kept separate"
"Preserve concentration · custody/admin · economics/assurance"
"Native source link per finding · four conclusions"

RIGHT column:
Top compact box:
"Assess evidence"
"Judgment · targeted verification"
Below a dashed group titled "Parallel research" with EXACTLY two boxes:
"Liquidity + market"
"Custody · exits · holders"
and
"Project + creator"
"Delivery · economics · history"
One short group footer: "Web evidence only"

BOTTOM: remove the entire verbose existing One session ledger panel and replace with a shallow elegant single strip, only:
"Shared guardrails"
"Authorized access · bounded budget · explicit evidence gaps"
No other footer text. All detailed timing, exception handling and operation rules belong in documentation, not this presentation.

CONNECTORS: Center flow downward. Onchain evidence connects into Collect + verify evidence. Project context connects into Parallel research, routed cleanly in whitespace, optionally labeled "Context". Shared evidence branches to BOTH Assess evidence and Parallel research. Dashed arrow from Parallel research UP to Assess evidence labeled "Leads". BOTH Assess evidence and Parallel research return into Reconcile assessments BEFORE Validate + preserve assessment. These return paths should be distinguishable and unambiguous, route around boxes and outside text, no stray lines or ambiguous intersection with unrelated connectors. Evidence integrity is a support annotation not a separate mandatory research stage. Keep input arrows off text. No extra lane, no invented safety claims, no claim that all source is verified. Perfect spelling and unclipped text. Use the freed space for clear hierarchy and comfortable spacing, not more content.
```
