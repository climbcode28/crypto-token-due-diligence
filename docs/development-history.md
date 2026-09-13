# Development provenance

Current release manifests link to the implementation and acceptance records retained
under `docs/reviews/`. Those records describe their original releases, not current setup or
provider authorization. Use README and [provider setup](provider-setup.md) for current operation.

The publication cleanup removed the following completed setup and retired-workflow
records from the public working tree:

- `plans/crypto-research-skill.md`
- `plans/drpc-local-setup-and-live-test.md`
- `plans/drpc-workflow-reliability.md`
- `plans/project-migration.md`
- `plans/relocation-manifest.json`
- `plans/rug-check-reporting-1.2.0.md`

Their original bytes remain available in Git at commit `80849a9` and in the maintainer's
ignored `history/publication-cleanup-2026-09-12/` archive, with a SHA-256 manifest.
The earlier frozen research-rubric provenance remains on the local `archive/pre-publish`
branch. These records are historical evidence; do not rerun their installers.

The superseded `sharing/` export system and ignored `share-export/` snapshot were removed.
Install from the repository using `install.sh`; no separate sanitized export is needed.

A second pass on 2026-09-12 removed the remaining development records under `plans/` that no
release manifest, document or test referenced, together with the diagram prompt note and the
standalone diagram viewer. The eight records that release manifests cite remain. The removed files
are unchanged in Git history at commit `190f40f`.

The eight retained records were subsequently moved from `plans/` to `docs/reviews/`,
with maintained links updated. Historical paths and captured baseline metadata within
the records describe their original execution context. `/plans/` is now ignored for
future local development drafts.
