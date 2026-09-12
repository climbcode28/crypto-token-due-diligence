"""Original SPL and Token-2022 base multisig layout, bound to its actual address."""
from solana_common import need, pubkey, b58encode, TOKEN_PROGRAM, TOKEN_2022, sha
from adapters.binary import raw_account


def decode(address, account):
    pubkey(address)
    need(account["owner"] in (TOKEN_PROGRAM, TOKEN_2022) and account["executable"] is False, "SPL multisig data account required")
    raw = raw_account(account, account["owner"])
    need(len(raw) == 355, "complete SPL multisig account required")
    threshold, count, initialized = raw[:3]
    need(initialized == 1 and 1 <= threshold <= count <= 11, "invalid multisig threshold/state")
    signers = [b58encode(raw[3+i*32:35+i*32]) for i in range(count)]
    need(len(set(signers)) == count, "duplicate signer threshold requires unsupported execution analysis")
    return {"kind": "spl_multisig", "address": address, "program": account["owner"],
            "threshold": threshold, "signer_count": count, "signers": signers,
            "data_sha256": sha(raw), "subject_linkage": "requires_observed_authority_edge",
            "timelock": "not_in_base_layout", "configuration": "fixed_base_signer_configuration"}
