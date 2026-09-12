# Source and deployed-byte correspondence

Treat these as distinct evidence levels:

1. A captured publication with a safe source URL and immutable repository revision.
2. A captured third-party verification claim bound to the exact program and hash kind.
3. Equality between a compatible claimed hash and complete captured loader payload.
4. Equality between a supplied local artifact and that same complete payload.
5. An independently reproduced build from identified source/toolchain/environment.

`source_assurance()` records each level separately. A matching artifact alone does
not establish level 5, because byte equality cannot demonstrate how it was produced.
No program repository, build script or wallet is executed during this implementation.
Any future independent-build claim needs its actual source inputs, immutable revision,
toolchain/environment, command, output artifact, build identifier and execution evidence.

Publication, service unavailability, unsupported hash normalization, mismatching
bytes and incomplete executable capture have different statuses. Missing verification
does not mean unpublished source. Metadata slices cannot produce executable hashes.
The loader payload hash covers all captured payload bytes; compare it only with the
same declared representation. Preserve the program identity, deployment slot, capture
context, source revision, build identifier when available and every relevant digest.

Use the optional routes selected in the tooling review during discovery: canonical
program metadata and pinned IDLs can locate sources; third-party verified-build APIs
can corroborate claims. Neither editable metadata authority nor an IDL proves the
upgrade authority or executable behavior. Their access failures remain access gaps.
Program byte correspondence never proves an individual pool's configuration, treasury
rights, reward liabilities or withdrawal restrictions. Those require their own account
and instruction evidence at disclosed contexts.
