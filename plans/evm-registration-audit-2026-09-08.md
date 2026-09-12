# EVM skill registration and task audit — 2026-09-08 UTC

## Outcome

Recent EVM development reached this repo's canonical
`skills/crypto-evm-token-due-diligence` folder. No reviewed post-migration EVM improvement
was found stranded in a separate Personal skill. The former Personal path was a symlink
to the canonical folder. Earlier Personal installs preceded the project migration.

Codex EVM registration is now project-only: `.agents/skills/crypto-evm-token-due-diligence`
is a relative symlink to `../../skills/crypto-evm-token-due-diligence`, and only the EVM
Personal symlink was removed. All 42 canonical files are byte-for-byte unchanged by
this cleanup. The three other crypto skills retain their existing Personal symlinks.
The Claude Code copy remains, with its port notes updated for the registration change.

The canonical skill still requires provider-context discovery before RPC selection,
then loading the documented private env file with tracing disabled in the same shell
as each check/collection. `HANDOFF.md` still records bounded paid read-only permission
and the configured network, Robinhood Chain mainnet (4663). The private endpoint/key
remain in `~/.config/crypto-research/env`, outside this repo. Neither value was displayed,
copied into the repo, or changed. Current configuration passed an offline availability
check both before cleanup and through the project registration afterward: `ready`,
`run_collector`, no blocking reasons, `network_requests: 0`, `provider_tested: false`.
This verifies local loading and invocation readiness, not live provider health.

## Scope and task evidence

Read the complete available turn pages for 22 crypto-related tasks and two adjacent
setup tasks from September 5–7 MDT, including the archived HOOKR attempt. Inspected
saved edit/command records, task completion messages, repo commit history and present
filesystem resolution. Older pages of the dRPC setup task were paginated to completion.
No messages were sent to other tasks and no task was restarted or modified.

| Exact task title | Task ID | Path conclusion |
| --- | --- | --- |
| Review evm token skill | `01a07512-ba92-7583-b3ec-a128999ca76d` | EVM review/rename used Personal paths before migration; those installed contents were subsequently moved into the repo. |
| Create crypto research skill | `01a07528-8ea5-79e2-a248-b8dde3596d5a` | Research skill and EVM routing were installed before migration. |
| Improve crypto research skills | `01a0754d-3f56-7ed0-8ff5-ee688e28d887` | Backend/fallback work initially installed to Personal; later turns performed the recorded project migration and retained compatibility symlinks. |
| Configure dRPC and offline checks | `01a07735-6c90-7ad0-8539-b9ad05a00ed4` | Setup/policy, timing and browser changes targeted this repo; new rug-check used a Personal symlink to its repo folder. |
| Assess Solana skill support | `01a077b4-0741-7923-8e0d-35c2308b879d` | Chain routing and Solana support targeted canonical repo skills; Personal Solana installation was a symlink. |
| Check FRIES rug risks | `01a077d9-b6f2-7f93-94d6-d8509afad029` | Related rug-check reporting iteration; no separate Personal EVM implementation found. |
| Assess SHROOM token diligence | `01a07824-8c9e-74d3-8d71-50e35bd1d79a` | Robinhood inference and private-env loading instructions changed canonical EVM files; standing authorization was saved in repo context. |
| Improve EVM diligence findings | `01a07853-fdf0-7d73-a239-b0bacbda732f` | Findings/reporting updates targeted canonical repo files; explicitly verified the installed path resolved there. |
| Fix dRPC workflow failure | `01a0786e-e284-7c23-aa0a-4febcc931caf` | Provider locator, invocation gates, tests and guidance changed canonical repo files. |
| Review EVM diligence skill | `01a0787d-f80f-79e2-9ba4-4154fef16349` | Comprehensive review and Pump.fun/Pons/Long additions changed canonical repo files; symlink resolution was checked. |
| Crypto EVM token due diligence skill | `01a07eac-bb6b-76d2-bb4f-c9c774191610` | Created the intentional `.claude` copy and then backported locator/tests/description improvements to canonical EVM. |
| Skill research isolation | `01a07eac-bb6d-7822-8765-817090b363d4` | Fresh-investigation instructions and workflow version changed canonical EVM and the Claude copy. |
| Review AI token diligence | `01a07e63-cccb-71c0-af3e-ffd9bec3117b` | Emoji update commands set the canonical root to `skills/crypto-evm-token-due-diligence` and mirrored into `.claude`. |
| dRPC endpoint research | `01a07eac-bb71-7ce3-96a1-a259183d1947` | Concurrent Claude emoji work was reconciled with the canonical update; final helper/test parity verified. |
| Investigate AI token diligence | `01a07e5b-b53d-7d00-8421-c24bd6f7132b` | Research invocation; no EVM skill maintenance identified. |
| Review HOOKR token diligence | `01a079ef-7327-7703-aa6f-767e7faa9d32` | Research invocation; explicitly returned the canonical repo skill path. |
| Assess HOOKR token risks | `01a079ee-5ef3-7b60-9a9b-5bd345809424` | Archived interrupted invocation; no EVM maintenance identified. |
| Assess BOW token diligence | `01a07867-b1b4-72b2-8118-3842a0f29bb0` | Diagnosed failure to follow existing dRPC instructions and handed repair to the task above; not a separate Personal-code defect. |
| Research FRIES token | `01a0781b-8a27-7932-a7ea-b63da0a78ab0` | Related research invocation; no EVM maintenance identified. |
| Screen FRIES token risks | `01a077ee-b4f4-7851-87a3-24fd2b8ce954` | Related research invocation; no EVM maintenance identified. |
| Screen FRIES token risks | `01a077e0-128b-79a2-a850-f41c99530636` | Related research invocation; no EVM maintenance identified. |
| Check Buttensor rug risk | `01a077b1-5046-7461-b51e-73b5795bc951` | Related research invocation; no EVM maintenance identified. |
| Changing directory mid-session | `01a07eac-bb66-7283-9b1f-567beebafdfc` | Adjacent setup discussion; no EVM maintenance identified. |
| Create generic deep-plan skill | `01a074cd-16a8-7293-8435-3ec260310325` | Adjacent workflow-skill development; its Personal edits concerned different skills. |

The audit is bounded to accessible saved task records and repository evidence; it does
not attribute actions from an external editor that those records do not capture.

## Duplicate and preservation review

- The migration record explicitly retained Personal compatibility symlinks. Moving the
  source into the repo therefore did not make registration project-only.
- Git records a separate 43-file `.agents` copy being added in commit `9c21597`.
  The reviewed task records do not establish who created that extra copy.
- Before cleanup, 37 of its 42 shared files matched canonical bytes, including all
  helpers and tests. Differences were `SKILL.md`, three release files with deeper
  review-record paths, and the source-routing reference; the extra file was Claude
  port documentation. Workflow/backend/reporting versions matched: 1.4.3/2.1.0/1.1.2.
- The `.agents` SKILL.md was a partly renamed Claude wrapper, retaining Claude-only
  placeholders/tools and a nonexistent `Codex-PORT.md` link. From `/private/tmp`, its
  provider locator returned no context files, whereas canonical and Personal-symlink
  invocations returned this repo's AGENTS/README/HANDOFF. Running from the repo itself
  could mask this problem through working-directory discovery.
- Replacing that wrapper with a symlink fixes discovery by using canonical code and
  paths. No canonical research behavior or engine version was changed.
- The former project copy and a digest/registration manifest are preserved at
  `/private/tmp/crypto-evm-registration-backup-8hz7lle6` for reversible recovery.
  Git also retains the original tracked files; nothing was committed or pushed.

## Verification and changed paths

- All four README suites pass: research 31, EVM 172, rug-check 18, Solana 23: **244 tests**.
- Claude EVM suite passes **172 tests**, for **416 total** across five suite runs.
- Through the project symlink from an unrelated working directory, provider discovery
  resolves all three repo policy files and the sourced offline availability check is ready.
- All 42 canonical file digests match the pre-cleanup manifest; all seven helper scripts
  and all eight test files still match the Claude copy. Credentials and `history/` were
  not edited. Source/pin/evidence requirements and current versions remain unchanged.

Changed tracked areas: `.agents/skills/crypto-evm-token-due-diligence` (43 copied files
replaced by one symlink), `AGENTS.md`, `README.md`, `HANDOFF.md`, Claude `CLAUDE-CODE-PORT.md`,
and this audit record. Outside Git, only the EVM Personal symlink was removed; the backup
and temporary consolidation helper were created under `/private/tmp`.

Suggested commit message: `Consolidate EVM skill registration in the project and preserve dRPC setup`
