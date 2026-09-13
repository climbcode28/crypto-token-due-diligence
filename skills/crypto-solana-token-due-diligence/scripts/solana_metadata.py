"""Metaplex Token Metadata (v1) for a legacy SPL mint: name, symbol, URI, update authority and creators.

Read-only decode of the on-chain account bound to the exact mint; URI content and off-chain identity are
never fetched or inferred here. The update authority and verified creators become attribution leads that the
coordinator's creator_history preset can sample; they are keys, not people."""
from solana_common import need, b58encode, base58_bytes, pubkey, sha
from solana_addresses import find_program_address
from adapters.binary import Reader, raw_account

VERSION = '1.0.0'
PROGRAM = 'metaqbxxUerdq28cj1RbAWkYQm3ybzjb6a8bt518x1s'
KEY_METADATA_V1 = 4
NAME_BOUND, SYMBOL_BOUND, URI_BOUND, CREATOR_BOUND = 32, 10, 200, 5
# Shared launchpad update authorities: they administer every token minted through the platform and never identify a
# creator. pump.fun's key was read from two live pump.fun token metadata accounts on 2026-09-13.
PLATFORM_UPDATE_AUTHORITIES = {'TSLvdd1pWpHVjahSpsvCXUbgwsL3JAcvokwaKt1eokM': 'pump.fun'}
SYSTEM_PROGRAM = '11111111111111111111111111111111'


def attributable(address):
    """A key that can be attributed to this token: set, not the system program (an unset field), not a shared launchpad authority."""
    return bool(address) and address != SYSTEM_PROGRAM and address not in PLATFORM_UPDATE_AUTHORITIES


def metadata_address(mint):
    """The metadata PDA: seeds 'metadata', program, mint."""
    return find_program_address([b'metadata', base58_bytes(PROGRAM, 32), base58_bytes(pubkey(mint), 32)], PROGRAM)[0]


def _string(reader, bound, label):
    size = reader.integer(4)
    need(size <= bound, 'metadata ' + label + ' exceeds its on-chain bound')
    raw = reader.take(size)
    try:
        text = raw.decode('utf-8')
    except UnicodeDecodeError:
        raise ValueError('metadata ' + label + ' is not UTF-8') from None
    return text.rstrip('\x00')


def decode_metadata(address, account, mint):
    """Decode a Metadata account at `address` for `mint`; fields after is_mutable are hashed, not interpreted."""
    mint = pubkey(mint)
    need(pubkey(address) == metadata_address(mint), 'metadata PDA does not belong to this mint')
    raw = raw_account(account, PROGRAM)
    reader = Reader(raw)
    key = reader.integer(1)
    need(key == KEY_METADATA_V1, 'unsupported metadata account key ' + str(key))
    update_authority = reader.key()
    need(reader.key() == mint, 'metadata mint mismatch')
    name = _string(reader, NAME_BOUND, 'name')
    symbol = _string(reader, SYMBOL_BOUND, 'symbol')
    uri = _string(reader, URI_BOUND, 'uri')
    seller_fee_basis_points = reader.integer(2)
    tag = reader.integer(1)
    need(tag in (0, 1), 'invalid creators option')
    creators = []
    if tag:
        count = reader.integer(4)
        need(count <= CREATOR_BOUND, 'creators exceed the on-chain bound')
        for _ in range(count):
            creator = reader.key()
            verified, share = reader.integer(1), reader.integer(1)
            need(verified in (0, 1) and share <= 100, 'invalid creator entry')
            creators.append({'address': creator, 'verified': bool(verified), 'share': share})
        need(not creators or sum(c['share'] for c in creators) == 100, 'creator shares do not total 100')
    primary_sale_happened = reader.integer(1)
    is_mutable = reader.integer(1)
    need(primary_sale_happened in (0, 1) and is_mutable in (0, 1), 'invalid metadata flags')
    trailing = raw[reader.offset:]
    return {'layout': 'metaplex_metadata_v1', 'program': PROGRAM, 'address': pubkey(address), 'mint': mint,
            'update_authority': update_authority, 'update_authority_platform': PLATFORM_UPDATE_AUTHORITIES.get(update_authority),
            'name': name, 'symbol': symbol, 'uri': uri,
            'seller_fee_basis_points': seller_fee_basis_points, 'creators': creators,
            'verified_creators': [c['address'] for c in creators if c['verified']],
            'primary_sale_happened': bool(primary_sale_happened), 'is_mutable': bool(is_mutable),
            'trailing_bytes': len(trailing), 'trailing_sha256': sha(trailing),
            'scope': 'on-chain metadata fields only; the URI is recorded as text, its content is not fetched, and no human identity is inferred'}


def attribution_leads(metadata):
    """Keys the metadata attributes to the token, in order: update authority, then verified creators. Keys, not people.
    A shared launchpad authority is skipped: it administers every token on that platform and attributes nothing."""
    leads = []
    for address, basis in [(metadata['update_authority'], 'metaplex_update_authority')] + [(a, 'metaplex_verified_creator') for a in metadata['verified_creators']]:
        if attributable(address) and address not in {l['address'] for l in leads}:
            leads.append({'address': address, 'basis': basis})
    return leads
