# Crypto research skills

A lightweight router and two specialist skills for evidence-bounded token diligence, with Python 3.10+ standard-library
helpers and offline regression tests. Use them with an AI coding assistant that can run
Python and perform web research. No pip packages or dRPC subscription are required.

![EVM diligence architecture](docs/diagrams/evm-diligence-architecture-dark.png)

| Skill | Purpose |
| --- | --- |
| [EVM token diligence](skills/crypto-evm-token-due-diligence/SKILL.md) | Broad or focused diligence on an exact EVM chain and token address. |
| [Solana token diligence](skills/crypto-solana-token-due-diligence/SKILL.md) | Diligence on an exact Solana mint. |
| [Token diligence router](skills/crypto-token-due-diligence/SKILL.md) | Offline candidate-family selection; preserves the full request and deadline for the specialist. |

## Codex

Keep all three `skills/` folders together. Open this repository in Codex. The relative
symlink in `.agents/skills/` registers EVM diligence for this project and points to its
canonical folder. Start a new task if the skill does not appear. Avoid installing a second
copy under the same name. Archives must preserve symlinks; if your extraction tool does
not, recreate the EVM link from the repository root:

```sh
mkdir -p .agents/skills
ln -s ../../skills/crypto-evm-token-due-diligence .agents/skills/crypto-evm-token-due-diligence
```

Run that command only when the link is absent. The sibling folders provide shared helpers
and routing references. To invoke the other skills directly, reference their `SKILL.md`
paths, or register those sibling folders in your own project skill setup.

Start with `$crypto-token-due-diligence` for an exact token address. It selects the EVM
or Solana candidate family without network calls, preserving all questions and one
5–7-minute target/10-minute stop budget; the specialist verifies identity. Native
assets and market-wide scoring are outside this entry point.

Direct specialist example: `Use $crypto-evm-token-due-diligence for broad diligence on chain <chain ID>,
token <address>.` The token name is optional. An omitted chain can be inferred only when
exact-address discovery is unambiguous; chain ID and deployed code are still verified.

Codex uses the two briefs in `skills/crypto-evm-token-due-diligence/assets/` with its
subagent tool. No Claude agent files or custom Codex agent definitions are required.
The coordinator performs both checklists if subagents are unavailable. See the
[runbook](skills/crypto-evm-token-due-diligence/references/runbook.md).

## Claude Code (optional)

The `.claude/skills/crypto-evm-token-due-diligence/` copy and the two `.claude/agents/`
definitions provide Claude-specific invocation and lane tooling. Keep the canonical
`skills/` folders too: sibling routing and shared helpers use them. The other two
skills can be read from their canonical paths. See the
[port notes](.claude/skills/crypto-evm-token-due-diligence/CLAUDE-CODE-PORT.md).

The personal project's `.claude/settings.json` permission allowlist is intentionally
excluded. The Claude skill itself declares allowed tools in its frontmatter; inspect
those permissions and use your own host permission settings.

## Providers and research output

Read [HANDOFF.md](HANDOFF.md) before provider use. No credentials or paid-use permission
are supplied. Prefer your own configured, authorized provider for its matching chain;
otherwise use available authorized public sources. Missing evidence stays unverified.
Optional credentials belong outside the repo, for example in
`~/.config/crypto-research/env`. Configuration does not authorize paid calls.

EVM workflow 3.0.0 / backend 3.2.0 / reporting 2.6.0 targets 5–7 minutes with a
10-minute cap and defined stopping rules. A prior live acceptance run on Claude Code
took 10 minutes; equivalent live Codex performance has not been verified.
Validation checks consistency, not token safety or completeness of external sources.

## Tests

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s skills/crypto-token-due-diligence/tests -q
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s skills/crypto-evm-token-due-diligence/tests -q
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s skills/crypto-solana-token-due-diligence/tests -q
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s .claude/skills/crypto-evm-token-due-diligence/tests -q
```

This distribution preserves source and test bytes. Release metadata may refer to historical
`plans/` review records retained in the maintainer's private development repo; these are
provenance pointers, not runtime dependencies. Personal research, cached evidence, historical
snapshots and development plans are not distributed. See `FILES.sha256` for file hashes.

No license has been selected for this prepared distribution; the owner should choose one
before publishing it for reuse.
