# Operational feedback and maintenance

Keep installed code immutable during research. Standard collection stages may write
at most eight typed operational observations to their existing run: category,
method/source class, attempted recovery, outcome, evidence SHA-256, component version,
capture time and expiry (at most seven days). They contain no source prose, token
identity, balances, credentials or provider approval. Capture/storage failure never
blocks collection, damages the evidence manifest or changes a judgment.

`solana_operations.py` accepts a closed schema with fixed enums. Corrupt, injected,
future, expired or wrong-version records are rejected. Stage summaries are observations,
not demonstrations of successful recovery; they cannot be promoted automatically.

Maintenance uses these offline commands outside an active token investigation:

```sh
python3 "$S/scripts/solana_maintain.py" ingest "$RUN" --out /path/to/new-ingestion.json
python3 "$S/scripts/solana_maintain.py" promote "$RUN" --record-id "$RECORD_ID" --review /path/to/review.json --out /path/to/new-lessons.json
python3 "$S/scripts/solana_maintain.py" active /path/to/new-lessons.json
```

Ingestion deduplicates exact record IDs and reports rejected records. It does not edit
persistent guidance. Promotion requires an independently hash-bound failure followed
by a successful valid response, exact method/source applicability, a supported bounded
retry or distinct public alternate, current version and expiry, and explicit review:

```json
{"reviewer":"maintainer","reviewed_at":1789142400,"decision":"approve"}
```

The example timestamp is illustrative; use the actual review time. Reviews must be
within the last day. Proof artifacts are confined regular files, with independently
checked status, request and ordering. Lesson text comes only from the maintained
rule table, never fetched prose. Review evidence sufficiency before replacing the
canonical lesson data in a separate authorized maintenance change. No active lesson
is the default. A record or lesson never changes permissions or runtime behavior.

Apply implement → review → improve → verify to a demonstrated defect. Preserve
regression fixtures and exact historical evidence. Review the pinned upstream
revision, layout size/discriminator, integer math, token/program/controller scope,
license and required capabilities before adding an adapter. Registry/layout/runtime
source provenance lives in the corresponding `assets/*-sources.json`,
`protocol-registry.json` and `runtime-provenance.json`; update actual component
versions for behavioral changes. Do not run frozen third-party code or historic
installers as an upgrade procedure.

Run the standard-library suites from repository root:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s skills/crypto-token-due-diligence/tests -q
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s skills/crypto-solana-token-due-diligence/tests -q
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s skills/crypto-evm-token-due-diligence/tests -q
```

New operational/guidance tests are included by discovery. The v2 workflow is the
default; live timing is a separate measured gate recorded in the plans, and synthetic
tests are not a live research-speed claim. Keep old bundles readable through
explicit `legacy-v1`; roll back a defective default without rewriting evidence.
No installs, commits, pushes or registration changes are required by this workflow.
