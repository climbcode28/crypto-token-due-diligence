# Disposable local-fork simulation

Use only when read-only evidence cannot settle a material sell/redemption/authority question. Never connect a wallet, request secrets, sign with a real key, broadcast to a live chain, or use a public testnet as the disposable fork.

Before any simulated write, establish all of the following:

- Endpoint is loopback, and the process was created for this investigation as a disposable local fork. A hostname, port, client-version string, or chain ID alone does not prove this. Verify process ownership, startup configuration and local node provenance.
- Record upstream chain, pinned fork block/hash, local endpoint and distinct local chain ID, snapshot ID, tool version and launch configuration with credentials redacted. Block outbound transaction forwarding; upstream access is for reads only.
- Use newly generated synthetic test accounts and local funding. No real private keys, user wallet accounts, hardware wallets, or remote signers. Avoid impersonating real accounts; if an authority scenario requires a substitute, explicitly describe artificial role/storage changes and their implications.
- Use a snapshot and reset between scenarios. Record every balance/storage/role/code override; no silent cheat-code provisioning of the very property being tested. Do not fabricate token inventory in a way that bypasses normal acquisition/transfer gates and then claim ordinary-holder sellability.

For a sale/redemption save inputs, approvals, route, sender/recipient, receipt status, logs, pre/post token AND intended underlying balances, gas and fee costs, and relevant state changes. Require status success and the intended balance delta; events/booleans are insufficient. Native underlying deltas need gas/refund adjustment. State tested sizes and recipient assumptions. Label all outputs counterfactual at the fork state; artificial funding/overrides, later state changes, MEV, pending transactions and node deviations limit applicability.

If isolation cannot be verified, do no simulation writes; preserve read-only quotes and mark the decisive execution check unresolved. The validator, renderer and detectors operate offline; the separately authorized collector sends allowlisted read-only RPC requests. None performs fork simulation. Manifest declarations document the investigator's actions and are not technical enforcement of external tooling.
