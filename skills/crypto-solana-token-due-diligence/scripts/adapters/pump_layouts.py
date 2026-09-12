"""Pinned Pump public IDL field facts, not a runtime IDL loader.

Revision e0687ae9b7e064a0f54efc7297c65eecfbba3a8f (2026-09-12; the creator-fee and
holder-reward upgrade appended a tail group to every account below). Upstream byte hashes in
assets/layout-sources.json. Older embedded cross-program type copies differ;
use each owning program's own IDL only. No downloaded executable code.
"""
from adapters.binary import Reader,raw_account,discriminator
from solana_common import need

FIELDS = {'BondingCurve': [('virtual_token_reserves', 'u64'),
                  ('virtual_quote_reserves', 'u64'),
                  ('real_token_reserves', 'u64'),
                  ('real_quote_reserves', 'u64'),
                  ('token_total_supply', 'u64'),
                  ('complete', 'bool'),
                  ('creator', 'pubkey'),
                  ('is_mayhem_mode', 'bool'),
                  ('is_cashback_coin', 'bool'),
                  ('quote_mint', 'pubkey'),
                  ('creator_fee_bps', 'u64'),
                  ('can_edit_creator_fee', 'bool'),
                  ('is_holder_reward', 'bool')],
 'Global': [('initialized', 'bool'),
            ('authority', 'pubkey'),
            ('fee_recipient', 'pubkey'),
            ('initial_virtual_token_reserves', 'u64'),
            ('initial_virtual_sol_reserves', 'u64'),
            ('initial_real_token_reserves', 'u64'),
            ('token_total_supply', 'u64'),
            ('fee_basis_points', 'u64'),
            ('withdraw_authority', 'pubkey'),
            ('enable_migrate', 'bool'),
            ('pool_migration_fee', 'u64'),
            ('creator_fee_basis_points', 'u64'),
            ('fee_recipients', {'array': ['pubkey', 7]}),
            ('set_creator_authority', 'pubkey'),
            ('admin_set_creator_authority', 'pubkey'),
            ('create_v2_enabled', 'bool'),
            ('whitelist_pda', 'pubkey'),
            ('reserved_fee_recipient', 'pubkey'),
            ('mayhem_mode_enabled', 'bool'),
            ('reserved_fee_recipients', {'array': ['pubkey', 7]}),
            ('is_cashback_enabled', 'bool'),
            ('buyback_fee_recipients', {'array': ['pubkey', 8]}),
            ('buyback_basis_points', 'u64'),
            ('initial_virtual_quote_reserves', 'u64'),
            ('whitelisted_quote_mints', {'array': ['pubkey', 1]}),
            ('creator_fee_configurable', 'bool'),
            ('max_configurable_creator_fee_bps', 'u64'),
            ('holder_reward_claim_authority', 'pubkey'),
            ('is_holder_reward_enabled', 'bool')],
 'GlobalConfig': [('admin', 'pubkey'),
                  ('lp_fee_basis_points', 'u64'),
                  ('protocol_fee_basis_points', 'u64'),
                  ('disable_flags', 'u8'),
                  ('protocol_fee_recipients', {'array': ['pubkey', 8]}),
                  ('coin_creator_fee_basis_points', 'u64'),
                  ('admin_set_coin_creator_authority', 'pubkey'),
                  ('whitelist_pda', 'pubkey'),
                  ('reserved_fee_recipient', 'pubkey'),
                  ('mayhem_mode_enabled', 'bool'),
                  ('reserved_fee_recipients', {'array': ['pubkey', 7]}),
                  ('is_cashback_enabled', 'bool'),
                  ('buyback_fee_recipients', {'array': ['pubkey', 8]}),
                  ('buyback_basis_points', 'u64'),
                  ('boost_authority', 'pubkey'),
                  ('boost_enabled', 'bool'),
                  ('creator_fee_configurable', 'bool'),
                  ('max_configurable_creator_fee_bps', 'u64')],
 'Pool': [('pool_bump', 'u8'),
          ('index', 'u16'),
          ('creator', 'pubkey'),
          ('base_mint', 'pubkey'),
          ('quote_mint', 'pubkey'),
          ('lp_mint', 'pubkey'),
          ('pool_base_token_account', 'pubkey'),
          ('pool_quote_token_account', 'pubkey'),
          ('lp_supply', 'u64'),
          ('coin_creator', 'pubkey'),
          ('is_mayhem_mode', 'bool'),
          ('is_cashback_coin', 'bool'),
          ('virtual_quote_reserves', 'i128'),
          ('creator_fee_bps', 'u64'),
          ('can_edit_creator_fee', 'bool'),
          ('is_holder_reward', 'bool')]}
# Trailing fields appended by the 2026-09 creator-fee/holder-reward upgrade. An account allocated before it lacks
# the whole group: the group is read only when the allocation holds all of it, otherwise every member is absent.
TAIL_GROUP={'BondingCurve':3,'Global':4,'GlobalConfig':2,'Pool':3}
ABSENT={'pubkey':None,'bool':False}


def fixed(account,program,name,*,sizes=None):
    raw=raw_account(account,program)
    need(not account['executable'] and 8<=len(raw)<=4096 and raw[:8]==discriminator(name),'Pump account discriminator/owner/size mismatch')
    if sizes is not None:need(len(raw) in sizes,'unsupported Pump account layout length')
    r=Reader(raw);r.take(8)
    def field(t):
        if t=='pubkey':return r.key()
        if t=='bool':
            v=r.integer(1);need(v in (0,1),'invalid Pump boolean');return bool(v)
        if isinstance(t,dict):return [field(t['array'][0]) for _ in range(t['array'][1])]
        return r.integer(int(t[1:])//8,signed=t.startswith('i'))
    def width(t):return 32 if t=='pubkey' else 1 if t=='bool' else width(t['array'][0])*t['array'][1] if isinstance(t,dict) else int(t[1:])//8
    fields=FIELDS[name];tail=TAIL_GROUP.get(name,0);base,group=fields[:len(fields)-tail],fields[len(fields)-tail:]
    result={k:field(t) for k,t in base}
    if sum(width(t) for _,t in group)<=len(raw)-r.offset:
        start=r.offset;result.update({k:field(t) for k,t in group});result['absent_fields']=[]
        result['tail_group_zero']=not any(raw[start:r.offset])  # all-zero bytes read as defaults; a pre-upgrade allocation looks the same
    else:result.update({k:ABSENT.get(t,0) for k,t in group});result['absent_fields']=[k for k,_ in group];result['tail_group_zero']=None
    result['allocated_padding_bytes']=len(raw)-r.offset
    need(not any(r.take(len(raw)-r.offset)),'unknown Pump reserved layout extension')
    return result
