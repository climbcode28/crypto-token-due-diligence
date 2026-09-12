"""Independent decoder of the pinned Squads v4 wire layout and documented PDA links."""
from solana_common import need, pubkey, base58_bytes, sha
from solana_addresses import create_program_address, find_program_address
from adapters.binary import raw_account, Reader, discriminator

PROGRAM = "SQDS4ep65T869zMMBKyuUq6aD6EgTu8psMjkvj52pCf"


def decode(address, account):
    pubkey(address)
    raw = raw_account(account, PROGRAM)
    need(account["executable"] is False, "Squads data account required")
    r = Reader(raw)
    need(r.take(8) == discriminator("Multisig"), "Squads multisig discriminator mismatch")
    create_key, config_authority = r.key(), r.key()
    threshold, timelock, transaction, stale = r.integer(2), r.integer(4), r.integer(8), r.integer(8)
    rent_collector, bump = r.option_key(), r.integer(1)
    members = r.vector(lambda reader: {"key": reader.key(), "permissions": reader.integer(1)})
    keys = [m["key"] for m in members]
    need(keys and len(set(keys)) == len(keys) and keys == sorted(keys, key=lambda k: base58_bytes(k, 32)), "invalid or unsorted Squads members")
    need(all(m["permissions"] < 8 for m in members), "unknown Squads permission bits")
    voters = [m["key"] for m in members if m["permissions"] & 2]
    need(1 <= threshold <= len(voters) and any(m["permissions"] & 1 for m in members) and any(m["permissions"] & 4 for m in members), "invalid Squads threshold/permissions")
    need(stale <= transaction and timelock <= 7776000, "invalid Squads configuration bounds")
    expected = create_program_address([b"multisig", b"multisig", base58_bytes(create_key, 32), bytes([bump])], PROGRAM)
    need(expected == address, "Squads multisig PDA mismatch")
    return {"kind": "squads_v4", "address": address, "program": PROGRAM, "create_key": create_key,
        "threshold": threshold, "members": members, "voters": voters, "time_lock_seconds": timelock,
        "config_authority": None if config_authority == "1"*32 else config_authority,
        "configuration_bypass": config_authority != "1"*32, "rent_collector": rent_collector,
        "transaction_index": str(transaction), "stale_transaction_index": str(stale), "bump": bump,
        "trailing_allocated_bytes": len(raw)-r.offset, "data_sha256": sha(raw),
        "spending_limits": "not_enumerated", "subject_linkage": "requires_observed_vault_or_authority_edge"}


def vault_address(multisig, index):
    need(type(index) is int and 0 <= index <= 255, "invalid vault index")
    return find_program_address([b"multisig", base58_bytes(multisig, 32), b"vault", bytes([index])], PROGRAM)


def verify_vault(subject_authority, multisig, index):
    need(vault_address(multisig["address"], index)[0] == pubkey(subject_authority), "unverified Squads vault relation")
    return {"from": subject_authority, "to": multisig["address"], "role": "squads_vault_controller", "vault_index": index}


def decode_spending_limit(address, account, multisig):
    pubkey(address)
    raw = raw_account(account, PROGRAM)
    need(account["executable"] is False, "spending limit data account required")
    r = Reader(raw)
    need(r.take(8) == discriminator("SpendingLimit"), "spending limit discriminator mismatch")
    parent, create_key, index, mint = r.key(), r.key(), r.integer(1), r.key()
    cap, period, remaining, reset, bump = r.integer(8), r.integer(1), r.integer(8), r.integer(8, signed=True), r.integer(1)
    members, destinations = r.vector(lambda reader: reader.key()), r.vector(lambda reader: reader.key())
    need(parent == multisig["address"] and cap > 0 and remaining <= cap and period < 4, "invalid spending limit relationship/configuration")
    need(members and len(set(members)) == len(members), "invalid spending limit members")
    need(create_program_address([b"multisig", base58_bytes(parent, 32), b"spending_limit", base58_bytes(create_key, 32), bytes([bump])], PROGRAM) == address, "spending limit PDA mismatch")
    return {"kind": "squads_spending_limit", "address": address, "multisig": parent,
        "vault": vault_address(parent, index)[0], "vault_index": index, "mint": mint,
        "asset_kind": "native_sol" if mint == "1"*32 else "token_mint",
        "period": ("one_time", "day", "week", "month")[period], "amount_atomic": str(cap),
        "remaining_amount_atomic": str(remaining), "last_reset": reset, "members": members,
        "destinations": destinations, "destination_restriction": "any" if not destinations else "listed",
        "bypasses_multisig_vote_and_timelock": True,
        "membership_independent_of_multisig": True, "data_sha256": sha(raw),
        "trailing_allocated_bytes": len(raw)-r.offset}
