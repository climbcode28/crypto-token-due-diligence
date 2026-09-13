#!/usr/bin/env sh
# Install the token-diligence and workflow skills for your user account so they work in every project.
#
#   ./install.sh            symlink the skills into ~/.claude/skills and ~/.agents/skills
#                           (Cursor reads ~/.agents/skills too; inside this folder it also
#                           sees the pointer skills in .cursor/skills)
#   ./install.sh --copy     copy instead of symlink (use when your tool cannot follow links)
#   ./install.sh --uninstall
#
# Nothing here needs network access, root, or any Python package. Re-running is safe.
set -eu

HERE="$(cd "$(dirname "$0")" && pwd)"
MODE="link"
[ "${1:-}" = "--copy" ] && MODE="copy"
[ "${1:-}" = "--uninstall" ] && MODE="uninstall"

CLAUDE_DIR="${HOME}/.claude/skills"
CLAUDE_AGENTS_DIR="${HOME}/.claude/agents"
CODEX_DIR="${HOME}/.agents/skills"
SKILLS="crypto-token-due-diligence crypto-evm-token-due-diligence crypto-solana-token-due-diligence deep-plan implement-review-improve"
AGENTS="evm-liquidity-lane.md evm-project-lane.md phase-reviewer.md"

install_one() {
  target_dir="$1"; name="$2"; source="$3"
  mkdir -p "$target_dir"
  dest="$target_dir/$name"
  if [ -e "$dest" ] || [ -L "$dest" ]; then
    if [ -L "$dest" ] && [ "$(readlink "$dest")" = "$source" ]; then
      echo "  already linked: $dest"; return
    fi
    echo "  exists, skipping (remove it first if you want this copy): $dest"; return
  fi
  if [ "$MODE" = "copy" ]; then
    cp -R "$source" "$dest"; echo "  copied:  $dest"
  else
    ln -s "$source" "$dest"; echo "  linked:  $dest -> $source"
  fi
}

remove_one() {
  dest="$1/$2"
  if [ -L "$dest" ]; then
    case "$(readlink "$dest")" in
      "$HERE"/*) rm "$dest"; echo "  removed link: $dest" ;;
      *) echo "  left alone (points elsewhere): $dest" ;;
    esac
  elif [ -e "$dest" ]; then
    echo "  left alone (a copy, not a link; delete it yourself if it came from this repo): $dest"
  fi
}

if [ "$MODE" = "uninstall" ]; then
  for s in $SKILLS; do remove_one "$CLAUDE_DIR" "$s"; remove_one "$CODEX_DIR" "$s"; done
  for a in $AGENTS; do remove_one "$CLAUDE_AGENTS_DIR" "$a"; done
  exit 0
fi

echo "Claude Code (personal skills in $CLAUDE_DIR):"
# Claude Code gets its own copy of the EVM skill (tool wording differs); the others are shared.
install_one "$CLAUDE_DIR" "crypto-evm-token-due-diligence" "$HERE/.claude/skills/crypto-evm-token-due-diligence"
install_one "$CLAUDE_DIR" "crypto-token-due-diligence" "$HERE/skills/crypto-token-due-diligence"
install_one "$CLAUDE_DIR" "crypto-solana-token-due-diligence" "$HERE/skills/crypto-solana-token-due-diligence"
install_one "$CLAUDE_DIR" "deep-plan" "$HERE/skills/deep-plan"
install_one "$CLAUDE_DIR" "implement-review-improve" "$HERE/skills/implement-review-improve"
echo "Claude Code subagents, research lanes and the read-only phase reviewer (personal agents in $CLAUDE_AGENTS_DIR):"
for a in $AGENTS; do install_one "$CLAUDE_AGENTS_DIR" "$a" "$HERE/.claude/agents/$a"; done

echo "Codex and Cursor (personal skills in $CODEX_DIR):"
for s in $SKILLS; do install_one "$CODEX_DIR" "$s" "$HERE/skills/$s"; done

echo
echo "Done. Start a new Claude Code or Codex session; the skills appear as"
echo "  /crypto-token-due-diligence, /crypto-evm-token-due-diligence, /crypto-solana-token-due-diligence,"
echo "  /deep-plan, /implement-review-improve                       (Claude Code and Cursor)"
echo "  \$crypto-token-due-diligence, \$crypto-evm-token-due-diligence, \$crypto-solana-token-due-diligence,"
echo "  \$deep-plan, \$implement-review-improve                     (Codex)"
echo "Both specialists use public RPC by default; optional dRPC setup: README.md, section 'Set an RPC endpoint'."
