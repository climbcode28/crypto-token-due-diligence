# RH Scan source integration and architecture update

## Phase 1 — Add the reviewed explorer and mirror the skill

Use the requested implement-review-improve workflow for this one phase in
`~/code/crypto-research`. The approved scope is resolved from the
preceding live RH Scan assessment and the user's implementation request. No existing
RH Scan plan was found; the working tree was clean at preparation.

Add RH Scan as a named, supplementary explorer for Robinhood Chain mainnet (4663)
within the existing chain-explorer source category. Preserve the official documentation's
Blockscout entrypoint as an alternate and keep explorer evidence subject to exact-target,
source-correspondence, pin, accounting and attribution standards. Keep all RH Trenches
rules, provider/private-env instructions, request budgets and evidence schemas intact.

Edit canonical `skills/crypto-evm-token-due-diligence` first, run its suite, then mirror
the changes into `.claude/skills/crypto-evm-token-due-diligence` under its port conventions.
Use workflow 1.6.0 for the additive source behavior; backend 2.1.0 and reporting 1.1.2
are unchanged. Add synthetic manual evidence cases, not tests that only match wording.
Add no API client, live RPC collection or new dependency. Do not access credentials.

Create v5 light/dark PNGs and an editable SVG from the current v4 diagrams, preserving
v4. Under Onchain data add "RH Scan · explorer" below "dRPC first · public fallback".
Adjust source-panel spacing as needed, retain every existing source including RH
Trenches, and retain all connector paths, specialist nodes and assessments. The existing
shared-evidence and onchain-checks flow already applies; no new specialist is needed.
Link the current diagrams from README and save the image edit prompts.

User clarification during implementation: under Wallet activity, change the descriptor
from "Tracked Fomo wallets · Robinhood" to "Fomo wallets · Robinhood" in every v5
variant and the SVG accessibility description. This avoids suggesting the skill
maintains a watchlist of particular traders. The source adapter's provider-coverage
limits still describe the source accurately; this clarification changes diagram wording.

Acceptance criteria:

- RH Scan appears in the explorer source row and a discoverable conditional adapter.
- Current chain/address and loaded page state are checked; placeholders are not facts.
- Indexed coverage, top-holder limits, rounded/capped counts, filters, page exports and
  full-history claims are bounded. Empty or inaccessible data never becomes a pass.
- Source badges, proxies, creator/pool labels, internal transfers and transaction
  finality require the existing appropriate verification and attribution.
- No Etherscan-compatible API or stable undocumented endpoint is assumed. Source access
  follows each host's existing tool conventions and the shared fallback/deadline.
- Explorer reads have one owner per fact across existing lanes; shared RH Trenches
  transaction evidence is reused without being counted as another independent trade.
- Canonical/Claude content agrees apart from documented tool/path differences; workflow
  releases and review links resolve; dRPC private-env access and registration are preserved.
- All diagram variants show the intended source label with readable text and intact flow.
- Relevant regression suites, direct review, manual cases and structural checks pass.

Verification: documented standard-library unittest discovery for canonical EVM,
crypto-research and Claude EVM; direct review of actual diffs and new artifacts; port,
release, local-link/fragment, provider/helper preservation and SVG label/connector checks;
visual inspection of PNGs and the SVG's changed region. The optional skill-creator
validator requires PyYAML, which was unavailable in both existing Python environments
earlier in this conversation; do not install a validation dependency for this change.

## Source evidence from the preceding assessment

Inspected 2026-09-08 UTC via public text fetches and a temporary hidden in-app browser.
[RH Scan's about page](https://rh-scan.com/about) identifies it as a community project
for chain 4663, unaffiliated with Robinhood or Etherscan, and claims its own full-history
indexer. [Robinhood's connection documentation](https://docs.robinhood.com/chain/connecting/)
listed [Blockscout](https://robinhoodchain.blockscout.com/) for mainnet. Neither a provider
claim nor a successful page load independently verifies indexing completeness.

The live [sampled WETH page](https://rh-scan.com/token/0x0bd7d308f8e1639fab988df18a8011f41eacad73)
showed a top-1,000 holder table from over 533,000 reported holders, labeled pools,
page-data download controls and capped transfer counts. Its contract tab displayed
"Exact match", TransparentUpgradeableProxy source, ABI/bytecode tabs and compiler
metadata. The address page displayed creator and creation-transaction links.

A sampled [transaction page](https://rh-scan.com/tx/0x7edaefee6d6fde394cfbe9f159994deabd8ec0b58f23d41564b92b48a208f099)
displayed success, block/time, sequencer confirmation, internal transfers and decoded
event data with raw topics and an integer amount. These are observed UI capabilities,
not independent receipt, runtime, holder-balance or financial verification.

Text fetching returned shells or a 403 on sampled detail pages; hidden browsing loaded
the records. Initial "Unknown Token" and zero-holder placeholders changed after loading.
[API documentation](https://rh-scan.com/api-docs) said endpoint references, access keys,
rate limits and stability guarantees were not finalized. Export correctness and complete
history were not tested. No paid RPC or private-env access was needed for this assessment.
Future diligence must capture fresh target evidence rather than reuse this sample.

## Execution, review and verification

Phase 1 completed on 2026-09-08 UTC. Implemented the canonical source instructions,
ran canonical tests, mirrored the Claude copy, reviewed actual diffs and final content
directly, and incorporated the user's diagram clarification. Changes remain in the
working tree; no commit or push was performed.

### Changed files and deliverables

- Canonical [SKILL.md](../skills/crypto-evm-token-due-diligence/SKILL.md),
  [source routing](../skills/crypto-evm-token-due-diligence/references/source-routing-and-execution.md),
  [RH Scan adapter](../skills/crypto-evm-token-due-diligence/references/platforms.md#rh-scan-explorer),
  [manual evidence cases](../skills/crypto-evm-token-due-diligence/references/reporting-scenarios.md#rh-scan-routing-and-evidence-cases)
  and [workflow release](../skills/crypto-evm-token-due-diligence/assets/workflow-release.json).
- The same five files in the [Claude Code copy](../.claude/skills/crypto-evm-token-due-diligence/SKILL.md),
  and its [port notes](../.claude/skills/crypto-evm-token-due-diligence/CLAUDE-CODE-PORT.md).
- [README.md](../README.md) describes workflow 1.6.0 and links the current architecture.
- New v5 light PNG (superseded asset removed),
  dark PNG (superseded asset removed),
  editable SVG (superseded asset removed) and
  image edit prompts (superseded asset removed),
  plus this plan/review record. Earlier diagram versions are preserved.

### Direct review and improvement

Reviewed both skill entrypoints, source selection and ownership in context, the new
adapter, all 12 synthetic cases, release metadata, Claude port conventions, README,
the actual patch and all new diagram artifacts. No actionable skill defects were found;
no unrelated refactors or artificial test-only wording assertions were added.

The user identified an ambiguity in the diagram: "Tracked Fomo wallets" could suggest
the skill maintains a watchlist of named traders. Updated every v5 image and the SVG's
visible/accessibility wording to "Fomo wallets · Robinhood". Confirmed the RH Scan
label, other sources, shared-evidence flow, specialist nodes and assessments remain.
The final prompts record both editing steps. No remaining actionable findings.

The 12 manual cases cover loading placeholders; holder/export/count limits; verified
proxy source with unresolved implementation; creator/named-wallet attribution; singleton
custody; sequencer versus settlement/destination evidence; mislabeled or failed trades;
unpinned state; reused transaction evidence; undocumented API endpoints; testnet/mainnet
identity; and access failure near cutoff. Direct reasoning review found each required
outcome supported by the final instructions. These are synthetic acceptance cases,
not live-agent tests or an independent audit of RH Scan.

### Verification and limits

- Documented standard-library commands passed: canonical EVM **172**, research **31**,
  Claude EVM **172** — **375 tests total**. Used `PYTHONDONTWRITEBYTECODE=1 python3 -m
  unittest discover -s <suite>/tests -q` from the repository root. The user's later
  wording correction affected diagrams only, so unchanged Python suites were not rerun.
- Preservation checks passed for **74 supporting skill files**, including all **30
  Python helper/test files** across canonical and Claude. Provider-context and optional
  dRPC sections, README private-env setup, HANDOFF, AGENTS, backend/reporting assets and
  the RH Trenches adapter are unchanged. No credentials were read and no live or paid
  RPC requests were made during this phase; frozen history is unchanged.
- Both copies declare workflow **1.6.0**, backend **2.1.0**, reporting **1.1.2**, with
  previous workflow **1.5.0**. Review paths resolve relative to their JSON files.
  Shared adapter/scenario files match byte for byte; intentional Claude entrypoint and
  source-routing tool/path differences are identical to their pre-change differences.
- The Codex project symlink still resolves to canonical; Personal EVM registrations
  remain absent. Local Markdown link/fragment checks passed for source, record and
  diagram links. All previous diagram files are byte-identical to HEAD.
- SVG XML parses; all **14 connector paths** match v4. Visible text changes are limited
  to adding "RH Scan · explorer" and the requested Wallet activity descriptor rename.
  Both final PNGs were visually inspected for wording, preserved sources, topology,
  margins and legibility. The SVG source-panel region was also rendered with Quick Look
  for inspection; its square thumbnail crops the unchanged right side, not the SVG.
- `git diff --check` passed. The optional skill-creator validator remains unavailable
  because PyYAML was missing from both existing Python environments earlier in this
  conversation; it was not rerun or reported as passing. Frontmatter is unchanged,
  and no validation dependency was installed.

All required acceptance criteria are satisfied. The only scope adjustment is the user's
diagram wording clarification. Source completeness, historical/export correctness,
source-to-runtime correspondence and end-to-end performance are not established by these
maintenance checks. Suggested commit message:
`feat(evm): add RH Scan source and clarify architecture diagrams`.

Diagram cleanup, 2026-09-10: superseded assets were removed; the maintained
[dark architecture diagram](../docs/diagrams/evm-diligence-architecture-dark.png) reflects the current workflow.
