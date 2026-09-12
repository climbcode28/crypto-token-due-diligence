from pathlib import Path
import sys,unittest,copy
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from pump_fixture import fixture,batch,curve,swap,key,fee_address,WSOL,owned,put
from test_solana_raydium import mutate


class PumpTests(unittest.TestCase):
    def test_retained_public_allocations_zero_padding_and_completed_zero_reserves(self):
        import json,base64
        data=json.loads((Path(__file__).parent/'fixtures/acceptance/pump-live-accounts.json').read_text())
        pool,curve_row=data['accounts'];p=swap.decode_pool(pool['account']);c=curve.decode_pool(curve_row['account'])
        self.assertEqual(p['allocated_padding_bytes'],40);self.assertEqual(p['virtual_quote_reserves'],17584505289)
        self.assertEqual(p['base_mint'],'2fRDA5f353VXLs2PeLJNqqHqTMhrjJunAXmWWpLkpump')
        self.assertEqual(c['allocated_padding_bytes'],9);self.assertTrue(c['complete']);self.assertTrue(c['zero_completed_reserves'])
        self.assertEqual(c['token_total_supply'],1000000000000000)
        self.assertTrue(all(c[k]==0 for k in ('virtual_token_reserves','virtual_quote_reserves','real_token_reserves','real_quote_reserves')))
        for row,decoder in ((pool,swap.decode_pool),(curve_row,curve.decode_pool)):
            value=copy.deepcopy(row['account']);raw=bytearray(base64.b64decode(value['data'][0]));raw[-1]=1;value['data'][0]=base64.b64encode(raw).decode()
            with self.assertRaisesRegex(ValueError,'reserved layout extension'):decoder(value)
        value=copy.deepcopy(curve_row['account']);raw=bytearray(base64.b64decode(value['data'][0]));raw[48]=0;value['data'][0]=base64.b64encode(raw).decode()
        with self.assertRaisesRegex(ValueError,'token reserves'):curve.decode_pool(value)

    def test_pre_and_completed_curve_are_not_migrated(self):
        for complete in (False,True):
            target,a,v=fixture(complete=complete);r=curve.analyze(target,a['curve'],batch(v))
            self.assertEqual(r['stage'],'completed_curve_migration_unverified' if complete else 'pre_migration_curve')
            self.assertIsNone(r['migration']);self.assertEqual(r['reserves_atomic'],['0' if complete else '500','1000'])
            self.assertEqual(r['virtual_reserves_atomic'],['1000','2000']);self.assertEqual(r['native_non_reserve_lamports'],'2000')
            self.assertEqual(r['selected_fees']['fees']['creator_fee_bps'],'10')
            self.assertIsNone(r['creator_role']['human_identity'])

    def test_pumpswap_actual_virtual_accounting_and_creator_roles(self):
        target,a,v=fixture();r=swap.analyze(target,a['pool'],batch(v),lp_accounts=[a['holder']])
        self.assertEqual(r['reserves_atomic'],['10000','20000']);self.assertEqual(r['selected_fees']['fees']['lp_fee_bps'],'20')
        lp=r['lp_custody'];self.assertEqual(lp['observed_atomic'],'450');self.assertEqual(lp['mint_supply_atomic'],'900');self.assertEqual(lp['pool_accounting_supply_atomic'],'1000')
        self.assertNotEqual(r['creator_roles']['pool_creator'],r['creator_roles']['coin_creator']);self.assertIsNone(lp['locked_share'])
        target,a,v=fixture(virtual=-1000);r=swap.analyze(target,a['pool'],batch(v))
        self.assertEqual(r['reserves_atomic'],['10000','20000']);self.assertEqual(r['effective_pricing_reserves_atomic'],['10000','19000'])
        self.assertNotIn('selected_fees',r);self.assertTrue(r['gaps'])

    def test_non_native_quote_has_distinct_holding_and_unknown_new_fee_rules(self):
        target,a,v=fixture(non_native=True);r=curve.analyze(target,a['curve'],batch(v))
        self.assertEqual(r['reserves_atomic'],['500','1000']);self.assertNotIn('native_lamports',r)
        self.assertNotIn('selected_fees',r);self.assertIn('stable_fee_tiers',r['fee_config'])
        del v[a['quote_holding']];r=curve.analyze(target,a['curve'],batch(v));self.assertIsNone(r['reserves_atomic'])

    def test_stale_unknown_program_discriminator_and_fake_suffix_rejected(self):
        import base64
        from solana_common import b58encode
        target,a,v=fixture()
        # A valid 32-byte key ending in 'pump' is still not a target-bound curve.
        from solana_common import ALPHABET
        number=int.from_bytes(bytes([9])*32,'big');radix=58**4
        suffix=0
        for c in 'pump':suffix=suffix*58+ALPHABET.index(c)
        fake=b58encode((number//radix*radix+suffix).to_bytes(32,'big'));self.assertTrue(fake.endswith('pump'))
        with self.assertRaises(ValueError):curve.analyze({**target,'mint':fake},a['curve'],batch(v))
        for kind in ('old','owner','disc','tail'):
            value=copy.deepcopy(v[a['curve']]);raw=base64.b64decode(value['data'][0])
            if kind=='old':value=owned(raw[:83],curve.PROGRAM)
            if kind=='owner':value['owner']=swap.PROGRAM
            if kind=='disc':value=mutate(value,0,bytes(8))
            if kind=='tail':value=owned(raw+bytes(34)+b'\1',curve.PROGRAM)
            with self.assertRaises(ValueError):curve.decode_pool(value)

    def test_mismatch_same_bank_fee_configuration_and_vault_fail_closed(self):
        for case in ('mint','vault','fee','mixed','completed','pool_pda'):
            target,a,v=fixture();obs=batch(v)
            if case=='mint':v[a['mints'][0]]['owner']=key(90)
            if case=='vault':v[a['vaults'][0]]=mutate(v[a['vaults'][0]],32,bytes([90])*32)
            if case=='fee':v[fee_address(swap.PROGRAM)]=mutate(v[fee_address(swap.PROGRAM)],41,(10000).to_bytes(8,'little'))
            if case=='mixed':obs[a['vaults'][0]]=batch(v,name='other')[a['vaults'][0]]
            if case=='completed':
                v[a['curve']]=mutate(v[a['curve']],48,b'\1')
                with self.assertRaises(ValueError):curve.analyze(target,a['curve'],batch(v))
                continue
            if case=='pool_pda':
                with self.assertRaises(ValueError):swap.analyze(target,key(80),{key(80):obs[a['pool']]})
                continue
            r=swap.analyze(target,a['pool'],obs if case=='mixed' else batch(v))
            self.assertTrue(r['gaps']);self.assertNotIn('selected_fees',r)

    def test_all_eight_explicit_dispatch_and_pump_presets(self):
        from adapters import pool_adapter
        from solana_presets import pump_sample
        names=('raydium_cpmm','raydium_amm_v4','raydium_clmm','orca_whirlpool','meteora_dlmm','meteora_damm_v2','pump_curve','pumpswap')
        for name in names:self.assertEqual(pool_adapter(name).CAPABILITY['id'],name)
        target,a,v=fixture();obs=batch(v)
        for name in ('pump_curve','pumpswap'):
            rows=pump_sample(name,target,{'pool':a['pool'],'packets':obs})
            self.assertEqual(len(rows),1);self.assertIn(fee_address(pool_adapter(name).PROGRAM),rows[0]['params'][0])


if __name__=='__main__':unittest.main()
