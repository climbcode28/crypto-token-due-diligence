# EVM workflow 1.4.2: fresh investigation on every invocation

Date: 2026-09-07. User instruction: the skill must not reference previous research runs;
it must always perform a fresh round of research.

## Observed problem

Invoking `/crypto-evm-token-due-diligence` for a token that already had a partial run under
`research/` led the coordinator to inspect and plan around that earlier workspace (stale pin,
unfinished bundle, lane notes) instead of starting a new collection.

## Change

`SKILL.md` in the canonical skill and the Claude Code copy: the packet section is now
"Start fresh; reuse the packet only within this investigation". Each invocation creates a
new dated workspace with its own output directory and cache file, captures new pins and
runs new collection and web reads. Earlier run directories, bundles and lane notes are never
opened, cited or built on. Packet reuse applies only inside the current investigation.

Provider-selection context in `HANDOFF.md` (verified chain/endpoint from an earlier run) is
unchanged: it selects a candidate provider and never substitutes for fresh identity and pins.

## Versions and validation

Workflow 1.4.1 -> 1.4.2 in both `assets/workflow-release.json` copies. Backend 2.1.0 and
reporting 1.1.1 unchanged. Validation: both offline EVM unittest suites and the
`diff -rq` sync check from `CLAUDE-CODE-PORT.md`. No live diligence was run.
