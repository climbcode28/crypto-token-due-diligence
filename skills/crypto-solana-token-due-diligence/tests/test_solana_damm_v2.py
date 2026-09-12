from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from adapters import meteora_damm_v2 as damm,meteora_dlmm as dlmm,meteora_common as common
from adapters.binary import discriminator
from meteora_fixture import fixture,batch,key,Q,owned,write,clock
from solana_common import base58_bytes
from test_solana_raydium import mutate


class DammTests(unittest.TestCase):
    def analyze(self,values=None,collect=0,lead=None):
        target,a,v=fixture('damm',collect)
        return damm.analyze(target,a['pool'],batch(v if values is None else values),positions=[lead or a['lead']]),a,v

    def test_range_principal_has_damm_scaling_and_separate_locked_fee_quantities(self):
        result,_,_=self.analyze();p=result['positions'][0]
        self.assertEqual(p['principal']['amounts_atomic'],['500','500'])
        self.assertEqual(p['stored_unlocked_principal']['amounts_atomic'],['250','250'])
        self.assertEqual(p['permanent_locked_principal']['amounts_atomic'],['50','50'])
        self.assertEqual(p['stored_pending_fees_atomic'],['7','11'])
        self.assertEqual(p['principal_after_vesting_refresh']['amounts_atomic'],['350','350'])
        self.assertEqual(p['releasable_liquidity'],str(200*Q));self.assertEqual(p['status'],'observed')
        self.assertIsNone(p['whole_pool_principal_share']);self.assertIsNone(p['exit_executable'])

    def test_compounding_uses_tracked_reserves_including_dead_liquidity_denominator(self):
        p=self.analyze(collect=2)[0]['positions'][0]
        self.assertEqual(p['principal']['amounts_atomic'],['5000','10000'])
        self.assertEqual(p['principal_after_vesting_refresh']['amounts_atomic'],['3500','7000'])
        _,a,v=self.analyze(collect=2);v[a['pool']]=mutate(v[a['pool']],696,b'\0')
        self.assertIsNone(self.analyze(v,collect=2)[0]['positions'][0]['principal'])

    def test_nft_retained_mint_authority_and_zero_allowance_protocol_delegate(self):
        p,a,v=self.analyze();c=p['positions'][0]['custody']
        self.assertEqual(c['mint_controls']['mint_authority'],a['authority'])
        self.assertEqual(c['mint_controls']['freeze_authority'],a['pool'])
        self.assertTrue(c['protocol_delegate_eligible']);self.assertFalse(c['delegate_has_nft_transfer_allowance'])
        self.assertEqual(c['delegate_protocol_permissions']['remove_liquidity'],'owner_ATA_only')
        self.assertEqual(c['delegate_protocol_permissions']['claim_fees'],'unrestricted')
        v[a['holding']]=mutate(v[a['holding']],121,(1).to_bytes(8,'little'))
        c=self.analyze(v)[0]['positions'][0]['custody']
        self.assertFalse(c['protocol_delegate_eligible']);self.assertTrue(c['delegate_has_nft_transfer_allowance'])
        self.assertIsNone(c['nft_transfer_executable'])

    def test_owner_transfer_and_missing_ownership_do_not_erase_mathematical_principal(self):
        _,a,v=self.analyze();v[a['holding']]=mutate(v[a['holding']],32,bytes([70])*32)
        self.assertEqual(self.analyze(v)[0]['positions'][0]['custody']['spending_owner'],key(70))
        del v[a['holding']];p=self.analyze(v)[0]['positions'][0]
        self.assertIsNone(p['custody']);self.assertIsNotNone(p['principal'])

    def test_external_vesting_must_reconcile_actual_position_and_captured_clock(self):
        _,a,v=self.analyze();lead={**a['lead'],'vestings':[key(68)]}
        # Remove embedded schedule but keep 400 vested units in the position.
        import base64
        original=base64.b64decode(v[a['position']]['data'][0])
        raw=discriminator('Vesting')+base58_bytes(a['position'],32)+original[312:392]+bytes(64)
        v[key(68)]=owned(raw,damm.PROGRAM);v[a['position']]=mutate(v[a['position']],312,bytes(80))
        p=self.analyze(v)[0]['positions'][0]
        self.assertIsNone(p['principal_after_vesting_refresh']);self.assertIsNotNone(p['stored_unlocked_principal'])
        p=self.analyze(v,lead=lead)[0]['positions'][0]
        self.assertEqual(p['principal_after_vesting_refresh']['amounts_atomic'],['350','350'])
        v[key(68)]=mutate(v[key(68)],8,bytes([70])*32)
        self.assertIsNone(self.analyze(v,lead=lead)[0]['positions'][0]['principal_after_vesting_refresh'])

    def test_slot_vs_timestamp_cliff_and_missing_clock(self):
        _,a,v=self.analyze();v[common.CLOCK]=clock(timestamp=85)
        v[a['pool']]=mutate(v[a['pool']],480,b'\1')
        p=self.analyze(v)[0]['positions'][0]
        self.assertEqual(p['principal_after_vesting_refresh']['amounts_atomic'],['250','250'])
        del v[common.CLOCK]
        p=self.analyze(v)[0]['positions'][0];self.assertIsNone(p['principal_after_vesting_refresh'])
        self.assertIsNotNone(p['permanent_locked_principal'])

    def test_configuration_boundaries_refuse_future_modes_and_keep_vaults(self):
        for offset,data in [(16,b'\5'),(48,b'e'),(56,b'\2'),(484,b'\3'),(696,b'\2'),(8,(500000001).to_bytes(8,'little'))]:
            _,a,v=self.analyze();v[a['pool']]=mutate(v[a['pool']],offset,data)
            result=self.analyze(v)[0]
            self.assertIsNone(result['positions'][0]['principal']);self.assertEqual(len(result['vaults']),2)
        _,a,v=self.analyze();v[a['pool']]=mutate(v[a['pool']],486,b'\1');v[a['pool']]=mutate(v[a['pool']],8,(990000000).to_bytes(8,'little'))
        self.assertIsNotNone(self.analyze(v)[0]['positions'][0]['principal'])

    def test_dynamic_configuration_requires_valid_reference(self):
        _,a,v=self.analyze();v[a['pool']]=mutate(v[a['pool']],56,b'\1')
        self.assertIsNone(self.analyze(v)[0]['positions'][0]['principal'])
        for offset,value,size in [(64,10000,4),(72,10,2),(74,5,2),(76,10,2),(78,5000,2),(88,Q//1000,16),(104,Q,16)]:
            v[a['pool']]=mutate(v[a['pool']],offset,value.to_bytes(size,'little'))
        self.assertIsNotNone(self.analyze(v)[0]['positions'][0]['principal'])

    def test_neighbor_layouts_and_wrong_pool_mint_vault_rejected(self):
        for kind in ('position_owner','position_pool','position_layout','vault','mint'):
            _,a,v=self.analyze()
            if kind=='position_owner':v[a['position']]['owner']=dlmm.PROGRAM
            if kind=='position_pool':v[a['position']]=mutate(v[a['position']],8,bytes([70])*32)
            if kind=='position_layout':v[a['position']]=mutate(v[a['position']],0,discriminator('PositionV2'))
            if kind=='vault':v[a['vaults'][0]]=mutate(v[a['vaults'][0]],0,bytes([70])*32)
            if kind=='mint':v[a['mints'][0]]['owner']=key(70)
            self.assertIsNone(self.analyze(v)[0]['positions'][0]['principal'])
        target,a,v=fixture('damm');v[a['pool']]['owner']=dlmm.PROGRAM
        with self.assertRaises(ValueError):damm.analyze(target,a['pool'],batch(v))

    def test_missing_and_different_atomic_samples_fail_only_affected_fact(self):
        target,a,v=fixture('damm');obs=batch(v)
        obs[a['holding']]=batch({a['holding']:v[a['holding']]},name='later')[a['holding']]
        p=damm.analyze(target,a['pool'],obs,positions=[a['lead']])['positions'][0]
        self.assertIsNone(p['custody']);self.assertIsNotNone(p['principal'])
        v[a['vaults'][0]]=mutate(v[a['vaults'][0]],64,(1).to_bytes(8,'little'))
        self.assertIsNone(self.analyze(v)[0]['positions'][0]['principal'])

    def test_permanent_lock_accounting_and_vesting_underflow(self):
        _,a,v=self.analyze();v[a['pool']]=mutate(v[a['pool']],552,bytes(16))
        self.assertIsNone(self.analyze(v)[0]['positions'][0]['principal'])
        _,a,v=self.analyze();v[a['position']]=mutate(v[a['position']],360,(300*Q).to_bytes(16,'little'))
        p=self.analyze(v)[0]['positions'][0];self.assertIsNone(p['principal_after_vesting_refresh'])

    def test_preset_collects_nft_and_explicit_vestings_without_global_scan(self):
        from solana_presets import position_sample
        _,a,v=fixture('damm');obs=batch(v);lead={**a['lead'],'vestings':[key(68)]}
        plans=position_sample('meteora_damm_v2',a['pool'],obs[a['pool']],[lead],obs)
        self.assertEqual(len(plans),1)
        self.assertTrue(set([a['nft'],a['holding'],common.CLOCK,key(68)]) <= set(plans[0]['params'][0]))
        self.assertLessEqual(len(plans[0]['params'][0]),25)

    def test_clock_from_another_bank_is_not_current_release_evidence(self):
        target,a,v=fixture('damm');obs=batch(v)
        obs[common.CLOCK]=batch({common.CLOCK:clock()},name='other-clock')[common.CLOCK]
        p=damm.analyze(target,a['pool'],obs,positions=[a['lead']])['positions'][0]
        self.assertIsNone(p['principal_after_vesting_refresh']);self.assertIsNotNone(p['principal'])
        v[common.CLOCK]=clock(slot=101)
        self.assertIsNone(self.analyze(v)[0]['positions'][0]['principal_after_vesting_refresh'])


if __name__=='__main__':unittest.main()
