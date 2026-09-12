# Sale-sample communication review — 2026-09-11

## Problem and implementation

The Flybrain response highlighted two small verified sales despite extensive reported
trading. The user correctly understood this as suggesting selling was barely established.
Workflow 3.2.6 distinguishes market activity, the analyst receipt sample and unmeasured
size-dependent execution costs. Broad activity leads when supported; sampled transactions
remain auditable supporting evidence. User-reported trading is acknowledged without
upgrading it to independent receipt verification.

The entrypoint routes this delivery rule to evidence-and-output.md. Five reporting
regression scenarios cover busy and sparse markets, user experience, missing size tests,
and actual restrictions despite active trading. Canonical guidance is mirrored to Claude
Code with port-specific metadata and paths preserved. Backend/reporting versions and
receipt-verification thresholds are unchanged; no live research was rerun.

## Review and improvement

Reviewed against the original miscommunication and the five scenarios. The rule does
not suppress a meaningful historical sale when sellability is the question, equate
indexer data with verified receipts, or hide actual restrictions and price impact.
It does not add collection requests or require user-provided position sizes.

Validation: canonical EVM suite 428/428 passed; mirrored Claude Code EVM suite
428/428 passed. `git diff --check` passed. Copy comparison shows only the documented
port differences. Final instruction review also moved the presentation rule into
summary selection before freezing, so chat need not contradict the frozen report.
The optional skill-creator quick validator could not run: PyYAML is absent in both
available Python runtimes. Frontmatter was unchanged.

Changed files: canonical SKILL.md, references/evidence-and-output.md,
references/reporting-scenarios.md, references/runbook.md and
assets/workflow-release.json; matching Claude Code files plus CLAUDE-CODE-PORT.md;
root README.md and this review record. No commits or pushes.

Suggested commit: `Clarify sale verification samples in EVM diligence reports`.
