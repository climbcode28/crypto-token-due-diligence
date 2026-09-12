# Proxy authority and critical bytecode

**Trigger:** unverified runtime, proxy/upgrade paths, or a critical selector/storage ambiguity prevents a material conclusion.

**Minimum evidence:** pinned deployed runtime, Ethereum code hash, relevant storage and calls, deployment transaction, any claimed source/build settings and source revision. Include authority keys/contracts in the scope manifest.

Escalate gradually:

1. Extract runtime/selectors and obvious call/delegatecall paths. Selectors are leads, not proof of reachability or semantics; collisions and fallback dispatch exist.
2. Resolve applicable EIP-1967 implementation/admin/beacon slots, beacon implementation, minimal clones, UUPS authorization, transparent admin, diamonds/facets and custom routing when encountered. Read each at the pin and follow reachable proxy dependencies. Do not assume “empty EIP-1967 slot” means immutable. Inspect init/reinit paths, role admins and administrator contract upgrades.
3. Seek verified predecessors, compiler metadata, exact version/settings, libraries, immutables, constructor arguments, optimizer and source revision. Recompile with an available toolchain and compare deployed runtime. Explain metadata/link/immutable differences; require executable equivalence to close meaningful differences before making that claim. Code-hash dedup saves analysis, not per-instance storage checks.
4. Use storage layout, historical upgrades/calls/receipts, and reachability to resolve the material path. Record ABI/selector basis and alternatives for uncertain decoding. Historical behavior alone does not prove all executable paths.
5. Only if verdict-changing ambiguity remains, perform deeper bytecode reconstruction or permitted isolated-fork simulation. Decompiler output remains a hypothesis, never verified source. Failed simulation is not proof a path is impossible.

Map current controller, threshold/delay/modules, authority-changing functions, and the assets affected. Distinguish immutable token code from an upgradeable reward/vault/locker and present each control surface separately.

On networks supporting [EIP-7702](https://eips.ethereum.org/EIPS/eip-7702), recognize a
material account's 23-byte `0xef0100 || address` delegation indicator. Capture its delegate
runtime and the authority account's relevant storage at the same pin; execution uses
the authority's context. Preserve the key's ability to replace or revoke delegation and
inspect delegate initialization/permissions. The protocol follows only the first
delegation pointer; do not recursively execute a chain of delegation indicators as if
it were a proxy graph. Code presence alone does not make this an immutable contract or
prove which person controls it. Establish support for the actual network/version.

**Stop:** the critical authority/path is proven or sufficiently bounded for the decision, or available evidence cannot close it at reasonable cost. Do not expand into a full exploit campaign merely because code is unverified.

**If incomplete:** identify the exact undecoded/replacement capability and affected assets; source correspondence, ownership or reachability stays unknown. Route broad invariant/exploit work to a separate audit when available.
