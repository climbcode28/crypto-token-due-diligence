# Fast screening and bounded research

Authorized 2026-09-06. Implement, review, improve; no live paid calls, purchases,
commits or pushes. Do not change frozen NUKE evidence or the scoring rubric.

## Intended behavior

- Add `crypto-rug-check`: a limited EVM risk screen, default 30-second collection
  budget, at most 55 seconds for its collector, and a concise answer targeted within
  60 seconds. Model/tool startup and synthesis are outside the collector's process
  timeout. Unknowns never pass; no certification of safety or ability to exit later.
- Reuse the existing RPC configuration, credential redaction and paid-use guards.
  Fixed read-only requests, concurrency four, maximum 24 attempts, no retries, no
  traces, no historical log scans. Preserve partial evidence on timeout. A separate
  process bounds stalled network calls, including DNS and slow response bodies.
- Preserve chain/address identity and numbered-block hash rechecks. A failed recheck
  makes collected state unconfirmed. Basic getter/storage observations do not prove
  source correspondence, complete privileges, sellability or LP custody.
- Make research Pass 1 target 5–10 minutes, with collection ending at eight minutes
  and time reserved for scenarios, scoring and validation. Required Robinhood broad
  diligence remains required; incomplete evidence yields Partial/Blocked or No Grade.
- Default to background web/API/connector reads and hidden in-app browsing when
  JavaScript is necessary. No personal Chrome tabs, groups or pinning by default.
- Recommended starting settings: Sol Low for the rapid screen, Sol Medium for
  research, Astra High for explicitly deeper investigation. Do not switch models
  automatically or promise measured latency/accuracy before benchmarking.

## Validation and review

Exercise synthetic normal, malformed, wrong-chain, reorg, missing-code, timeout,
request-cap and secret-echo cases. Verify unapproved dRPC never constructs transport.
Run existing research/diligence suites and the new quick-screen suite. Review actual
diff, output semantics, side effects, and shareable sibling layout, then fix findings.
Record actual outcomes here before completion.

Backend 1.1.0 and rubric v2.1 remain unchanged. New screen engine starts at 1.0.0;
research/diligence orchestration policy is versioned separately in workflow-release.json.

## Completed implement-review-improve cycle

- Implemented the three workflow entrypoints, prepared quick collector, immutable
  research deadlines, UI metadata, release manifests and sharing/setup documentation.
- Reviewed the actual diff and the collector's request construction, process lifetime,
  credential handling, source snapshots, output claims, dependency links and fallback.
- Improved the candidate after review: stable query truncation reserves rechecks;
  fixed a sibling reference; old/future block timestamps now carry an explicit
  freshness gap; capture timestamps follow responses; snapshots include the transitive
  validator import; packet evidence/attempts have integrity digests. Synthetic process
  runs are labeled. Existing research and backend arithmetic/rules were not changed.
- **145 offline tests passed:** 25 research (including four deadline cases), 106 existing
  diligence/backend, 14 quick-screen cases. The stalled-worker test terminates the
  process and retains the attempt record. Cases include wrong chain, reorg, stale
  block, malformed/missing evidence, capped reads, secret echo and paid-use fallback.
- All three skill-format checks passed using a pre-existing temporary PyYAML validator
  dependency; no package was installed. All 52 relative skill Markdown links resolve.
- Installed `~/.codex/skills/crypto-rug-check` as a symlink to its canonical project
  folder, matching the other personal skills. Verified invocation through that link:
  offline fallback, zero network requests, no credential values printed.
- Git whitespace validation passed. Git diff confirms frozen history, rubric, score
  engine and the existing backend scripts are unchanged. No live token benchmark,
  paid RPC call, purchase, commit or push was performed in this implementation task.

## Changed files

- `AGENTS.md`, `README.md`, `HANDOFF.md`, this implementation record.
- `skills/crypto-research/SKILL.md`; references `evidence-pull.md`,
  `robinhood-diligence.md`, `runtime-and-browser.md`; `scripts/research_budget.py`;
  `tests/test_budget.py`; `assets/workflow-release.json`.
- `skills/crypto-evm-token-due-diligence/SKILL.md` and `assets/workflow-release.json`.
- New `skills/crypto-rug-check/`: `SKILL.md`, `agents/openai.yaml`,
  `assets/release.json`, `references/collector.md`, `scripts/rug_check.py`,
  `tests/test_rug_check.py`.

## Practical limits

The quick collector is a bounded observation packet, not a complete rug detector:
it does not close sellability, arbitrary admin powers or LP custody. The skill can
corroborate findings through available background sources within the same deadline.
Live end-to-end time and detection accuracy remain unmeasured. The process timeout
contains RPC stalls; the research checkpoint helper cannot kill the model or other
tools. Hidden-browser selection is a tool-routing policy, not a tested browser-service
deployment. No personal Chrome state was modified while implementing the policy.

Suggested commit message: `feat: add rapid rug screen and bounded background research`.
