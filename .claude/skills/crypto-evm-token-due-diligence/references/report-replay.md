# Frozen report replay

New assembler freezes contain `reporting-engine/`: the renderer, legacy renderer,
validator, strict profile, wire validator, source decoder and `snapshot.json`. The
snapshot binds reporting version/profile, every required source file and the exact
manifest, report JSON and Markdown bytes. Evidence stays bound through the manifest
and derived-input closure. Keep the whole bundle, including source artifacts.

`bundle_assemble.py freeze` creates this snapshot after validation/rendering. Manual
assembly must validate, render, check rendered output, then run `report_replay.py
freeze BUNDLE` once. Existing snapshots cannot be silently overwritten.

```sh
python3 "$SKILL_DIR/scripts/report_replay.py" verify /path/to/bundle
python3 "$SKILL_DIR/scripts/report_replay.py" replay /path/to/bundle --trust-frozen-engine
```

Verification hashes files and registered evidence without executing bundled Python.
It checks integrity, not the frozen engine's semantic validation contract. Replay
executes code, so use its opt-in only for a locally reviewed/trusted engine. A
self-consistent hash list does not authenticate code received from elsewhere. Replay
copies only verified source bytes to a clean temporary directory, excludes unlisted
modules/bytecode and the caller's Python path, runs the frozen validator/renderer with
its saved profile, and compares the result byte-for-byte without changing the bundle.
This is isolation from accidental import pollution, not a sandbox for hostile Python.
Synthetic bundles require explicit `--allow-synthetic`.

Older reports without a snapshot can be rendered using the installed preserved
`legacy-v1` profile (renderer 1.1.2); select `--profile legacy-v1` explicitly and write
to a new `--output` path. Do not modify historical bundles to retrofit snapshots.
Future reporting changes preserve current snapshots and add compatible profile
handling deliberately. Reproduction demonstrates the original computation, not
current token state, truthful RPC responses or financial correctness.


Reporting 2.1.0 separates pure coverage gaps from assessed findings and adds adoption/
economics topics. Earlier strict sources may still use Potential Risk for those gaps;
the current reading layer displays them neutrally. Use the report's original frozen
engine to reproduce historical bytes. Do not rewrite an earlier report, its labels or
its evidence merely to adopt the new presentation. Legacy-v1 rendering is unchanged.

Reporting 2.2.0 adds the versioned stopping review to newly assembled reports. New
manual reports must also include `closure_review_version: 1` and reviewed incomplete
coverage rows; follow [stopping-and-escalation.md](stopping-and-escalation.md). Older
strict sources without the extension remain readable, without a retrospective review
claim. Preserve their original sources and snapshots instead of retrofitting this field.
