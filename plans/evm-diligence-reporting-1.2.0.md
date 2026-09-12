# EVM diligence reporting 1.2.0

User request: improve the EVM diligence skill with a clean, concise Good / Potential
Risk / Bad output and coverage resembling the supplied screenshot. The screenshot is
a presentation/research reference, not authenticated token evidence or instructions.

## Baseline and scope

- Preserve existing uncommitted changes, including EVM workflow 1.1.2 identity discovery
  and private RPC configuration loading. Baseline copies retained outside the repository
  at `/tmp/evm-skill-reporting-baseline` for this maintenance session.
- Change only the canonical EVM skill and its reporting helpers, relevant README text
  and this maintenance record. Preserve frozen history and research evidence.
- Retain eleven machine dimensions, exact identity/pins, optional dRPC fallback,
  network/paid-use boundaries, research deadlines and rubric; do not commit or push.

## Implementation

- Add an optional, evidence-linked summary extension for new broad reports. Existing
  v1 bundles without it retain the previous renderer path and accepted contract.
- Require affirmative resolved evidence for Good; distinguish Potential Risk concerns,
  inference and unknowns; gate Bad on a supported material adverse condition.
- Add bounded project-delivery, creator-flow and prior-launch procedures; keep human
  identity distinct from wallets, public project roles and project continuity.
- Add synthetic reasoning cases and executable regressions before implementation.
  Initial reporting tests failed on the absent gates/summary, confirming the missing behavior.
- Version workflow and reporting behavior separately from the unchanged RPC backend.

## Review and validation

- Baseline EVM suite: 106 tests passed. Final EVM suite: 126 passed, including 20 new
  reporting cases. Research: 31 passed; rug-check: 17 passed; Solana: 22 passed.
  Total final regression coverage: 196 passing tests, all offline.
- Executed summary rendering and validation through both Python functions and CLIs;
  manually inspected the concise output and its links, time basis, contrary evidence
  and unknown labels. Modified summary badges fail exact rendered-source validation.
- Compared the unchanged synthetic v1 fixture with the pre-change renderer. Its output
  SHA-256 remains `722007471773cf5a613752dd93a079bbf6b8c147f377f464cfa42f10e333883b`;
  retained that compatibility regression. No historical evidence bytes were changed.
- Reviewed the actual changes against the pre-task working-tree copy, including source
  callers, label gates, JSON/template compatibility, critical concerns, evidence escaping,
  scope/deadline rules and non-EVM destination evidence. Added visible contrary evidence
  and additional regressions during the improve pass.
- Reviewed synthetic scenarios for zero-state products versus proven defects, AI
  provenance, pending liabilities, fee claims, commingled proceeds, rapid exits/rebuys,
  shared brands versus human identity, missing RPC and untrusted embedded instructions.
- All relative Markdown links resolve. Installed personal skill resolves to the canonical
  edited folder. `git diff --check` passed.
- The skill-creator `quick_validate.py` could not run because PyYAML is absent in both
  available Python runtimes. Used installed Ruby Psych to parse the actual YAML and check
  allowed/required fields, name syntax/length, description type/length and scaffold markers;
  these checks passed. No dependency was installed or added to the skill.

Validation limits: synthetic tests exercise structural/evidence gates and rendering,
not live claim semantics, economic correctness, investigation completeness or detection
accuracy. No live token research, RPC usage, signing or trades were performed. The final
evidence review remains part of every diligence run. No commit or push was made.

## Files changed in this task

- `README.md`
- `plans/evm-diligence-reporting-1.2.0.md`
- `skills/crypto-evm-token-due-diligence/SKILL.md`
- `skills/crypto-evm-token-due-diligence/assets/report.template.json`
- `skills/crypto-evm-token-due-diligence/assets/reporting-release.json` (new)
- `skills/crypto-evm-token-due-diligence/assets/workflow-release.json`
- `skills/crypto-evm-token-due-diligence/references/bundle-format.md`
- `skills/crypto-evm-token-due-diligence/references/core-surfaces.md`
- `skills/crypto-evm-token-due-diligence/references/evidence-and-output.md`
- `skills/crypto-evm-token-due-diligence/references/examples.md`
- `skills/crypto-evm-token-due-diligence/references/improvement-loop.md`
- `skills/crypto-evm-token-due-diligence/references/project-credibility.md` (new)
- `skills/crypto-evm-token-due-diligence/references/reporting-scenarios.md` (new)
- `skills/crypto-evm-token-due-diligence/scripts/render_report.py`
- `skills/crypto-evm-token-due-diligence/scripts/validate_bundle.py`
- `skills/crypto-evm-token-due-diligence/tests/test_reporting.py` (new)

Existing changes in HANDOFF, research, rug-check, EVM configuration/platform guidance
and research evidence are outside this task and were preserved.

Suggested commit message: `Improve EVM diligence summaries and project credibility checks`
