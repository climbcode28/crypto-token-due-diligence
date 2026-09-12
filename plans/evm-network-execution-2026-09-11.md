# EVM first-call network execution

## Observed cause and scope

In this task's Flybrain run, the host declared restricted network access. Two identical
`broad_collect.py start` invocations using default shell permissions returned
`dns_resolution` before chain verification. The same command, private-env sourcing,
provider and run directory succeeded after `exec_command` requested
`sandbox_permissions: "require_escalated"`. The pipeline then completed in 14.116 seconds.
The project lane also reported default-shell DNS failures before an escalated capture
succeeded. This strongly supports execution context as the avoidable cause; it is not a
controlled proof that every DNS failure is caused by sandboxing.

Frozen run: `research/flybrain-20260911T-diligence`. Its evidence and report are unchanged.
Official context: https://learn.chatgpt.com/docs/agent-approvals-security describes network
restrictions and per-command approval separately from a program's own flags.

## Implementation and review

Workflow 3.2.4 adds first-call host-network selection to SKILL.md and the runbook, and
places the same rule inside both self-contained lane templates. The collector's
`--allow-network`/paid-use gates remain distinct from host execution permission.
The generic transport retry is preceded by correcting an omitted execution permission.
No helper logic, backend/reporting version, request limits, paid authorization, global
configuration, registrations or historical evidence changed. Canonical edits mirrored
into the Claude copy with its existing host-specific wording preserved.

Reviewed cases:

- Restricted network plus available escalation: request permission on the first live
  command; no intentionally failing network preflight.
- Necessary network already allowed: normal execution; no needless escalation.
- Offline policy/availability/compose: normal execution; no network request.
- Default permission accidentally used: corrected permission on the one bounded retry,
  same command/session/budget; no second knowingly restricted attempt.
- Escalation denied or unavailable: honor the boundary; no alternate-tool bypass.
- DNS failure despite permitted network: ordinary bounded retry; no claim that DNS proves
  sandbox denial and no automatic endpoint substitution.
- New lane or later preset: apply that call's permissions; do not assume a previous
  escalation changed future defaults.

Review improvement: explicitly covered later presets and independent lane captures, not
only `start`, because execution permissions do not persist across calls. Preserved the
existing behavioral regression suites; no wording-matching tests were added for this
instruction-only change. No fresh paid research was needed to test documentation.

## Validation

- Canonical EVM suite: 425 tests passed in 19.078 seconds.
- Mirrored Claude EVM suite: 425 tests passed in 19.851 seconds.
- `git diff --check` passed; mirror differences match the documented allowlist.
- Bundled `quick_validate.py` could not start: PyYAML is absent in both available
  Python runtimes. No dependency installed for this documentation edit. Both skill
  frontmatter blocks were separately verified unchanged against Git HEAD; edited release
  JSON parsed successfully. This does not claim the bundled validator passed.
- These offline checks preserve existing regression coverage; they do not measure future
  model compliance or first-attempt network success rates.

## Files changed by this update

- `skills/crypto-evm-token-due-diligence/SKILL.md`
- `skills/crypto-evm-token-due-diligence/references/runbook.md`
- `skills/crypto-evm-token-due-diligence/assets/lane-brief-liquidity.md`
- `skills/crypto-evm-token-due-diligence/assets/lane-brief-project.md`
- `skills/crypto-evm-token-due-diligence/assets/workflow-release.json`
- The corresponding five files under `.claude/skills/crypto-evm-token-due-diligence/`
- `.claude/skills/crypto-evm-token-due-diligence/CLAUDE-CODE-PORT.md`
- `README.md`
- This record.

Pre-existing citation/reporting edits were retained. No commit or push performed.
Suggested commit: `fix(evm): request required network permission on first research call`
