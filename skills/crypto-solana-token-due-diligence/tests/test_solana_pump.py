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
        self.assertEqual(p['allocated_padding_bytes'],30);self.assertEqual(p['virtual_quote_reserves'],17584505289)  # the 301-byte allocation holds the zeroed tail group
        self.assertEqual((p['creator_fee_bps'],p['can_edit_creator_fee'],p['is_holder_reward'],p['absent_fields']),(0,False,False,[]))
        self.assertEqual(p['base_mint'],'2fRDA5f353VXLs2PeLJNqqHqTMhrjJunAXmWWpLkpump')
        self.assertEqual(c['allocated_padding_bytes'],9);self.assertTrue(c['complete']);self.assertTrue(c['zero_completed_reserves'])
        self.assertEqual(c['absent_fields'],['creator_fee_bps','can_edit_creator_fee','is_holder_reward'])  # a 124-byte allocation predates the tail group
        self.assertEqual(c['token_total_supply'],1000000000000000)
        self.assertTrue(all(c[k]==0 for k in ('virtual_token_reserves','virtual_quote_reserves','real_token_reserves','real_quote_reserves')))
        for row,decoder in ((pool,swap.decode_pool),(curve_row,curve.decode_pool)):
            value=copy.deepcopy(row['account']);raw=bytearray(base64.b64decode(value['data'][0]));raw[-1]=1;value['data'][0]=base64.b64encode(raw).decode()
            with self.assertRaisesRegex(ValueError,'reserved layout extension'):decoder(value)
        value=copy.deepcopy(curve_row['account']);raw=bytearray(base64.b64decode(value['data'][0]));raw[48]=0;value['data'][0]=base64.b64encode(raw).decode()
        with self.assertRaisesRegex(ValueError,'token reserves'):curve.decode_pool(value)

    def test_zero_padded_allocations_of_any_length_decode_and_truncation_is_refused(self):
        import base64
        target,a,v=fixture()
        def resized(address,size):
            value=copy.deepcopy(v[address]);raw=base64.b64decode(value['data'][0]);raw=raw+bytes(size-len(raw)) if size>len(raw) else raw[:size]
            value['data'][0]=base64.b64encode(raw).decode();value['space']=len(raw);return value
        # A longer zero-padded allocation (the live 151-byte curve of 2026-09-12) decodes: the tail group is read as zeros.
        c=curve.decode_pool(resized(a['curve'],151));self.assertEqual((c['allocated_padding_bytes'],c['absent_fields'],c['creator_fee_bps'],c['tail_group_zero']),(26,[],0,True))
        self.assertIsNone(curve.decode_pool(v[a['curve']])['tail_group_zero'])  # a pre-upgrade allocation has no tail group at all
        p=swap.decode_pool(resized(a['pool'],300));self.assertEqual((p['allocated_padding_bytes'],p['absent_fields']),(29,[]))
        for address,decoder,size in ((a['curve'],curve.decode_pool,100),(a['pool'],swap.decode_pool,200)):
            with self.assertRaisesRegex(ValueError,'truncated binary account'):decoder(resized(address,size))
        self.assertEqual(curve.CAPABILITY['allocation_bytes'],[115,124,125,151]);self.assertEqual(swap.CAPABILITY['allocation_bytes'],[261,271,301])
        for cap in (curve.CAPABILITY,swap.CAPABILITY):self.assertIn('nonzero tail is refused',cap['reserved_tail_policy'])

    def test_upgraded_allocations_carry_the_creator_fee_and_holder_reward_tail(self):
        import base64,struct
        from pump_fixture import batch
        target,a,v=fixture()
        def extended(address,size,writes):
            value=copy.deepcopy(v[address]);raw=bytearray(base64.b64decode(value['data'][0]));raw+=bytes(size-len(raw))
            for offset,fmt,val in writes:struct.pack_into(fmt,raw,offset,val)
            value['data'][0]=base64.b64encode(bytes(raw)).decode();value['space']=len(raw);return value
        v[a['curve']]=extended(a['curve'],151,[(115,'<Q',150),(123,'<B',1),(124,'<B',1)])
        v[a['pool']]=extended(a['pool'],301,[(261,'<Q',75),(269,'<B',1),(270,'<B',0)])
        v[curve.GLOBAL]=extended(curve.GLOBAL,1087,[(1045,'<B',1),(1046,'<Q',1000),(1086,'<B',1)]);v[swap.GLOBAL]=extended(swap.GLOBAL,949,[(940,'<B',1),(941,'<Q',500)])
        c=curve.decode_pool(v[a['curve']]);self.assertEqual((c['creator_fee_bps'],c['can_edit_creator_fee'],c['is_holder_reward'],c['absent_fields'],c['allocated_padding_bytes'],c['tail_group_zero']),(150,True,True,[],26,False))
        with self.assertRaisesRegex(ValueError,'creator fee rate'):curve.decode_pool(extended(a['curve'],151,[(115,'<Q',20000)]))
        over=curve.analyze(target,a['curve'],batch({**v,a['curve']:extended(a['curve'],151,[(115,'<Q',1500)])}));self.assertIn('creator fee exceeds the configurable maximum',over['gaps'])
        p=swap.decode_pool(v[a['pool']]);self.assertEqual((p['creator_fee_bps'],p['can_edit_creator_fee'],p['is_holder_reward'],p['allocated_padding_bytes']),(75,True,False,30))
        r=curve.analyze(target,a['curve'],batch(v));self.assertEqual((r['global']['creator_fee_configurable'],r['global']['max_configurable_creator_fee_bps'],r['global']['is_holder_reward_enabled']),(True,1000,True))
        r=swap.analyze(target,a['pool'],batch(v));self.assertEqual((r['global']['creator_fee_configurable'],r['global']['max_configurable_creator_fee_bps']),(True,500));self.assertEqual(r['reserves_atomic'],['10000','20000'])
        self.assertIsNone(r['fee_config']['exotic_flat_fees']);self.assertIsNone(r['fee_config']['exotic_flat_fees_zero'])

    def test_extended_fee_config_with_many_tiers_decodes(self):
        import struct
        from adapters.pump_common import decode_fees,FEE_PROGRAM
        from adapters.binary import discriminator
        from solana_addresses import find_program_address
        from solana_common import base58_bytes
        address,bump=find_program_address([b'fee_config',base58_bytes(swap.PROGRAM,32)],FEE_PROGRAM)
        tier=lambda i:(i*1000).to_bytes(16,'little')+struct.pack('<3Q',20,5,5)
        raw=discriminator('FeeConfig')+bytes([bump])+base58_bytes(key(60),32)+struct.pack('<3Q',25,5,0)+struct.pack('<I',25)+b''.join(tier(i) for i in range(25))+struct.pack('<I',25)+b''.join(tier(i) for i in range(25))+struct.pack('<3Q',20,5,5)
        raw+=bytes(4097-len(raw))  # the live extend_fee_config allocation
        fees=decode_fees(address,owned(raw,FEE_PROGRAM),swap.PROGRAM)
        self.assertEqual((len(fees['fee_tiers']),len(fees['stable_fee_tiers']),fees['exotic_flat_fees'],fees['exotic_flat_fees_zero']),(25,25,{'lp_fee_bps':'20','protocol_fee_bps':'5','creator_fee_bps':'5'},False))
        self.assertEqual(fees['fee_tiers'][3]['market_cap_quote_atomic_threshold'],'3000')

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
            self.assertIn(pool_adapter(name).PROGRAM,rows[0]['params'][0])  # the program account is a dependency for both products


if __name__=='__main__':unittest.main()
