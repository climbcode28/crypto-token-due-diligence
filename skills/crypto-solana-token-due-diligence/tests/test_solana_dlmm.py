from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from adapters import meteora_dlmm as dlmm,meteora_damm_v2 as damm,meteora_common as common
from meteora_fixture import fixture,batch,key,Q
from test_solana_raydium import mutate


class DlmmTests(unittest.TestCase):
    def analyze(self,values=None):
        target,a,v=fixture()
        return dlmm.analyze(target,a['pool'],batch(v if values is None else values),positions=[a['lead']]),a,v

    def test_three_bins_use_independent_share_denominators(self):
        result,a,_=self.analyze();p=result['positions'][0]
        self.assertEqual(p['principal']['amounts_atomic'],['750','1000'])
        self.assertEqual(p['bins'][0]['principal_atomic'],['250','0'])
        self.assertEqual(p['bins'][1]['principal_atomic'],['500','1000'])
        self.assertEqual(p['custody']['spending_owner'],a['owner'])
        self.assertIsNone(result['reserves_atomic']);self.assertIsNone(p['whole_pool_principal_share'])
        self.assertFalse(result['adapter']['quote']);self.assertEqual(p['status'],'observed')

    def test_lock_clock_and_fee_claims_are_separate(self):
        result,a,v=self.analyze();p=result['positions'][0]
        self.assertTrue(p['lock_release_reached']);self.assertEqual(p['stored_pending_fees_atomic'],['7','11'])
        self.assertIsNone(p['current_uncollected_fees_atomic'])
        v[a['position']]=mutate(v[a['position']],7992,(101).to_bytes(8,'little'))
        self.assertFalse(self.analyze(v)[0]['positions'][0]['lock_release_reached'])
        del v[common.CLOCK];p=self.analyze(v)[0]['positions'][0]
        self.assertIsNone(p['lock_release_reached']);self.assertIsNotNone(p['principal'])

    def test_missing_bin_retains_covered_bin_facts_but_not_position_total(self):
        _,a,v=self.analyze();del v[a['arrays'][1]]
        result=self.analyze(v)[0];p=result['positions'][0]
        self.assertIsNone(p['principal']);self.assertEqual(len(p['bins']),1);self.assertEqual(len(result['vaults']),2)

    def test_wrong_pool_program_neighbor_and_future_position(self):
        for kind in ('owner','discriminator','version','expanded'):
            target,a,v=fixture()
            if kind=='owner':v[a['position']]['owner']=damm.PROGRAM
            if kind=='discriminator':v[a['position']]=mutate(v[a['position']],0,bytes(8))
            if kind=='version':v[a['position']]=mutate(v[a['position']],8033,b'\2')
            if kind=='expanded':v[a['position']]=mutate(v[a['position']],7916,(70).to_bytes(4,'little'))
            p=dlmm.analyze(target,a['pool'],batch(v),positions=[a['lead']])['positions'][0]
            self.assertIsNone(p['principal']);self.assertTrue(p['gaps'])
            expected={'version':'unsupported DLMM position version 2','expanded':'expanded DLMM position unsupported'}.get(kind)
            if expected:self.assertIn(expected,p['gaps'])
        target,a,v=fixture();v[a['pool']]['owner']=damm.PROGRAM
        with self.assertRaises(ValueError):dlmm.analyze(target,a['pool'],batch(v))

    def test_pair_version_bump_and_reserved_bytes_are_named_gaps(self):
        for offset,data,gap in [(882,b'\2','unsupported_DLMM_pair_version_2'),(890,b'\1','DLMM_pair_reserved_bytes_set'),(75,b'\4','unsupported_DLMM_control_configuration')]:
            _,a,v=self.analyze();v[a['pool']]=mutate(v[a['pool']],offset,data)
            result=self.analyze(v)[0]
            self.assertIsNone(result['positions'][0]['principal']);self.assertEqual(len(result['vaults']),2)
            self.assertIn(gap,result['gaps'])
        for offset in (882,8033):  # version 1 (live pairs and positions) is accepted on both accounts
            _,a,v=self.analyze();key=a['pool'] if offset==882 else a['position'];v[key]=mutate(v[key],offset,b'\1')
            self.assertEqual(self.analyze(v)[0]['positions'][0]['principal']['amounts_atomic'],['750','1000'])

    def test_known_bin_array_versions_decode_and_future_or_padded_arrays_refuse(self):
        # Live arrays carried version 2 on 2026-09-13; the SDK default is 3 (limit orders). Principal offsets are unchanged.
        for version in range(dlmm.BIN_ARRAY_MAX_VERSION+1):
            target,a,v=fixture(bin_array_version=version)
            p=dlmm.analyze(target,a['pool'],batch(v),positions=[a['lead']])['positions'][0]
            self.assertEqual(p['principal']['amounts_atomic'],['750','1000'],version);self.assertEqual(p['status'],'observed')
        for offset,data in [(16,bytes([dlmm.BIN_ARRAY_MAX_VERSION+1])),(17,b'\1')]:
            _,a,v=self.analyze();v[a['arrays'][0]]=mutate(v[a['arrays'][0]],offset,data)
            p=self.analyze(v)[0]['positions'][0]
            self.assertIsNone(p['principal']);self.assertIn('unsupported bin array version',p['gaps'])

    def test_resolved_sample_with_program_control_is_observed_without_reserves(self):
        from broad_fixture import program_accounts
        target,a,v=fixture();v.update(program_accounts(dlmm.PROGRAM))
        result=dlmm.analyze(target,a['pool'],batch(v),positions=[a['lead']])
        self.assertEqual((result['status'],result['position_coverage'],result['reserves_atomic'],result['gaps']),('observed','sampled',None,[]))
        self.assertEqual(result['program_control']['upgradeability'],'authority_present')
        self.assertEqual(dlmm.analyze(target,a['pool'],batch(v),positions=[])['status'],'partial')  # no sampled positions: custody unresolved

    def test_fee_configuration_boundary_and_future_modes(self):
        for offset,data in [(36,b'\2'),(35,b'\3'),(80,(401).to_bytes(2,'little')),(32,(10001).to_bytes(2,'little')),(40,(10001).to_bytes(4,'little')),(8,(65535).to_bytes(2,'little'))]:
            _,a,v=self.analyze();v[a['pool']]=mutate(v[a['pool']],offset,data)
            # Large factor needs large step to exceed the pinned 10% cap.
            if offset==8:v[a['pool']]=mutate(v[a['pool']],80,(400).to_bytes(2,'little'))
            result=self.analyze(v)[0]
            self.assertIsNone(result['positions'][0]['principal']);self.assertEqual(len(result['vaults']),2)

    def test_wrong_mint_vault_and_mixed_batch_are_not_custody_depth(self):
        for kind in ('mint','vault','batch','pool'):
            target,a,v=fixture();obs=batch(v)
            if kind=='mint':v[a['mints'][0]]['owner']=key(70)
            if kind=='vault':v[a['vaults'][0]]=mutate(v[a['vaults'][0]],32,bytes([70])*32)
            if kind=='pool':v[a['position']]=mutate(v[a['position']],8,bytes([70])*32)
            obs=batch(v)
            if kind=='batch':obs[a['arrays'][0]]=batch({a['arrays'][0]:v[a['arrays'][0]]},name='other-read')[a['arrays'][0]]
            result=dlmm.analyze(target,a['pool'],obs,positions=[a['lead']])
            self.assertIsNone(result['positions'][0]['principal']);self.assertIsNone(result['exit_executable'])

    def test_duplicate_and_overallocated_positions_do_not_double_count(self):
        target,a,v=fixture()
        with self.assertRaises(ValueError):dlmm.analyze(target,a['pool'],batch(v),positions=[a['lead']]*2)
        other=key(66);v[other]=v[a['position']]
        leads=[a['lead'],{**a['lead'],'position':other}]
        third=key(67);v[third]=v[a['position']];leads.append({**a['lead'],'position':third})
        result=dlmm.analyze(target,a['pool'],batch(v),positions=leads)
        self.assertTrue(all(p['principal'] is None for p in result['positions']))

    def test_zero_liquidity_retains_fee_only_position(self):
        _,a,v=self.analyze();v[a['position']]=mutate(v[a['position']],72,bytes(1120))
        p=self.analyze(v)[0]['positions'][0]
        self.assertEqual(p['principal']['amounts_atomic'],['0','0']);self.assertEqual(p['stored_pending_fees_atomic'],['7','11'])

    def test_preset_derives_only_two_arrays_and_clock_from_named_position(self):
        from solana_presets import position_sample
        from adapters import pool_adapter
        _,a,v=fixture();obs=batch(v)
        plans=position_sample('meteora_dlmm',a['pool'],obs[a['pool']],[a['lead']],obs)
        self.assertEqual(len(plans),1);self.assertEqual(plans[0]['method'],'getMultipleAccounts')
        self.assertTrue(set(a['arrays']+[common.CLOCK,a['position']]) <= set(plans[0]['params'][0]))
        for neighbor in ('meteora_damm_v1','meteora_dbc'):
            with self.assertRaises(ValueError):pool_adapter(neighbor)


if __name__=='__main__':unittest.main()
