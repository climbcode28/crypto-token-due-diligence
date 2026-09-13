# EVM native source links and company/product icons

## Request and result

The user liked the screenshot's short signal-labeled findings, selective bolding and
adjacent source links. They explicitly required no increase in research tool calls or
agent turns and retention of the approximately seven-minute review time. The screenshot
is a presentation reference, not evidence for this run's sale or other token findings.

The user clarified that source-link icons mean official company/product branding, not
emoji substitutes. Workflow 3.2.3 and reporting 2.6.2 now require each chat finding to carry
an adjacent native Markdown citation, with a local frozen-report fallback when a
supporting direct URL is unavailable. Grouped Unverified text gets a Detailed findings
link. Source labels contain no emoji or image markup. The client may decorate native links
with company/product icons; a plain text link is the fallback where unsupported. The
skill cannot guarantee client-rendered branding. Signal meanings, evidence thresholds,
concentration/custody/economics disclosures,
300–600 words and the four separate conclusions are preserved.

## Implementation and review

- `render_report.py` puts up to two distinct, already-cited successful document source
  URLs beside each assessed summary finding, while retaining the frozen finding link.
  It reuses loaded evidence and existing URL escaping; it does not construct explorer
  URLs, fetch sources, download icons, or open artifacts.
- RPC-only findings and pure gaps retain the local evidence link. Failed, redacted,
  unrelated, identity-only and counterevidence references are excluded from affirmative
  source selection. Host-based labels use exact domains/subdomains, not substring matches.
- Instructions select the link supporting the actual chat claim; composite claims may
  use the frozen finding or multiple necessary sources. URLs do not upgrade claim strength.
- No collector, lane, preset, compose/finalize invocation, request budget, deadline or
  agent sequence changed. Citations are rendered/read in the existing report step and
  formatted in the existing answer turn. The target remains 5–7 minutes, capped at ten
  under the existing stopping rules; live model/network latency is not guaranteed.
- Canonical changes were mirrored to Claude Code with its documented differences intact.
  Frozen research and history were not modified; the saved Flybrain snapshot still verifies.

Review improved the initial test fixture to express all required typed gap fields;
the corrected test confirms gaps cannot acquire affirmative source citations.

## Validation

- Canonical EVM: **425 tests passed**.
- Mirrored Claude EVM: **425 tests passed**.
- Crypto research: **31 tests passed**.
- Rug check: **18 tests passed**.
- Solana diligence: **23 tests passed**.
- Total: **922 tests passed**. Five new citation regressions per EVM copy cover
  existing-summary integration, frozen input preservation, no network access, exact
  evidence routing, local fallbacks, failed/redacted/support-role exclusions, safe URL
  escaping, duplicate suppression, the two-link cap and deceptive hostname labeling. The corrected
  integration regression also prohibits emoji/image substitutes in source citations
  while preserving the assessment markers.
- Existing Flybrain evidence rendered offline with adjacent Market snapshot/Repository
  links; 100 summary renders averaged **0.325 ms** locally. This is summary-render time,
  not a live diligence benchmark. No network or agent run was used for the preview.
- `git diff --check` passed; mirror comparison showed only documented port differences.
- The optional system skill `quick_validate.py` could not run because PyYAML is absent
  in both available Python runtimes. Frontmatter was verified byte-identical to HEAD;
  the skill's existing regression suites passed. No dependency was installed for formatting.

## Changed files

Canonical paths under `skills/crypto-evm-token-due-diligence/`, mirrored under
`.claude/skills/crypto-evm-token-due-diligence/`:

- `SKILL.md`
- `references/evidence-and-output.md`
- `references/runbook.md`
- `scripts/render_report.py`
- `scripts/validate_bundle.py` (reporting version only)
- `tests/test_finding_citations.py`
- `assets/workflow-release.json`
- `assets/reporting-release.json`

Also updated: `README.md`, the mirror's `CLAUDE-CODE-PORT.md`, and this review record.
Backend version remains 3.4.2; schema versions, registration and provider policy are unchanged.

Suggested commit message: `Use native EVM source links without emoji logo substitutes`

No commit or push performed.

## Source-branding correction

Removed emoji prefixes from all generated source labels and local evidence links;
kept assessment/gap markers intact. Mirrored instructions and tests require native links,
with official company/product icons delegated to the client where supported. No fabricated
logo, favicon request, external asset or additional research step is introduced. Release
versions remain the same unreleased working-tree change.
