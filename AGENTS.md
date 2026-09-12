# Project guidance

- Canonical editable skills live in `skills/crypto-token-due-diligence`,
  `skills/crypto-evm-token-due-diligence` and `skills/crypto-solana-token-due-diligence`.
  Codex discovers EVM diligence through the project-local symlink
  `.agents/skills/crypto-evm-token-due-diligence` to its canonical folder. Keep EVM
  registration project-only; do not create a Personal registration or a second Codex copy.
  The router and Solana skill have Personal symlinks to their canonical folders.
  The router only classifies candidate format; specialists verify identity and share the
  original request deadline. Retired crypto-research is not an active skill.
- `.claude/skills/crypto-evm-token-due-diligence` is the Claude Code copy of the EVM skill.
  Edit the canonical folder first, then mirror the change there per its `CLAUDE-CODE-PORT.md`.
- Preserve archived research-rubric provenance, verified EVM/Solana diligence routing, optional dRPC
  fallback, and evidence/identity/pin standards.
- Use the implement-review-improve workflow for changes. Run the relevant standard-library
  unittest suites documented in README.md. Version behavioral improvements and retain
  regression coverage; relocation alone does not change the engine version.
- `history/` (frozen development provenance) is not part of the published tree; it lives on the
  maintainer's local `archive/pre-publish` branch and is ignored here. When present on disk, do not
  rerun its historical installers as an installation or upgrade procedure; preserve evidence bytes.
- Keep credentials outside the project. A configured dRPC key is not permission for paid
  usage. Before the first EVM provider check or RPC attempt, read the current policy that
  the EVM skill's `provider_context.py --policy` prints (the Solana skill uses credential-free
  public RPC and reads no policy file): the untracked personal `HANDOFF.local.md` when it
  exists on this machine, otherwise the generic section at the top of `HANDOFF.md`. Honor a
  standing bounded paid read-only authorization recorded in the personal file unless the
  current user restricts it; it does not authorize purchases, top-ups, plan changes or
  unlimited usage. Never commit `HANDOFF.local.md`. Source the
  documented private env file with tracing disabled in the same shell invocation as
  every check/collection. For its matching network, prefer configured authorized dRPC
  before public RPC. Omitted flags are an invocation issue, not provider failure.
- Research uses background access or hidden in-app browsing by default, not personal
  Chrome tabs/groups/pins. Preserve the quick-screen scope and research time budgets;
  timeouts or missing evidence never become passing checks.
- Never run `git commit` or `git push` unless explicitly requested in the conversation.
