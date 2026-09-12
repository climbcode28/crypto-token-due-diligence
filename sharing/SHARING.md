# Public sharing handoff — 2026-09-10

**Superseded (2026-09-11).** This repository is now published directly: friends clone it and run
`./install.sh` (see the README quick start). Personal policy lives in the untracked
`HANDOFF.local.md`, so no sanitized export is needed. The export procedure and manifest below
are kept as history.

**Maintenance note (2026-09-11):** Crypto Rug Check and the old Crypto Research workflow were retired. The current export
manifest and templates include the new token router and two canonical specialists. The prepared directory and
validation counts below describe the original snapshot; rebuild after reviewing
current source hashes before sharing.

The original prepared copy is `share-export/crypto-research-public/` (ignored in this
personal hub). After rebuilding, copy the new export's **contents, including its hidden
folders**, into a fresh repository.
Do not copy this hub's `.git/` or publish this hub wholesale. Nothing was committed,
pushed, published or sent to Telegram during preparation.

## Exactly what to include

| Public destination | Source in this hub | Why |
| --- | --- | --- |
| `skills/crypto-evm-token-due-diligence/` | Same path, excluding compiled caches | Canonical EVM skill, both lane briefs, helpers, schemas, references and tests. |
| `skills/crypto-solana-token-due-diligence/` | Same path, excluding compiled caches | Sibling routing and Solana support. |
| `skills/crypto-token-due-diligence/` | Same path, excluding compiled caches | Offline router, metadata and regression tests. |
| `.agents/skills/crypto-evm-token-due-diligence` | Generated relative symlink to `../../skills/crypto-evm-token-due-diligence` | Codex project registration. |
| `.claude/skills/crypto-evm-token-due-diligence/` | Same path | Optional Claude host adaptation; retain with the canonical siblings. |
| `.claude/agents/evm-liquidity-lane.md` | Same path | Optional Claude lane wrapper. |
| `.claude/agents/evm-project-lane.md` | Same path | Optional Claude lane wrapper. |
| `docs/diagrams/evm-diligence-architecture-dark.png` | Same path | Single maintained architecture diagram. |
| `README.md` | `sharing/README.public.md` | Public usage, installation and tests. |
| `AGENTS.md` | `sharing/AGENTS.public.md` | Portable project guidance. |
| `HANDOFF.md` | `sharing/HANDOFF.public.md` | Neutral provider policy; no inherited paid-use authorization. |
| `.gitignore` | `sharing/gitignore.public` | Excludes future local data and credentials. |
| `FILES.sha256` | Generated | Exact hash list for the selected files. |

The machine-readable [export manifest](export-manifest.json) enumerates every copied file
and its source hash. The symlink and hash list are generated separately. Claude support
can be omitted for a Codex-only distribution; keep all three canonical skills either way.
No license was chosen on the owner's behalf. Select one before publishing for reuse.

## What remains private

- This hub's `README.md`, `AGENTS.md` and `HANDOFF.md`: personal installation and provider
  context. Use the public replacements above.
- `research/`, `runs/`: token reports, captured web/RPC evidence, SQLite sessions,
  source snapshots, scratch tooling and local paths. These remain ignored and local.
- `history/`, `plans/`: frozen provenance, development records and acceptance evidence.
  Retained for this hub's maintenance/replay requirements; unnecessary for distribution.
- `.git/`: history, local account/path metadata and application task state.
- `.claude/settings.json`: project-wide permission allowlist. The optional Claude skill
  still has its own declared allowed-tools; recipients should inspect it.
- `sharing/`, diagram generation notes, caches, `.env*`, private keys and user configuration:
  not part of the distribution. The public export contains only its explicit allowlist.

Some release JSONs retain historical `review_record` pointers into private `plans/`.
They are documented provenance references, not required runtime files; source bytes
and released versions were preserved rather than rewriting their history.

## Cleanup and audit

- Scanned 13,556 regular files outside `.git/`, including ignored run folders, for
  private-key headers, common service-token formats, credential-bearing URLs,
  long credential assignments and this user's absolute home path. This was an
  automated content/inventory review, not a line-by-line security audit or Git-history scan.
- Portable source matches were synthetic URL rejection/redaction fixtures at
  `example.com` / `api.invalid`. Compiled Python caches contained absolute local paths.
  No apparent live credential was found in the selected export under those checks;
  pattern matching cannot guarantee absence of every secret format.
- Removed 21 old diagram/image-prompt files and 39 compiled cache files from current
  skill trees. Renamed the final dark PNG to its stable main filename. Updated current
  links and annotated historical plan links as removed, without rewriting their results.
- Preserved research evidence and frozen history in the personal hub. Age alone is not
  evidence that a report, snapshot, legacy renderer or regression fixture is disposable.
- Exact deleted-file list: [cleanup-record.json](cleanup-record.json).

## Architecture recommendation

Keep the present arrangement. The symlink resolves to the canonical EVM folder, and its
`assets/lane-brief-liquidity.md` and `assets/lane-brief-project.md` already contain the
shared lane instructions. `broad_collect.py brief` adds run-specific facts and the cutoff.
Codex spawns its own subagents with those briefs. The `.claude/agents/*.md` files only wrap
the briefs for Claude's tool names; copying or symlinking those wrappers into Codex would
not configure Codex agents. Custom Codex agents use a different TOML format and are optional.

All shared scripts/tests/briefs matched between canonical and Claude copies; the only
differences were those documented in `CLAUDE-CODE-PORT.md`. The single-source briefs
avoid a second set of checklists drifting over time. They are instruction-level limits,
not a separate hard sandbox. Consider custom Codex profiles only if a concrete need for
host-specific settings emerges. A live Codex run remains the useful next validation;
this cleanup did not perform paid RPC or a live token investigation.

Official references checked:
[skill discovery and symlinks](https://learn.chatgpt.com/docs/build-skills),
[Codex subagents and optional custom profiles](https://learn.chatgpt.com/docs/agent-configuration/subagents).

## Validation

The exported copy passed all README suites: research 31, EVM through the relative
Codex symlink 352, rug check 18, Solana 23, Claude EVM 352 (776 total).
Python 3.14 emitted non-failing ResourceWarnings for mocked HTTPError cleanup in the
EVM suites. The 231 copied files matched their reviewed SHA-256 hashes, the skill link
resolved inside the export, and all Markdown file links in the export resolved.
The export is approximately 4.2 MB, without Git history or private run data.

## Rebuilding later

From this hub, use a new destination:

```sh
python3 sharing/export.py /path/to/new-empty-export
```

The exporter refuses existing destinations and files changed since this review. After
future skill changes, review the changed/new files and refresh `export-manifest.json`
hashes and entries intentionally before rebuilding. It never copies unlisted files,
follows external source symlinks, initializes Git, publishes or grants provider access.
