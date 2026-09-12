# EVM diligence: route the user's extra asks and links into the run (2026-09-11)

## Problem

A user invokes the EVM skill with more than an address, for example:
"Flybrain - 0x4Eb9…2d35 - please also dig into the lore behind this coin and if it's
true or just AI slop: https://x.com/fruitflydev/status/2098116826366415136".
Today the address, chain and stated acceptance requirements are handled (the question is
recorded, requirements are quoted in the decision review). The extra ask and the link are
visible only to the coordinator: the two lane briefs are rendered from a fixed template and
never receive the user's words or URLs, so the specific post is never captured and the
"true or hype" question is answered only incidentally.

## Design decisions

- `broad_collect.py start` gains `--focus TEXT` (the user's extra asks, verbatim) and
  `--url URL` (repeatable, at most 6, validated by the fetcher's credential-free URL rule).
  Both are stored in `intake.json` (`focus`, `user_urls`). Absent values mean "standard scope".
- `brief()` reads `intake.json` and fills a new `{{USER_FOCUS}}` placeholder in both lane
  briefs with a "What the user asked" section: the quoted asks, the URLs, and how to treat
  them (capture the URLs first with the fetcher; X status pages carry the post text in the
  `og:description`/`twitter:description` meta tags of an otherwise JavaScript shell; answer
  each ask in a finding, using `inference` for documentary truth-versus-hype judgements and
  never Good for lore that cannot be observed; unanswerable asks become a coverage attempt).
  The project lane captures every user URL; the liquidity lane captures only those about
  pools, holders or trades.
- `scaffold` echoes `user_focus` and `user_urls` in its result and adds a reminder that the
  verdict text must answer the user's asks explicitly.
- Runbook and SKILL.md: Step 1 passes the user's whole request as `--question`, extra asks
  as `--focus`, links as `--url`; Deliver answers the asks explicitly, labeled by evidence
  strength.
- No new research calls, budgets or turns: URLs ride inside the lanes' existing 20-request
  budgets.

## Phase 1: user focus pass-through (the only phase)

Deliverables: the `--focus`/`--url` options and intake fields; the `{{USER_FOCUS}}` section
in `assets/lane-brief-liquidity.md` and `assets/lane-brief-project.md`; `brief()` rendering;
scaffold echo; runbook and SKILL.md wording; regression tests; Claude copy mirrored.

Acceptance criteria:
1. `start --focus "…" --url https://x.com/… --url https://…` records both in `intake.json`;
   a credential-bearing URL is refused with the fetcher's message; a seventh URL is refused.
2. `brief()` for both lanes contains the user's words and every URL when present, and the
   sentence "No additional asks beyond the standard scope." when absent; no `{{` remains.
3. `scaffold_note` returns `user_focus` and `user_urls` from `intake.json`.
4. Existing suites pass in both copies; the Claude copy is byte-identical for scripts,
   tests and assets after mirroring.

Validation: `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s
skills/crypto-evm-token-due-diligence/tests -q` and the same for
`.claude/skills/crypto-evm-token-due-diligence/tests`.
