# Programs and authority paths

Version 1.0.0; pinned definitions are in
[`layout-sources.json`](../assets/layout-sources.json). A layout reference identifies
the supported decoder. It does not verify a particular deployed binary.

`solana_programs.py` binds each account to a successful request, address/index and
actual context. Supported loaders are upgradeable v3 (Program → ProgramData),
nonupgradeable v2 and runtime-managed native programs. Other loaders remain unknown.
Upgradeable Program accounts require the correct variant, full 36-byte layout,
ProgramData PDA, corresponding account owner and tested 45-byte metadata prefix.
ProgramData's deployment slot cannot follow its observed context. Missing ProgramData
is unresolved; a null authority field with unknown upgradeability is not revocation.

Metadata-prefix reads identify observed loader fields only. Complete code capture
requires an unsliced response, matching total space and a nonempty loader payload.
The code digest covers the entire captured payload, including allocated padding; it
must not be compared to a differently normalized ELF digest. Program rechecks require
distinct evidence requests, later starts, nondecreasing contexts and comparisons of
loader, ProgramData, deployment slot, authority and code digest. Neither loader
immutability nor authority revocation establishes token safety.

The ordinary authority graph follows at most three edges and inspects at most twenty
controller accounts, including auxiliary ProgramData and multisig parent accounts.
Every edge has a subject, destination, concrete role, capability scope and evidence
aliases. Mint and holding powers, custom hook programs, token programs, signers and
upgrade authorities remain distinct. Upgrade edges describe possible future program
changes; they do not assert an arbitrary current withdrawal or transfer instruction.
Cycles, missing accounts, truncation and unrecognized code remain explicit gaps while
retaining previously observed edges. A system-owned key account does not identify its
human controller; an off-curve address alone does not identify its signing program.

SPL multisig decoding requires all 355 bytes, initialized state, a valid threshold
and every active signer (up to eleven). Duplicate signer configurations require
separate execution analysis and are rejected by this supported path. No shortened
signer display substitutes for the full account. A valid multisig is linked to a
subject only by an observed authority field.

Squads v4 is pinned to production program
`SQDS4ep65T869zMMBKyuUq6aD6EgTu8psMjkvj52pCf` and revision
`af94153ff77a28b6effe46b9c94baaa93742b48c`. The independent binary decoder checks
the discriminator, actual owner, full member vector, permission bits, voter threshold,
configuration limits, Option encoding and exact stored-bump PDA. Allocated trailing
bytes are recorded rather than interpreted as extra members. More than 256 members
is unsupported locally, not a partial signer list presented as complete.

A nonzero configuration authority can change members, threshold and timelock via
the pinned controlled-multisig path. This is a distinct configuration bypass. A vault
relation additionally requires its multisig and vault-index PDA. Spending limits must
match their actual parent, create-key PDA, vault index, mint, amounts, period and full
member/destination vectors. These independently authorized members can differ from
multisig voters, and a permitted spending-limit transfer bypasses normal voting and
timelock. An empty destination vector means unrestricted destination within that
limit's asset/amount rules. A sampled set of spending limits never proves none others
exist; remaining search coverage and program upgrades stay unresolved.

The Squads sources are AGPL-3.0; this skill records interface facts and implements
an independent wire decoder. It does not import, install or execute the Squads program.
