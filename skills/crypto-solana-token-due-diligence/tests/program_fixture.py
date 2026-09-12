"""Synthetic loader/controller layouts, derived from pinned interface fields."""
import base64
import struct
from solana_common import base58_bytes, b58encode
from solana_addresses import find_program_address
from solana_programs import UPGRADEABLE
from solana_presets import settings
from adapters.binary import discriminator
from adapters import squads_v4
from solana_fixture import KEY, OTHER, account, request, response

PROGRAM_KEY = b58encode(bytes([10])*32)


def packet(address, value, name="observation", *, sliced=None, start=1, slot=100):
    config = settings()
    if sliced is not None:
        config["dataSlice"] = {"offset": 0, "length": sliced}
        raw = base64.b64decode(value["data"][0])
        value = {**value, "data": [base64.b64encode(raw[:sliced]).decode(), "base64"]}
    req = request("getAccountInfo", [address, config], name)
    return {"request": req, "response": response(req, {"context": {"slot": slot}, "value": value}),
            "status": "ok", "started_at": start, "completed_at": start+.1}


def program(authority=OTHER, *, code=b"\x7fELFsynthetic bytes", sliced=False, start=1):
    pd = find_program_address([base58_bytes(PROGRAM_KEY, 32)], UPGRADEABLE)[0]
    program_account = {**account(struct.pack("<I", 2)+base58_bytes(pd, 32)), "owner": UPGRADEABLE, "executable": True}
    metadata = struct.pack("<IQ", 3, 50)+(b"\0"+bytes(32) if authority is None else b"\1"+base58_bytes(authority, 32))
    data_account = {**account(metadata+code), "owner": UPGRADEABLE}
    suffix = "" if start == 1 else "-"+str(int(start))
    return PROGRAM_KEY, pd, packet(PROGRAM_KEY, program_account, "program"+suffix, start=start), packet(pd, data_account, "programdata"+suffix, sliced=45 if sliced else None, start=start+.2)


def squads(*, config_authority=None, threshold=2, masks=(7, 7, 7), rent_collector=None, create_seed=20):
    create = b58encode(bytes([create_seed])*32)
    address, bump = find_program_address([b"multisig", b"multisig", base58_bytes(create, 32)], squads_v4.PROGRAM)
    raw = discriminator("Multisig")+base58_bytes(create, 32)+base58_bytes(config_authority or "1"*32, 32)
    raw += struct.pack("<HIQQ", threshold, 3600, 20, 10)
    raw += b"\1"+base58_bytes(rent_collector, 32) if rent_collector else b"\0"
    raw += bytes([bump])+struct.pack("<I", len(masks))
    raw += b"".join(bytes([i+2])*32+bytes([mask]) for i, mask in enumerate(masks))
    raw += bytes(0 if rent_collector else 32)
    return address, {**account(raw), "owner": squads_v4.PROGRAM}


def spending(multisig, *, outsider=None):
    create = bytes([21])*32
    address, bump = find_program_address([b"multisig", base58_bytes(multisig["address"], 32), b"spending_limit", create], squads_v4.PROGRAM)
    raw = discriminator("SpendingLimit")+base58_bytes(multisig["address"], 32)+create+b"\2"+base58_bytes(KEY, 32)
    raw += struct.pack("<QBQqB", 1000, 1, 300, 1234, bump)
    raw += struct.pack("<I", 1)+base58_bytes(outsider or b58encode(bytes([22])*32), 32)+struct.pack("<I", 0)
    return address, {**account(raw), "owner": squads_v4.PROGRAM}
