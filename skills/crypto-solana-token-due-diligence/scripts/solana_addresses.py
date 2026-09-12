"""Bounded PDA/ATA derivation matching the pinned SDK. No signing primitives."""
import hashlib

from solana_common import need, base58_bytes, b58encode, TOKEN_PROGRAM, TOKEN_2022

ASSOCIATED_PROGRAM = "ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL"
P = 2**255-19
D = -121665*pow(121666, P-2, P) % P


def bytes_are_curve_point(raw):
    """Edwards-Y decompression, not signature validity or prime-order validation.

    Dalek reduces the low 255 bits as a field element. Small-order and noncanonical
    compressed representations must also be rejected as PDA candidates.
    """
    need(type(raw) is bytes and len(raw) == 32, "compressed Edwards point requires 32 bytes")
    y = (int.from_bytes(raw, "little") & (2**255-1)) % P
    u, v = (y*y-1) % P, (D*y*y+1) % P
    if v == 0:
        return u == 0
    square = u*pow(v, P-2, P) % P
    return square == 0 or pow(square, (P-1)//2, P) == 1


def _seeds(seeds, maximum=16):
    need(isinstance(seeds, (list, tuple)) and len(seeds) <= maximum, "too many PDA seeds")
    need(all(type(seed) is bytes and len(seed) <= 32 for seed in seeds), "PDA seeds must be bytes of length 0–32")


def create_program_address(seeds, program):
    _seeds(seeds)
    digest = hashlib.sha256(b"".join(seeds)+base58_bytes(program, 32)+b"ProgramDerivedAddress").digest()
    need(not bytes_are_curve_point(digest), "PDA candidate is on curve")
    return b58encode(digest)


def find_program_address(seeds, program):
    _seeds(seeds, 15)
    base58_bytes(program, 32)
    # Match the pinned SDK's 255 attempts (255 down to 1).
    for bump in range(255, 0, -1):
        try:
            return create_program_address([*seeds, bytes([bump])], program), bump
        except ValueError as exc:
            if str(exc) != "PDA candidate is on curve":
                raise
    raise ValueError("no off-curve address in bounded bump search")


def associated_token_address(owner, mint, token_program):
    need(token_program in (TOKEN_PROGRAM, TOKEN_2022), "explicit supported token program required")
    return find_program_address([base58_bytes(owner, 32), base58_bytes(token_program, 32), base58_bytes(mint, 32)], ASSOCIATED_PROGRAM)
