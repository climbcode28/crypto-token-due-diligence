# RH Trenches source integration and architecture diagram

## Phase 1 — Integrate the reviewed source and update the diagram

Requested workflow: implement-review-improve. This single phase is resolved from the
user's explicit request and the preceding live-site assessment; existing source plans
cover earlier additions, not RH Trenches. The working tree was clean at preparation.

Add RH Trenches as a supplementary source for tracked Fomo wallet activity on Robinhood
Chain mainnet (4663). Preserve exact-target identity, attributed observations, the
existing coordinator's dRPC-first verification, private-env instructions, one shared
deadline/budget, and the three-lane ownership model. Add no API client, collector,
report schema, token recommendation, or new provider requirement.

Implement in canonical `skills/crypto-evm-token-due-diligence` first; mirror the relevant
text into `.claude/skills/crypto-evm-token-due-diligence` using its port conventions.
The Codex project registration remains a symlink to canonical, with no Personal copy.
Version additive source instructions as workflow 1.5.0; backend 2.1.0 and reporting
1.1.2 remain unchanged. Retain existing tests and add meaningful manual routing cases.

After skill review and verification, update the current architecture diagram as v4:
add a distinct "Wallet activity" source category containing "RH Trenches" and
"Tracked Fomo wallets · Robinhood"; retain every previous source. In shared evidence,
show "Wallet leads · onchain checks" as an additional line. Retain specialist roles,
the coordinator, all existing connectors and assessments. Update the editable SVG and
light/dark image variants while preserving the established sketch style and palette.

Acceptance criteria:

- Explicit RH Trenches source row, discoverable platform adapter and lane owner.
- Exact chain/address checks; symbol fallback cannot substitute a namesake token.
- Tracked-wallet/history/filter limitations stay explicit; no activity is not proof
  of no trades, clean history or an absent creator exit.
- Estimated values, displayed profit, persona attribution and automated warning labels
  remain source observations until the necessary execution/accounting/control evidence.
- Fomo/RH Trenches duplicates share provenance; bounded lookups fit the existing budget.
- dRPC access/loading/authorization and provider-first logic remain intact.
- Canonical/Claude guidance agree apart from documented tool/path conventions; versions
  and links agree, and no helper, schema or frozen evidence is changed.
- Diagram labels express supplementary wallet leads and verification without implying
  RH Trenches is a trading venue, a launchpad, an RPC provider or a new specialist.
- Skill regressions, manual cases, structural checks and visual inspection pass.

Validation from the repository root: canonical EVM and research standard-library
unittest suites, Claude EVM suite, skill-creator quick validation when its existing
dependency is available, local links/fragments and release metadata, provider-section
and helper-byte preservation, actual diff review, SVG XML/label/connector checks,
and visual inspection of both PNGs. Re-run only checks affected by review fixes.

## Source evidence from the preceding assessment

On 2026-09-08 UTC, `https://robinhoodtrenches.com/` redirected to
[RH Trenches](https://rhtrenches.com/). A hidden in-app browser loaded live data without
login: 147 tracked wallets, a displayed history start, buy/sell rows, Fomo persona links,
full EVM wallets, contract addresses and explorer transaction links on chain 4663.
These were site observations, not independently verified trade/accounting facts.

The interface exposed a warning-hiding "clean" filter; some dollar values were labeled
as price-feed estimates without a readable cash leg. A potential-honeypot tooltip used
many buys and few sells as its heuristic. A full-contract filter failed to show known
VISTA rows that a symbol lookup returned. These observations justify evidence limits
and a verified-address fallback; they are not permanent UI/API guarantees.

Text fetching exposed only the page shell. Hidden browsing supplied the live rows.
No documented API/export, complete history, wallet-selection methodology or independent
P&L calculation was verified. No live RPC, paid dRPC usage or credential access is
needed for this maintenance phase. Do not treat this saved assessment as fresh token
evidence in later investigations.

## Execution, review and verification

Phase 1 completed on 2026-09-08 UTC using the implement-review-improve workflow.
Implemented canonical guidance, ran its regression suite, mirrored into Claude Code,
reviewed the actual changes directly, applied the fixes below and verified the result.
No commits or pushes were made.

### Changed files and delivered artifacts

- Canonical [SKILL.md](../skills/crypto-evm-token-due-diligence/SKILL.md),
  [source routing](../skills/crypto-evm-token-due-diligence/references/source-routing-and-execution.md),
  [platform adapter](../skills/crypto-evm-token-due-diligence/references/platforms.md#rh-trenches-tracked-wallet-activity),
  [manual scenarios](../skills/crypto-evm-token-due-diligence/references/reporting-scenarios.md#rh-trenches-routing-and-evidence-cases)
  and [workflow release](../skills/crypto-evm-token-due-diligence/assets/workflow-release.json).
- The same five files in the [Claude Code copy](../.claude/skills/crypto-evm-token-due-diligence/SKILL.md),
  plus its [port notes](../.claude/skills/crypto-evm-token-due-diligence/CLAUDE-CODE-PORT.md).
- [README.md](../README.md) source/version entry and links to the current diagram.
- New light PNG (superseded asset removed),
  dark PNG (superseded asset removed),
  editable SVG (superseded asset removed) and
  built-in imagegen prompt set (superseded asset removed).
  The PNGs are generated visual variants, not exact SVG rasterizations. Previous
  diagram versions are preserved. This plan records the implementation and review.

### Direct review and improvements

| Finding | Fix and verification |
| --- | --- |
| P2: wording about material trade verification could imply dRPC is mandatory, contradicting the existing optional-provider policy when configuration, authorization or capability is absent | Reference the coordinator's existing policy explicitly, with matching authorized dRPC first and authorized fallback when unavailable. Reviewed against the unchanged provider section and backend guide. |
| P3: source applicability and lookup wording could leave the network or time limit ambiguous | Name Robinhood Chain mainnet (4663) explicitly and bound the initial lookup to 30 seconds or the remaining collection window, whichever is shorter. Deepening stays within the original budget. |
| P3: an early diagram subtitle, "Wallet leads → verified trades", could imply every lead is successfully verified | Use "Wallet leads · onchain checks" in all v4 variants. The adapter separately requires successful receipts and matching decoded flows for material execution claims. |

Also kept the new README release paragraph outside the unrelated fast-check section.
Final direct review covered both entrypoints, the new adapter, source/lane routing,
all nine synthetic scenarios, release metadata, port differences, README, new SVG,
both PNGs and the saved prompts. No remaining actionable findings or unrelated
refactors were identified.

The nine manual cases were reviewed for other-chain namesakes, failed address filters,
untracked wallets/intervals, estimates and incomplete cost basis, reverted/mismatched
transactions, unproven persona control/creator roles, hidden warnings and heuristics,
shared Fomo provenance, and stale/inaccessible data near cutoff. Each required outcome
is supported by the final instructions. This is a reasoning review, not an automated
live-agent benchmark or proof of the site's accuracy.

### Verification results and limits

- Canonical EVM suite: **172 passed**; research suite: **31 passed**; Claude EVM suite:
  **172 passed**. Commands used the documented standard-library unittest discovery with
  `PYTHONDONTWRITEBYTECODE=1`. Total: **375 passing tests**. The unchanged rug-check and
  Solana suites were outside this phase's validation scope.
- Preservation checks passed: **30 Python helper/test files** are byte-identical to
  HEAD; provider-context sections, README private-env setup, HANDOFF, AGENTS, backend
  guide, backend/reporting releases and frozen history are unchanged. No credentials
  were read and no live/paid RPC request was made during this phase.
- Canonical and Claude versions are workflow **1.5.0**, backend **2.1.0**, reporting
  **1.1.2**. Review-record paths resolve from their release files. The original
  Claude-specific entrypoint/tool differences are preserved, and shared adapter and
  scenario files are byte-identical.
- The `.agents` registration resolves to the canonical folder; Personal registrations
  remain absent. Local Markdown link/fragment checks passed, including the adapter,
  review record and all diagram variants.
- SVG XML parses; every previous text label remains and only the four intended labels
  were added. All **14 connector paths** match v3. Both final PNGs were visually checked
  for exact labels, source retention, topology, legibility and margins. A temporary
  Quick Look thumbnail also confirmed the SVG's changed source/shared-evidence region
  has no overlapping or clipped labels; Quick Look's square preview crops the unchanged
  right side, not the underlying SVG canvas.
- `git diff --check` passed. The initial ad hoc release-link check incorrectly resolved
  a metadata path from the skill root; correcting the check to use the JSON file's
  directory passed without changing valid release paths.
- The optional skill-creator `quick_validate.py` could not start under either system
  or bundled Python because **PyYAML is not installed**. No dependency was installed
  for this documentation change. Frontmatter is unchanged; this unavailable check is
  not reported as passing. Quick Look initially hit a sandbox initialization error;
  the same bounded local thumbnail render succeeded through reviewed escalation.

All required deliverables and acceptance criteria are satisfied. Source accuracy,
complete history, live end-to-end latency and independent P&L remain unverified as
specified in the adapter. Suggested commit message:
`feat(evm): add RH Trenches source and update architecture diagrams`.

Diagram cleanup, 2026-09-10: superseded assets were removed; the maintained
[dark architecture diagram](../docs/diagrams/evm-diligence-architecture-dark.png) reflects the current workflow.
