"""Synthetic Metaplex Metadata v1 account for the fixture mint."""
import struct
from solana_common import base58_bytes
from solana_fixture import account
from solana_metadata import PROGRAM, metadata_address, KEY_METADATA_V1


def borsh_string(text, capacity):
    raw = text.encode('utf-8'); raw = raw + bytes(max(0, capacity-len(raw)))  # over-bound text stays unpadded so the decoder must refuse it
    return struct.pack('<I', len(raw)) + raw


def metadata_account(mint, *, update_authority, creators=(), name='Fixture Token', symbol='FIX', uri='https://example.invalid/meta.json',
                     key=KEY_METADATA_V1, mutable=True, bound_mint=None, trailing=b'\0\0\0\0'):
    raw = bytes([key]) + base58_bytes(update_authority, 32) + base58_bytes(bound_mint or mint, 32)
    raw += borsh_string(name, 32) + borsh_string(symbol, 10) + borsh_string(uri, 200) + struct.pack('<H', 500)
    if creators:
        raw += b'\1' + struct.pack('<I', len(creators)) + b''.join(base58_bytes(a, 32) + bytes([int(v), s]) for a, v, s in creators)
    else:
        raw += b'\0'
    raw += bytes([0, int(mutable)]) + trailing
    return {'address': metadata_address(mint), 'account': {**account(raw), 'owner': PROGRAM}}
