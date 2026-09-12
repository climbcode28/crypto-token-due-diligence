from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from adapters import orca_whirlpool as orca
from adapters.concentrated_math import sqrt_at_tick,price_tick_consistent,principal
from concentrated_fixture import fixture,batch
from pool_fixture import key,holding
from test_solana_raydium import mutate


class WhirlpoolTests(unittest.TestCase):
    def run_case(self,**kwargs):
        target,a,values=fixture('orca',**kwargs)
        return orca.analyze(target,a['pool'],batch(values),positions=[a['lead']]),a,values

    def test_official_tick_boundaries_and_fixed_dynamic_equivalence(self):
        self.assertEqual(sqrt_at_tick(-443636,'orca'),4295048016)
        self.assertEqual(sqrt_at_tick(443636,'orca'),79226673515401279992447579055)
        fixed=self.run_case()[0]['positions'][0];dynamic=self.run_case(dynamic=True)[0]['positions'][0]
        self.assertEqual(fixed['principal'],dynamic['principal'])
        self.assertEqual(dynamic['principal']['amounts_atomic'],['4987','4987'])
        self.assertEqual(dynamic['status'],'observed')

    def test_spl_bundle_membership_separate_from_delegate_and_program_control(self):
        result,a,_=self.run_case(bundle=True)
        custody=result['positions'][0]['custody']
        self.assertEqual(custody['representation'],'bundle_nft')
        self.assertEqual(custody['bundle_index'],7);self.assertEqual(custody['spending_owner'],a['owner'])
        self.assertEqual(custody['delegate'],key(56));self.assertIsNone(custody['principal_locked'])
        self.assertIsNone(result['program_control'])
        target,a,values=fixture('orca',bundle=True);values[a['lead']['bundle']]=mutate(values[a['lead']['bundle']],40,b'\0')
        p=orca.analyze(target,a['pool'],batch(values),positions=[a['lead']])['positions'][0]
        self.assertIsNone(p['custody']);self.assertTrue(any('bitmap' in g for g in p['gaps']))

    def test_outside_range_boundary_and_fee_only_amounts(self):
        for tick,expected,inside in [(0,['4987','0'],True),(100,['0','5012'],False)]:
            p=self.run_case(tick=tick,lower=0,upper=100)[0]['positions'][0]
            self.assertEqual(p['principal']['amounts_atomic'],expected);self.assertEqual(p['in_range'],inside)
        p=self.run_case(liquidity=0)[0]['positions'][0]
        self.assertEqual(p['principal']['amounts_atomic'],['0','0']);self.assertEqual(p['fees_owed_checkpoint_atomic'],['17','23'])
        self.assertIsNone(p['live_uncollected_fees_atomic'])
        p=self.run_case(tick=-200)[0]['positions'][0];self.assertEqual(p['principal']['amounts_atomic'],['9999','0'])
        self.assertIsNone(p['whole_pool_principal_share'])

    def test_dynamic_bitmap_unknown_discriminator_and_wrong_pool_refuse_principal(self):
        for change in ('bitmap','discriminator','pool','missing'):
            target,a,values=fixture('orca',dynamic=True)
            array=a['arrays'][0]
            if change=='bitmap':values[array]=mutate(values[array],44,bytes(16))
            if change=='discriminator':values[array]=mutate(values[array],0,bytes(8))
            if change=='pool':values[a['position']]=mutate(values[a['position']],8,bytes([70])*32)
            if change=='missing':del values[array]
            p=orca.analyze(target,a['pool'],batch(values),positions=[a['lead']])['positions'][0]
            self.assertIsNone(p['principal']);self.assertTrue(p['gaps'])

    def test_token2022_nft_and_unsupported_bundle_representation(self):
        p=self.run_case(token22=True)[0]['positions'][0]
        self.assertEqual(p['custody']['representation'],'token2022_nft')
        p=self.run_case(bundle=True,token22=True)[0]['positions'][0]
        self.assertIsNone(p['custody']);self.assertTrue(any('unsupported' in g for g in p['gaps']))

    def test_owner_transfer_and_mixed_context_holdings_do_not_become_custody(self):
        target,a,values=fixture('orca');values[a['holding']]=holding(a['nft'],key(75),1)
        p=orca.analyze(target,a['pool'],batch(values),positions=[a['lead']])['positions'][0]
        self.assertEqual(p['custody']['spending_owner'],key(75));self.assertIsNone(p['custody']['delegate'])
        observations=batch(values);observations[a['holding']]=batch({a['holding']:values[a['holding']]},name='later',slot=101)[a['holding']]
        p=orca.analyze(target,a['pool'],observations,positions=[a['lead']])['positions'][0]
        self.assertIsNone(p['custody']);self.assertIsNotNone(p['principal'])

    def test_invalid_program_pool_mint_order_and_tick_price_are_rejected(self):
        for change in ('program','mints','price'):
            target,a,values=fixture('orca')
            if change=='program':values[a['pool']]['owner']=key(70)
            if change=='mints':values[a['pool']]=mutate(values[a['pool']],101,bytes([3])*32)
            if change=='price':values[a['pool']]=mutate(values[a['pool']],65,sqrt_at_tick(200,'orca').to_bytes(16,'little'))
            with self.assertRaises(ValueError):orca.analyze(target,a['pool'],batch(values),positions=[a['lead']])
        # Exact boundary at downward crossing is valid with current tick one lower.
        price_tick_consistent(sqrt_at_tick(100,'orca'),99,'orca')
        with self.assertRaises(ValueError):principal(1<<127,sqrt_at_tick(0,'orca'),-443636,443636,'orca')


if __name__=='__main__':unittest.main()
