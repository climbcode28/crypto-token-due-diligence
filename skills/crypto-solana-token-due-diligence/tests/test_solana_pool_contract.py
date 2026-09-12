from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from adapters import pool_adapter, raydium_cpmm as cp
from pool_fixture import fixture, batch, key, holding
from solana_discovery import select_pools
from solana_presets import pool_sample


class PoolContractTests(unittest.TestCase):
    def test_offline_dispatch_capability_and_network_refusal(self):
        self.assertIs(pool_adapter('raydium_cpmm'),cp)
        with self.assertRaises(ValueError):pool_adapter('raydium')
        target,a,values=fixture();target['genesis_hash']=key(50)
        with self.assertRaises(ValueError):cp.analyze(target,a['pool'],batch(values))
        self.assertTrue(cp.CAPABILITY['quote']);self.assertIn('SPL estimate',cp.CAPABILITY['quote_scope']);self.assertEqual(cp.CAPABILITY['locks'],[])

    def test_custody_partial_missing_and_transferred_owner_are_scoped(self):
        target,a,values=fixture();values[a['holder']]=holding(a['lp'],key(60),450)
        result=cp.analyze(target,a['pool'],batch(values),lp_accounts=[a['holder'],key(70)])
        lp=result['lp_custody']
        self.assertEqual(lp['accounts'][0]['spending_owner'],key(60))
        self.assertEqual(lp['accounts'][0]['delegate'],None)
        self.assertEqual(len(lp['missing']),1);self.assertEqual(lp['observed_atomic'],'450')
        self.assertEqual(lp['enumeration'],'explicit_subset_not_exhaustive')
        self.assertIsNone(lp['locked_share']);self.assertIsNone(result['all_principal_locked'])

    def test_same_slot_other_request_cannot_supply_lp_percentage(self):
        target,a,values=fixture();observations=batch(values)
        observations[a['holder']]=batch({a['holder']:values[a['holder']]},name='lp-later')[a['holder']]
        lp=cp.analyze(target,a['pool'],observations,lp_accounts=[a['holder']])['lp_custody']
        self.assertEqual(lp['observed_atomic'],'0');self.assertEqual(len(lp['missing']),1)
        self.assertEqual(lp['accounts'],[])

    def test_pool_read_plan_keeps_denominators_and_vaults_in_one_bounded_batch(self):
        target,a,values=fixture();packets=batch(values)
        rows=pool_sample('raydium_cpmm',a['pool'],packets[a['pool']],lp_accounts=[a['holder']])
        self.assertEqual(len(rows),1);self.assertTrue(rows[0]['critical'])
        self.assertTrue(set([a['pool'],*a['mints'],*a['vaults'],a['lp'],a['config'],a['holder']]) <= set(rows[0]['params'][0]))
        self.assertEqual(rows[0]['params'][1]['minContextSlot'],100)

    def test_declared_rank_retains_unpriced_conflicts_and_cap_exclusions(self):
        target,a,_=fixture()
        def row(n,price):return {'pool':key(n),'target_mint':target['mint'],'genesis_hash':target['genesis_hash'],
            'base_mint':a['mints'][0],'quote_mint':a['mints'][1], 'source':'dexscreener','evidence':['capture'],
            'liquidity_usd':price,'conflicts':[]}
        packet={'target':target,'candidates':[row(60,'10'),row(61,None),row(62,'20'),row(63,'30')],'rejected':[]}
        result=select_pools([packet],target,maximum=1)
        self.assertEqual(result['selected'][0]['pool'],key(63));self.assertEqual(len(result['excluded']),3)
        self.assertEqual(result['canonical_status'],'not_asserted')
        packet['candidates'][3]['conflicts']=['different claims']
        self.assertEqual(select_pools([packet],target,maximum=1)['selected'][0]['pool'],key(62))


if __name__=='__main__':unittest.main()
