# Frozen schema-1 compatibility fixtures

Captured before implementation changes using the trusted fc60201 collector and
bundle functions with `test_solana.FakeTransport`; no network requests occurred.
`collection` preserves the nine-attempt synthetic collection, original five-file
engine snapshot, summary, manifest, report and rendered bytes. `independent`
preserves a separate synthetic RPC-evidence bundle with an independently rechecked
header. Both intentionally remain partial with unknown broad coverage.

`golden-sha256.json` binds the captured bytes. Tests apply `rejections.json` mutations
to temporary copies and never update these fixtures. Do not execute the historical
snapshot: it intentionally retains the old incomplete dependency inventory. The
installed legacy reader reproduces its deterministic contract without those imports.
