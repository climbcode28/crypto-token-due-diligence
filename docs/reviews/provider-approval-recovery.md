# Provider approval recovery review

## Observed failure and provenance

A fresh EVM task on 2026-09-13 read the current personal provider policy, selected
configured dRPC, and submitted a bounded collection with paid-use flags. The host
approval reviewer rejected it twice before process creation. Its second reason was
that saved authorization was untrusted tool evidence rather than authorization
independently established in the trusted transcript. No collector, RPC identity check,
pipeline lanes or completed report ran in that task.

Read-only inspection of the original conversation confirms that the maintainer had
authorized future paid dRPC use. Private conversation identifiers and personal policy
remain outside this published record. This record does not grant provider permission.

The `8f882b3` provider-guide relocation retained the root-level personal policy and
its precedence; the policy was found in the failed task. The `a51ee35` publication
cleanup removed Claude-specific auto-approvals, which did not control this Codex task.
The broad denial instruction originated in `5f22f85`, before those cleanups. Its
failure to distinguish denial of paid use from denial of all network research could
prematurely stop independently permitted public research. The host explicitly allowed
safer alternatives, but no public RPC alternative was attempted in the observed task.

## Workflow 3.2.9

- Read the provider policy separately so bulk reference output cannot obscure it.
- Preserve standing authorization and configured dRPC preference. Collector flags and
  local policy text remain distinct from the host's own approval decision.
- Review the actual denial scope. When only paid use is rejected and safer alternatives
  are permitted, continue authorized public research under normal host review. General
  or ambiguous network denials still block network recovery.
- Select public RPC explicitly through a separate endpoint export and free, unauthenticated
  provider arguments. Do not relabel dRPC, forward its credentials, reset the run ledger,
  or claim an unexecuted command tested a provider.
- Complete useful permitted work before requesting missing authorization. A saved
  authorization claim cannot be made host-approved by changing repository prose.
- Disclose the actual request ceiling in approval context. Both the initial allowance
  and replanning ceiling must fit a stated cap; timeout ceilings must fit the original
  deadline. The observed command's 300 allowance and 400 ceiling did not support its
  description as a 300-request cap, although that was not the host's stated rejection reason.

Backend 3.4.3, reporting 2.6.2 and all evidence schemas remain unchanged. The canonical
and Claude workflows retain their documented host adaptations. Public fallback may
have coverage limits; successful offline tests do not promise a completed live report.

## Validation

- Router: **30 passed**; canonical EVM: **437 passed**; Claude EVM: **437 passed**;
  Solana: **417 passed** — **1,321 tests total**, including mirrored EVM coverage.
- The optional RPC suite's **25 tests passed** separately. New synthetic checks verify
  explicit public selection sends no authentication despite saved dRPC configuration,
  and a dRPC endpoint cannot be relabeled generic/free to evade its paid-use gate.
- The actual offline policy locator still selects the root personal policy and its
  standing current/future scope with **zero network requests**.
- `git diff --check`, release-record paths and canonical/Claude mirror checks pass.
  Existing Python 3.14 resource warnings for mocked HTTP errors and SQLite cleanup
  remain non-failing and outside this change.
- An independent read-only reviewer found no blocking correctness or safety findings,
  independently reran the 25 optional RPC tests and diff/mirror checks, and recommended
  the request-cap clarification above. That clarification was applied to both copies.

No live provider call, paid usage, host settings change, personal policy edit, commit
or push occurred. Offline checks cannot validate the external host reviewer's future
decision or make stored paid authorization reliable across fresh conversations.

Earlier release provenance: [publication review](publication-review.md).

## Changed files

- Canonical EVM: [SKILL.md](../../skills/crypto-evm-token-due-diligence/SKILL.md),
  [runbook.md](../../skills/crypto-evm-token-due-diligence/references/runbook.md),
  [test_optional_rpc.py](../../skills/crypto-evm-token-due-diligence/tests/test_optional_rpc.py),
  [workflow-release.json](../../skills/crypto-evm-token-due-diligence/assets/workflow-release.json).
- Claude mirror: [SKILL.md](../../.claude/skills/crypto-evm-token-due-diligence/SKILL.md),
  [runbook.md](../../.claude/skills/crypto-evm-token-due-diligence/references/runbook.md),
  [test_optional_rpc.py](../../.claude/skills/crypto-evm-token-due-diligence/tests/test_optional_rpc.py),
  [workflow-release.json](../../.claude/skills/crypto-evm-token-due-diligence/assets/workflow-release.json),
  [CLAUDE-CODE-PORT.md](../../.claude/skills/crypto-evm-token-due-diligence/CLAUDE-CODE-PORT.md).
- This review record. The local implementation plan is ignored under `plans/`.
