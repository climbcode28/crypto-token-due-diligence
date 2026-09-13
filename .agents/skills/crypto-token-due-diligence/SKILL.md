---
name: crypto-token-due-diligence
description: Codex entry point for token due diligence. Routes an exact EVM token address or Solana mint plus the complete request to the EVM or Solana specialist in this repository and continues that specialist's work in the same task. Invoke explicitly with /crypto-token-due-diligence. Not for price prediction, trading, native-asset prices or a safety verdict.
disable-model-invocation: true
---

# Crypto token due diligence (Codex pointer)

This file only registers the skill for Codex. The skill itself is
`skills/crypto-token-due-diligence/SKILL.md` in this repository, shared unchanged with Claude
Code and Codex; it is the single source of truth and this pointer adds no rules of its own.

1. Read `skills/crypto-token-due-diligence/SKILL.md` and follow it exactly, with the user's
   complete request as the intake. Treat `skills/crypto-token-due-diligence/` as the skill
   root: resolve `scripts/route.py` and the sibling links
   `../crypto-evm-token-due-diligence/SKILL.md` and
   `../crypto-solana-token-due-diligence/SKILL.md` against that folder, and set `SKILL_DIR`
   to its absolute path when a command needs it.
2. The specialist it selects is likewise the canonical folder under `skills/`. Treat that
   folder as the skill root for its own `scripts/`, `references/` and `assets/` paths, and
   read `AGENTS.md` at the repository root for provider policy before any RPC attempt.
3. Where a specialist says to spawn research lanes, use Codex subagents launched in one
   message so they run in parallel. Codex recognizes the EVM lane definitions in
   `.claude/agents/`. Without subagents, follow the specialist's inline fallback for lanes.
4. Budgets, read-only rules, refusals and checkpoint behavior are the specialist's; nothing
   here extends or relaxes them.
