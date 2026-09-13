# First-run reliability acceptance

This change starts from `9c40579` and implements built-in public EVM selection,
consistent paid-consent guidance, and repeatable clean-install acceptance checks.
Backend **3.5.0**, workflow **3.3.0**, reporting **2.6.2**; evidence schemas and frozen
replay contracts are unchanged. Solana workflow **2.0.1**, provider workflow **1.2.0**,
broad runner **1.4.1**; existing profile/reporting/session contracts remain unchanged.

## Behavior

The backend selects public RPC for the exact target chain when no endpoint is
configured. Seven registered mainnets have defaults with [primary-source provenance](../../skills/crypto-evm-token-due-diligence/references/public-rpc.md).
Configured endpoints preserve their existing authorization and authentication gates.
Explicit public mode ignores saved endpoint/key exports, rejects custom authentication,
and uses free policy; unknown chains and missing custom exports do not select a different
network. Subsequent presets derive the network from saved target facts. Existing live
chain, runtime, pin and budget checks still apply.

The normal example needs no private env or paid-use question. The configured-provider
variant retains authorized dRPC preference and reuses valid consent within its bounds;
every command still supplies the appropriate flags and respects the host's approvals.

Solana receives the same current-user consent and provider-denial recovery rules.
Unused malformed dRPC configuration cannot block public selection or forward its key.
Selected paid URLs remain strictly validated, and an already-started run retains its
provider lock, consumed grants and original deadline. Executed blocked starts no longer
instruct the agent to create a fresh run: repeated start returns the retained result,
and useful permitted document capture uses the same session. A pre-process host denial
still allows an independently approved public start at the original unused run path.

## Repeatable offline acceptance

Run `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -q` at the repository
root. Tests export the publishable working tree into a temporary package and exercise
the real installer in isolated child-process homes. No maintainer credentials, ignored
personal policy, historical reports or real Personal registrations are used.

Checks cover link/copy installs and repeat installation, all five skill entrypoints for
Codex/Cursor and Claude, exact-address routing, zero-request public readiness, preservation
of unrelated files on uninstall, and EVM/Claude/Solana synthetic report delivery after
the original package directory is made unavailable. These are installation and synthetic
integration checks, not live host/model acceptance.

Specialist regression tests cover no-config defaults, configured paid gates, public
selection without credential forwarding, unsupported chains, missing exports, unavailable
RPC, and unchanged retry identity/deadline/request accounting. Host approval rejection is
an external event and is not reproduced by a mocked collector gate.

## Live host acceptance

Six fresh CLI sessions were attempted on 2026-09-13, one EVM and one Solana target per
host. Each used a copy installation from a publishable working-tree export, a separate
research directory and a receipt +600-second watchdog. No RPC credentials were passed
in the child environment. Existing authenticated host accounts were retained: these
were clean package installations, not newly created accounts or virgin host settings.
No real Personal skill registrations changed. Hosts ran concurrently, so shared public
rate limits may have affected coverage.

| Host | Client/model | Permission mode |
| --- | --- | --- |
| Codex | `0.154.0-alpha.6.2`; default model, model ID not emitted in transcript | `exec --ignore-user-config --ephemeral --approve-for-me`; ordinary Auto-review |
| Claude Code | `2.1.270`; `claude-opus-5` | `--permission-mode auto --permission-prompts none`; project/local settings; strict empty MCP config |
| Cursor | `2026.09.10-fd3934a`; Auto/default | `--sandbox enabled --auto-review`; temporary workspace trusted |

The EVM target was PONS `0x39dBED3a2bd333467115dE45665cC57F813C4571`, discovered and
verified on chain 4663. The Solana target was STONK
`6GmAFSYs4gk3FDao5FzzySQpPZaWsa4rUJHacpMpUNgx`, verified on mainnet. These cases test
execution and report integrity, not token safety or universal provider availability.

| Host / target | Elapsed | Observed outcome | Coverage / limitation |
| --- | ---: | --- | --- |
| Codex / EVM | 503 s | Public collection and validated final report | 1 checked, 10 partial surfaces; both agent launches failed `no thread with id` in the ephemeral CLI session, local lane fallback used |
| Claude / EVM | 300 s | Public collection and validated final report | 2 checked, 8 partial, 1 unavailable; generic lanes used because named agent definitions were absent |
| Cursor / EVM | 444 s | Public collection and validated final report | 2 checked, 7 partial, 2 not applicable; source-access and custody gaps retained |
| Codex / Solana | 481 s | Validated **partial checkpoint**, incomplete broad diligence | 6 partial, 5 not checked; agent-launch failure, late/incomplete fallback lanes and public-provider limits |
| Claude / Solana | 362 s | Validated **partial checkpoint**, incomplete broad diligence | 1 checked, 5 partial, 4 not checked, 1 unavailable; unfinished lane checks, refused holder census and HTTP 429 |
| Cursor / Solana | 153 s | **Blocked acceptance cell** after public collection | CLI exited 1 with account usage limit; no final report; no retry or purchase |

All six reached public collection without a paid-access prompt or paid dRPC attempt.
That is a provider-flow result, not six completed broad-research passes. EVM bundles
passed the installed validator including deterministic rendered-report comparison.
Solana checkpoints passed schema validation and inventory/hash verification; gaps
remain gaps. No frozen code was executed by the inventory verification.

The live copies preceded the final Solana entrypoint shortening and blocked-start
advice correction. Their public-selection code was the same, and none hit the executed
identity-block branch. The latter correction is covered by synthetic regression and
independent follow-up review, not by claiming these live runs exercised it.

To repeat, export the current package with `tests/install_support.py`, run `install.sh
--copy` in an isolated child-process home, then open a fresh authenticated CLI session
at the temporary workspace with the permission modes above. Use its copied router and
this prompt shape, substituting the exact target, paths and actual receipt/deadline:

> Use the installed crypto-token-due-diligence skill to research this exact address.
> Use only this package's installed skills, not other installations or past reports.
> Use public RPC only; do not load personal provider policy, private env files or RPC
> credentials. Ordinary host permissions and network approval review still apply;
> do not bypass a denial. Save the report and working research in this run directory.
> Follow standard broad diligence with the original receipt, absolute deadline and
> finite request ceilings. Report any host prerequisite and incomplete work truthfully.

Enforce a 600-second process watchdog, retain the raw transcript and exit status, and
validate any delivered artifact independently. Stop on authentication/usage prerequisites
instead of changing account settings. Private request/result/validation records and
raw transcripts from this attempt are retained under ignored
`research/first-run-acceptance-20260913/`; reports remain in its recorded temporary
workspaces. The explicit public-only prompt and offline no-config tests complement
each other; this matrix does not prove unconstrained model selection or desktop/IDE UI
parity. First-time account setup, interactive permission dialogs and complete Solana
broad delivery across all three hosts remain unverified.

## Verification and independent review

All **1,344 tests passed**: router 30, canonical EVM 444, Claude EVM 444, Solana 424
and clean-install 2. The Solana full suite was rerun after its review fix. The initial Solana guidance line-limit failure was fixed by
shortening the entrypoint, retaining the detailed rules in its runbook.

An independent read-only reviewer inspected the diff, provider callers, snapshot
compatibility and session enforcement, and ran the new EVM/Solana provider tests plus
installation tests. One P2 finding identified conflicting old advice to create a new
run after an executed blocked Solana start. The fix removes that advice from emitted
diagnostics, entrypoint, runbook and README; a regression checks retained attempts,
identity/deadlines, the provider lock and same-session document capture. Focused
follow-up review independently ran the three affected blocked-start tests, confirmed
the P2 fixed, and found no remaining actionable findings. The reviewer also checked
the acceptance record against retained result/validation evidence. Mirror comparison
showed only documented Claude adaptations; whitespace checks passed. No commit or push
was made.

## Changed files

- [.claude/skills/crypto-evm-token-due-diligence/CLAUDE-CODE-PORT.md](../../.claude/skills/crypto-evm-token-due-diligence/CLAUDE-CODE-PORT.md)
- [.claude/skills/crypto-evm-token-due-diligence/SKILL.md](../../.claude/skills/crypto-evm-token-due-diligence/SKILL.md)
- [.claude/skills/crypto-evm-token-due-diligence/assets/backend-release.json](../../.claude/skills/crypto-evm-token-due-diligence/assets/backend-release.json)
- [.claude/skills/crypto-evm-token-due-diligence/assets/workflow-release.json](../../.claude/skills/crypto-evm-token-due-diligence/assets/workflow-release.json)
- [.claude/skills/crypto-evm-token-due-diligence/references/deterministic-backend.md](../../.claude/skills/crypto-evm-token-due-diligence/references/deterministic-backend.md)
- [.claude/skills/crypto-evm-token-due-diligence/references/public-rpc.md](../../.claude/skills/crypto-evm-token-due-diligence/references/public-rpc.md)
- [.claude/skills/crypto-evm-token-due-diligence/references/runbook.md](../../.claude/skills/crypto-evm-token-due-diligence/references/runbook.md)
- [.claude/skills/crypto-evm-token-due-diligence/scripts/backend_common.py](../../.claude/skills/crypto-evm-token-due-diligence/scripts/backend_common.py)
- [.claude/skills/crypto-evm-token-due-diligence/scripts/broad_collect.py](../../.claude/skills/crypto-evm-token-due-diligence/scripts/broad_collect.py)
- [.claude/skills/crypto-evm-token-due-diligence/scripts/rpc_collect.py](../../.claude/skills/crypto-evm-token-due-diligence/scripts/rpc_collect.py)
- [.claude/skills/crypto-evm-token-due-diligence/tests/test_public_rpc.py](../../.claude/skills/crypto-evm-token-due-diligence/tests/test_public_rpc.py)
- [README.md](../../README.md)
- [docs/provider-setup.md](../../docs/provider-setup.md)
- [docs/reviews/first-run-reliability.md](../../docs/reviews/first-run-reliability.md)
- [env.example](../../env.example)
- [skills/crypto-evm-token-due-diligence/SKILL.md](../../skills/crypto-evm-token-due-diligence/SKILL.md)
- [skills/crypto-evm-token-due-diligence/assets/backend-release.json](../../skills/crypto-evm-token-due-diligence/assets/backend-release.json)
- [skills/crypto-evm-token-due-diligence/assets/workflow-release.json](../../skills/crypto-evm-token-due-diligence/assets/workflow-release.json)
- [skills/crypto-evm-token-due-diligence/references/deterministic-backend.md](../../skills/crypto-evm-token-due-diligence/references/deterministic-backend.md)
- [skills/crypto-evm-token-due-diligence/references/public-rpc.md](../../skills/crypto-evm-token-due-diligence/references/public-rpc.md)
- [skills/crypto-evm-token-due-diligence/references/runbook.md](../../skills/crypto-evm-token-due-diligence/references/runbook.md)
- [skills/crypto-evm-token-due-diligence/scripts/backend_common.py](../../skills/crypto-evm-token-due-diligence/scripts/backend_common.py)
- [skills/crypto-evm-token-due-diligence/scripts/broad_collect.py](../../skills/crypto-evm-token-due-diligence/scripts/broad_collect.py)
- [skills/crypto-evm-token-due-diligence/scripts/rpc_collect.py](../../skills/crypto-evm-token-due-diligence/scripts/rpc_collect.py)
- [skills/crypto-evm-token-due-diligence/tests/test_public_rpc.py](../../skills/crypto-evm-token-due-diligence/tests/test_public_rpc.py)
- [skills/crypto-solana-token-due-diligence/SKILL.md](../../skills/crypto-solana-token-due-diligence/SKILL.md)
- [skills/crypto-solana-token-due-diligence/assets/release.json](../../skills/crypto-solana-token-due-diligence/assets/release.json)
- [skills/crypto-solana-token-due-diligence/references/runbook.md](../../skills/crypto-solana-token-due-diligence/references/runbook.md)
- [skills/crypto-solana-token-due-diligence/scripts/solana_broad_collect.py](../../skills/crypto-solana-token-due-diligence/scripts/solana_broad_collect.py)
- [skills/crypto-solana-token-due-diligence/tests/test_solana_broad_collect.py](../../skills/crypto-solana-token-due-diligence/tests/test_solana_broad_collect.py)
- [skills/crypto-solana-token-due-diligence/tests/test_solana_handoff.py](../../skills/crypto-solana-token-due-diligence/tests/test_solana_handoff.py)
- [tests/install_support.py](../../tests/install_support.py)
- [tests/test_installation.py](../../tests/test_installation.py)

Suggested commit message: `fix: harden first-run provider selection and recovery across EVM and Solana`
