"""Shared range-position evidence processing; protocol layouts/math remain explicit."""
from solana_common import need, pubkey, TOKEN_PROGRAM, TOKEN_2022
from solana_accounts import decode_holding, ratio
from solana_session import label
from adapters.base import Sample
from adapters.concentrated_math import principal, price_tick_consistent


def analyze(module, target, pool, observations, positions):
    need(isinstance(positions, list) and len(positions) <= 6, "position discovery sample exceeds six")
    need(all(isinstance(p, dict) and p.get("evidence") and isinstance(p["evidence"], list) and len(p["evidence"]) <= 8 for p in positions), "captured position discovery leads required")
    need(len({pubkey(p['position']) for p in positions}) == len(positions), "duplicate position lead")
    for lead in positions:
        for evidence in lead['evidence']: label(evidence)
        need(lead.get('kind') in ('explicit', 'indexer', 'transaction', 'account', 'census'), "position discovery kind required")
    sample = Sample(target, pool, observations, module.CAPABILITY)
    state = module.decode_pool(pool, sample.account(pool))
    need(target["mint"] in state["mints"], "target mint not in concentrated pool")
    sample.result.update(state=state, mints=state["mints"], positions=[],
        discovery={"requested_positions": len(positions), "maximum": 6, "coverage": "specific_leads_not_exhaustive", "evidence": sorted({e for p in positions for e in p['evidence']})},
        quote_dependencies="complete traversal arrays, fees/oracle and transfer controls are separately required")
    sample.controls(module.PROGRAM)
    core = [pool, state['config'], *state['mints'], *state['vaults']]
    core_valid = True
    for i in range(2):
        try:
            value = sample.account(state['mints'][i])
            token_program = value['owner']
            sample.mint(state['mints'][i], token_program, state.get('decimals', [None, None])[i])
            sample.vault(state['vaults'][i], state['mints'][i], token_program, pool)
        except ValueError as exc:
            core_valid = False; sample.result['gaps'].append(str(exc))
    try:
        module.config(sample, state)
    except ValueError as exc:
        core_valid = False
        sample.result['gaps'].append(str(exc))
    active = 0
    for lead in positions:
        address = lead['position']
        row = {'address': address, 'status': 'partial', 'principal': None, 'custody': None,
               'active_liquidity_share': None, 'whole_pool_principal_share': None, 'gaps': [],
               'discovery_evidence': lead['evidence']}
        sample.result['positions'].append(row)
        try:
            position = module.decode_position(address, sample.account(address), pool, lead)
            row.update(position)
            need(position['lower_tick'] % state['tick_spacing'] == 0 and position['upper_tick'] % state['tick_spacing'] == 0, "position ticks do not match spacing")
            price_tick_consistent(state['sqrt_price_x64'], state['current_tick'], module.MATH)
            if module.MATH == 'orca' and state['tick_spacing'] >= 32768:
                low = -(443636//state['tick_spacing'])*state['tick_spacing']
                need(position['lower_tick'] == low and position['upper_tick'] == (443636//state['tick_spacing'])*state['tick_spacing'], "full-range-only spacing requires full range")
            arrays, boundaries = [], []
            for tick in (position['lower_tick'], position['upper_tick']):
                array_address = module.tick_array_address(pool, tick, state['tick_spacing'])
                arrays.append(array_address)
                boundary = module.decode_boundary(array_address, sample.account(array_address), pool, tick, state['tick_spacing'])
                need(int(boundary['liquidity_gross']) >= position['liquidity'], "position liquidity exceeds boundary gross liquidity")
                boundaries.append(boundary)
            row.update(tick_arrays=list(dict.fromkeys(arrays)), boundaries=boundaries)
            need(core_valid, "verified pool mints and vaults required for principal")
            sample.same_bank([*core, address, *arrays])
            computed = principal(position['liquidity'], state['sqrt_price_x64'], position['lower_tick'], position['upper_tick'], module.MATH)
            inside = position['lower_tick'] <= state['current_tick'] < position['upper_tick']
            if inside:
                need(position['liquidity'] <= state['liquidity'], "position exceeds active pool liquidity")
                active += position['liquidity']
            row.update(principal=computed, in_range=inside,
                active_liquidity_atomic=str(position['liquidity'] if inside else 0),
                active_liquidity_share=ratio(position['liquidity'], state['liquidity']) if inside else None)
            try:
                custody_dependencies = module.position_relationship(sample, address, position, lead)
                nft = position['position_mint']
                mint_account = sample.account(nft)
                need(mint_account['owner'] in (TOKEN_PROGRAM, TOKEN_2022), "unsupported position mint program")
                if lead.get('bundle'):
                    need(mint_account['owner'] == TOKEN_PROGRAM, "Token-2022 bundle representation unsupported")
                mint = sample.mint(nft, mint_account['owner'], 0)
                need(mint['supply_atomic'] == '1' and mint['mint_authority'] is None, "position NFT supply/issuance authority unresolved")
                need(lead.get('holding'), lead.get('holding_gap') or 'position NFT holder unresolved')
                holding_address = pubkey(lead.get('holding'))
                holding = decode_holding(sample.account(holding_address), mint=nft, token_program=mint_account['owner'])
                need(holding['amount_atomic'] == '1' and holding['state'] != 'uninitialized', "position holding does not own one NFT")
                sample.same_bank([pool, address, nft, holding_address, *custody_dependencies])
                row['custody'] = {'holding': holding_address, **holding, 'mint_program': mint_account['owner'],
                    'representation': 'bundle_nft' if lead.get('bundle') else 'token2022_nft' if mint_account['owner'] == TOKEN_2022 else 'spl_nft',
                    'mint_controls': mint, 'bundle': lead.get('bundle'), 'bundle_index': lead.get('bundle_index'),
                    'principal_locked': None, 'beneficial_owner': None,
                    'scope': 'observed spending owner/delegate; freeze, extension and controller paths separate'}
                if not holding['extensions_valid'] or holding['unknown_extensions']:
                    row['gaps'].append('position_holding_extensions_unresolved')
                if not mint['extensions_valid'] or mint['unknown_extensions']:
                    row['gaps'].append('position_mint_extensions_unresolved')
            except ValueError as exc:
                row['gaps'].append(str(exc))
            row['status'] = 'observed' if not row['gaps'] else 'partial'
        except ValueError as exc:
            row['gaps'].append(str(exc))
        if 'liquidity' in row: row['liquidity'] = str(row['liquidity'])
        row['evidence'] = sorted({e for a in [pool, address, *row.get('tick_arrays', [])] if a in sample.used for e in sample.used[a]['evidence']})
    if active > state['liquidity']:
        sample.result['gaps'].append('sampled_positions_exceed_pool_active_liquidity')
        for row in sample.result['positions']:
            row.update(active_liquidity_share=None, principal=None, status='partial')
            row['gaps'].append('contradictory_position_sample')
    state['liquidity'], state['sqrt_price_x64'] = str(state['liquidity']), str(state['sqrt_price_x64'])
    result = sample.finish()
    result['position_coverage'] = 'sampled' if positions and all(p['status'] == 'observed' for p in result['positions']) else 'partial'
    # A resolved sample with observed positions is observed; reserves are never inferred here, so they cannot gate it.
    result['status'] = 'observed' if not result['gaps'] and result['position_coverage'] == 'sampled' else 'partial'
    result['controller_roots'] += [{'address': p['custody'][role], 'role': role, 'position': p['address'], 'evidence': p['evidence']}
        for p in result['positions'] if p['custody'] for role in ('spending_owner','delegate','close_authority') if p['custody'][role] is not None]
    return result
