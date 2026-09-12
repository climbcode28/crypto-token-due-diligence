# Reviewed operational improvement

Research records observations; authorized maintenance changes guidance or code. Keep
installed skill code and `memories.md` immutable during research. A useful report does
not depend on recording feedback successfully. Never reuse an earlier token run as
current evidence or treat operational memory as spending/provider authorization.

## During a fresh investigation

Use one investigation directory containing its session, collections, source captures,
drafts and `operational-feedback.json`. Collector, bootstrap and source lookup route
automatic failures to the shared session directory. Pass `--feedback-root "$RUN"`
before the assembly subcommand. External browser/connector work uses the same root.
There is one cap of eight observations and 32 KB per investigation; full, corrupt,
unsupported or locked feedback is a non-blocking gap. POSIX locking is optional;
unsupported hosts skip capture without stopping collection.

Automatic entries use fixed sanitized language. For a useful browser-only problem or
successful recovery, explicitly capture a structured observation:

```sh
python3 "$SKILL_DIR/scripts/operations.py" capture "$RUN" "$RUN/observation.json"
```

Observation schema 1 has exact fields `id`, `component`, `operation`, `category`,
`access_mode`, `tool_version`, `observed_at_utc`, `symptom`, `outcome`, `recovery`,
`artifact`, `collection_sha256`, `impact`. Artifact is `{path,sha256}` below the run root.
Collection digest may be null: initial chain/pin failures, invalid collections and
browser captures need no invented usable collection. A non-null digest binds
`collection.json` or explicit `collection_path`. Recovery is `{action,status}` with
status `not_attempted`, `proposed`, `failed` or `succeeded`; `recovered` requires
`succeeded`. Impact is `{extra_requests: integer_or_null, lost_coverage: boolean}`.
Keep unknown extra requests null. Artifact hashing streams at most 32 MB per file.

Use concise procedural descriptions, never pasted source instructions, secrets,
endpoints, private paths, approvals, addresses, balances, owners, fee schedules, lock
dates, verdicts or wallet allegations. Field/byte limits and text screening are defense
in depth, not a semantic secret detector. Raw observations stay in evidence artifacts;
memory contains reviewed procedures only. Preserve operation/tool/access mode/status/
timing in acquisition provenance. An accessible browser view, blocked API and missing
export can coexist; label snapshots and transcriptions honestly.

## Review recurrence separately from state caches

Maintenance can ingest hash-validated observations into a separate operations database:

```sh
python3 "$SKILL_DIR/scripts/operations.py" ingest "$RUN" --store /path/to/operations.sqlite
python3 "$SKILL_DIR/scripts/operations.py" recent --store /path/to/operations.sqlite --limit 20
```

This database cannot also be a token RPC cache or investigation session. Reimporting
the same observation is idempotent. Issue context includes component, operation,
category, access mode, tool version and sanitized symptom; distinct occurrences and
distinct runs are retained. Conflicting copies of the same observation are rejected
atomically. Retrieval defaults to 20, with a hard cap of 100; it is a maintenance view,
not an automatic source of token facts. The legacy `maintain.py` recorder remains
available for usable collections with bounded, deduplicated notes.

## Read and promote reviewed guidance

Normal research reads only relevant active guidance:

```sh
python3 "$SKILL_DIR/scripts/operations.py" read "$SKILL_DIR/memories.md" \
  --component browser --operation capture --version v3.0.0
```

The file contains one schema 1 JSON block, at most 20 entries and 32 KB. Retrieval selects
at most five exact component/operation/version matches, excluding expired (UTC),
superseded and retired entries. Missing/corrupt/irrelevant memory returns an empty set.
Text outside the JSON block is explanatory, not dynamically imported instructions.

Candidate → verified recovery → reviewed active guidance → superseded/retired. A
proposed recovery has never succeeded and cannot be promoted as a solution. During
explicitly authorized maintenance, reproduce the failure and successful recovery,
write a bounded general lesson, add a regression and a nearby non-error case, review
the actual diff and source, then promote:

```sh
python3 "$SKILL_DIR/scripts/operations.py" promote --memories "$SKILL_DIR/memories.md" \
  --entry /path/to/reviewed-entry.json --observation-root "$RUN" \
  --observation-id OBSERVATION_ID --review-artifact /path/to/review.md
```

Promotion requires matching component/operation/version, successful recorded recovery,
review date, expiry, verification description and explicit active status. It records
the observation ID/digest and review artifact digest in `review_provenance` before an
atomic write. Hashes bind review artifacts; they cannot prove a reviewer was correct.
The command cannot authorize itself, execute memory commands or rewrite production
logic. Edits/retirement of an existing entry require the same maintenance review.
Retire lessons once a tested helper/reference implements them; the initial five audit
lessons are retired for this reason. Do not keep redundant active instructions.

## Version and verify changes

Use implement-review-improve. Add failing regressions for demonstrated weaknesses;
review callers, negative cases, uncertainty, credentials, budgets and compatibility.
Run all four README suites and the Claude EVM suite after mirroring its documented
port differences. Do not edit frozen history, original evidence or source snapshots.
Keep the research rubric, optional provider fallback and project-only registration.

Version behavior: backend 3.0.0 makes live sessions mandatory. Workflow/reporting 2.1.0
separated neutral gaps and adoption/economics context. Workflow/reporting 2.2.0 added reviewed stopping bases for incomplete surfaces.
Workflow/reporting 2.3.0 also require evidence-linked decision types, explicit
user requirements, four-axis synthesis and proportionate actions in new assembly.
Research gaps no longer generate a global favorable-conclusion veto. Public credibility
and neutral economic terms receive their own assessment without hiding adverse powers. Reporting retains strict profile `evm-evidence-v2`
and the supported shared-session route.
Bundle/collection/cache schema 1 remains compatible; cache keys have version 2 and
fresh investigation identity. Detector rules remain 1.0.1. Explicit legacy validation
and the 1.1.2 renderer preserve old reports. Freeze reporting dependencies for
[offline replay](report-replay.md), rather than relying on the next installed version.

Record measured request counts, cache hits, durations, bytes and coverage. The rolling
scheduler benchmark is synthetic, not evidence of live speed or research accuracy.
Do not automatically tune thresholds, change rubric weights, incur paid usage, commit
or push as part of feedback collection. JSON-RPC batching, Multicall, new HTTP clients,
WAL and vector memory remain deferred until measurements justify their complexity.

Workflow/reporting 2.4.0 separates completed research from interrupted checkpoints.
The final gate rejects budget-stopped or unattempted required work; externally bounded
unknowns keep their ratings. Broad timing uses a progress checkpoint and a longer
planned operational window, preserving finite request caps and authorization.

Backend 3.1.0 adds schema-2 operational replanning within immutable finite ceilings.
All eleven surfaces, expected overhead and remaining time participate in the reviewed
plan; same-session revisions retain usage and reservations. Workflow/reporting 2.5.0
requires a separate final-delivery check; an internal checkpoint does not end the task.
Completion review version 2 distinguishes storage from delivery. Old sessions and
reporting snapshots retain their original limits and replay semantics. Forward tests
must exercise exhausted analyst allowances, proactive shortfalls, actual user ceilings,
zero-request unfinished analysis, external evidence boundaries, and checkpoint delivery,
not just validators accepting/rejecting report declarations.

Workflow 3.2.0 and backend 3.4.0 (2026-09-10, same day) answered the next live run: 6.7 minutes
but five findings and three Unverified rows, because Cloudflare blocked the explorer (and the
public RPC) for generic client agents and the creation transaction was never found. The fix
was access (browser-like agent, verified) plus moving the factual half of the report into the
pipeline (`pipeline_note.py`) so depth no longer depends on coordinator turns; the report
standard in the runbook names the minimum an established token must read as.

Workflow 3.1.0 and backend 3.3.0 (2026-09-10) came out of the forensics of a 12.7-minute
live run: 86% of the wall clock was coordinator model time across 73 turns, so the changes
cut turns rather than compute (structured start diagnostics with in-place restart, brief
files with pointer prompts, lane self-validation, the coordinator-note scaffold, compose
repairs for the execution and coverage mistakes, reverted probes recorded as answers). The
per-run forensics table is in the plan's live-results file; a live 3.1.0 acceptance run is
the next measurement to record.

Workflow 3.0.0 and backend 3.2.0 (reporting engine unchanged at 2.6.0) target 5–7-minute
completed reviews: one-process standard collection (`broad_collect.py`), bundled Keccak
and presets, the compose layer that expands compact notes into the strict contract, the
bounded web capture helper, two brief-driven lanes with a 4-minute cutoff, and a phase
timeline in the session ledger so every run self-benchmarks. Model-authored assembly
scripts are no longer part of any run; recurring assembly needs go into the helpers.

Workflow/reporting 2.6.0 targeted 10–15-minute completed reviews through early critical
checks and incremental draft preflight, not a lower evidence threshold. Decision version 2
removes compulsory follow-ups and rejects final research homework. Comparison 1.1.0 closes
false metadata-layout gaps with legacy replay retained. Forward review must exercise a
missing export with available raw-event reconstruction, an actual inaccessible-history
boundary, a local matcher failure and an observed severe authority. Measure live latency
separately from synthetic/offline timing; never promise complete knowledge of unpublished facts.
