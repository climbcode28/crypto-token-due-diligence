"""Small, strict Solana identity and mint decoders. Python standard library only."""
import base64
import hashlib
import json
from pathlib import Path
import struct

ENGINE_VERSION = "1.0.0"
ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
TOKEN_PROGRAM = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
TOKEN_2022 = "TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb"


def need(condition, message):
    if not condition:
        raise ValueError(message)


def b58encode(raw):
    number, out = int.from_bytes(raw, "big"), ""
    while number:
        number, remainder = divmod(number, 58)
        out = ALPHABET[remainder] + out
    return "1" * (len(raw) - len(raw.lstrip(b"\0"))) + out


def pubkey(value):
    need(isinstance(value, str) and 32 <= len(value) <= 44, "invalid public key")
    number = 0
    for char in value:
        need(char in ALPHABET, "invalid base58")
        number = number * 58 + ALPHABET.index(char)
    raw = b"\0" * (len(value) - len(value.lstrip("1")))
    raw += number.to_bytes((number.bit_length() + 7) // 8, "big")
    need(len(raw) == 32 and b58encode(raw) == value, "public key must encode 32 bytes")
    return value  # Case sensitive: never normalize Solana public keys.


def base58_bytes(value, size):
    """Canonical bounded base58 decoding; keys and signatures have different sizes."""
    need(type(size) is int and 1 <= size <= 128, "invalid decoded size")
    need(isinstance(value, str) and size <= len(value) <= (size*138//100+1), "invalid base58 length")
    number = 0
    for char in value:
        need(char in ALPHABET, "invalid base58")
        number = number*58 + ALPHABET.index(char)
    raw = bytes(len(value)-len(value.lstrip("1"))) + number.to_bytes((number.bit_length()+7)//8, "big")
    need(len(raw) == size and b58encode(raw) == value, "noncanonical base58 or wrong size")
    return raw


def signature(value):
    base58_bytes(value, 64)
    return value


def natural(value):
    need(type(value) is int and 0 <= value < 2**64, "invalid unsigned integer")
    return value


def target_identity(target):
    need(target.get("family") == "solana", "not a Solana target")
    return {"family": "solana", "genesis_hash": pubkey(target["genesis_hash"]),
            "mint": pubkey(target["mint"])}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def write_new(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x") as handle:
        json.dump(obj, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")


def optional_key(raw):
    need(len(raw) == 32, "invalid optional key")
    return b58encode(raw) if any(raw) else None


def coption_key(raw):
    need(len(raw) == 36, "invalid COption")
    tag = int.from_bytes(raw[:4], "little")
    need(tag in (0, 1), "invalid COption discriminator")
    # A present all-zero key is still Some(pubkey), not revoked authority.
    return b58encode(raw[4:]) if tag else None


def extension(kind, raw):
    """Decode a deliberately bounded set; preserve everything else as unknown."""
    supported = {1: ("transfer_fee_config", 108), 3: ("mint_close_authority", 32),
                 6: ("default_account_state", 1), 9: ("non_transferable", 0),
                 12: ("permanent_delegate", 32), 14: ("transfer_hook", 64),
                 26: ("pausable", 33)}
    row = {"type": kind, "length": len(raw), "sha256": sha(raw), "decoded": False}
    if kind not in supported:
        return row
    name, size = supported[kind]
    need(len(raw) == size, "invalid extension length")
    row.update(name=name, decoded=True)
    if kind in (3, 12):
        row["authority"] = optional_key(raw)
    elif kind == 14:
        row.update(authority=optional_key(raw[:32]), program=optional_key(raw[32:]))
    elif kind == 6:
        need(raw[0] in (1, 2), "invalid initialized default account state")
        row["state"] = "frozen" if raw[0] == 2 else "initialized"
    elif kind == 26:
        need(raw[32] in (0, 1), "invalid pause flag")
        row.update(authority=optional_key(raw[:32]), paused=bool(raw[32]))
    elif kind == 1:
        row.update(config_authority=optional_key(raw[:32]),
                   withdraw_authority=optional_key(raw[32:64]),
                   withheld_atomic=str(int.from_bytes(raw[64:72], "little")))
        for label, start in (("older", 72), ("newer", 90)):
            epoch, cap, bps = struct.unpack("<QQH", raw[start:start+18])
            need(bps <= 10000, "invalid fee basis points")
            row[label] = {"epoch": epoch, "maximum_fee_atomic": str(cap), "basis_points": bps}
        # Selecting an active fee requires epoch evidence; don't invent it here.
    return row


def decode_mint(account):
    need(isinstance(account, dict) and account.get("executable") is False, "not a data account")
    owner = account.get("owner")
    need(owner in (TOKEN_PROGRAM, TOKEN_2022), "unsupported mint owner program")
    data = account.get("data")
    need(isinstance(data, list) and len(data) == 2 and data[1] == "base64", "raw base64 required")
    raw = base64.b64decode(data[0], validate=True)
    need(len(raw) >= 82 and len(raw) != 355, "invalid mint length")
    need(raw[45] == 1, "mint not initialized")
    if "space" in account:
        need(type(account["space"]) is int and account["space"] == len(raw), "space mismatch")
    row = {"program": owner, "data_sha256": sha(raw),
           "mint_authority": coption_key(raw[:36]),
           "supply_atomic": str(int.from_bytes(raw[36:44], "little")),
           "decimals": raw[44], "freeze_authority": coption_key(raw[46:82]),
           "extensions": []}
    if owner == TOKEN_PROGRAM:
        need(len(raw) == 82, "legacy mint has unexpected data")
    elif len(raw) != 82:
        need(len(raw) >= 166 and not any(raw[82:165]) and raw[165] == 1,
             "invalid extended mint padding or account type")
        offset, seen = 166, set()
        while offset < len(raw):
            if not any(raw[offset:]):
                break  # Zero padding, including the multisig-length avoidance padding.
            need(len(raw) - offset >= 4, "truncated TLV")
            kind, size = struct.unpack("<HH", raw[offset:offset+4])
            need(kind != 0 and kind not in seen, "duplicate or invalid extension")
            need(kind not in {2, 5, 7, 8, 11, 13, 15, 17, 27}, "account extension on mint")
            seen.add(kind)
            offset += 4
            need(offset + size <= len(raw), "truncated extension")
            row["extensions"].append(extension(kind, raw[offset:offset+size]))
            offset += size
    row["unknown_extensions"] = [x["type"] for x in row["extensions"] if not x["decoded"]]
    return row
