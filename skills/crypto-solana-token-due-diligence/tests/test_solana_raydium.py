import base64
from pathlib import Path
import struct
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from adapters import raydium_cpmm as cp, raydium_amm_v4 as amm
from pool_fixture import fixture, batch, key, holding
from solana_common import base58_bytes, TOKEN_PROGRAM


def mutate(value, offset, data):
    raw=bytearray(base64.b64decode(value['data'][0]));raw[offset:offset+len(data)]=data
    return {**value,'data':[base64.b64encode(raw).decode(),'base64']}


class RaydiumTests(unittest.TestCase):
    def test_cpmm_exact_reserves_fee_buckets_and_two_lp_denominators(self):
        target,a,values=fixture()
        result=cp.analyze(target,a['pool'],batch(values),lp_accounts=[a['holder']])
        self.assertEqual(result['reserves_atomic'],['9860','19740'])
        self.assertEqual(result['reserved_fees_atomic'],['140','260'])
        lp=result['lp_custody'];self.assertEqual(lp['observed_atomic'],'450')
        self.assertEqual(lp['mint_supply_atomic'],'900');self.assertEqual(lp['pool_accounting_supply_atomic'],'1000')
        self.assertEqual(lp['accounts'][0]['delegate'],key(36))
        self.assertIsNone(lp['locked_share']);self.assertIsNone(result['all_principal_locked'])
        self.assertIn('program_control_not_observed',result['gaps'])

    def test_cpmm_missing_config_retains_vaults_without_reserve_assertion(self):
        target,a,values=fixture();del values[a['config']]
        result=cp.analyze(target,a['pool'],batch(values))
        self.assertEqual(len(result['vaults']),2);self.assertIsNone(result['reserves_atomic'])
        self.assertTrue(any('missing dependency' in g for g in result['gaps']))

    def test_cpmm_rejects_owner_layout_mint_and_pda_substitution(self):
        for change in ('owner','discriminator','mint','vault_pda'):
            target,a,values=fixture()
            if change=='owner':values[a['pool']]['owner']=amm.PROGRAM
            if change=='discriminator':values[a['pool']]=mutate(values[a['pool']],0,bytes(8))
            if change=='mint':target['mint']=key(70)
            if change=='vault_pda':values[a['pool']]=mutate(values[a['pool']],72,base58_bytes(key(71),32))
            with self.subTest(change=change),self.assertRaises(ValueError):cp.analyze(target,a['pool'],batch(values))

    def test_both_families_reject_wrong_vault_owner_mint_and_program(self):
        for kind,module in [('cpmm',cp),('amm',amm)]:
            for change in ('owner','mint','program'):
                target,a,values=fixture(kind)
                v=a['vaults'][0]
                if change=='owner':values[v]=holding(a['mints'][0],key(80),10000)
                if change=='mint':values[v]=holding(key(80),a['authority'],10000)
                if change=='program':values[v]['owner']=cp.PROGRAM
                result=module.analyze(target,a['pool'],batch(values))
                with self.subTest(kind=kind,change=change):
                    self.assertIsNone(result['reserves_atomic']);self.assertTrue(result['gaps'])

    def test_amm_vault_only_modes_and_fee_validation(self):
        target,a,values=fixture('amm')
        result=amm.analyze(target,a['pool'],batch(values),lp_accounts=[a['holder']])
        self.assertEqual(result['reserves_atomic'],['9900','19800'])
        self.assertEqual(result['lp_custody']['observed_atomic'],'450')
        values[a['pool']]=mutate(values[a['pool']],152,bytes(8))
        result=amm.analyze(target,a['pool'],batch(values))
        self.assertIsNone(result['reserves_atomic']);self.assertEqual(len(result['vaults']),2)

    def test_amm_maker_event_pnl_and_version_ambiguity(self):
        target,a,values=fixture('amm',status=1)
        result=amm.analyze(target,a['pool'],batch(values))
        # 300 coin + 70 received; 600 quote - 100 paid, then vault - PnL.
        self.assertEqual(result['open_orders_adjusted_atomic'],['370','500'])
        self.assertEqual(result['reserve_variants_atomic']['legacy_openbook'],['10270','20300'])
        self.assertEqual(result['reserve_variants_atomic']['current_vault_only'],['9900','19800'])
        self.assertIsNone(result['reserves_atomic']);self.assertIsNone(result['exit_executable'])

    def test_amm_missing_or_foreign_open_orders_queue_and_market_refuse_overclaim(self):
        for change in ('missing_oo','missing_queue','foreign_market','wrong_order_owner','wrong_queue_owner'):
            target,a,values=fixture('amm',status=1)
            if change=='missing_oo':del values[a['oo']]
            if change=='missing_queue':del values[a['event']]
            if change=='foreign_market':values[a['market']]=mutate(values[a['market']],53,base58_bytes(key(80),32))
            if change=='wrong_order_owner':values[a['oo']]=mutate(values[a['oo']],45,base58_bytes(key(80),32))
            if change=='wrong_queue_owner':values[a['event']]['owner']=cp.PROGRAM
            result=amm.analyze(target,a['pool'],batch(values))
            with self.subTest(change=change):
                self.assertIsNone(result['reserves_atomic']);self.assertEqual(len(result['vaults']),2)
                self.assertNotIn('reserve_variants_atomic',result)

    def test_amm_wrong_program_layout_target_are_rejected(self):
        for change in ('owner','short','mint'):
            target,a,values=fixture('amm')
            if change=='owner':values[a['pool']]['owner']=cp.PROGRAM
            if change=='short':values[a['pool']]['space']=751
            if change=='mint':target['mint']=key(80)
            with self.subTest(change=change),self.assertRaises(ValueError):amm.analyze(target,a['pool'],batch(values))

    def test_cpmm_fee_underflow_and_mixed_requests_do_not_produce_reserves(self):
        target,a,values=fixture();values[a['pool']]=mutate(values[a['pool']],341,struct.pack('<Q',20000))
        self.assertIsNone(cp.analyze(target,a['pool'],batch(values))['reserves_atomic'])
        target,a,values=fixture();observations=batch(values)
        observations[a['vaults'][0]]=batch({a['vaults'][0]:values[a['vaults'][0]]},name='other')[a['vaults'][0]]
        result=cp.analyze(target,a['pool'],observations)
        self.assertIsNone(result['reserves_atomic']);self.assertTrue(any('one account batch' in g for g in result['gaps']))

    def test_cpmm_reserved_config_and_lp_decimals_are_not_silently_accepted(self):
        for change in ('config_padding','pool_padding','lp_decimals','config_index'):
            target,a,values=fixture()
            if change=='config_padding':values[a['config']]=mutate(values[a['config']],235,b'\1')
            if change=='pool_padding':values[a['pool']]=mutate(values[a['pool']],636,b'\1')
            if change=='lp_decimals':values[a['lp']]=mutate(values[a['lp']],44,b'\6')
            if change=='config_index':values[a['config']]=mutate(values[a['config']],10,b'\2')
            result=cp.analyze(target,a['pool'],batch(values))
            with self.subTest(change=change):
                self.assertTrue(result['gaps']);self.assertIsNone(result['lp_custody'])
                if change!='lp_decimals':self.assertIsNone(result['reserves_atomic'])

    def test_amm_pnl_can_exceed_vault_when_legacy_orderbook_covers_it(self):
        target,a,values=fixture('amm',status=1)
        values[a['pool']]=mutate(values[a['pool']],192,struct.pack('<Q',10200))
        result=amm.analyze(target,a['pool'],batch(values))
        self.assertEqual(result['reserve_variants_atomic']['legacy_openbook'],['170','20300'])
        self.assertIsNone(result['reserve_variants_atomic']['current_vault_only'])
        self.assertIsNone(result['reserves_atomic'])

    def test_program_upgrade_control_is_observed_separately_from_lp_owners(self):
        from solana_programs import UPGRADEABLE
        from solana_addresses import find_program_address
        from solana_fixture import account
        target,a,values=fixture()
        pd=find_program_address([base58_bytes(cp.PROGRAM,32)],UPGRADEABLE)[0]
        values[cp.PROGRAM]={**account(struct.pack('<I',2)+base58_bytes(pd,32)), 'owner':UPGRADEABLE,'executable':True}
        values[pd]={**account(struct.pack('<IQB',3,90,1)+base58_bytes(key(72),32)), 'owner':UPGRADEABLE}
        result=cp.analyze(target,a['pool'],batch(values),lp_accounts=[a['holder']])
        self.assertEqual(result['program_control']['upgrade_authority'],key(72))
        self.assertEqual(result['lp_custody']['accounts'][0]['spending_owner'],key(31))
        self.assertEqual(result['status'],'observed')
        self.assertIsNone(result['all_principal_locked'])


if __name__=='__main__':unittest.main()
