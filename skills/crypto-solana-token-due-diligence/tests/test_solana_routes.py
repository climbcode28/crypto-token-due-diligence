"""Routed, fee-emitting, Token-2022 and boundary-limited swap receipts; receipt classification."""
from pathlib import Path
import copy,json,struct,sys,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from solana_transactions import decode_transaction,verify_sales,verify_rebuys,classify_receipt,SYSTEM,WSOL
from solana_common import b58encode,base58_bytes,TOKEN_PROGRAM,TOKEN_2022
from solana_discovery import MAINNET
from transaction_fixture import fixture,key
from solana_swaps import tag
from adapters import raydium_cpmm as cp

LIVE=Path(__file__).resolve().parent/'fixtures/receipts/wif-raydium-amm-v4-routed.json'


def live():
    d=json.loads(LIVE.read_text());target={'family':'solana','genesis_hash':MAINNET,'mint':d['mint']}
    rows=[({'status':'ok',**r['transaction']},{'status':'ok',**r['block']}) for r in d['receipts']]
    return target,d['pool'],rows


def routed(**kwargs):
    """Wrap the fixture's outer CPMM swap in a router CPI: swap at stack 2, its transfers at stack 3."""
    target,a,p,b=fixture(**kwargs);tx=p['response']['result'];message=tx['transaction']['message'];keys=list(message['accountKeys'])
    router=key(60);keys.append(router);message['accountKeys']=keys;n=a['swap_index']
    swap=message['instructions'][n];inner=tx['meta']['innerInstructions'][0]['instructions']
    message['instructions'][n]={'programIdIndex':keys.index(router),'accounts':swap['accounts'],'data':b58encode(b'route'),'stackHeight':1}
    swap['stackHeight']=2
    for ix in inner:ix['stackHeight']=3
    tx['meta']['innerInstructions'][0]['instructions']=[swap,*inner]
    tx['meta']['preBalances'].append(0);tx['meta']['postBalances'].append(0)
    return target,a,p,b


ORCA=Path(__file__).resolve().parent/'fixtures/receipts/wif-orca-legacy-swap.json'


def orca_live():
    d=json.loads(ORCA.read_text());target={'family':'solana','genesis_hash':d['genesis_hash'],'mint':d['mint']}
    headers={v['request']['params'][0]:v for v in d['headers'].values()}
    rows=[(v,headers[v['response']['result']['slot']]) for v in d['transactions'].values()]
    return target,d['pool'],rows


class RouteTests(unittest.TestCase):
    def test_live_legacy_whirlpool_swaps_are_recognized_and_verified(self):
        # Both live Orca receipts use the legacy `swap` instruction (f8c69e91e17587c8, 11 accounts, 42 bytes),
        # one direct and one behind a router CPI; neither carries mint accounts.
        target,pool,rows=orca_live();self.assertEqual(len(rows),2)
        kinds=[classify_receipt(target,p,pool) for p,_ in rows]
        self.assertTrue(all(k['swap'] for k in kinds),kinds);self.assertEqual(sorted(k['route'] for k in kinds),['aggregated','direct'])
        candidates=[{'pool':pool,'execution':decode_transaction(target,p,b)} for p,b in rows]
        sales=verify_sales(target,candidates);rebuys=verify_rebuys(target,candidates)
        verified=[r for r in sales['receipts'] if r['status']=='verified_sale']+[r for r in rebuys['receipts'] if r['status']=='verified_rebuy']
        self.assertEqual(len(verified),2,(sales,rebuys))
        for row in verified:
            self.assertEqual(row['counter_mint'],WSOL);self.assertTrue(int(row['input_atomic'])>0 and int(row['output_atomic'])>0)
        self.assertEqual({k['direction'] for k in kinds},{r['direction'] if 'direction' in r else ('sell' if r['status']=='verified_sale' else 'buy') for r in verified})


    def test_live_router_receipts_verify_as_aggregated_sales_with_distinct_fee_payer(self):
        target,pool,rows=live();candidates=[{'pool':pool,'execution':decode_transaction(target,p,b)} for p,b in rows]
        result=verify_sales(target,candidates)
        self.assertEqual(result['verified_receipts'],2)
        for (p,_),row,expected in zip(rows,result['receipts'],(('3607631056','6892742849'),('1946690646','3720802120'))):
            self.assertEqual((row['status'],row['route'],row['input_atomic'],row['output_atomic'],row['counter_mint']),('verified_sale','aggregated',*expected,WSOL))
            # The seller is the RPC-reported owner of the target token account, never the fee payer.
            owners={b['owner'] for b in p['response']['result']['meta']['preTokenBalances'] if b['mint']==target['mint'] and b['owner']!='5Q544fKrFoe6tsEbD7S8EmxGTJYAKtTVhAW5Q5pge4j1'}
            self.assertEqual({row['seller']},owners);self.assertEqual(row['counter_asset_realization'],'retained_in_recipient_account')
            self.assertEqual(row['protocol_fees_atomic'],[]);self.assertIsNone(row['native_proceeds']);self.assertIsNone(row['profit'])
        self.assertNotEqual(candidates[0]['execution']['fee_payer'],result['receipts'][0]['seller'])
        self.assertEqual(verify_rebuys(target,candidates)['verified_receipts'],0)
        for p,_ in rows:
            c=classify_receipt(target,p,pool);self.assertEqual((c['swap'],c['direction'],c['route']),(True,'sell','aggregated'))
        self.assertFalse(classify_receipt(target,rows[0][0],key(80))['swap'])

    def test_synthetic_router_wrapping_verifies_and_nested_frame_needs_stack_heights(self):
        target,a,p,b=routed();e=decode_transaction(target,p,b)
        self.assertEqual(e['gaps'],[]);row=verify_sales(target,[{'pool':a['pool'],'execution':e}])['receipts'][0]
        self.assertEqual((row['status'],row['route'],row['seller']),('verified_sale','aggregated',a['owner']))
        stripped=copy.deepcopy(e)
        for i in stripped['instructions']:i['stack_height']=None
        for x in stripped['effects']:x['stack_height']=None
        row=verify_sales(target,[{'pool':a['pool'],'execution':stripped}])['receipts'][0]
        self.assertEqual(row['status'],'unverified');self.assertIn('stack heights',row['gaps'][0])

    def test_transfer_outside_the_swap_frame_is_not_part_of_the_leg(self):
        target,a,p,b=routed();tx=p['response']['result'];inner=tx['meta']['innerInstructions'][0]['instructions']
        # A sibling CPI after the swap frame at the router's level: the frame ends there.
        keys=tx['transaction']['message']['accountKeys'];stray=copy.deepcopy(inner[2]);stray['stackHeight']=2;inner.append(stray)
        e=decode_transaction(target,p,b);row=verify_sales(target,[{'pool':a['pool'],'execution':e}])['receipts'][0]
        self.assertEqual(row['status'],'unverified');self.assertIn('touch sale accounts',row['gaps'][0])

    def test_declared_fee_sinks_are_recorded_and_undeclared_flows_refused(self):
        target,a,p,b=fixture();e=decode_transaction(target,p,b);out=e['effects'][2]
        sink=key(66);fee=copy.deepcopy(out);fee['id']='fee';fee['amount_atomic']='7';fee['participants']={**out['participants'],'destination':sink}
        fee['locator']={'outer_index':out['locator']['outer_index'],'inner_index':2};e['effects'].append(fee);e['instructions'].append({**e['instructions'][-1],'id':'fee','locator':fee['locator'],'stack_height':2})
        e['post_token_balances'][a['output_vault']]['amount_atomic']=str(int(e['post_token_balances'][a['output_vault']]['amount_atomic'])-7)
        for side,value in (('pre_token_balances','0'),('post_token_balances','7')):e[side][sink]={'mint':out['mint'],'owner':key(67),'program':TOKEN_PROGRAM,'amount_atomic':value,'decimals':6}
        row=verify_sales(target,[{'pool':a['pool'],'execution':e}])['receipts'][0]
        self.assertEqual(row['status'],'unverified');self.assertIn('ambiguous',row['gaps'][0])
        e['effects'][0]['fee_accounts']=[sink]
        row=verify_sales(target,[{'pool':a['pool'],'execution':e}])['receipts'][0]
        self.assertEqual(row['status'],'verified_sale');self.assertEqual(row['protocol_fees_atomic'],[{'effect_id':'fee','mint':out['mint'],'amount_atomic':'7','destination':sink}])
        self.assertIn('fee',row['effect_ids'])

    def test_pumpswap_sell_declares_protocol_and_creator_fee_sinks(self):
        from solana_swaps import decode as swap_decode
        from adapters import pump_swap as pump
        accounts=[key(100+i) for i in range(21)];accounts[11]=accounts[12]=TOKEN_PROGRAM
        result=swap_decode(pump.PROGRAM,tag('sell')+struct.pack('<QQ',1000,1),accounts)
        self.assertEqual(result['fee_accounts'],[accounts[10],accounts[17]])
        accounts[10]=accounts[7]
        with self.assertRaises(ValueError):swap_decode(pump.PROGRAM,tag('sell')+struct.pack('<QQ',1000,1),accounts)

    def test_pumpswap_trades_accept_router_remaining_accounts_and_optional_track_flag(self):
        from solana_swaps import decode as swap_decode
        from adapters import pump_swap as pump
        # Live routers (2026-09-12) append remaining accounts after the named roles and omit the trailing track_volume flag.
        accounts=[key(100+i) for i in range(24)];accounts[11]=accounts[12]=TOKEN_PROGRAM
        sell=swap_decode(pump.PROGRAM,tag('sell')+struct.pack('<QQ',1000,1),accounts)
        self.assertEqual((sell['pool'],sell['input_account'],sell['output_account'],sell['vaults'],sell['mode']),(accounts[0],accounts[5],accounts[6],accounts[7:9],'exact_in'))
        buy=swap_decode(pump.PROGRAM,tag('buy_exact_quote_in')+struct.pack('<QQ',2000,1),accounts+[key(130),key(131)])
        self.assertEqual((buy['input_account'],buy['output_account'],buy['mode'],buy['fee_accounts']),(accounts[6],accounts[5],'exact_in_fee_inclusive',[accounts[10],accounts[17],accounts[23],key(130),key(131)]))
        self.assertEqual(sell['fee_accounts'],[accounts[10],accounts[17],accounts[21],accounts[22],accounts[23]])  # appended accounts are candidate fee sinks
        # The trader's cashback rebate account (quote ATA of their user_volume_accumulator PDA) is never a fee sink.
        from adapters.pump_common import pda
        from solana_addresses import associated_token_address
        from solana_common import base58_bytes
        rebate=associated_token_address(pda(pump.PROGRAM,b'user_volume_accumulator',base58_bytes(accounts[1],32)),accounts[4],TOKEN_PROGRAM)[0]
        cashback=accounts[:22]+[rebate];sell=swap_decode(pump.PROGRAM,tag('sell')+struct.pack('<QQ',1000,1),cashback)
        self.assertEqual((sell['fee_accounts'],sell['rebate_accounts']),([accounts[10],accounts[17],accounts[21]],[rebate]))
        self.assertEqual(swap_decode(pump.PROGRAM,tag('buy')+struct.pack('<QQ',2000,1)+b'\x01',accounts[:23])['mode'],'exact_out')
        for data,keys in ((tag('buy')+struct.pack('<QQ',2000,1)+b'\x02',accounts[:23]),(tag('buy')+struct.pack('<QQ',2000,1),accounts[:22]),(tag('sell')+struct.pack('<QQ',1000,1)[:15],accounts)):
            with self.assertRaises(ValueError):swap_decode(pump.PROGRAM,data,keys)

    def test_fee_inclusive_buy_verifies_leg_plus_fees_and_a_rebate_is_refused(self):
        from solana_transactions import verify_rebuys
        target,a,p,b=fixture(buy=True);e=decode_transaction(target,p,b);swap=next(x for x in e['effects'] if x['kind']=='swap_instruction')
        inp=next(x for x in e['effects'] if x['kind']=='transfer' and x['participants']['source']==a['source'])
        sink=key(66);fee=copy.deepcopy(inp);fee['id']='fee';fee['amount_atomic']='7';fee['participants']={**inp['participants'],'destination':sink}
        fee['locator']={'outer_index':inp['locator']['outer_index'],'inner_index':2};e['effects'].append(fee);e['instructions'].append({**e['instructions'][-1],'id':'fee','locator':fee['locator'],'stack_height':2})
        e['post_token_balances'][a['source']]['amount_atomic']=str(int(e['post_token_balances'][a['source']]['amount_atomic'])-7)
        for side,value in (('pre_token_balances','0'),('post_token_balances','7')):e[side][sink]={'mint':inp['mint'],'owner':key(67),'program':TOKEN_PROGRAM,'amount_atomic':value,'decimals':9}
        swap.update(mode='exact_in_fee_inclusive',specified_amount_atomic='1007',fee_accounts=[sink])
        row=verify_rebuys(target,[{'pool':a['pool'],'execution':e}])['receipts'][0]
        self.assertEqual((row['status'],row['input_atomic'],[f['amount_atomic'] for f in row['protocol_fees_atomic']]),('verified_rebuy','1000',['7']),row['gaps'])
        swap['specified_amount_atomic']='1000'
        row=verify_rebuys(target,[{'pool':a['pool'],'execution':e}])['receipts'][0];self.assertIn('spendable-input',row['gaps'][0])
        swap.update(specified_amount_atomic='1007',fee_accounts=[],rebate_accounts=[sink])  # the same flow declared as the trader's rebate
        row=verify_rebuys(target,[{'pool':a['pool'],'execution':e}])['receipts'][0];self.assertIn('cashback rebate',row['gaps'][0])

    def test_token_2022_leg_verifies_only_with_both_checked_boundaries(self):
        target,a,p,b=fixture();tx=p['response']['result']
        for row in tx['meta']['preTokenBalances']+tx['meta']['postTokenBalances']:row['programId']=TOKEN_2022
        keys=tx['transaction']['message']['accountKeys'];keys[keys.index(TOKEN_PROGRAM)]=TOKEN_2022
        e=decode_transaction(target,p,b);self.assertEqual(e['gaps'],[])
        row=verify_sales(target,[{'pool':a['pool'],'execution':e}])['receipts'][0]
        self.assertEqual((row['status'],row['token_programs']),('verified_sale',[TOKEN_2022]))
        withheld=copy.deepcopy(e);withheld['post_token_balances'][a['input_vault']]['amount_atomic']='20990'  # a fee withheld on transfer
        self.assertEqual(verify_sales(target,[{'pool':a['pool'],'execution':withheld}])['receipts'][0]['status'],'unverified')
        missing=copy.deepcopy(e);del missing['pre_token_balances'][a['source']]
        row=verify_sales(target,[{'pool':a['pool'],'execution':missing}])['receipts'][0]
        self.assertEqual(row['status'],'unverified');self.assertIn('Token-2022',row['gaps'][0])

    def test_input_account_closed_in_transaction_reconciles_against_the_vault(self):
        target,a,p,b=fixture();tx=p['response']['result'];keys=tx['transaction']['message']['accountKeys']
        tx['meta']['postTokenBalances']=[r for r in tx['meta']['postTokenBalances'] if keys[r['accountIndex']]!=a['source']]
        tx['transaction']['message']['instructions'].append({'programIdIndex':keys.index(TOKEN_PROGRAM),'accounts':[keys.index(a['source']),keys.index(a['owner']),keys.index(a['owner'])],'data':b58encode(b'\x09')})
        e=decode_transaction(target,p,b);self.assertEqual(e['gaps'],[])
        row=verify_sales(target,[{'pool':a['pool'],'execution':e}])['receipts'][0]
        self.assertEqual((row['status'],row['input_atomic']),('verified_sale','1000'))
        e['post_token_balances'][a['input_vault']]['amount_atomic']='20999'
        self.assertEqual(verify_sales(target,[{'pool':a['pool'],'execution':e}])['receipts'][0]['status'],'unverified')

    def test_temporary_wsol_rebuy_created_with_seed_reconciles(self):
        buy_target,a,p,b=fixture(wsol=True);buy_target={**buy_target,'mint':a['output_mint']}
        # The trader funds a seeded temporary WSOL account that pays for the buy of the (WSOL-denominated) target.
        tx=p['response']['result'];keys=tx['transaction']['message']['accountKeys']
        seed=b'temp';data=struct.pack('<I',3)+base58_bytes(a['owner'],32)+struct.pack('<Q',len(seed))+seed+struct.pack('<QQ',2039280,165)+base58_bytes(TOKEN_PROGRAM,32)
        tx['transaction']['message']['instructions'].insert(0,{'programIdIndex':keys.index(SYSTEM),'accounts':[keys.index(a['owner']),keys.index(a['source'])],'data':b58encode(data)})
        tx['meta']['innerInstructions'][0]['index']+=1
        e=decode_transaction(buy_target,p,b);created=[x for x in e['effects'] if x['kind']=='native_account_create']
        self.assertEqual((len(created),created[0]['seed'],created[0]['amount_atomic'],created[0]['participants']['account']),(1,'temp','2039280',a['source']))
        row=verify_rebuys(buy_target,[{'pool':a['pool'],'execution':e}])['receipts'][0]
        self.assertEqual((row['status'],row['buyer'],row['counter_mint']),('verified_rebuy',a['owner'],a['input_mint']))

    def test_system_allocate_and_assign_decode_without_amounts(self):
        target,a,p,b=fixture();tx=p['response']['result'];keys=tx['transaction']['message']['accountKeys']
        for data in (struct.pack('<IQ',8,165),struct.pack('<I',1)+base58_bytes(TOKEN_PROGRAM,32)):
            tx['transaction']['message']['instructions'].append({'programIdIndex':keys.index(SYSTEM),'accounts':[keys.index(a['destination'])],'data':b58encode(data)})
        e=decode_transaction(target,p,b);kinds=[x['kind'] for x in e['effects']]
        self.assertEqual(kinds[-2:],['native_account_allocate','native_account_assign']);self.assertIsNone(e['effects'][-1]['amount_atomic'])
        self.assertEqual(e['effects'][-1]['owning_program'],TOKEN_PROGRAM)

    def test_onward_hop_marks_counter_asset_as_converted_and_skips_native_proceeds(self):
        target,a,p,b=routed(wsol=True);e=decode_transaction(target,p,b)
        second=copy.deepcopy(e['effects'][0]);second['id']='swap2';second['pool']=key(81);second['vaults']=[key(82),key(83)];second['input_account']=a['destination'];second['output_account']=key(84)
        hop={'id':'hop','kind':'transfer','mint':WSOL,'program':TOKEN_PROGRAM,'participants':{'source':a['destination'],'destination':key(82),'authority':a['owner']},'amount_atomic':'500','decimals':9,
             'locator':{'outer_index':e['effects'][0]['locator']['outer_index'],'inner_index':5},'stack_height':3}
        e['effects']+=[second,hop];e['post_token_balances'][a['destination']]['amount_atomic']='0'
        row=verify_sales(target,[{'pool':a['pool'],'execution':e}])['receipts'][0]
        self.assertEqual((row['status'],row['route'],row['counter_asset_realization'],row['native_proceeds']),('verified_sale','aggregated','converted_within_route',None))
        unrelated=copy.deepcopy(e);unrelated['effects'][-1]['participants']['destination']=key(99)
        self.assertEqual(verify_sales(target,[{'pool':a['pool'],'execution':unrelated}])['receipts'][0]['status'],'unverified')

    def test_round_trip_back_into_the_input_account_is_not_a_sale(self):
        # TARGET -> WSOL at pool A, then WSOL -> TARGET at pool B back into the same input account: a cycle, not a sale.
        target,a,p,b=routed(wsol=True);e=decode_transaction(target,p,b)
        second=copy.deepcopy(e['effects'][0]);second['id']='swap2';second['pool']=key(81);second['vaults']=[key(82),key(83)];second['input_account']=a['destination'];second['output_account']=a['source']
        back={'id':'back','kind':'transfer','mint':target['mint'],'program':TOKEN_PROGRAM,'participants':{'source':key(83),'destination':a['source'],'authority':key(81)},'amount_atomic':'1000','decimals':9,
              'locator':{'outer_index':e['effects'][0]['locator']['outer_index'],'inner_index':6},'stack_height':3}
        e['effects']+=[second,back]
        row=verify_sales(target,[{'pool':a['pool'],'execution':e}])['receipts'][0]
        self.assertEqual(row['status'],'unverified');self.assertTrue(any('unrelated balance' in g for g in row['gaps']),row['gaps'])

    def test_duplicate_receipt_is_a_row_gap_not_a_dropped_derivation(self):
        target,a,p,b=routed(wsol=True);e=decode_transaction(target,p,b)
        result=verify_sales(target,[{'pool':a['pool'],'execution':e},{'pool':a['pool'],'execution':copy.deepcopy(e)}])
        self.assertEqual([r['status'] for r in result['receipts']],['verified_sale','unverified']);self.assertIn('duplicate receipt',result['receipts'][1]['gaps'][0])

    def test_legacy_curve_buy_and_pinned_create_v2_account_count(self):
        from adapters.pump_instructions import decode,tag as ptag
        from pump_fixture import fixture as pump_fixture,CURVE_PROGRAM
        target,a,_=pump_fixture();accounts=[key(100+i) for i in range(16)];accounts[2]=target['mint'];accounts[3]=a['curve']
        e=decode(CURVE_PROGRAM,ptag('buy')+struct.pack('<QQB',1000,2000,1),accounts)
        self.assertEqual((e['kind'],e['direction'],e['participants']['user'],e['participants']['base_account'],e['quote_mint']),('protocol_trade_instruction','buy_base',accounts[6],accounts[5],WSOL))
        with self.assertRaises(ValueError):decode(CURVE_PROGRAM,ptag('buy')+struct.pack('<QQB',1000,2000,2),accounts)
        with self.assertRaises(ValueError):decode(CURVE_PROGRAM,ptag('buy')+struct.pack('<QQ',1000,2000),accounts)
        create=[key(120+i) for i in range(17)];create[0]=target['mint'];create[2]=a['curve'];create[7]=TOKEN_2022
        raw=ptag('create_v2')+b''.join(struct.pack('<I',len(x))+x for x in (b'C',b'C',b'u'))+base58_bytes(a['creator'],32)+b'\0\0'
        with self.assertRaises(ValueError):decode(CURVE_PROGRAM,raw,create)
        e=decode(CURVE_PROGRAM,raw,create[:16]);self.assertEqual((e['kind'],e['quote_mint']),('launch_initialize',None))


if __name__=='__main__':unittest.main()
