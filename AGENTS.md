# Project guidance

- Canonical editable skills live in `skills/crypto-token-due-diligence`,
  `skills/crypto-evm-token-due-diligence`, `skills/crypto-solana-token-due-diligence`,
  `skills/deep-plan` and `skills/implement-review-improve`.
  Codex discovers EVM diligence through the project-local symlink
  `.agents/skills/crypto-evm-token-due-diligence` to its canonical folder. Keep EVM
  registration project-only on the maintainer's machine; do not add or modify Personal
  registrations during repository maintenance. Recipients who explicitly run `install.sh`
  opt into Personal links for all five skills; that packaging path does not require
  changing the maintainer's existing registrations.
  The router only classifies candidate format; specialists verify identity and share the
  original request deadline. Retired crypto-research is not an active skill.
- `.claude/skills/crypto-evm-token-due-diligence` is the Claude Code copy of the EVM skill.
  Edit the canonical folder first, then mirror the change there per its `CLAUDE-CODE-PORT.md`.
- `skills/deep-plan` and `skills/implement-review-improve` are the shared workflow skills, explicit
  invocation only, used unchanged by Claude Code, Codex and Cursor. They are registered in this
  project through relative symlinks in `.agents/skills/` and `.claude/skills/`; `.cursor/skills/`
  holds Cursor pointer skills that only name the canonical folder under `skills/` to read. Change
  behavior in the canonical folder, never in a symlink target copy or a pointer. The read-only
  `phase-reviewer` agent in `.claude/agents/` backs the review stage in Claude Code and Cursor.
- Preserve archived research-rubric provenance, verified EVM/Solana diligence routing, optional dRPC
  fallback, and evidence/identity/pin standards.
- Use the implement-review-improve workflow for changes. Run the relevant standard-library
  unittest suites documented in README.md. Version behavioral improvements and retain
  regression coverage; relocation alone does not change the engine version.
- `history/` (frozen development provenance) is ignored and is not part of the published tree.
  Older records live on the maintainer's local `archive/pre-publish` branch; the publication
  cleanup also preserves selected setup records there on disk, indexed in `docs/development-history.md`. When present on disk, do not
  rerun its historical installers as an installation or upgrade procedure; preserve evidence bytes.
- Keep credentials outside the project. A configured dRPC key is not permission for paid
  usage. Before the first EVM provider check or RPC attempt, read the current policy that
  the EVM skill's `provider_context.py --policy` prints (Solana defaults to public RPC; configured
  dRPC use requires explicit paid-use flags and current-user authorization): the untracked personal `HANDOFF.local.md` when it
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
