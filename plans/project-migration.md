# Consolidate crypto research into a project

## Requested phase

Move the existing crypto research work to `~/code/crypto-research`,
preserve skill use and evidence reproducibility, then add and pin the folder as a Codex
project. Use an implement, review, improve cycle. No Git commits or pushes, live RPC
requests, purchases, or paid usage.

## Acceptance and execution

- Move both current skill directories to `skills/` without changing their contents.
- Preserve prior implementation work, baselines, plans and synthetic evidence in `history/`
  and `plans/`. Leave user-provided inputs and third-party temporary dependencies alone.
- Leave compatibility symlinks at old locations for skill discovery and historical paths.
- Record all relocated file digests and verify them after the move.
- Run both regression suites, skill format checks, local link checks, the no-key offline
  availability check, and a frozen synthetic detector replay from the project location.
- Review actual relocation mappings, frozen-file integrity, documentation and test results.
- Add and pin the saved project in Codex; verify using project and sidebar tools.

## App capability discovered

The app connector can list and pin saved projects but has no add-project operation.
Computer Use refuses access to Codex (`com.openai.codex`) for safety reasons. If the
folder is not already registered after migration, the user must add it in the app;
the connector can then pin it. Do not modify internal app state to bypass that boundary.

## Result — files and sidebar complete

Moved 10 source entries into this project and left compatibility symlinks at their
original locations. [relocation-manifest.json](relocation-manifest.json) records original
paths, project-relative destinations, and SHA-256, byte length and permissions for all
384 preserved files. Verified every recorded file and all 10 links after migration.
Both current skill directories remain byte-for-byte unchanged; engine 1.1.0 is retained.

Verification from the new project directory:

- Research: 21 regression tests passed.
- Diligence/backend: 106 regression tests passed.
- Both skill-creator format validations passed using the existing temporary PyYAML
  dependency; no dependency installation was required.
- All 52 current local Markdown links resolve.
- The explicit missing-key availability check returned `fallback`, `drpc_key_missing`,
  `continue_standard_flow`, and zero network requests.
- Replayed frozen engine 1.0.0 synthetic evidence using the unchanged current engine
  1.1.0 from the new path. [Findings](../history/project-migration-replay/findings.json)
  are exactly identical to the prior saved engine 1.1.0 replay, including provenance.

Direct review checked all relocation mappings, file digests and permissions, sibling
skill references, Python imports through the new paths, archived evidence preservation,
and the project documentation. No remaining actionable file-migration finding. Original
Downloads/attachments and temporary third-party validator dependencies were not moved.
No secrets were copied, live RPC called, paid usage incurred, Git repository initialized,
or commits/pushes made.

The user added the folder in Codex. The connector then pinned project
`2bdc8918-1dab-4ca9-8fee-6b3aa0c4cae8`; `list_threads` verified its project item in the
Pinned section. The project relocation and sidebar acceptance criteria are complete.

The user subsequently explicitly requested Git initialization and an initial commit of
all existing work, superseding the earlier no-commit instruction for that one commit.
Git was initialized on `main`. [HANDOFF.md](../HANDOFF.md) captures project state,
verification, local dRPC setup and the remaining live-test approval boundary. No push
or paid usage was authorized by this request.

Suggested commit message: `Organize crypto research skills and evidence history into a project`
