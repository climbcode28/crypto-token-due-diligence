# Evidence and readable output

A report has independent research and delivery states. `completed` means the eleven
standard surfaces and two lane checklists are closed with evidence or evidenced
external limits. It does not mean complete knowledge or that a token is safe.
`checkpoint` preserves actual partial/blocked work and is never final broad delivery.
A focused answer cannot be relabeled completed broad research.

Write judgments in `notes/coordinator.json`; lane authors write their owned notes.
Use [compose](compose.md) preflight before finalizing. Finalize repeats composition
and validation in a private staging directory, preserves the active draft, snapshots
the engine, renders the report and reproduces it with the copied engine before an
atomic new-directory publication. An existing output is never replaced. Failure
removes the staging tree and leaves the previous draft/report intact.

The frozen inventory includes manifest/report bytes, every registered evidence
artifact and immutable lane-note snapshot, readable Markdown, `reading.json`, every
Solana script/adapter, and all assets including registry/layout/source provenance and
licenses. Python bytecode and mutable active notes are excluded. `delivery.json`
records exact hashes and versions; its integrity inventory is not an authentication
signature or proof that source statements are true.

The report renders the exact question/focus, verdict, four conclusions, requirements,
all findings and concerns, eleven-surface coverage, complete typed observations and
evidence ledger. Source text is escaped as data. Citation URLs must be safe public
HTTPS; otherwise use the frozen artifact. Citations carry source/time/hash and make
zero network requests. Relative links work inside the frozen report; `read` also
returns absolute local `answer_link` values for the user-facing answer. The report opens
with a Summary: labeled findings (✅ Good / 🟡 Potential Risk / 🔴 Bad, ⚪ Unverified) with
adjacent citations and exactly four Conclusions bullets, mirroring the chat contract.

A successful finalize/read returns `report_path`, its compact reading checklist and
citations in the same call; the full Markdown stays in the frozen report. Read all
checklist entries before answering. Keep exact quantities and units, spending
owner versus beneficial owner, sample account/receipt counts, custody exclusions,
LP principal versus fees, named controllers and bypass paths, quote versus execution,
net proceeds versus gross/refunds/profit, economics/rights, assurance levels and the
original focus. A short answer must not erase a material limitation or adverse fact.
The checklist keeps every material quantity and limit in a compact shape: typed-fact
details are nested, omit provenance (timestamps, digests, evidence ids, context slots)
and null or empty fields, list same-shaped rows as column tables, and carry the fact's
own pipeline finding; addresses that recur are `@aliases` resolved once in `addresses`
(expand them when naming an account); only publication-derived details (indexer
listings, repository metadata, quote routes) are capped with an explicit remainder note. Refer to the frozen report for supporting detail; do not assign standard
unfinished research to the user as homework.

Use [replay guidance](report-replay.md) for verification and trust boundaries, and
[reporting scenarios](reporting-scenarios.md) to calibrate conclusions.
