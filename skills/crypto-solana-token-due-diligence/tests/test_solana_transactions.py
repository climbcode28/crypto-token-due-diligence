from pathlib import Path
import copy
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from solana_transactions import decode_transaction,data_bytes
from solana_common import b58encode
from transaction_fixture import fixture


class TransactionTests(unittest.TestCase):
    def test_initialization_variants_require_their_actual_accounts(self):
        from solana_transactions import token_effect
        from solana_common import TOKEN_PROGRAM
        from pool_fixture import key
        accounts=[key(i+40) for i in range(4)]
        for op,count in ((1,4),(16,3),(18,2)):
            raw=bytes([op])+(bytes(32) if op!=1 else b'')
            self.assertEqual(token_effect(raw,accounts[:count],{},TOKEN_PROGRAM)['kind'],'token_account_initialize')
            with self.assertRaises(ValueError):token_effect(raw,accounts[:count-1],{},TOKEN_PROGRAM)

    def test_legacy_v0_historical_loaded_keys_equivalent(self):
        results=[]
        for v in ('legacy',0):
            target,a,p,b=fixture(v);r=decode_transaction(target,p,b)
            self.assertEqual(r['execution_status'],'succeeded');self.assertEqual(r['gaps'],[])
            self.assertEqual(len(r['effects']),3);self.assertEqual(r['network_fee_lamports'],'5000')
            self.assertEqual(r['effects'][1]['locator'],{'outer_index':0,'inner_index':0})
            results.append(r['effects'])
        self.assertEqual(results[0],results[1])

    def test_missing_loaded_accounts_header_or_balance_prevents_effects(self):
        for change in ('loaded','short_native','missing_tokens','inner','lookup','index','header','readonly'):
            target,a,p,b=fixture(0);tx=p['response']['result'];meta=tx['meta'];message=tx['transaction']['message']
            if change=='loaded':del meta['loadedAddresses']
            if change=='short_native':meta['postBalances'].pop()
            if change=='missing_tokens':meta['preTokenBalances']=None
            if change=='inner':meta['innerInstructions']=None
            if change=='lookup':message['addressTableLookups'][0]['writableIndexes'].pop()
            if change=='index':message['instructions'][0]['programIdIndex']=255
            if change=='header':b['request']['params'][0]=101
            if change=='readonly':message['header']['numReadonlyUnsignedAccounts']=len(message['accountKeys'])-2
            r=decode_transaction(target,p,b)
            if change=='readonly':self.assertFalse(any(e['kind']=='transfer' for e in r['effects']))
            else:self.assertEqual(r['effects'],[])
            self.assertTrue(r['gaps'])

    def test_failed_transaction_has_fee_but_no_reverted_token_effects(self):
        target,a,p,b=fixture();p['response']['result']['meta']['err']={'InstructionError':[0,'Custom']}
        r=decode_transaction(target,p,b)
        self.assertEqual(r['execution_status'],'failed');self.assertEqual(r['network_fee_lamports'],'5000');self.assertEqual(r['effects'],[])

    def test_unknown_version_and_conflicting_time_status(self):
        for kind in ('version','time','status','duplicate'):
            target,a,p,b=fixture();tx=p['response']['result']
            if kind=='version':tx['version']=1
            if kind=='time':tx['blockTime']=1001
            if kind=='status':tx['meta']['status']={'Err':{'bad':1}}
            if kind=='duplicate':tx['transaction']['message']['accountKeys'][2]=a['payer']
            self.assertEqual(decode_transaction(target,p,b)['effects'],[])

    def test_wrong_requested_signature_and_raw_encoding_rejected(self):
        target,a,p,b=fixture();p['request']['params'][0]=b58encode(bytes([8])*64)
        with self.assertRaises(ValueError):decode_transaction(target,p,b)
        for s in ('0','a'*14001):
            with self.assertRaises(ValueError):data_bytes(s)
        self.assertEqual(data_bytes(''),b'')

    def test_mint_burn_authority_effect_types_have_locators(self):
        import struct
        target,a,p,b=fixture();tx=p['response']['result'];inner=tx['meta']['innerInstructions'][0]['instructions']
        mint_index=a['keys'].index(a['input_mint']);source_index=a['keys'].index(a['source']);owner_index=a['keys'].index(a['owner'])
        for op,args,raw,kind in [(14,[mint_index,source_index,owner_index],struct.pack('<BQB',14,123,6),'mint'),
                                  (15,[source_index,mint_index,owner_index],struct.pack('<BQB',15,123,6),'burn'),
                                  (6,[source_index,owner_index],bytes([6,2,0]),'authority_change')]:
            inner[0]['accounts']=args;inner[0]['data']=b58encode(raw)
            r=decode_transaction(target,p,b);e=r['effects'][1]
            self.assertEqual(e['kind'],kind);self.assertEqual(e['locator']['inner_index'],0)

    def test_each_enabled_swap_role_decoder_is_distinct_and_rejects_short_layout(self):
        import struct
        from solana_swaps import decode,tag,cp,amm,clmm,orca,dlmm,damm
        from pool_fixture import key
        from solana_common import TOKEN_PROGRAM
        for module,n,raw,pool_index,source_index in [
            (clmm,14,tag('swap_v2')+struct.pack('<QQ',1000,400)+bytes(16)+b'\1',2,3),
            (orca,15,tag('swap_v2')+struct.pack('<QQ',1000,400)+bytes(16)+b'\1\1\0',4,7),
            (dlmm,16,tag('swap2')+struct.pack('<QQ',1000,400)+bytes(4),0,4),
            (damm,14,tag('swap2')+struct.pack('<QQB',1000,400,0),1,2),
            (amm,8,struct.pack('<BQQ',16,1000,400),1,5),
            (amm,17,struct.pack('<BQQ',9,1000,400),1,14)]:
            accounts=[key(i+30) for i in range(n)]
            if module is amm:accounts[0]=TOKEN_PROGRAM
            result=decode(module.PROGRAM,raw,accounts)
            self.assertEqual(result['pool'],accounts[pool_index]);self.assertEqual(result['input_account'],accounts[source_index])
            self.assertEqual(result['mode'],'exact_in');self.assertEqual(result['specified_amount_atomic'],'1000')
            with self.assertRaises(ValueError):decode(module.PROGRAM,raw[:-1],accounts)
            self.assertIsNone(decode(key(90),raw,accounts))

    def test_position_instruction_not_sale_or_current_position_owner(self):
        from solana_swaps import position_instruction,tag,orca,damm,cp,dlmm
        from pool_fixture import key
        import struct
        for module,n,raw,kind in [(orca,10,tag('open_position')+struct.pack('<Bii',255,-100,100),'position_initialize'),
             (damm,11,tag('create_position'),'position_initialize'),
             (dlmm,7,tag('initialize_position2')+struct.pack('<ii',-100,70),'position_initialize'),
             (damm,15,tag('remove_liquidity')+(1000).to_bytes(16,'little')+struct.pack('<QQ',1,1),'position_liquidity_remove'),
             (cp,14,tag('withdraw')+struct.pack('<QQQ',1000,1,1),'position_liquidity_remove')]:
            accounts=[key(i+30) for i in range(n)];effect=position_instruction(module.PROGRAM,raw,accounts)
            self.assertEqual(effect['kind'],kind);self.assertIsNone(effect['amount_atomic'])
            with self.assertRaises(ValueError):position_instruction(module.PROGRAM,raw+b'\0',accounts)

    def test_mint_effect_cannot_name_an_unrelated_historical_mint(self):
        import struct
        target,a,p,b=fixture();ix=p['response']['result']['meta']['innerInstructions'][0]['instructions'][0]
        ix['accounts']=[a['keys'].index(a['output_mint']),a['keys'].index(a['source']),a['keys'].index(a['owner'])]
        ix['data']=b58encode(struct.pack('<BQB',14,123,6))
        result=decode_transaction(target,p,b)
        self.assertFalse(any(e['kind']=='mint' for e in result['effects']));self.assertTrue(result['gaps'])

    def test_bounded_receipt_preset_derives_header_from_returned_slot(self):
        from solana_presets import historical_sample,historical_headers
        _,a,p,b=fixture()
        plan=historical_sample([p['request']['params'][0]])
        self.assertEqual(plan[0]['method'],'getTransaction')
        self.assertEqual(historical_headers([p])[0]['params'][0],100)
        with self.assertRaises(ValueError):historical_sample([p['request']['params'][0]]*3)


if __name__=='__main__':unittest.main()
