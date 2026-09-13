"""Evidence helpers shared by Meteora products; arithmetic stays product-specific."""
from solana_common import need, pubkey, TOKEN_PROGRAM, TOKEN_2022
from solana_session import label
from adapters.base import Sample
from adapters.binary import raw_account

CLOCK = 'SysvarC1ock11111111111111111111111111111111'
SYSVAR = 'Sysvar1111111111111111111111111111111111111'


def begin(module, target, pool, observations, positions):
    need(isinstance(positions, list) and len(positions) <= 6, 'at most six position leads')
    need(all(isinstance(p, dict) and isinstance(p.get('evidence'), list) and 1 <= len(p['evidence']) <= 8 for p in positions), 'captured position leads required')
    need(len({pubkey(p.get('position')) for p in positions}) == len(positions), 'duplicate position lead')
    for p in positions:
        need(p.get('kind') in ('explicit', 'account', 'indexer', 'transaction', 'census'), 'position lead kind required')
        for e in p['evidence']: label(e)
    sample = Sample(target, pool, observations, module.CAPABILITY)
    state = module.decode_pool(pool, sample.account(pool))
    need(target['mint'] in state['mints'], 'target mint not in Meteora pool')
    core = [pool, *state['mints'], *state['vaults']]
    sample.result.update(state=state, mints=state['mints'], positions=[],
        discovery={'maximum': 6, 'requested_positions': len(positions), 'coverage': 'specific_leads_not_exhaustive',
                   'evidence': sorted({e for p in positions for e in p['evidence']})},
        quote_dependencies='Complete swap fees/traversal and token controls are separately required')
    sample.controls(module.PROGRAM)
    valid = not state.get('configuration_gaps')
    sample.result['gaps'].extend(state.get('configuration_gaps', []))
    for i in range(2):
        try:
            program = state['token_programs'][i]
            sample.mint(state['mints'][i], program)
            sample.vault(state['vaults'][i], state['mints'][i], program, state['authority'])
        except ValueError as exc:
            valid = False
            sample.result['gaps'].append(str(exc))
    try:
        sample.same_bank(core)
    except ValueError as exc:
        valid = False
        sample.result['gaps'].append(str(exc))
    return sample, state, core, valid


def point(sample, dependencies, activation_type):
    """Use the captured bank's Clock, never local time or an estimated block time."""
    need(activation_type in (0, 1), 'unknown activation type')
    value = sample.account(CLOCK)
    raw = raw_account(value, SYSVAR)
    need(not value['executable'] and len(raw) == 40, 'invalid Clock sysvar layout')
    slot = int.from_bytes(raw[:8], 'little')
    timestamp = int.from_bytes(raw[32:40], 'little', signed=True)
    need(slot == sample.used[CLOCK]['context_slot'] and timestamp >= 0, 'Clock context mismatch')
    sample.same_bank([*dependencies, CLOCK])
    return slot if activation_type == 0 else timestamp


def row(sample, lead):
    result = {'address': lead['position'], 'status': 'partial', 'principal': None, 'custody': None,
              'whole_pool_principal_share': None, 'exit_executable': None, 'gaps': [],
              'discovery_evidence': lead['evidence']}
    sample.result['positions'].append(result)
    return result


def finish(sample):
    result = sample.finish()
    for p in result['positions']:
        # Each successful calculation requires the same full atomic packet as the pool.
        p['evidence'] = sorted({e for a in p.get('dependencies', [p['address']]) if a in sample.used for e in sample.used[a]['evidence']})
        p['status'] = 'observed' if p['principal'] is not None and p['custody'] is not None and not p['gaps'] else 'partial'
        for role, address in p.get('controllers', {}).items():
            if address:
                result['controller_roots'].append({'address': address, 'role': role, 'position': p['address'], 'evidence': p['evidence']})
    result['position_coverage'] = 'sampled' if result['positions'] and all(p['status'] == 'observed' for p in result['positions']) else 'partial'
    # A resolved sample with observed positions is observed; depth limits are scope, not a missing dependency.
    result['status'] = 'observed' if not result['gaps'] and (result['reserves_atomic'] is not None or result['position_coverage'] == 'sampled') else 'partial'
    return result


def token_programs(flags):
    need(all(f in (0, 1) for f in flags), 'unsupported token program flag')
    return [(TOKEN_PROGRAM, TOKEN_2022)[f] for f in flags]
