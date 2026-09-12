"""Small bounded readers for fixed integers and Borsh vectors."""
import base64
import hashlib
from solana_common import need, b58encode
from solana_wire import account as wire_account


def raw_account(account, owner, *, sliced=False):
    wire_account(account, sliced=sliced)
    need(account is not None and account["owner"] == owner, "account owner mismatch")
    return base64.b64decode(account["data"][0], validate=True)


def discriminator(name):
    return hashlib.sha256(("account:"+name).encode()).digest()[:8]


class Reader:
    def __init__(self, raw):
        self.raw, self.offset = raw, 0

    def take(self, count):
        need(type(count) is int and 0 <= count <= len(self.raw)-self.offset, "truncated binary account")
        value = self.raw[self.offset:self.offset+count]
        self.offset += count
        return value

    def integer(self, size, *, signed=False):
        return int.from_bytes(self.take(size), "little", signed=signed)

    def key(self):
        return b58encode(self.take(32))

    def option_key(self):
        tag = self.integer(1)
        need(tag in (0, 1), "invalid Borsh option")
        return self.key() if tag else None

    def vector(self, decoder, *, maximum=256):
        count = self.integer(4)
        need(count <= maximum, "vector exceeds supported bound; no truncated display")
        return [decoder(self) for _ in range(count)]
