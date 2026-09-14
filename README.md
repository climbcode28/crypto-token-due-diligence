# Crypto token due diligence

Crypto token due-diligence skills for [Claude Code](https://claude.com/claude-code),
[Codex](https://openai.com/codex) and [Cursor](https://cursor.com).

[![Token due-diligence architecture](docs/diagrams/crypto-token-diligence-architecture-dark.png)](docs/diagrams/crypto-token-diligence-architecture-dark.png)
**Input**
```text
token_address:       Exact EVM or Solana token address (required)
token_name:          Token name (optional)
additional_context:  Questions, links, or specific requirements (optional)
```
**Output:** A source-linked assessment of token controls, liquidity, project
credibility, creator history and token economics.

Reports label each finding as **✅ Good**, **🟡 Potential Risk**, **🔴 Bad** or **⚪️ Unverified**, explain
what could not be verified, and save the full supporting evidence under `research/`.
Research is read-only: no wallet connection, signing or trading.

**THIS SKILL IS FOR INFORMATIONAL AND EDUCATIONAL PURPOSES ONLY - <ins>NOT FINANCIAL OR INVESTMENT ADVICE</ins>.**
Findings may be incomplete or incorrect and do not constitute a recommendation to buy,
sell, or hold any asset. Independently verify key information before making financial decisions. AI can miss things or get them wrong, so verify important findings yourself. A positive report doesn’t guarantee a token is safe.

## Skills

| Skill | Purpose |
| --- | --- |
| [crypto-token-due-diligence](skills/crypto-token-due-diligence/SKILL.md) | Start here. Routes your request to the appropriate specialist. |
| [crypto-evm-token-due-diligence](skills/crypto-evm-token-due-diligence/SKILL.md) | EVM token research, including Robinhood Chain. |
| [crypto-solana-token-due-diligence](skills/crypto-solana-token-due-diligence/SKILL.md) | Solana mint research for SPL and Token-2022 tokens. |
| [deep-plan](skills/deep-plan/SKILL.md) | General workflow skill: interviews you about an idea and saves a phased plan. |
| [implement-review-improve](skills/implement-review-improve/SKILL.md) | General workflow skill: implements one phase or all phases of a plan, reviewing, fixing and verifying each phase. |

All five skills support Claude Code, Codex and Cursor. Most use the shared copies
under `skills/`; Claude Code uses an adapted EVM copy. The two workflow skills run
only when you invoke them by name.

## Quick start

Requires **Python 3.10+**, **Git**, and **Claude Code, Codex or Cursor**. No Python packages required. If you don't have these tools installed, or aren't sure whether you do, ask your agent - they can help you 🙂 
```sh
git clone https://github.com/climbcode28/crypto-token-due-diligence.git ~/crypto-research
cd ~/crypto-research
./install.sh
```

The installer links the skills into your user account and leaves existing files alone.
Start a new session after installation. Use `./install.sh --copy` if symlinks are
unavailable, or `./install.sh --uninstall` to remove installed links.
Linked installs pick up updates when you run `git pull` in the clone.
Run the installer for access to all five skills. The clone also includes project
registrations for development, but those do not register every skill in every host.
Tool execution uses your host's normal permission settings.

## Example Usage

In **Codex**:
```text
$crypto-token-due-diligence
$PONS 0x39dBED3a2bd333467115dE45665cC57F813C4571

Focus on liquidity, creator history, and whether
the project has delivered what it claims.
```

In **Claude Code** or **Cursor**, use `/crypto-token-due-diligence` with the same request format.

You receive a concise assessment with evidence links, clearly labeled research gaps,
and a saved report. Public data availability affects coverage; a positive finding is
not a guarantee that a token is safe.

## Set an RPC endpoint

**Both EVM and Solana work without dRPC or an API key.** The EVM skill selects a
public RPC from built-in defaults for its seven registered mainnets when no dRPC key is
configured; other chains need an explicit endpoint. Solana uses public mainnet RPC by
default.

To configure a custom dRPC endpoint yourself, copy the template example file outside the repository and edit it:
```sh
mkdir -p ~/.config/crypto-research
cp env.example ~/.config/crypto-research/env
chmod 600 ~/.config/crypto-research/env
```

The example uses Robinhood Chain's public endpoint. Despite its name,
`ROBINHOOD_DRPC_URL` accepts a public or dRPC HTTPS endpoint for your EVM chain.
`SOLANA_DRPC_URL` selects Solana's dRPC endpoint. The separate `SOLANA_RPC_URL`
variable is only for overriding public RPC; leave it unset when configuring dRPC.

**Optional dRPC:** add the following to that private env file, using your own key:

```sh
export ROBINHOOD_DRPC_URL='https://lb.drpc.org/robinhood'
export SOLANA_DRPC_URL='https://lb.drpc.org/solana'
export DRPC_API_KEY='your-key'
```

Keep keys out of URLs and the repository. Configuring the key is your authorization:
whenever it is present the skills use dRPC within their built-in per-run ceilings, and
otherwise they fall back to public RPC, which needs no key or private file. No consent
prompt is asked per run; remove the key from the file to stop, or pass `--provider public`
(Solana also accepts `--cost-policy free`) on a single command. Host network approval
still applies to every live command.
See [provider setup](docs/provider-setup.md) and the
[Solana runbook](skills/crypto-solana-token-due-diligence/references/runbook.md) for details.

Every collection command needs outbound network under the host's normal approval rules.
A Solana start with no identity response retains a blocked result and its consumed
budget; it must not restart in a new directory to obtain fresh allowances. Follow the
runbook's recovery rules and keep missing identity explicit. On a keyed dRPC run the Solana session
ceiling is 160 sends instead of 120, the room it uses to census LP positions on concentrated
pools after the standard collection.

## Development

Editable skills live under `skills/`. Follow [project guidance](AGENTS.md) and the
[EVM port notes](.claude/skills/crypto-evm-token-due-diligence/CLAUDE-CODE-PORT.md)
when changing them.

The [first-run acceptance record](docs/reviews/first-run-reliability.md) separates
installation tests, live host results and incomplete cases. Run the offline suites
from the repository root:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s skills/crypto-token-due-diligence/tests -q
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s skills/crypto-evm-token-due-diligence/tests -q
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s skills/crypto-solana-token-due-diligence/tests -q
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -q
```

## License

[MIT](LICENSE).
