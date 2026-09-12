# EVM assessment calibration

## Scope and decision

The user authorized updating the EVM diligence skill and its Claude Code copy after
a report presented unfinished checks as yellow risk flags and underrepresented market
adoption. This is one implement-review-improve phase derived from that discussion;
no earlier plan phase or live research is required. The initial working tree was clean.

## Phase 1 — Calibrate evidence gaps and adoption context

1. Separate pure research gaps into neutral **Unverified** output. Keep supported
   positives, observed concerns and adverse inferences distinct. Missing evidence
   limits confidence and can prevent a decision without alleging a token defect.
2. Add a bounded adoption/maturity and token-economics screen. Consider sustained use,
   market valuation versus depth, social participation, operating history and actual
   token benefits. Avoid numerical safety scores, popularity-based overrides and
   automatic penalties for absent rights that were never promised.
3. Preserve the eleven risk dimensions, strict evidence gates, critical-finding
   visibility, research deadlines, provider policy and frozen evidence. Update assembly,
   validation and rendering together; preserve legacy rendering and frozen replay.
4. Version workflow/reporting behavior, update active references, mirror canonical
   changes into Claude Code while retaining its documented execution differences.

## Acceptance and validation

- Pure gaps render in a separate neutral section, including compatible older strict
  inputs whose machine signal is Potential Risk. New assembly emits Unverified.
- An observed or inferred adverse finding cannot be moved into that neutral section;
  all high/critical adverse findings remain individually visible despite adoption positives.
- Adoption and token-economics findings are evidence-linked and independently described;
  partial/unavailable technical dimensions never become passes through market context.
- Missing history/access is a research limitation; no automatic adverse creator,
  audit or holder-rights conclusion. Disclosed discretion and failed promises differ.
- Relevant regression cases exercise rendering, validation, assembly and replay.
- Run all four README standard-library unittest suites and the Claude EVM suite.
  Inspect final changes, local reference links, release records and canonical/Claude parity.
- Leave changes uncommitted. Do not alter prior research reports or history provenance.

## Review and completion record

Phase 1 is complete. Workflow and reporting versions are **2.1.0** in both skill
copies; the backend remains **3.0.0**. No further phase is authorized by this plan.

### Implemented files

The canonical [skill](../skills/crypto-evm-token-due-diligence/SKILL.md) and the
[Claude Code skill](../.claude/skills/crypto-evm-token-due-diligence/SKILL.md) include
the same assessment behavior. Changes in both directories cover:

- `SKILL.md`, `assets/reporting-release.json` and `assets/workflow-release.json`.
- New `references/adoption-and-assessment.md`, plus `bundle-format.md`,
  `core-surfaces.md`, `evidence-and-output.md`, `examples.md`, `improvement-loop.md`,
  `project-credibility.md`, `report-replay.md`, `reporting-scenarios.md`,
  `source-routing-and-execution.md`, `strict-report-profile.md` and
  `supported-research-flow.md` in `references/`.
- `scripts/bundle_assemble.py`, `render_report.py`, `report_profile.py` and
  `validate_bundle.py`.
- New `tests/test_assessment_reporting.py`, plus `test_research_helpers.py` and
  `test_strict_profile.py` in `tests/`.

The root README and Claude `CLAUDE-CODE-PORT.md` record the current versions and
behavior. Claude's tool/execution conventions and relative release-record paths
remain distinct; changed scripts, tests and shared references match the canonical
copy. The project-only Codex symlink remains unchanged.

### Direct review and improvements

Reviewed the actual code, callers, new tests, instructions, examples and final diff.
The review covered typed gap classification, serious-finding visibility, old strict
input compatibility, legacy rendering, source immutability, escaping and Claude parity.

- **P2, fixed — legacy compatibility:** the legacy renderer does not support the new
  signal/topics. Validation now rejects them for legacy input before rendering;
  regression coverage exercises each new value. Existing legacy output is preserved.
- **P3, fixed — empty presentation:** an all-gap summary would leave an empty assessed
  findings table. The renderer now omits that table and explicitly states that no
  assessed findings were selected; its gap-only regression checks this behavior.
- **P2, fixed — inconsistent example:** the redemption-cycle example in
  `references/reporting-scenarios.md` still labeled missing operational evidence as
  Potential Risk. It now appears as Unverified, separately from the demonstrated
  fee-path defect and creator-sale concern. The corrected example is mirrored.
- The stronger summary gate rejects one existing invalid fixture earlier. Its expected
  error was updated to that gate; the separate assertion for individual high/critical
  findings remains. No assertion or evidence requirement was relaxed.

No actionable review findings remain within this phase. There are no deferred product
decisions. No numerical score, popularity override or empirical probability model was
introduced.

### Acceptance evidence and checks

All suites ran from the repository root with `PYTHONDONTWRITEBYTECODE=1 python3 -m
unittest discover -s <directory> -q`:

| Directory | Result |
| --- | --- |
| `skills/crypto-evm-token-due-diligence/tests` | 252 passed |
| `.claude/skills/crypto-evm-token-due-diligence/tests` | 252 passed |
| `skills/crypto-research/tests` | 31 passed |
| `skills/crypto-rug-check/tests` | 18 passed |
| `skills/crypto-solana-token-due-diligence/tests` | 23 passed |

**576 test executions passed**, including the mirrored EVM tests. The twelve new
assessment regressions initially exposed missing behavior, then passed after the
implementation. They exercise neutral pure gaps, unchanged older strict sources,
positive adoption alongside technical unknowns, adverse inferences, rejected misuse
of Unverified, serious-finding visibility, legacy guards, escaped output, exact-render
binding and assembly/freezing without draft mutation. The supported CLI-flow test also
checks the default Unverified summary. Existing replay and legacy suites pass.

The bounded adoption/maturity and token-economics guidance was reviewed against the
synthetic scenarios: market cap versus executable depth, sustained use versus social
attention, version-specific operating history, discretion versus a failed promise,
and absent unpromised rights. The eleven dimensions, exact identity/pin standards,
research deadlines and provider policy are unchanged. These are offline behavioral
and reasoning checks, not empirical validation of investment outcomes.

`git diff --check`, changed local Markdown links, release-record links, registration
and canonical/Claude parity checks passed. The optional skill-creator Python format
helper could not run because PyYAML is absent from both inspected Python runtimes.
As a separate fallback, the existing Ruby YAML parser successfully checked both
entrypoints' frontmatter, allowed fields, name/description constraints and unfinished
placeholders. No dependency was installed; the Python helper is not reported as passing.

The original PONS report replay verified successfully with its frozen reporting
engine **2.0.0**. Preserved SHA-256 values:

- Manifest: `e97874b9716036bfd98c46c777d3af25c12b5c0861632c641663fd79a1e59d72`
- Report JSON: `46a62439f40a34475cdec7957c55c10fd23c44f0ec3ef9232ccf5560e6c9e842`
- Report Markdown: `e94bd06a5f882f38095cc47230e610f75701c14898b5a793484ba610a62db928`

The final example correction was documentation-only; it received direct review and
parity/whitespace checks without repeating unchanged passing runtime suites. No live
token investigation, RPC/provider access, frozen-report rewrite, history edit, commit
or push was performed. The only workflow adaptation was saving this single-phase plan
from the already agreed scope because no existing plan covered the request.

Suggested commit message: `Improve EVM diligence calibration and adoption context`.
