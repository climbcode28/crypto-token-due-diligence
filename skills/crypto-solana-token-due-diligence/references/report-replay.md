# Frozen reading, verification and trusted replay

Set `S` to the canonical Solana skill directory and `FINAL` to an existing frozen
bundle. These commands are offline. Synthetic fixtures require `--allow-synthetic`;
never use that switch to present fixture facts as real token research.

```sh
python3 "$S/scripts/solana_bundle.py" read "$FINAL" --profile solana-evidence-v2
python3 "$S/scripts/solana_bundle.py" verify "$FINAL" --profile solana-evidence-v2
python3 "$S/scripts/solana_bundle.py" replay "$FINAL" --profile solana-evidence-v2 --trust-frozen-code
```

`read` checks the inventory/hashes, then returns `report_path`, the compact reading
checklist and ready-to-use citations without recomputing against the installed
engine; the frozen Markdown stays in the report. This permits formatting after an installed version change. It distinguishes
an incomplete checkpoint from a deliverable completed report.

`verify` parses bounded JSON and checks confined regular files, exact inventory,
source hashes, identities, statuses and required engine assets. It never executes
frozen code. Missing files, modified evidence/code, unlisted files, bytecode or
symlink/path escapes fail. Hashes detect changes relative to the supplied inventory;
they do not authenticate its author. Review provenance before trusting a bundle.

`replay` requires explicit `--trust-frozen-code`. It first verifies, copies only the
verified code/data to a clean temporary tree, then runs the copied validator and
renderer with isolated Python (`-I -B -S`), a minimal environment and no inherited
Python paths, current-directory imports, site packages or bytecode. It compares
both Markdown and reading-checklist bytes and leaves the source bundle unchanged.
Only the frozen scripts directory is added to Python's standard-library path.
This is reproducible import isolation, **not a hostile-code sandbox**. Trusted
Python retains host capabilities; do not trust arbitrary bundles merely because
self-supplied hashes match. Finalize may replay the installed code it just captured;
external bundle replay always requires the explicit flag.

For old schema-1 bundles, retain their original bytes and select the compatibility
reader explicitly:

```sh
python3 "$S/scripts/solana_bundle.py" validate "$OLD" --profile legacy-v1 --rendered "$OLD/report.md"
```

Do not migrate a frozen bundle in place. The legacy golden corpus records original
bytes and its original engine snapshot as provenance, not executable installation
instructions. A release rollback selects legacy reading/defaults; it never rewrites
evidence. V2 frozen replay uses its own captured dependency versions.
