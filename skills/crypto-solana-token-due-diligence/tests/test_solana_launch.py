from pathlib import Path
import sys,unittest,copy,struct
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from pump_fixture import fixture,batch,curve,swap,migration,receipt,key,CURVE_PROGRAM,TOKEN_PROGRAM,base58_bytes
from adapters.pump_instructions import tag,decode
from solana_transactions import decode_transaction
from solana_launch import launch_facts,history_pages,prior_launches
from solana_fixture import request,response


class LaunchTests(unittest.TestCase):
    def test_launch_publication_is_exact_mint_lead_not_verified_launch(self):
        from solana_discovery import launch_leads
        from test_solana_discovery import capture
        target,a,_=fixture();record,raw=capture({'mint':target['mint']},'https://example.com/coin')
        r=launch_leads(target,[(record,raw)])
        self.assertEqual(r['candidate_curve'],a['curve']);self.assertEqual(len(r['documents']),1)
        self.assertFalse(r['documents'][0]['platform_or_creator_verified'])
        record['sha256']='f'*64
        with self.assertRaises(ValueError):launch_leads(target,[(record,raw)])

    def test_migration_requires_receipt_cpi_funding_and_current_destination(self):
        target,a,v=fixture(complete=True);p,b=migration(target,a);ex=decode_transaction(target,p,b)
        self.assertEqual(ex['gaps'],[])
        c=curve.analyze(target,a['curve'],batch(v));s=swap.analyze(target,a['pool'],batch(v))
        r=launch_facts(target,[ex],curve=c,pool=s)
        self.assertEqual(r['gaps'],[]);self.assertEqual(r['stage'],'migration_verified_current_pool_observed')
        self.assertEqual(r['migration']['current_reserves_atomic'],['10000','20000'])
        self.assertIsNone(launch_facts(target,[],curve=c,pool=s)['migration'])

    def test_migration_wrong_assets_pool_lp_funding_and_stale_state(self):
        for case in ('asset','pool','lp','funding','failed','stale','incomplete'):
            target,a,v=fixture(complete=True);p,b=migration(target,a);ex=decode_transaction(target,p,b)
            c=curve.analyze(target,a['curve'],batch(v));s=swap.analyze(target,a['pool'],batch(v))
            if case=='asset':s['state']['mints'][1]=key(9)
            if case=='pool':s['pool']=key(9)
            if case=='lp':s['state']['lp_mint']=key(9)
            if case=='funding':ex['effects'].pop()
            if case=='failed':ex['execution_status']='failed'
            if case=='stale':s['contexts'][0]['context_slot']=94
            if case=='incomplete':c['state']['complete']=False
            r=launch_facts(target,[ex],curve=c,pool=s);self.assertIsNone(r['migration'],case);self.assertTrue(r['gaps'])

    def create(self):
        target,a,v=fixture();accounts=[key(100+i) for i in range(14)]
        for i,k in {0:target['mint'],2:a['curve'],3:a['curve_holding'],7:key(70),9:TOKEN_PROGRAM}.items():accounts[i]=k
        raw=tag('create')+b''.join(struct.pack('<I',len(x))+x for x in (b'Coin',b'COIN',b'https://example.com'))+base58_bytes(a['creator'],32)
        init=bytes([20,6])+base58_bytes(key(80),32)+b'\0'
        p,b=receipt(target,(CURVE_PROGRAM,accounts,raw),[(TOKEN_PROGRAM,[target['mint']],init)])
        return target,a,p,b

    def test_exact_creation_and_prior_key_links_do_not_infer_human_identity(self):
        target,a,p,b=self.create();ex=decode_transaction(target,p,b);r=launch_facts(target,[ex])
        self.assertEqual(r['mint_creation_time'],1000);self.assertEqual(len(r['initializations']),1)
        links=prior_launches(key(70),[ex]);self.assertEqual(links['observed_launch_links'][0]['relationship'],'signer_continuity');self.assertIsNone(links['human_identity'])
        links=prior_launches(a['creator'],[ex]);self.assertEqual(links['observed_launch_links'][0]['relationship'],'recorded_creator_argument')
        ex['effects']=[e for e in ex['effects'] if e['kind']!='mint_initialize']
        self.assertIsNone(launch_facts(target,[ex])['mint_creation_time'])

    def test_failed_creation_or_signature_page_does_not_become_absence(self):
        target,a,p,b=self.create();p['response']['result']['meta']['err']={'failure':1};ex=decode_transaction(target,p,b)
        self.assertIsNone(launch_facts(target,[ex])['mint_creation_time']);self.assertIsNone(prior_launches(a['creator'],[ex])['total_prior_launches'])
        req=request('getSignaturesForAddress',[a['creator'],{'commitment':'finalized','limit':25}],'history')
        r=history_pages(a['creator'],[{'request':req,'status':'failed'}],start_slot=1,end_slot=100)
        self.assertFalse(r['window_covered']);self.assertTrue(r['gaps'])

    def test_page_window_boundaries_and_pagination_continuity(self):
        from solana_common import b58encode
        key1=key(90);req=request('getSignaturesForAddress',[key1,{'commitment':'finalized','limit':2}],'history')
        rows=[{'signature':b58encode(bytes([i])*64),'slot':slot,'blockTime':1000,'err':None} for i,slot in ((91,101),(92,90))]
        p={'request':req,'status':'ok','response':response(req,rows)}
        r=history_pages(key1,[p],start_slot=95,end_slot=105)
        self.assertTrue(r['window_covered']);self.assertEqual(len(r['signatures']),1)
        r=history_pages(key1,[p],start_slot=80,end_slot=105);self.assertFalse(r['window_covered'])
        with self.assertRaises(ValueError):history_pages(key1,[p,p],start_slot=80,end_slot=105)
        empty={'request':req,'status':'ok','response':response(req,[])}
        self.assertFalse(history_pages(key1,[empty],start_slot=80,end_slot=105)['window_covered'])

    def test_pump_trade_and_fee_instructions_do_not_imply_sales(self):
        target,a,_=fixture();accounts=[key(100+i) for i in range(26)];accounts[1]=target['mint'];accounts[10]=a['curve']
        e=decode(CURVE_PROGRAM,tag('sell_v2')+struct.pack('<QQ',1000,1),accounts)
        self.assertEqual(e['kind'],'protocol_trade_instruction');self.assertFalse(e['sale_verified'])
        with self.assertRaises(ValueError):decode(CURVE_PROGRAM,tag('sell_v2')+struct.pack('<QQ',1000,1),accounts[:-1])
        fee=decode(CURVE_PROGRAM,tag('collect_creator_fee'),accounts[:5]);self.assertEqual(fee['kind'],'creator_fee_claim');self.assertIsNone(fee['amount_atomic'])

    def test_pumpswap_sell_buy_and_exact_quote_layouts(self):
        from solana_swaps import decode as swap_decode
        for name,n,raw,mode in (('sell',21,struct.pack('<QQ',1000,1),'exact_in'),('buy',23,struct.pack('<QQB',1000,2000,1),'exact_out'),
                              ('buy_exact_quote_in',23,struct.pack('<QQB',1000,1,0),'exact_in')):
            accounts=[key(100+i) for i in range(n)];accounts[11]=accounts[12]=TOKEN_PROGRAM
            result=swap_decode(swap.PROGRAM,tag(name)+raw,accounts)
            self.assertEqual(result['mode'],mode)
            self.assertEqual(result['input_account'],accounts[5 if name=='sell' else 6])
            with self.assertRaises(ValueError):swap_decode(swap.PROGRAM,tag(name)+raw[:-1],accounts)


if __name__=='__main__':unittest.main()
