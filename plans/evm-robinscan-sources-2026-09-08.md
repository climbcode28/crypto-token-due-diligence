# Robinscan source integration and architecture update

## Phase 1 — Add the reviewed explorer and mirror the skill

Execute one implement-review-improve cycle in `~/code/crypto-research`.
Scope comes from the preceding Robinscan assessment and the user's explicit approval.
No Robinscan plan existed, so this record saves that agreed phase. The earlier RH Scan
1.6.0 edits and v5 diagrams are already present and uncommitted; preserve and build on
them. Preparation captured file hashes and relevant original files outside the repo at
`/private/tmp/evm-robinscan-baseline-20260908` to isolate this phase's changes.

Add Robinscan alongside RH Scan in the existing Robinhood mainnet explorer category.
Select sources by the missing fact, keeping the shared deadline and one-alternate limit.
Document coverage and source/proxy/trace limits, separate Fomo's cross-chain leaderboard
from Robinscan's capped wallet PnL, and describe authenticated API/MCP as optional future
access requiring separately provisioned credentials. No client installation, API/RPC
collection, credential access, paid usage or new dependency is part of this phase.

Edit canonical `skills/crypto-evm-token-due-diligence` first, run its suite, then mirror
into `.claude/skills/crypto-evm-token-due-diligence` with the existing tool/path differences.
Version the additive source behavior as workflow 1.7.0; backend 2.1.0 and reporting 1.1.2
remain unchanged. Add synthetic judgment cases in the established reporting scenarios.

Create sibling v6 light/dark PNGs and editable SVG from v5, changing the Onchain data
source line to `RH Scan · Robinscan`. The existing shared-evidence, specialist and
onchain-check flow applies to both explorers; no extra lane or connector is needed.
Keep `Fomo wallets · Robinhood`, every other source, all assessments and connections.
Update the SVG accessibility description, README links and image prompt record.

Acceptance criteria:

- Both explorers and their conditional adapters are discoverable in the skill.
- Mainnet 4663 and exact identity, loading/missing data, index freshness/history,
  current holder snapshots, top-N coverage, adjusted labels and partial exports are bounded.
- Source/ABI/proxy/trace and rollup publication records remain evidence candidates under
  existing runtime, pin, receipt, accounting and attribution rules; scores do not certify safety.
- Fomo leaderboard PnL/trades/volume are cross-chain; only Top Holdings is chain-filtered.
  Repeated Fomo data and the same onchain event are not independent corroboration.
- Robinscan wallet PnL remains a distinct Beta estimate with history/basis limits.
  Documented partner API/MCP capability is not claimed as installed, tested or public access.
- Source ownership, research budgets, dRPC private-env access, optional fallback, engine
  schemas, frozen history and project-only Codex registration are preserved.
- Canonical and Claude content agrees apart from documented host differences.
- All v6 diagrams have the intended labels, legible text and intact topology; v5 is retained.
- Relevant unittest suites, manual evidence cases, direct review, preservation, links,
  release metadata, SVG structure and visual checks pass.

Validation uses the README standard-library unittest commands for canonical EVM and
crypto-research, then the port-notes command for Claude EVM. Review actual phase diffs
against the snapshot, including new files. Run `git diff --check` and inspect images.
The optional skill-creator validator previously lacked PyYAML; do not install a new
validation dependency or call an unavailable check passing. No commit or push.

## Source evidence

Public pages and documentation inspected on 2026-09-08 UTC in the preceding assessment:
[explorer](https://robinscan.io/), [overview](https://docs.robinscan.io/),
[coverage](https://docs.robinscan.io/data-coverage),
[verified contracts](https://docs.robinscan.io/api-contracts),
[batches](https://docs.robinscan.io/blocks-and-batches),
[partner API](https://docs.robinscan.io/api-reference),
[MCP](https://docs.robinscan.io/mcp), and
[Fomo leaderboard explanation](https://robinscan.io/leaderboard).

Public homepage and token metadata populated in text fetches, while sampled transaction
and holder tables retained loading rows. A sample batch detail fetch failed. These
observations do not establish full UI/API availability, indexing completeness, latency,
source-to-runtime correspondence or financial accuracy. API/MCP, contract read metadata
and analytical methods were assessed from documentation, without authenticated access.
Fresh diligence must inspect current documentation and capture target-specific records.

During implementation, also read the dedicated [Token Intelligence](https://docs.robinscan.io/api-intelligence)
and [wallet PnL](https://docs.robinscan.io/api-wallet-pnl) documentation. The former defines
sample completeness as a ratio and permits a null holder snapshot block; the latter
documents zero-cost inbound non-swap quantity and current-rate USD conversion. These
details refine the adapter and synthetic cases without asserting authenticated access.

## Execution, review and verification

Phase 1 completed on 2026-09-08 UTC. Implemented the canonical source instructions,
ran its suite, mirrored the Claude copy and ran that suite, reviewed actual changes
against the preparation snapshot, and applied the in-scope corrections below. All
changes remain in the working tree alongside the earlier RH Scan work; no commit or push.

### Changed files and deliverables

- Canonical [SKILL.md](../skills/crypto-evm-token-due-diligence/SKILL.md),
  [source routing](../skills/crypto-evm-token-due-diligence/references/source-routing-and-execution.md),
  [platform adapters](../skills/crypto-evm-token-due-diligence/references/platforms.md#robinscan-explorer),
  [manual evidence cases](../skills/crypto-evm-token-due-diligence/references/reporting-scenarios.md#robinscan-routing-and-evidence-cases)
  and [workflow release](../skills/crypto-evm-token-due-diligence/assets/workflow-release.json).
- Claude [SKILL.md](../.claude/skills/crypto-evm-token-due-diligence/SKILL.md),
  [source routing](../.claude/skills/crypto-evm-token-due-diligence/references/source-routing-and-execution.md),
  [platform adapters](../.claude/skills/crypto-evm-token-due-diligence/references/platforms.md#robinscan-explorer),
  [manual cases](../.claude/skills/crypto-evm-token-due-diligence/references/reporting-scenarios.md#robinscan-routing-and-evidence-cases),
  [workflow release](../.claude/skills/crypto-evm-token-due-diligence/assets/workflow-release.json)
  and [port notes](../.claude/skills/crypto-evm-token-due-diligence/CLAUDE-CODE-PORT.md).
- [README.md](../README.md) records workflow 1.7.0 and links the current architecture.
- New v6 light PNG (superseded asset removed),
  dark PNG (superseded asset removed),
  editable SVG (superseded asset removed) and
  built-in image edit prompts (superseded asset removed),
  plus this plan/review record. This phase modifies 12 existing files and adds five files.

### Direct review and improvements

Reviewed source selection and lane ownership, both adapters and entrypoints, releases,
Claude conventions, README, all 13 new judgment cases, and every new diagram artifact.

- P3, corrected: the first mirrored Claude source-index row used singular `explorer`
  while canonical used `explorers`. Aligned the row and verified that only the established
  host-specific differences remain.
- P3, corrected: the synthetic holder case initially described sample completeness as
  `true`. The dedicated API documentation specifies a numeric ratio. Changed the fixture
  to `basis.sampleCompleteness=1`, added a null snapshot block and the required refusal
  to substitute the chain tip, and distinguished adjusted concentration from risk score.
  Linked the dedicated analytical guides, explained zero-cost non-swap quantity, and
  qualified documented web badges by actual live availability.

No remaining actionable findings or unrelated refactors. No deviation from the approved
scope; the agreed phase was saved as a new plan because no Robinscan plan already existed.

### Acceptance evidence

- Both source indexes and the Robinhood adapter route to RH Scan or Robinscan by missing
  fact. Source switching shares the existing deadline and one-alternate allowance.
- Direct reasoning review of all **13 synthetic cases** found the required outcomes
  supported by the final instructions: source reuse; exhausted alternate budget; chain
  mismatch; placeholders/unseen accounts; top-N coverage and null pins; adjusted/unknown
  scores; pagination/export scope; proxy/trace uncertainty; batch/destination limits;
  cross-chain Fomo totals; capped/non-swap native PnL; repeated upstream/event evidence;
  and unavailable partner access. These are manual judgment cases, not live-agent tests.
- Documented standard-library commands passed: canonical EVM **172**, crypto-research
  **31**, Claude EVM **172** — **375 tests**. Commands used
  `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s <suite>/tests -q`
  from the repo root. Final corrections affected prose only; their manual/parity checks
  were repeated, rather than rerunning unchanged Python logic.
- Hash comparison against the starting working tree preserves **467 of 479 existing
  files**; only the 12 intended existing files changed. All Python code/tests, supporting
  engine/schema assets, HANDOFF, AGENTS, frozen history and prior diagrams are preserved.
  Entrypoint changes are limited to two source-index rows; all provider-context, private
  env and optional dRPC instructions are byte-identical. README's provider setup is also
  unchanged. No private credentials were read and no provider/RPC requests were made.
- Canonical/Claude shared adapter and scenario files match byte for byte. Their existing
  entrypoint and source-routing host differences are unchanged. Both releases declare
  workflow **1.7.0**, previous **1.6.0**, backend **2.1.0**, reporting **1.1.2**, and resolve
  to this review record. Project registration still links to canonical; no Personal
  EVM registration was created.
- Local Markdown paths/fragments resolve and `git diff --check` passes. SVG XML parses;
  all **14 connectors**, dimensions and other visible labels match v5. Its accessibility
  description includes both explorers. Both final PNGs were visually inspected for
  source spelling, retained `Fomo wallets · Robinhood`, complete source lists, topology,
  assessment markers and legibility. Quick Look rendered the changed SVG source region;
  its square thumbnail crops the unchanged right side, not the SVG itself.
- The optional skill-creator `quick_validate.py` was attempted for both copies and
  could not start: `ModuleNotFoundError: No module named 'yaml'`. It is not counted as
  passing. No validation dependency was installed; frontmatter is unchanged.

All required phase deliverables and acceptance checks are satisfied. Authenticated
Robinscan API/MCP access, source-to-runtime matching, index completeness and financial
accuracy remain outside these maintenance checks; future research must establish its
own target evidence. Suggested commit message:
`feat(evm): add Robinscan source and refresh architecture diagrams`.

Diagram cleanup, 2026-09-10: superseded assets were removed; the maintained
[dark architecture diagram](../docs/diagrams/evm-diligence-architecture-dark.png) reflects the current workflow.
