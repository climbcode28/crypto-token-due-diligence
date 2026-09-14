from pathlib import Path
import copy
import json
import sys
import unittest
from fractions import Fraction
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from solana_quotes import size_policy,estimate,quote_url,public_quote,quote_ladder,percent
from solana_common import TOKEN_PROGRAM,TOKEN_2022
from pool_fixture import fixture,batch,key
from meteora_fixture import clock
from adapters.meteora_common import CLOCK
from test_solana_raydium import mutate
from test_solana_discovery import capture


class QuoteTests(unittest.TestCase):
    def test_three_sizes_user_priority_price_exact_units_and_fallback(self):
        target,a,v=fixture();p=batch(v)[target['mint']]
        price={'genesis_hash':target['genesis_hash'],'price_denominator_mint':target['mint'],'price_usd':'2.50','captured_at':1000,'evidence':['price']}
        result=size_policy(target,p,price=price,now=1001)
        self.assertEqual([r['input_atomic'] for r in result['sizes']],['40000000','400000000','4000000000'])
        result=size_policy(target,p,user_sizes=['0.000001','2','3'],price=price,now=1001)
        self.assertEqual([r['input_atomic'] for r in result['sizes']],['1','2000000','3000000'])
        result=size_policy(target,p,user_sizes=['7'])
        self.assertEqual(result['sizes'][0]['input_atomic'],'7000000');self.assertEqual(len(result['sizes']),3)
        for altered in ({**price,'price_denominator_mint':key(9)},{**price,'genesis_hash':key(9)},{**price,'captured_at':600},{**price,'conflicts':[{'other':1}]}):
            result=size_policy(target,p,price=altered,now=1001)
            self.assertEqual(result['basis'],'illustrative_token_quantity_probes');self.assertTrue(result['gaps'])
        with self.assertRaises(ValueError):size_policy(target,p,user_sizes=['0.0000001'])

    def test_cpmm_golden_rounding_and_input_output_creator_fee(self):
        for mode,outputs in [(0,['196','1812','9924']),(2,['195','1811','9922'])]:
            target,a,v=fixture();v[CLOCK]=clock();v[a['pool']]=mutate(v[a['pool']],389,bytes([mode]))
            for quantity,expected in zip(['100','1000','10000'],outputs):
                r=estimate(target,'raydium_cpmm',a['pool'],batch(v),quantity)
                self.assertEqual(r['status'],'modeled',r);self.assertEqual(r['output_atomic'],expected)
                self.assertLess(int(r['minimum_output_atomic']),int(expected));self.assertFalse(r['execution_observed'])
            self.assertEqual(r['fees']['trade_input_atomic'],'25');self.assertEqual(r['fees']['creator_atomic'],'5')
            self.assertEqual(r['fees']['protocol_input_atomic'],'3');self.assertEqual(r['fees']['fund_input_atomic'],'1')

    def test_quote_refuses_missing_fee_clock_frozen_disabled_or_token2022_state(self):
        for case in ('fee','clock','frozen','disabled','token22','unknown_tail','future_time'):
            target,a,v=fixture();v[CLOCK]=clock()
            if case=='fee':del v[a['config']]
            if case=='clock':del v[CLOCK]
            if case=='frozen':v[a['vaults'][0]]=mutate(v[a['vaults'][0]],108,b'\2')
            if case=='disabled':v[a['pool']]=mutate(v[a['pool']],329,b'\4')
            if case=='token22':v[a['mints'][0]]['owner']=TOKEN_2022
            if case=='unknown_tail':v[a['pool']]=mutate(v[a['pool']],636,b'\1')
            if case=='future_time':v[a['pool']]=mutate(v[a['pool']],373,(1001).to_bytes(8,'little'))
            r=estimate(target,'raydium_cpmm',a['pool'],batch(v),'1000')
            self.assertIsNone(r['output_atomic'],case);self.assertTrue(r['gaps'])
        target,a,v=fixture()
        for family in ('raydium_clmm','orca_whirlpool','meteora_dlmm','meteora_damm_v2','raydium_amm_v4'):
            r=estimate(target,family,a['pool'],batch(v),'1000')
            self.assertIsNone(r['output_atomic']);self.assertTrue(r['gaps'])

    def quote(self,source):
        target,a,_=fixture();url=quote_url(source,target,a['mints'][1],'1000')
        if source=='jupiter_v2':
            body={'inputMint':target['mint'],'outputMint':a['mints'][1],'inAmount':'1000','outAmount':'500','otherAmountThreshold':'497',
                  'slippageBps':50,'swapMode':'ExactIn','transaction':None,'priceImpact':'-0.1','feeBps':0,'feeMint':target['mint'],
                  'routePlan':[{'swapInfo':{'ammKey':a['pool'],'inputMint':target['mint'],'outputMint':a['mints'][1],'feeAmount':'3','feeMint':target['mint']},'percent':100}]}
        else:
            body={'version':'V1','success':True,'data':{'inputMint':target['mint'],'outputMint':a['mints'][1],'inputAmount':'1000','outputAmount':'500',
                'otherAmountThreshold':'497','slippageBps':50,'swapType':'BaseIn','priceImpactPct':0.0012,
                'routePlan':[{'poolId':a['pool'],'inputMint':target['mint'],'outputMint':a['mints'][1],'feeAmount':'3','feeMint':target['mint']}]}}
        return target,a,url,body

    def test_public_quotes_keep_thresholds_fee_scopes_context_and_impact_units(self):
        for source in ('jupiter_v2','raydium_quote'):
            target,a,url,body=self.quote(source);rec,raw=capture(body,url)
            q=public_quote(source,target,rec,raw,a['mints'][1],'1000')
            self.assertEqual(q['output_atomic'],'500');self.assertEqual(q['minimum_output_atomic'],'497')
            self.assertIsNone(q['context_slot']);self.assertEqual(q['route'][0]['pool'],a['pool'])
            self.assertNotIn('taker',url);self.assertNotIn('wallet',url);self.assertFalse(q['execution_observed'])
            if source=='jupiter_v2':self.assertEqual(q['price_impact_fraction'],{'numerator':'-1','denominator':'1000'})
            else:self.assertIsNone(q['price_impact_fraction'])

    def test_quote_ladder_follows_the_size_policy_and_names_missing_sizes(self):
        target,a,_=fixture();out=a['mints'][1]
        policy={'target':target,'basis':'illustrative_USD_equivalents_floor_to_atomic_units','sizes':[{'input_atomic':'10000000'},{'input_atomic':'100000000'},{'input_atomic':'1000000000'}]}
        def q(size,output,status='quoted',source='jupiter_v1_lite',mint=None):
            return {'kind':'api_quote','source':source,'input_mint':mint or target['mint'],'output_mint':out,'input_atomic':str(size),'output_atomic':str(output) if output is not None else None,
                    'status':status,'route':[{'pool':a['pool']}],'provider_price_impact_raw':'0.001','captured_at':'2026-09-13T00:00:00+00:00','gaps':[] if output is not None else ['provider reports execution error: 1']}
        ladder=quote_ladder(target,policy,[('q3',q(10**9,45*10**7)),('q1',q(10**7,4995*10**3)),('q2',q(10**8,495*10**5))],source='jupiter_v1_lite',output_mint=out)
        self.assertEqual([r['quote'] for r in ladder['rows']],['q1','q2','q3'],'rows follow the policy sizes whatever the input order')
        self.assertEqual([r['impact_vs_smallest_percent'] for r in ladder['rows']],['0.0000','0.9009','9.9099'])
        self.assertEqual(ladder['rows'][0]['output_per_input'],{'numerator':'999','denominator':'2000'});self.assertEqual(ladder['rows'][2]['impact_vs_smallest'],{'numerator':'11','denominator':'111'})
        self.assertEqual((ladder['sizes_quoted'],ladder['sizes_requested'],ladder['largest_size_quoted'],ladder['largest_impact_vs_smallest_percent'],ladder['evidence'],ladder['gaps'],ladder['policy_basis']),(3,3,True,'9.9099',['q1','q2','q3'],[],policy['basis']))
        self.assertFalse(ladder['execution_observed']);self.assertIn('never execution',ladder['scope'])
        # A policy size with no usable quote is a named row: the smallest quoted size is the baseline, the missing one keeps its reason, and the largest size's impact still reads.
        ladder=quote_ladder(target,policy,[('q1',q(10**7,4995*10**3)),('q3',q(10**9,5*10**8))],source='jupiter_v1_lite',output_mint=out,missing={'100000000':'capture http_error (http 429)'})
        self.assertEqual([(r['status'],r.get('reason')) for r in ladder['rows']],[('quoted',None),('not_captured','capture http_error (http 429)'),('quoted',None)])
        self.assertEqual((ladder['sizes_quoted'],ladder['sizes_requested'],ladder['largest_impact_vs_smallest_percent'],ladder['gaps']),(2,3,'-0.1001',['size 100000000 not captured (capture http_error (http 429))']))
        # A quote the provider answered without a route keeps its status and gap; a missing largest size leaves largest_size_quoted false.
        ladder=quote_ladder(target,policy,[('q1',q(10**7,4995*10**3)),('q2',q(10**8,None,status='quote_with_execution_error'))],source='jupiter_v1_lite',output_mint=out,missing={'1000000000':'not captured'})
        self.assertEqual((ladder['sizes_quoted'],ladder['largest_size_quoted'],ladder['largest_impact_vs_smallest_percent'],len(ladder['gaps'])),(1,False,None,2))
        self.assertIn('size 100000000 not quoted (quote_with_execution_error)',ladder['gaps'][0]);self.assertEqual(ladder['rows'][2]['status'],'not_captured')
        self.assertEqual(percent(Fraction(-1,2000)),'-0.0500');self.assertEqual(percent(Fraction(1,3),2),'33.33')
        for bad in ([],[('q1',q(10**7,1)),('q2',q(10**7,2))],[('q1',q(10**7,1)),('q2',q(10**8,2,source='jupiter_v2'))],[('q1',q(10**7,1,mint=key(9)))],[('q0',q(1000,500))]):
            with self.assertRaises(ValueError):quote_ladder(target,policy,bad,source='jupiter_v1_lite',output_mint=out)
        with self.assertRaises(ValueError):quote_ladder(target,policy,[('q1',q(10**7,1))],source='jupiter_v1_lite',output_mint=out,missing={'1000':'x'})  # only policy sizes can be missing
        with self.assertRaises(ValueError):quote_ladder(target,{**policy,'target':{**target,'mint':key(9)}},[('q1',q(10**7,1))],source='jupiter_v1_lite',output_mint=out)

    def test_jupiter_lite_quote_accepts_reordered_benign_parameters_and_refuses_wallets(self):
        from solana_quotes import quote_request
        target,a,_=fixture();out=a['mints'][1]
        body={'inputMint':target['mint'],'outputMint':out,'inAmount':'1000','outAmount':'500','otherAmountThreshold':'497','slippageBps':50,'swapMode':'ExactIn',
              'priceImpactPct':'0.0012','contextSlot':446296732,'swapUsdValue':'999.94','timeTaken':0.01,
              'routePlan':[{'swapInfo':{'ammKey':a['pool'],'label':'Raydium','inputMint':target['mint'],'outputMint':out,'inAmount':'1000','outAmount':'500','feeAmount':'3','feeMint':target['mint']},'percent':100}]}
        url='https://lite-api.jup.ag/swap/v1/quote?outputMint='+out+'&amount=1000&inputMint='+target['mint']+'&slippageBps=50&onlyDirectRoutes=false'
        rec,raw=capture(body,url);q=public_quote('jupiter_v1_lite',target,rec,raw,out,'1000')
        self.assertEqual((q['output_atomic'],q['minimum_output_atomic'],q['context_slot'],q['provider_usd_value'],q['provider_price_impact_raw']),('500','497',446296732,'999.94','0.0012'))
        self.assertIsNone(q['price_impact_fraction']);self.assertEqual(q['route'][0]['pool'],a['pool']);self.assertEqual(q['fees'][0]['amount_atomic'],'3')
        self.assertEqual(quote_request(url)[0],'jupiter_v1_lite');self.assertEqual(quote_request(quote_url('jupiter_v2',target,out,'1000'))[0],'jupiter_v2')
        for bad in (url+'&taker='+key(9),url.replace('amount=1000','amount=1001'),url.replace('lite-api.jup.ag','api.jup.ag'),url+'&unknown=1'):
            rec,raw=capture(body,bad)
            with self.assertRaises(ValueError):public_quote('jupiter_v1_lite',target,rec,raw,out,'1000')
        rec,raw=capture({**body,'swapTransaction':'AQID'},url)
        with self.assertRaises(ValueError):public_quote('jupiter_v1_lite',target,rec,raw,out,'1000')

    def test_captured_quote_bytes_input_route_and_transaction_assembly_attacks(self):
        for kind in ('transaction','input','mint','route','threshold','hash','url','leg'):
            target,a,url,body=self.quote('jupiter_v2')
            if kind=='transaction':body['transaction']='serialized-transaction'
            if kind=='input':body['inAmount']='1001'
            if kind=='mint':body['outputMint']=key(90)
            if kind=='route':body['routePlan'][0]['swapInfo']['outputMint']=key(90)
            if kind=='leg':body['routePlan'][0]=None
            if kind=='threshold':body['otherAmountThreshold']='501'
            rec,raw=capture(body,url)
            if kind=='hash':rec['sha256']='f'*64
            if kind=='url':rec['url']+='&taker='+key(9)
            with self.assertRaises(ValueError):public_quote('jupiter_v2',target,rec,raw,a['mints'][1],'1000')

    def test_quoted_price_with_error_or_missing_rfq_route_is_not_execution(self):
        target,a,url,body=self.quote('jupiter_v2');body.update(transaction='',errorCode=1,routePlan=[])
        rec,raw=capture(body,url);q=public_quote('jupiter_v2',target,rec,raw,a['mints'][1],'1000')
        self.assertEqual(q['status'],'quote_with_execution_error');self.assertEqual(q['output_atomic'],'500');self.assertTrue(q['gaps'])

    def test_quote_preset_and_tiny_input_fee_rounding(self):
        from solana_presets import quote_sample
        target,a,v=fixture();v[CLOCK]=clock();obs=batch(v)
        plan=quote_sample('raydium_cpmm',a['pool'],obs[a['pool']])
        self.assertEqual(len(plan),1);self.assertIn(CLOCK,plan[0]['params'][0])
        r=estimate(target,'raydium_cpmm',a['pool'],obs,'1')
        self.assertIsNone(r['output_atomic']);self.assertIn('fees round input to zero',r['gaps'])

    def test_zero_combined_fee_respects_pinned_split_failure(self):
        target,a,v=fixture();v[CLOCK]=clock()
        v[a['config']]=mutate(v[a['config']],12,bytes(8));v[a['config']]=mutate(v[a['config']],108,bytes(8))
        r=estimate(target,'raydium_cpmm',a['pool'],batch(v),'1000')
        self.assertIsNone(r['output_atomic']);self.assertIn('pinned CPMM input fee split has zero denominator',r['gaps'])


if __name__=='__main__':unittest.main()
