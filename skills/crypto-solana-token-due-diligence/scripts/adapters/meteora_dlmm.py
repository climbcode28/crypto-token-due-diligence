"""DLMM fixed PositionV2/bin observations. No vault-based swap/depth approximation."""
import sys
from solana_common import need, base58_bytes, b58encode
from solana_addresses import find_program_address
from solana_accounts import ratio
from adapters.base import capability
from adapters.binary import raw_account, discriminator
from adapters import meteora_common as common

PROGRAM = 'LBUZKhRxPF3XUpBCjp4YzTKgLccjZhTSDM9YuVaPwxo'
REVISION = '576919e3e4368e542c402f000b4264724f7f23ec'
BIN_ARRAY_MAX_VERSION = 3
CAPABILITY = capability('meteora_dlmm', PROGRAM, REVISION, model='per_bin_position_shares',
    dependencies=['pair_with_embedded_fees', 'mints', 'vaults', 'PositionV2', 'covered_bin_arrays'])
CAPABILITY.update(position_variants=['fixed_PositionV2_70_bins'],
    unsupported=['expanded_positions', 'DAMM_v1', 'DAMM_v2', 'DBC', 'limit_order_ownership', 'swap_traversal'],
    locks=['observed_lock_release_point_only'])


def number(raw, offset, size=8, signed=False):
    return int.from_bytes(raw[offset:offset+size], 'little', signed=signed)


def layout(value, name, length):
    raw = raw_account(value, PROGRAM)
    need(not value['executable'] and len(raw) == length and raw[:8] == discriminator(name), 'unsupported DLMM '+name+' layout')
    return raw


def decode_pool(address, value):
    raw = layout(value, 'LbPair', 904)
    mints = [b58encode(raw[o:o+32]) for o in (88, 120)]
    vaults = [b58encode(raw[o:o+32]) for o in (152, 184)]
    need(mints[0] != mints[1], 'duplicate DLMM mints')
    for mint, vault in zip(mints, vaults):
        need(find_program_address([base58_bytes(address,32), base58_bytes(mint,32)], PROGRAM)[0] == vault, 'DLMM reserve PDA mismatch')
    cfg = {k: number(raw, o, size, signed) for k,o,size,signed in [
        ('base_factor',8,2,False), ('filter_period',10,2,False), ('decay_period',12,2,False),
        ('reduction_factor',14,2,False), ('variable_fee_control',16,4,False),
        ('max_volatility_accumulator',20,4,False), ('min_bin_id',24,4,True), ('max_bin_id',28,4,True),
        ('protocol_share_bps',32,2,False), ('base_fee_power_factor',34,1,False), ('function_type',35,1,False),
        ('collect_fee_mode',36,1,False), ('volatility_accumulator',40,4,False), ('volatility_reference',44,4,False),
        ('index_reference',48,4,True), ('last_update_timestamp',56,8,True)]}
    step, active, gaps = number(raw,80,2), number(raw,76,4,True), []
    # Principal MM balances precede the reward/limit-order union in both known versions.
    if not (raw[882] in (0,1) and not any(raw[883:]) and raw[75] < 4 and raw[82] < 2 and raw[86] < 2 and raw[87] < 2):
        gaps.append('unsupported_DLMM_version_or_control_configuration')
    if not (1 <= step <= 400 and cfg['min_bin_id'] <= active <= cfg['max_bin_id'] and
            cfg['function_type'] <= 2 and cfg['collect_fee_mode'] <= 1 and cfg['reduction_factor'] <= 10000 and
            cfg['protocol_share_bps'] <= 10000 and cfg['base_fee_power_factor'] <= 10 and
            cfg['filter_period'] <= cfg['decay_period'] and cfg['volatility_accumulator'] <= cfg['max_volatility_accumulator']):
        gaps.append('invalid_DLMM_embedded_fee_configuration')
    else:
        base = cfg['base_factor'] * step * 10 * 10**cfg['base_fee_power_factor']
        if base > 100000000: gaps.append('DLMM_base_fee_exceeds_pinned_cap')
        cfg['base_fee_numerator'] = str(base)
    cfg.update(fee_denominator='1000000000', fee_cap_numerator='100000000',
               scope='captured parameters; dynamic fee evolves per traversed bin and Clock')
    return {'mints': mints, 'vaults': vaults, 'authority': address,
            'token_programs': common.token_programs(raw[880:882]), 'bin_step': step, 'active_id': active,
            'status': raw[82], 'pair_type': raw[75], 'version': raw[882], 'activation_type': raw[86],
            'activation_point': str(number(raw,816)), 'creator': b58encode(raw[848:880]),
            'creator_pool_on_off_control': raw[87], 'configuration': cfg, 'configuration_gaps': gaps,
            'protocol_fees': [number(raw,216), number(raw,224)]}


def decode_position(address, value, pool, lead=None):
    raw = layout(value, 'PositionV2', 8120)
    need(b58encode(raw[8:40]) == pool, 'DLMM position belongs to another pair')
    lower, upper = number(raw,7912,4,True), number(raw,7916,4,True)
    need(0 <= upper-lower < 70 and raw[8033] in (0,1) and not any(raw[8035:]), 'expanded/future DLMM position unsupported')
    shares = [number(raw,72+16*i,16) for i in range(70)]
    need(not any(shares[upper-lower+1:]), 'nonzero shares outside position range')
    return {'pool': pool, 'spending_owner': b58encode(raw[40:72]), 'lower_bin_id': lower, 'upper_bin_id': upper,
            'shares': shares[:upper-lower+1], 'operator': b58encode(raw[7960:7992]),
            'fee_owner': b58encode(raw[8001:8033]), 'lock_release_point': str(number(raw,7992)),
            'permissionless_operation_bits': raw[8034], 'version': raw[8033],
            'stored_pending_fees_atomic': [str(sum(number(raw,4552+48*i+offset) for i in range(70))) for offset in (32,40)],
            'claimed_fees_atomic': [str(number(raw,7928)), str(number(raw,7936))],
            'current_uncollected_fees_atomic': None, 'rewards': 'stored/accruing rewards separate from principal'}


def bin_array_address(pool, bin_id):
    return find_program_address([b'bin_array',base58_bytes(pool,32),(bin_id//70).to_bytes(8,'little',signed=True)],PROGRAM)[0]


def decode_bin(address, value, pool, bin_id):
    raw = layout(value, 'BinArray', 10136)
    need(number(raw,8,8,True) == bin_id//70 and b58encode(raw[24:56]) == pool and
         address == bin_array_address(pool,bin_id), 'DLMM bin array relationship mismatch')
    # Version tags upstream releases (3 = limit orders, SDK BIN_ARRAY_DEFAULT_VERSION); the 144-byte Bin keeps
    # amount_x, amount_y, price and liquidity_supply at the same offsets in both pinned IDL revisions (ce0e6afe, 576919e3).
    need(raw[16] <= BIN_ARRAY_MAX_VERSION and not any(raw[17:24]), 'unsupported bin array version')
    start = 56+(bin_id%70)*144
    return {'id': bin_id, 'amounts': [number(raw,start),number(raw,start+8)],
            'price_x64': number(raw,start+16,16), 'liquidity_supply': number(raw,start+32,16)}


def analyze(target, pool, observations, *, positions=None):
    positions = [] if positions is None else positions
    sample, state, core, valid = common.begin(sys.modules[__name__], target, pool, observations, positions)
    bin_totals = {}
    for lead in positions or []:
        row = common.row(sample, lead)
        try:
            pos = decode_position(lead['position'], sample.account(lead['position']), pool)
            row.update({k:v for k,v in pos.items() if k != 'shares'}, bins=[], dependencies=[*core,lead['position']])
            row['custody'] = {'spending_owner':pos['spending_owner'], 'operator':pos['operator'], 'fee_owner':pos['fee_owner'],
                'representation':'program_position_account', 'beneficial_owner':None,
                'operator_permissions':'unresolved; fee owner is not inferred to own principal'}
            row['controllers'] = {k:pos[k] for k in ('spending_owner','operator','fee_owner') if pos[k] != '11111111111111111111111111111111'}
            need(valid, 'verified embedded configuration/mints/vaults required for DLMM principal')
            need(state['configuration']['min_bin_id'] <= pos['lower_bin_id'] <= pos['upper_bin_id'] <= state['configuration']['max_bin_id'], 'position outside configured bin bounds')
            amounts = [0,0]
            for offset, share in enumerate(pos['shares']):
                bin_id = pos['lower_bin_id']+offset
                address = bin_array_address(pool, bin_id)
                b = decode_bin(address, sample.account(address), pool, bin_id)
                sample.same_bank([*core, lead['position'], address])
                row['dependencies'].append(address)
                supply = b['liquidity_supply']
                need(share <= supply and (supply > 0 or share == 0), 'position share exceeds bin liquidity')
                value = [share*a//supply if supply else 0 for a in b['amounts']]
                row['bins'].append({'bin_id':bin_id, 'array':address, 'position_share':ratio(share,supply),
                    'share_atomic':str(share), 'supply_atomic':str(supply), 'principal_atomic':list(map(str,value))})
                bin_totals.setdefault(bin_id,[]).append((row,share,supply))
                amounts = [a+b for a,b in zip(amounts,value)]
            need(all(a < 2**64 for a in amounts), 'position token amount overflow')
            row['principal'] = {'amounts_atomic':list(map(str,amounts)), 'rounding':'floor per bin',
                'scope':'gross market-making position only; fees, rewards, limit orders and transfer fees excluded'}
            try:
                current = common.point(sample,row['dependencies'],state['activation_type'])
                row['dependencies'].append(common.CLOCK)
                row['lock_release_reached'] = current >= int(pos['lock_release_point'])
                row['lock_scope'] = 'observed release point only; operator/program/control conditions remain separate'
            except ValueError as exc:
                row['lock_release_reached'] = None
                row['gaps'].append(str(exc))
        except ValueError as exc:
            row['gaps'].append(str(exc))
    for rows in bin_totals.values():
        if sum(r[1] for r in rows) > rows[0][2]:
            for row,_,_ in rows:
                row['principal'] = None
                row['gaps'].append('sampled_position_shares_exceed_bin_supply')
    # A resolved sample is observed; depth limits are scope, not a missing dependency.
    sample.result.setdefault('limitations',[]).append('pool_depth_and_total_principal_not_inferred_from_sampled_bins_or_vaults')
    return common.finish(sample)
