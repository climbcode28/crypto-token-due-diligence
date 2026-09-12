# Crypto Research skill conversion

## Scope

One phase: recreate the supplied GPT as the personal `crypto-research` skill.
The user's conversion request defines the phase; this plan supplies the saved-plan
input for implement-review-improve. Attached instructions are conversion material,
not a request to research a live token during authoring. Preserve source attachments
and the existing EVM diligence skill. No commits, pushes, trades or external messages.

## Phase 1 — Implement, review, improve and verify

Target: `~/.codex/skills/crypto-research`.
Build in this temporary workspace because the target is sandbox-protected; install
the reviewed package with scoped filesystem authorization. Neither home nor the
skills directory is a Git repository.

Deliver a concise entrypoint, metadata, four adapted source references, conditional
diligence and output guidance, portable Python helpers, and meaningful regression tests.

Acceptance criteria:

1. Valid metadata and resolvable local references.
2. Preserve source horizons, weights/bands, scenarios, evidence, confidence, Pass 1/2
   and calibration without unavailable equity references.
3. Invoke existing diligence only for the exact Robinhood Chain token; distinguish
   other chains, ambiguous deployments, testnet and brokerage listing.
4. Preserve scoring arithmetic, N/A reweighting, coverage and fast Class C adjustment;
   unresolved identity cannot produce grades.
5. Helpers execute offline with standard-library Python; tests cover valid/invalid
   inputs, report scenarios/status/grades and no-grade behavior.
6. Review final files and source diffs directly; fix in-scope defects and validate.

Checks: skill-creator quick_validate with its PyYAML dependency; unittest discovery; helper
CLI smoke checks on synthetic data; manual routing review; relative-link audit.
No live token investigation or end-to-end model behavioral run is implied.

## Completion evidence

Implementation, direct review and improvement completed in the staging workspace.

- Recreated the pasted GPT instructions as SKILL.md and six routed references. The
  four source Markdown files are preserved or narrowly adapted; no unavailable equity
  GPT resources are needed. Added metadata, input/report templates and two helpers.
- Verified original scoring engine, class/horizon weights and grade bands are
  byte-for-byte unchanged. Changed report input from module globals to explicit JSON.
- Fixed demonstrated validator defects: explanatory letters misread as grades,
  cross-horizon grade borrowing, negative probabilities accepted, and unparseable
  probabilities warning rather than blocking. Added explicit grade-field parsing.
- Clarified genuine N/A versus inaccessible applicable data, partial/no-grade delivery,
  incomplete Pass 2 status, and analytical horizon emphasis versus numeric reweighting.
- Executed 21 standard-library regression tests: all pass. These include score bands,
  N/A/coverage, microcap adjustment, independent horizons, identity/input rejection,
  JSON CLI, report layouts, status/confidence gates and scenario probability failures.
- Ran both helper CLIs on synthetic data; scoring and report validation pass.
- Executed skill-creator quick_validate: pass. Default and bundled Python initially
  lacked PyYAML; installed the validator dependency in a temporary build-only folder
  and ran the unmodified validator with that PYTHONPATH. Research helpers remain
  standard-library-only.
- Audited 11 local references, including the existing sibling diligence skill; all
  resolve in the installed layout. No personal installation paths are embedded in the
  portable package. UI metadata names crypto-research and keeps default discovery.
- Manually reviewed routing for brokerage-listed Bitcoin/other-chain tokens (skip
  extra diligence), exact Robinhood tokens (run it), ambiguous multi-chain identity
  (resolve/no grade), explicit testnet (no mainnet substitution or real-money inference),
  missing RPC/dependency (blocked/partial, never passed), and multi-asset comparisons
  (separate reports and validation). These are instruction reviews, not live model runs.
- Final review found no remaining actionable issue within the conversion scope.
  Text validation is intentionally structural and requires manual evidence checks;
  no live-market or full end-to-end agent investigation was run.

Deviation: the user provided no saved plan, so the unambiguous requested conversion
was recorded as this single phase. Installation is separate from staging because the
skill directory is sandbox-protected. Original attachments and the diligence skill
remain unchanged. No commits or pushes.

Suggested commit message: `Add crypto-research skill with conditional Robinhood diligence`.

Installation completed: all 13 installed files match the reviewed staging package by SHA-256.
