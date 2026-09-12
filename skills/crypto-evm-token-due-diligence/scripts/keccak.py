"""Ethereum Keccak-256 in the standard library. Not NIST SHA3-256 (different padding).

Deterministic hashing of a caller-supplied signature is not a signature guess: the
signature text must come from a verified ABI or specification. This module performs no
I/O and has no third-party dependencies.
"""
import re

_RC = (
    0x0000000000000001, 0x0000000000008082, 0x800000000000808A, 0x8000000080008000,
    0x000000000000808B, 0x0000000080000001, 0x8000000080008081, 0x8000000000008009,
    0x000000000000008A, 0x0000000000000088, 0x0000000080008009, 0x000000008000000A,
    0x000000008000808B, 0x800000000000008B, 0x8000000000008089, 0x8000000000008003,
    0x8000000000008002, 0x8000000000000080, 0x000000000000800A, 0x800000008000000A,
    0x8000000080008081, 0x8000000000008080, 0x0000000080000001, 0x8000000080008008,
)
_ROT = (
    (0, 36, 3, 41, 18), (1, 44, 10, 45, 2), (62, 6, 43, 15, 61), (28, 55, 25, 21, 56), (27, 20, 39, 8, 14),
)
_MASK = (1 << 64) - 1
_RATE = 136  # bytes; 1088-bit rate for a 256-bit digest


def _rol(value, shift):
    shift %= 64
    return ((value << shift) | (value >> (64 - shift))) & _MASK if shift else value


def _keccak_f(state):
    for rc in _RC:
        # theta
        c = [state[x] ^ state[x + 5] ^ state[x + 10] ^ state[x + 15] ^ state[x + 20] for x in range(5)]
        d = [c[(x - 1) % 5] ^ _rol(c[(x + 1) % 5], 1) for x in range(5)]
        state = [state[i] ^ d[i % 5] for i in range(25)]
        # rho and pi
        b = [0] * 25
        for x in range(5):
            for y in range(5):
                b[y + 5 * ((2 * x + 3 * y) % 5)] = _rol(state[x + 5 * y], _ROT[x][y])
        # chi
        state = [b[i] ^ ((~b[(i % 5 + 1) % 5 + 5 * (i // 5)]) & b[(i % 5 + 2) % 5 + 5 * (i // 5)]) for i in range(25)]
        # iota
        state[0] ^= rc
    return state


def keccak256(data):
    """Return the 32-byte Keccak-256 digest of ``data`` (bytes)."""
    if not isinstance(data, (bytes, bytearray)):
        raise TypeError("keccak256 requires bytes")
    padded = bytearray(data)
    padded.append(0x01)  # Keccak padding; SHA3 would use 0x06.
    while len(padded) % _RATE:
        padded.append(0x00)
    padded[-1] |= 0x80
    state = [0] * 25
    for offset in range(0, len(padded), _RATE):
        block = padded[offset:offset + _RATE]
        for i in range(_RATE // 8):
            state[i] ^= int.from_bytes(block[8 * i:8 * i + 8], "little")
        state = _keccak_f(state)
    out = b"".join(lane.to_bytes(8, "little") for lane in state[:4])
    return out[:32]


def keccak256_hex(data):
    return "0x" + keccak256(data).hex()


_TYPE = re.compile(r"(address|bool|string|bytes|bytes(?:[1-9]|[12][0-9]|3[0-2])|u?int(?:8|16|24|32|40|48|56|64|72|80|88|96|104|112|120|128|136|144|152|160|168|176|184|192|200|208|216|224|232|240|248|256)|u?fixed[0-9]+x[0-9]+)(\[[0-9]*\])*")


def canonical_signature(signature):
    """Reject anything that is not a canonical ABI signature so typos or aliases cannot become selectors."""
    if not isinstance(signature, str) or " " in signature or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*\([A-Za-z0-9_\[\],()]*\)", signature):
        raise ValueError("signature must be name(type,type,...) without spaces")
    inner = signature[signature.index("(") + 1:-1]
    if inner:
        # Flatten tuples for the type check; commas separate types at every depth.
        for part in re.sub(r"[()]", ",", inner).split(","):
            if part and not _TYPE.fullmatch(part):
                raise ValueError("non-canonical ABI type in signature: " + part + " (use uint256/int256, not uint/int)")
        if ",," in inner or inner.endswith(",") or inner.startswith(",") or "(," in inner or ",)" in inner:
            raise ValueError("empty type slot in signature")
    depth = 0
    for char in signature[signature.index("("):]:
        depth += (char == "(") - (char == ")")
        if depth < 0:
            raise ValueError("unbalanced parentheses in signature")
    if depth != 0:
        raise ValueError("unbalanced parentheses in signature")
    return signature


def selector(signature):
    """Four-byte function selector as 8 lowercase hex characters, no 0x prefix."""
    return keccak256(canonical_signature(signature).encode()).hex()[:8]


def topic(signature):
    """Event topic0 as a 0x-prefixed 32-byte hex string."""
    return keccak256_hex(canonical_signature(signature).encode())


def pool_id(currency0, currency1, fee, tick_spacing, hooks):
    """Uniswap v4 PoolId = keccak256(abi.encode(PoolKey)); inputs are checked, not discovered."""
    def word_address(value):
        if not isinstance(value, str) or not re.fullmatch(r"0x[0-9a-fA-F]{40}", value):
            raise ValueError("pool key currency/hooks must be 20-byte hex")
        return "0" * 24 + value[2:].lower()
    if type(fee) is not int or not 0 <= fee < 2 ** 24:
        raise ValueError("fee must be uint24")
    if type(tick_spacing) is not int or not -(2 ** 23) <= tick_spacing < 2 ** 23:
        raise ValueError("tick spacing must be int24")
    if int(currency0, 16) >= int(currency1, 16):
        raise ValueError("pool key currencies must be sorted: currency0 < currency1")
    encoded = (word_address(currency0) + word_address(currency1) + format(fee, "064x")
               + format(tick_spacing % (1 << 256), "064x") + word_address(hooks))
    return keccak256_hex(bytes.fromhex(encoded))


if __name__ == "__main__":
    import sys
    print(keccak256_hex(sys.stdin.buffer.read()))
