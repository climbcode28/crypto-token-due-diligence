from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from adapters import raydium_clmm as ray
from adapters.concentrated_math import sqrt_at_tick
from concentrated_fixture import fixture,batch
from pool_fixture import key,holding
from test_solana_raydium import mutate


class CLMMTests(unittest.TestCase):
    def run_case(self,**kwargs):
        target,a,values=fixture(**kwargs)
        return ray.analyze(target,a['pool'],batch(values),positions=[a['lead']]),a,values

    def test_tick_bounds_and_in_range_principal(self):
        self.assertEqual(sqrt_at_tick(-443636,'raydium'),4295048016)
        self.assertEqual(sqrt_at_tick(443636,'raydium'),79226673521066979257578248091)
        result,a,_=self.run_case();p=result['positions'][0]
        self.assertEqual(p['principal']['amounts_atomic'],['4987','4987'])
        self.assertTrue(p['in_range']);self.assertEqual(p['active_liquidity_share']['numerator_atomic'],'1000000')
        self.assertEqual(p['active_liquidity_share']['denominator_atomic'],'2000000')
        self.assertEqual(p['fees_owed_checkpoint_atomic'],['17','23'])
        self.assertEqual(p['custody']['spending_owner'],a['owner']);self.assertEqual(p['custody']['delegate'],key(56))
        self.assertIsNone(p['whole_pool_principal_share']);self.assertIsNone(result['all_principal_locked'])

    def test_outside_range_principal_is_one_sided_not_zero(self):
        for tick,expected in [(200,['0','9999']),(-200,['9999','0'])]:
            p=self.run_case(tick=tick)[0]['positions'][0]
            self.assertEqual(p['principal']['amounts_atomic'],expected);self.assertFalse(p['in_range'])
            self.assertIsNone(p['active_liquidity_share']);self.assertEqual(p['active_liquidity_atomic'],'0')

    def test_missing_ticks_and_wrong_pool_refuse_principal(self):
        for change in ('missing','pool','tick_owner','position_discriminator'):
            target,a,values=fixture()
            if change=='missing':del values[a['arrays'][0]]
            if change=='pool':values[a['position']]=mutate(values[a['position']],41,bytes([80])*32)
            if change=='tick_owner':values[a['arrays'][0]]['owner']=key(80)
            if change=='position_discriminator':values[a['position']]=mutate(values[a['position']],0,bytes(8))
            p=ray.analyze(target,a['pool'],batch(values),positions=[a['lead']])['positions'][0]
            self.assertIsNone(p['principal']);self.assertTrue(p['gaps'])

    def test_zero_liquidity_fee_checkpoint_and_token2022_nft(self):
        p=self.run_case(liquidity=0)[0]['positions'][0]
        self.assertEqual(p['principal']['amounts_atomic'],['0','0']);self.assertEqual(p['fees_owed_checkpoint_atomic'],['17','23'])
        p=self.run_case(token22=True)[0]['positions'][0]
        self.assertEqual(p['custody']['representation'],'token2022_nft');self.assertIsNone(p['custody']['principal_locked'])

    def test_wrong_pool_program_order_and_position_cap(self):
        target,a,values=fixture();values[a['pool']]['owner']=key(80)
        with self.assertRaises(ValueError):ray.analyze(target,a['pool'],batch(values),positions=[a['lead']])
        target,a,values=fixture()
        with self.assertRaises(ValueError):ray.analyze(target,a['pool'],batch(values),positions=[a['lead']]*7)
        values[a['pool']]=mutate(values[a['pool']],73,bytes([3])*32+bytes([2])*32)
        with self.assertRaises(ValueError):ray.analyze(target,a['pool'],batch(values),positions=[a['lead']])

    def test_new_owner_and_no_implicit_global_custody_claim(self):
        target,a,values=fixture();values[a['holding']]=holding(a['nft'],key(75),1)
        result=ray.analyze(target,a['pool'],batch(values),positions=[a['lead']])
        self.assertEqual(result['positions'][0]['custody']['spending_owner'],key(75))
        self.assertEqual(result['discovery']['coverage'],'specific_leads_not_exhaustive')
        self.assertIsNone(result['positions'][0]['custody']['principal_locked'])

    def test_position_read_plan_and_missing_config_gate(self):
        from solana_presets import position_sample
        target,a,values=fixture();observations=batch(values)
        reads=position_sample('raydium_clmm',a['pool'],observations[a['pool']],[a['lead']],observations)
        self.assertEqual(len(reads),1);self.assertTrue(reads[0]['critical'])
        self.assertTrue(set([a['pool'],a['config'],a['position'],a['nft'],a['holding'],*a['arrays']]) <= set(reads[0]['params'][0]))
        del values[a['config']]
        result=ray.analyze(target,a['pool'],batch(values),positions=[a['lead']])
        self.assertIsNone(result['positions'][0]['principal'])
        self.assertTrue(any('missing dependency' in g for g in result['gaps']))


if __name__=='__main__':unittest.main()
