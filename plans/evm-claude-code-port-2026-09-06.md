# EVM diligence Claude Code port and locator backport

Requested workflow: implement-review-improve. Target: a Claude Code project-skill copy of
the canonical EVM diligence skill, then a backport of its tool-agnostic improvements.

## Phase 1 — Create the Claude Code copy

Copied every canonical file (minus `__pycache__`) to `.claude/skills/crypto-evm-token-due-diligence`
and adapted only tool wording and paths: `${CLAUDE_SKILL_DIR}` for `SKILL_DIR`, one Bash
call per env `source` plus helper, `WebFetch`/`WebSearch` instead of hidden in-app tabs,
`Agent` lanes with the main session as coordinator, a fail-safe injected
`provider_context.py` listing, sibling links via `../../../skills/`, and deeper
`review_record` paths. `CLAUDE-CODE-PORT.md` in the copy lists every difference.

Review findings (independent reviewer, nine items) were applied: consistent lane tool
list, coordinator-run separate collectors per the lane rules, no unexpanded placeholders
in Bash, a `skills`-parent guard in the locator, and complete port notes.

## Phase 2 — Backport to the canonical skill (workflow 1.4.1)

- `scripts/provider_context.py`: accepts `<checkout>/.claude/skills/<skill>` in addition to
  `<checkout>/skills/<skill>`; still ignores unrelated ancestor `AGENTS.md` files.
- `tests/test_provider_context.py`: adds tests for the `.claude/skills` layout and for the
  unrelated-ancestor case.
- `SKILL.md` description names exact EVM (chain ID, token address) targets including
  Robinhood Chain and excludes Solana mints.
- `assets/workflow-release.json` records 1.4.1 in both copies. Backend 2.1.0, reporting
  1.1.1, schemas, procedures, checks, provider policy and evidence rules are unchanged.

Not backported: Claude Code tool names, the injection line, and the deeper relative paths.

## Verification

Canonical suite and copy suite pass offline. The locator returns the checkout's
`AGENTS.md`, `README.md` and `HANDOFF.md` from `/tmp` and from the checkout for both
layouts. `diff -rq -x __pycache__` between the copies shows only SKILL.md, one reference,
three release assets and the port notes. No live diligence, RPC request or benchmark ran.
