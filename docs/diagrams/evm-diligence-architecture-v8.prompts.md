# Architecture v8 review and image prompt

Historical detailed-label revision. The stable PNG now uses the simplified
[v9 architecture-review presentation](evm-diligence-architecture-v9.prompts.md).

Updated 2026-09-11 using the built-in image_gen tool in edit mode.
Output: [main dark PNG](evm-diligence-architecture-dark.png).
Edit target and style reference: the existing v7 dark PNG. This remains the single
maintained raster diagram; the stable asset path is preserved.

## Scope and source of truth

Reviewed against the canonical EVM SKILL.md, references/runbook.md,
references/compose.md and current release manifests: workflow **3.2.4**, backend
**3.4.2**, reporting **2.6.2**. Also reviewed the performance, delivery consistency,
production review, citation presentation and network execution records under plans/.
The [v7 prompt record](evm-diligence-architecture-sketch-v7.prompts.md) is historical.

## Changes

The subsequent purpose-label revision replaces visible filenames, command flags and
internal field names with descriptions of what each step accomplishes. Implementation
names in the historical prompts below document the edit sequence, not current image labels.

- Collection produces facts and automatic pipeline findings, with exact computed holder totals.
- Coordinator scaffolding, signal assignment and concern assessment are explicit.
- Composition receives pipeline, lane and coordinator notes.
- Provider policy and host network permission are separate; each live call checks execution permission.
- Lane notes self-check with compose --check; no additional research lane is introduced.
- Finalize supplies its existing delivery reading_checklist.
- The answer preserves concentration, custody/admin, economics and assurance limits,
  reuses native source links per finding, and gives four independent conclusions.
- Shared limits include retries. Backend sale-matching and missing-data repairs remain
  within the existing collection/backend stages rather than new branches.
- Source matching is labeled an attempt so the diagram does not promise correspondence.

No executable skill behavior, version, registration, provider policy or frozen research
was changed. The two lanes, eleven surfaces, bounded presets, pinned evidence,
5–7 minute target, ten-minute cap and focused/formal exceptions remain intact.

## Validation

Visual review of the first edit confirmed the new pipeline note, coordinator judgment,
three-note composition, host network checks, checklist and citation labels. It caught
an omitted checkpoint-at-cutoff sentence; a targeted correction restores that rule.
The final image was visually checked for text legibility, the restored checkpoint rule,
two-lane sequencing, arrows returning to composition before finalize, and all new labels.
The selected output was copied to the stable project PNG path. Documentation links and
release versions were checked; `git diff --check` passed. No commit or push was run.
This documentation and image change does not require a runtime regression run; it
makes no new claim about live research latency or token safety.

## Exact edit prompt

The latest purpose-label edit, applied after the checkpoint correction, used the
built-in image_gen tool with this exact prompt. Visual review confirmed all eight
replacements, no remaining visible filenames or command flags, preserved connectors
and legible text. The final PNG replaces the image at the same stable path.

```text
Edit this existing architecture diagram. Replace implementation filenames and command/field jargon with the PURPOSE of each step. Preserve ALL layout, arrows, typography, dark palette, boxes, icons, other text, spacing and guardrails. Make exactly these text replacements:
1 "Source-match attempt → facts.json + pipeline note" becomes "Check source match → facts + automatic findings"
2 "Scaffold note · assign signals · assess concerns" becomes "Prepare assessment · rate findings · assess concerns"
3 "web_capture.py → captures + compose --check + one note per lane" becomes "Capture web evidence → validate findings → lane report"
4 "bundle_assemble.py finalize" becomes "Validate + preserve final assessment"
5 "Compose → preflight → freeze → deliver" becomes "Combine findings → check → preserve → deliver"
6 "Delivery reading_checklist" becomes "Checklist to retain material findings"
7 "Frozen report.md → chat / formal report" becomes "Present findings from the preserved report"
8 "Focused: facts + presets, no lanes or broad finalize" becomes "Focused: targeted checks, no lanes or full review"
Keep the vertical bar and existing Formal footer text after replacement 8.
No filenames ending .py, .json, .md, command flags or underscored field names should remain anywhere in the image. Leave source brands like GitHub and Sourcify unchanged. Preserve the cutoff checkpoint rule, exact two web lanes, four conclusions, citation guidance and coordinator/lane arrows returning to composition before final validation. Text must be legible and fit without clipping.
```

### Initial architecture update prompt

Built-in image_gen; referenced image: docs/diagrams/evm-diligence-architecture-dark.png
(the v7 contents before replacement).

```text
Use case: text-localization / infographic-diagram edit.
Edit target: attached existing EVM architecture diagram. Update its content accurately while preserving the dark navy/teal background, mint thin outlines, white hand-lettered typography, three-column layout, main title, assessment markers, source panel, arrow semantics and calm spacing. Can modestly expand boxes or canvas for legibility. No visible version subtitle. Crisp text, high resolution landscape.

Make these exact replacements:
1 Research coordinator subtitle becomes "Scope · provider policy · host network permission" and add another small line "Time · shared request budget". This distinguishes provider authorization from host execution access.
2 Collect + verify evidence: retain "Discovery → four pinned RPC phases" and replace last line with "Source-match attempt → facts.json + pipeline note". Add small line "Computed holder totals · factual findings". Source match is an attempt, not guaranteed success.
3 Shared facts + evidence aliases remains unchanged.
4 Coordinator judges facts retain controls/custody/exits/dependencies and at most two conclusion-changing presets. Add line "Scaffold note · assign signals · assess concerns".
5 Compose + reconcile replace "Lane notes + coordinator note → strict report" with "Pipeline + lane + coordinator notes → strict report". Retain eleven surfaces and four independent decision axes.
6 Finalize retains Compose → preflight → freeze → deliver, and adds "Delivery reading_checklist".
7 Frozen report.md → chat / formal report retains all four Good / Potential Risk / Bad / Unverified markers and line about missing evidence; add two concise lines:
"Preserve concentration · custody/admin · economics/assurance"
"Native source link per finding · four conclusions"
8 Bottom guardrail panel retain one session ledger, timings, focused/formal distinction and validation not safety. Add a compact line "Each live call checks host network permission; retries count toward shared limits". Update focused footer if necessary to "Focused: facts + presets, no lanes or broad finalize | Formal: render frozen evidence".

Preserve two parallel web lanes: they start before coordinator reads facts, self-contained briefs, return by minute 4, liquidity and market / project and creator; no RPC or credentials. Their two notes self-check: change group footer to "web_capture.py → captures + compose --check + one note per lane", followed by existing precharged budget/no RPC line. Keep arrows from shared facts to coordinator and lanes; lane leads dashed to coordinator; coordinator and lane outputs both feed Compose + reconcile BEFORE finalize. No new research stage for citations or checklist. No invented logos, no new third lane, no added safety pass claims. All unchanged source family labels preserved. Ensure all text fits without crossings or clipping.
```

## Targeted correction prompt

```text
undefined
```
