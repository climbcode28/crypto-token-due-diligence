# Publication review and cleanup

Reviewed from `80849a9` on `main`; cleanup completed 2026-09-12. This record covers
publication hygiene and targeted security review, not a guarantee of security.

## Security findings resolved

| Finding | Resolution |
| --- | --- |
| EVM web capture accepted localhost, private IPs and metadata-service URLs. | The canonical helper and Claude copy now reject non-public URL destinations and actual connected peers before sending HTTP request data. Redirects use the same checks, and anonymous captures do not inherit proxies. Public HTTP/HTTPS remains supported. |
| Claude shipped broad shell auto-approvals. | Removed `.claude/settings.json` and the EVM skill's `allowed-tools` auto-approval list. Commands use the recipient's normal host permissions. The research instructions remain in place; they are not a technical sandbox. |

The network-boundary reproduction and regressions use fake transports and sockets;
no real localhost, metadata service, or live provider was contacted. Tests cover direct
private destinations, redirects, private connected peers behind public-looking names,
public-peer success, proxy isolation, malformed ports and URL control characters.

EVM backend is now **3.4.3**, workflow **3.2.8**; reporting remains **2.6.2**.
Schema and evidence compatibility are unchanged. Shared canonical/Claude scripts,
tests and references match, aside from the documented host adaptation.

## Cleanup completed

- Removed the eight-file superseded `sharing/` exporter and the ignored
  `share-export/` snapshot. Its old 205-entry manifest had 75 outdated source hashes.
- Preserved six completed setup/retired-workflow plans in the ignored local archive,
  checked their SHA-256 hashes, and removed them from the public working tree. See
  [development provenance](../development-history.md) for exact filenames and locations.
- Preserved the earlier handoff privately and replaced the tracked handoff with concise
  current provider policy, configuration and operating references. Personal setup
  narrative and task identifiers are no longer in that public document.
- Retained the existing four old diagram-prompt deletions and short Carbon style note.
- Clarified README installation requirements, the Claude EVM adaptation, public RPC
  fallback, and the distinct `SOLANA_RPC_URL`/`SOLANA_DRPC_URL` roles. Updated the
  installer completion message and distinguished maintainer registration preferences
  from recipients' explicit Personal installation.
- Added explicit all-remaining-phases support to the implementation workflow contract,
  keeping a complete implementation/review/verification cycle per phase and preserving
  its explicit-invocation policy.
- Retained referenced acceptance/provenance records, tests, legacy replay fixtures,
  source registries, third-party notices, diagrams and their convenience viewer.
  Research evidence and the private archive branch were not deleted or rewritten.

## Credential and privacy checks

The initial scan covered 506 tracked regular files, 37,268 ignored regular files and
1,376 unique reachable Git blobs across both local branches. The post-cleanup scan,
including new files, covered 495 working regular files, 37,044 ignored regular files
and 1,377 reachable blobs. Counts describe the scan snapshots, not a file manifest.
All five tracked registration symlinks resolve within the checkout.

No apparent live credential was found in current publishable content or reachable
Git history. Current secret-like matches were synthetic security fixtures. An exact
byte search for the configured dRPC key found no matches in working files, ignored
files, or reachable Git objects; its value was never printed. Ignored PEM matches
were third-party cryptography self-test fixtures, not evidence of a user key leak.

The owner confirmed the commit email is acceptable; main's author/committer identity
matches that approved address. Git identity and history were left unchanged. Personal
home paths occur in archive-only historical blobs, not main-reachable blobs. Keep
`archive/pre-publish` local. Deleting a tracked file does not erase earlier commits;
the archived setup records remain in main's existing history as documented.

`HANDOFF.local.md`, environment files, local Claude settings, and research/run/history
folders remain ignored. Ignoring protects ordinary Git inclusion, not filesystem zips
or force-adds. No remote is configured in this checkout; GitHub-side settings or old
published copies were not audited. Replace README's clone URL placeholder when the
repository destination is chosen.

## Verification and limits

- Router: **30** tests; canonical EVM: **435**; Claude EVM: **435**; Solana: **417**.
  All four offline suites pass (**1,317 total**, including mirrored EVM coverage).
- The Solana guidance check was updated for the shortened handoff while preserving
  assertions for public fallback, distinct dRPC configuration and explicit paid-use
  authorization. Its full suite passed after that update.
- All local Markdown links and release-review references resolve. Archive hashes,
  mirror consistency, shell syntax, and `git diff --check` passed.
- Skill frontmatter and explicit-invocation settings were checked directly. The optional
  bundled skill validator could not run because PyYAML is absent; no dependency was
  installed just for this documentation change. Host skill discovery was not live-tested.
- Existing Python 3.14 resource-cleanup warnings for mocked HTTP errors and SQLite
  connections remain non-failing; this cleanup does not claim to fix them.

The custom scan checks common service-token formats, private-key headers, credential
assignments/URLs and personal metadata; Gitleaks and TruffleHog were unavailable.
Pattern scanning skips binary content; the exact configured-key search includes binary
bytes. It does not unpack arbitrary archives, OCR all images, inspect unreachable or
reflog-only objects, or prove that unknown/rotated credentials never existed.
No live RPC, credential validation, paid access, publishing, commit or push was performed.
