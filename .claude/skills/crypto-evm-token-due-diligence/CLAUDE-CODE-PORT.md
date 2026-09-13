# Claude Code port notes

This directory is the Claude Code project-skill copy of the canonical
`skills/crypto-evm-token-due-diligence` at the project root. Claude Code loads it from
`.claude/skills/`; Codex uses the canonical folder through the project-local
`.agents/skills/crypto-evm-token-due-diligence` symlink. The maintainer keeps EVM project-only; recipients can opt into Personal installation with `install.sh`.
Both carry EVM workflow 3.4.1, backend engine 3.7.0 and reporting engine 2.6.2
(pipeline 1.0.2, note schema 1, investigation schema 3, source comparison 1.1.0). Both copies
use the same checks, procedures, thresholds, rules, schemas, strict profile, reviewed
memories and regression fixtures. Live operations share one session across targets.

## What differs from the canonical copy

- `SKILL.md`: sibling skill links point to `../../../skills/<sibling>/SKILL.md`; the
  skill uses the host's normal tool permissions, with no shipped `allowed-tools`
  auto-approval list; a
  "Claude Code execution conventions" section maps `SKILL_DIR` to `${CLAUDE_SKILL_DIR}`,
  requires the env `source` and helper command in one Bash call, runs the pipeline with
  `run_in_background` plus `Monitor`, and names the lanes as `Agent` subagents
  `evm-liquidity-lane` / `evm-project-lane`. The provider policy excerpt is injected at load with
  `` !`python3 "${CLAUDE_SKILL_DIR}/scripts/provider_context.py" --policy 2>&1 || echo ...` ``
  (fail-safe: a failing injected command would otherwise abort the skill load). Step 1 and
  step 3 of the pipeline section use that wording. Everything else is verbatim.
- `references/source-routing-and-execution.md`: the background-read sentence names
  `WebFetch`/`WebSearch`, and the lane paragraph says "two independent `Agent` lanes when
  that tool is available". All source, lane and stop rules are unchanged.
- `assets/*-release.json`: `review_record` paths gained one extra `../` for the deeper
  directory. Versions and change lists are unchanged.
- Canonical-only: `agents/openai.yaml` (Codex UI metadata). Claude-only, at the project
  level rather than inside this folder: `.claude/agents/evm-liquidity-lane.md`,
  `.claude/agents/evm-project-lane.md` (lane subagent definitions with tool lists).
  No shared `.claude/settings.json` is shipped; recipients retain control of their
  own command approvals and sandbox settings.
- `scripts/`, `tests/`, `assets/*.template.json`, `assets/lane-brief-*.md`,
  `assets/chain-registry.json`, `memories.md` and every other reference are byte-identical.

## Keeping the copies in sync

Edit the canonical folder first (see `AGENTS.md`), run its suite, copy `scripts/`, `tests/`,
`references/`, `assets/` and `memories.md` here, re-apply the differences above, then run
this copy's suite:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s .claude/skills/crypto-evm-token-due-diligence/tests -q
```

`diff -rq -x __pycache__ skills/crypto-evm-token-due-diligence .claude/skills/crypto-evm-token-due-diligence`
should show only `SKILL.md`, `references/source-routing-and-execution.md`, the three release
JSONs, `CLAUDE-CODE-PORT.md` (here only) and `agents/` (canonical only). Credentials never
belong in either copy.
