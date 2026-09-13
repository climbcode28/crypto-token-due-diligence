"""Position census for concentrated pools: which accounts hold a pool's liquidity, ranked into bounded leads.

One filtered program-account read per pool (dataSize plus a memcmp on the pool key, sliced to the ranking fields)
names the pool's fixed-layout positions at one context slot. The largest few become leads for the existing position
sample, which decodes each lead in full with its dependencies; the census weight only orders leads and is never
principal. Expanded or unknown layouts do not match the filter and stay a stated gap."""
import base64
from solana_common import need, pubkey, b58encode
from solana_presets import read, settings
from solana_wire import validate_response
from solana_accounts import ratio
from adapters.binary import discriminator
from adapters.raydium_clmm import MIN_TICK, MAX_TICK

VERSION = '1.1.0'
LEAD_CAP = 4
# Fixed layouts: account size, where the pool key sits, the slice that keeps the ranking field, and how to rank.
LAYOUTS = {
    'raydium_clmm': {'size': 281, 'pool_offset': 41, 'slice': 97, 'ranking': 'liquidity_u128_at_81', 'account': 'PersonalPositionState'},
    'meteora_dlmm': {'size': 8120, 'pool_offset': 8, 'slice': 1192, 'ranking': 'summed_bin_shares_u128_from_72', 'account': 'PositionV2'},
}


def census_read(adapter_id, pool, *, name='positions'):
    """The single bounded census read for one pool; refused adapters have no fixed position layout to count."""
    from adapters import pool_adapter
    need(adapter_id in LAYOUTS, 'position census unsupported for ' + str(adapter_id))
    layout = LAYOUTS[adapter_id]
    return read(name, 'getProgramAccounts', [pool_adapter(adapter_id).PROGRAM, {**settings(), 'withContext': True,
        'dataSlice': {'offset': 0, 'length': layout['slice']},
        'filters': [{'dataSize': layout['size']}, {'memcmp': {'offset': layout['pool_offset'], 'bytes': pubkey(pool)}}]}])


def _weight(adapter_id, raw):
    if adapter_id == 'raydium_clmm':
        return int.from_bytes(raw[81:97], 'little'), {'position_mint': b58encode(raw[9:41]),
            'lower_tick': int.from_bytes(raw[73:77], 'little', signed=True), 'upper_tick': int.from_bytes(raw[77:81], 'little', signed=True)}
    return sum(int.from_bytes(raw[72+16*i:88+16*i], 'little') for i in range(70)), {'spending_owner': b58encode(raw[40:72])}


def sampled_share(leads, total):
    """The share of counted ranking weight the given leads carry; recompute it whenever leads are dropped."""
    total = int(total)
    return ratio(sum(int(l['weight']) for l in leads), total) if total else None


def census_leads(adapter_id, pool, packet, *, cap=LEAD_CAP):
    """Ranked leads and a census summary from one successful census packet bound to this pool."""
    need(adapter_id in LAYOUTS, 'position census unsupported for ' + str(adapter_id))
    need(packet.get('status') == 'ok', 'census read unsuccessful')
    request = packet['request']
    need(request['method'] == 'getProgramAccounts' and request['params'][1]['filters'][1]['memcmp']['bytes'] == pubkey(pool)
         and request['params'][1]['filters'][0]['dataSize'] == LAYOUTS[adapter_id]['size'], 'census request is not this pool census')
    checked = validate_response(request, packet['response'])
    need(checked['status'] == 'ok', 'census response invalid')
    rows = [];other_layouts = 0;invalid_rows = 0;expected = discriminator(LAYOUTS[adapter_id]['account'])
    for address, item in zip(checked['addresses'], checked['result']['value']):
        raw = base64.b64decode(item['account']['data'][0], validate=True)
        if raw[:8] != expected:
            other_layouts += 1;continue  # same size and pool key, another account type: not a position
        weight, extra = _weight(adapter_id, raw)
        if adapter_id == 'raydium_clmm' and not (MIN_TICK <= extra['lower_tick'] < extra['upper_tick'] <= MAX_TICK):
            invalid_rows += 1;continue  # an out-of-range tick pair cannot plan a tick array; it stays a counted gap, never a lead
        rows.append({'position': address, 'weight': weight, **extra})
    rows.sort(key=lambda r: (-r['weight'], r['position']))
    active = [r for r in rows if r['weight'] > 0]
    total = sum(r['weight'] for r in active)
    chosen = active[:cap]
    leads = [{'position': r['position'], 'kind': 'census', 'evidence': [request['id']], 'weight': str(r['weight']), **{k: v for k, v in r.items() if k in ('position_mint', 'spending_owner', 'lower_tick', 'upper_tick')}} for r in chosen]
    summary = {'read': request['id'], 'adapter': adapter_id, 'pool': pubkey(pool), 'context_slot': checked['context_slot'],
               'positions_counted': len(rows), 'positions_with_liquidity': len(active), 'other_layouts_skipped': other_layouts, 'invalid_rows_skipped': invalid_rows, 'ranking': LAYOUTS[adapter_id]['ranking'],
               'sampled': len(leads), 'weight_total': str(total), 'sampled_weight_share': sampled_share(leads, total),
               'scope': 'fixed-layout positions matching the pool filter at the census slot; expanded or unknown layouts are not counted; '
                        'weights rank leads and are not principal or ownership'}
    return leads, summary
