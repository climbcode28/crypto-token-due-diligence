from pathlib import Path
import sys,unittest,unittest.mock,json,urllib.error,io,time,tempfile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'));sys.path.insert(0,str(Path(__file__).resolve().parent))
from broad_fixture import RichRpc,Web
from concentrated_fixture import fixture as clmm_fixture
from solana_broad_collect import start
from solana_common import b58encode
import solana_session


def key(n):return b58encode(bytes([n])*32)


class CensusFlowTests(unittest.TestCase):
    """A Raydium CLMM pool ranked first by discovery: start censuses its positions, samples the largest with its NFT holding, and the pool fact carries custody."""
    def setup_run(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);root=Path(tmp.name)/'run';target=RichRpc.reset();Web.calls=[];Web.blocked=False
        patcher=unittest.mock.patch.object(solana_session,'CONNECTION_WINDOW',10000);patcher.start();self.addCleanup(patcher.stop)
        _,c,values=clmm_fixture();RichRpc.values.update(values);RichRpc.largest[c['pool']]=[c['position']];RichRpc.largest[c['nft']]=[c['holding']]
        pair=lambda pool,liq:{'chainId':'solana','pairAddress':pool,'baseToken':{'address':target['mint']},'quoteToken':{'address':key(3)},'dexId':'raydium','liquidity':{'usd':liq},'priceUsd':'2','volume':{'h24':'500000'},'info':{'websites':[{'url':'https://project.example/token'}]}}
        Web.pairs=[pair(c['pool'],'9000000'),pair(RichRpc.pool['pool'],'1000000')]
        opts={'question':'Assess exact token, project claims and exit depth.','received_at':time.time()-10,'deadline_at':time.time()+590,'scope':'broad','focus':[],
          'urls':[],'synthetic':True,'config':{'url':'https://synthetic.invalid','headers':{}},'factory':RichRpc,'opener_factory':Web}
        return root,target,c,opts

    def test_start_censuses_clmm_positions_and_samples_the_largest_with_custody(self):
        root,target,c,opts=self.setup_run();r=start(root,target,**opts);self.assertFalse(r['diagnostics'],r['diagnostics'])
        leads=json.loads((root/'automatic-leads.json').read_text());lead=next(l for l in leads if l['pool']==c['pool'])
        self.assertEqual([p['position'] for p in lead['positions']],[c['position']]);self.assertEqual(lead['positions'][0]['holding'],c['holding']);self.assertEqual(lead['positions'][0]['kind'],'census')
        self.assertEqual((lead['census']['positions_counted'],lead['census']['sampled'],lead['census']['sampled_weight_share']['percent_display']),(1,1,'100.0000'))
        facts=json.loads((root/'draft/facts.json').read_text())['facts'];pool=next(f['data'] for f in facts if f['operation']=='pool' and f['data']['pool']==c['pool'])
        self.assertEqual(pool['position_coverage'],'sampled');self.assertEqual(pool['position_census']['positions_counted'],1)
        row=pool['positions'][0];self.assertEqual(row['status'],'observed',row.get('gaps'));self.assertEqual(row['custody']['spending_owner'],c['owner'])
        census_reads=[q for q in RichRpc.calls if q['method']=='getProgramAccounts' and q['params'][1]['filters'][0]['dataSize']==281];self.assertEqual(len(census_reads),1)
        self.assertFalse([q for q in RichRpc.calls if str(q['id']).startswith('census0l_')],'a CLMM census plans its batch from the slice and needs no lead sample')

    def test_refused_census_is_a_named_diagnostic_and_the_pool_still_decodes(self):
        root,target,c,opts=self.setup_run();original=RichRpc.__call__
        def refusing(rpc,request):
            if request['method']=='getProgramAccounts' and request['params'][1]['filters'][0]['dataSize']==281:
                raise urllib.error.HTTPError('https://synthetic.invalid',429,'limited',{'Retry-After':'10','x-ratelimit-method-limit':'0'},io.BytesIO(b''))
            return original(rpc,request)
        with unittest.mock.patch.object(RichRpc,'__call__',refusing):r=start(root,target,**opts)
        rows=[d for d in r['diagnostics'] if d.get('category')=='position_census_unavailable'];self.assertEqual(len(rows),1);self.assertEqual(rows[0]['pools'][0]['pool'],c['pool'])
        leads=json.loads((root/'automatic-leads.json').read_text());lead=next(l for l in leads if l['pool']==c['pool'])
        self.assertEqual(lead['positions'],[]);self.assertEqual(lead['census']['status'],'unavailable')
        facts=json.loads((root/'draft/facts.json').read_text())['facts'];pool=next(f['data'] for f in facts if f['operation']=='pool' and f['data']['pool']==c['pool'])
        self.assertEqual((pool['positions'],pool['position_coverage']),([],'partial'))


    def extra_clmm_positions(self,c,values,specs):
        """Clone the fixture position for more NFTs so a pool has several census candidates; shared tick arrays keep them in one batch."""
        import base64
        from pool_fixture import mint as mint_account,holding
        from solana_addresses import find_program_address
        from solana_common import base58_bytes
        from adapters import raydium_clmm
        base=bytearray(base64.b64decode(values[c['position']]['data'][0]));extra=[]
        for nft,owner,holder,liquidity in specs:
            pos,bump=find_program_address([b'position',base58_bytes(nft,32)],raydium_clmm.PROGRAM)
            raw=bytearray(base);raw[8]=bump;raw[9:41]=base58_bytes(nft,32);raw[81:97]=liquidity.to_bytes(16,'little')
            values[pos]={**values[c['position']],'data':[base64.b64encode(bytes(raw)).decode(),'base64']}
            values[nft]=mint_account(1,None,0);values[holder]=holding(nft,owner,1,key(56));RichRpc.largest[nft]=[holder];extra.append((pos,owner))
        return extra

    def test_several_clmm_positions_are_sampled_in_one_atomic_batch_and_all_resolve(self):
        root,target,c,opts=self.setup_run();values=dict(RichRpc.values)
        extra=self.extra_clmm_positions(c,values,[(key(70),key(72),key(74),500_000),(key(71),key(73),key(75),250_000)])
        RichRpc.values.update(values);RichRpc.largest[c['pool']]=[c['position']]+[p for p,_ in extra]
        r=start(root,target,**opts);self.assertFalse(r['diagnostics'],r['diagnostics'])
        lead=next(l for l in json.loads((root/'automatic-leads.json').read_text()) if l['pool']==c['pool'])
        self.assertEqual([p['position'] for p in lead['positions']],[c['position'],extra[0][0],extra[1][0]]);self.assertEqual(lead['census']['dropped_for_one_batch'],[])
        batches={q['id'] for q in RichRpc.calls if q['method']=='getMultipleAccounts' and str(q['id']).startswith('census0p_position_')}
        self.assertEqual({b.split('_position_')[1].split('_')[0] for b in batches},{'0'},batches)  # one atomic dependency batch (group 0), plus its final recheck
        self.assertEqual(max(len(q['params'][0]) for q in RichRpc.calls if q['method']=='getMultipleAccounts' and str(q['id']).startswith('census0p_position_')),17)
        facts=json.loads((root/'draft/facts.json').read_text())['facts'];pool=next(f['data'] for f in facts if f['operation']=='pool' and f['data']['pool']==c['pool'])
        self.assertEqual([(row['status'],row['custody']['spending_owner']) for row in pool['positions']],[('observed',c['owner']),('observed',key(72)),('observed',key(73))])
        self.assertEqual(pool['position_coverage'],'sampled');self.assertEqual(pool['position_census']['positions_counted'],3)

    def test_dlmm_positions_are_censused_with_owners_from_the_account(self):
        from meteora_fixture import fixture as dlmm_fixture
        root,target,c,opts=self.setup_run();_,d,values=dlmm_fixture('dlmm');RichRpc.values.update(values);RichRpc.largest[d['pool']]=[d['position']]
        pair=lambda pool,liq:{'chainId':'solana','pairAddress':pool,'baseToken':{'address':target['mint']},'quoteToken':{'address':key(3)},'dexId':'meteora','liquidity':{'usd':liq},'priceUsd':'2','volume':{'h24':'500000'},'info':{'websites':[{'url':'https://project.example/token'}]}}
        Web.pairs=[pair(d['pool'],'9000000'),pair(RichRpc.pool['pool'],'1000000')]
        r=start(root,target,**opts);self.assertFalse(r['diagnostics'],r['diagnostics'])
        lead=next(l for l in json.loads((root/'automatic-leads.json').read_text()) if l['pool']==d['pool'])
        self.assertEqual(lead['positions'][0]['spending_owner'],d['owner']);self.assertEqual(lead['census']['ranking'],'summed_bin_shares_u128_from_72')
        self.assertTrue([q for q in RichRpc.calls if str(q['id']).startswith('census0l_')],'a DLMM census still reads its leads in full before planning')
        facts=json.loads((root/'draft/facts.json').read_text())['facts'];pool=next(f['data'] for f in facts if f['operation']=='pool' and f['data']['pool']==d['pool'])
        row=pool['positions'][0];self.assertEqual((row['status'],row['custody']['spending_owner']),('observed',d['owner']),row.get('gaps'))
        self.assertIn('summed bin shares',__import__('solana_facts').describe('pool',pool))

    def test_census_is_skipped_with_a_reason_when_the_leftover_grant_is_too_small(self):
        root,target,c,opts=self.setup_run();original=solana_session.Session.status
        def starved(self_):s=original(self_);s['remaining_requests']=min(s['remaining_requests'],5);return s
        with unittest.mock.patch.object(solana_session.Session,'status',starved):r=start(root,target,**opts)
        rows=[d for d in r['diagnostics'] if d.get('category')=='position_census_unavailable'];self.assertEqual(rows[0]['pools'][0]['status'],'skipped');self.assertIn('13 needed for one lead including the two-send margin',rows[0]['pools'][0]['reason'])
        lead=next(l for l in json.loads((root/'automatic-leads.json').read_text()) if l['pool']==c['pool']);self.assertEqual(lead['positions'],[])
        self.assertFalse([q for q in RichRpc.calls if q['method']=='getProgramAccounts' and q['params'][1]['filters'][0]['dataSize']==281])

    def test_census_that_stops_mid_way_is_partial_not_a_stage_failure(self):
        import solana_broad_collect as bc
        root,target,c,opts=self.setup_run();original=bc.collect_sample
        def failing(session_root,out,config,sample,rows,**kw):
            if sample.endswith('p') and sample.startswith('census'):raise ValueError('fixture: dependency batch refused')
            return original(session_root,out,config,sample,rows,**kw)
        with unittest.mock.patch.object(bc,'collect_sample',failing):r=start(root,target,**opts)
        rows=[d for d in r['diagnostics'] if d.get('category')=='position_census_unavailable'];self.assertEqual(rows[0]['pools'][0]['status'],'partial');self.assertIn('dependency batch refused',rows[0]['pools'][0]['reason'])
        lead=next(l for l in json.loads((root/'automatic-leads.json').read_text()) if l['pool']==c['pool']);self.assertEqual(lead['census']['status'],'partial');self.assertTrue(lead['positions'])
        self.assertTrue(any(m['phase']=='pool_transaction_quote_dependencies' and json.loads(m['details']).get('state')=='finished' for m in r['session']['phases']))

    def test_census_runs_after_the_receipt_and_program_samples(self):
        root,target,c,opts=self.setup_run();start(root,target,**opts)
        ids=[str(q['id']) for q in RichRpc.calls];census=next(i for i,x in enumerate(ids) if x.startswith('census0_'));receipts=[i for i,x in enumerate(ids) if x.startswith('receipts_')]
        programs=[i for i,x in enumerate(ids) if x.startswith('programs_')]
        self.assertTrue(receipts and max(receipts)<census,'the census must spend only what the standard samples left');self.assertTrue(not programs or max(programs)<census)

    def tick_arrays(self,pool,lower,upper,liquidity,values):
        """Synthetic Raydium tick arrays for one position's boundaries, mirroring the concentrated fixture's layout."""
        import struct
        from solana_common import base58_bytes
        from solana_fixture import account
        from adapters.binary import discriminator
        from adapters import raydium_clmm
        for boundary in (lower,upper):
            start=(boundary//60)*60;addr=raydium_clmm.tick_array_address(pool,start,1)
            data=bytearray(10240);data[:8]=discriminator('TickArrayState');data[8:40]=base58_bytes(pool,32);struct.pack_into('<i',data,40,start)
            at=44+(boundary-start)*168;struct.pack_into('<i',data,at,boundary);data[at+20:at+36]=liquidity.to_bytes(16,'little')
            values[addr]={**account(bytes(data)),'owner':raydium_clmm.PROGRAM}

    def test_a_lead_whose_dependencies_do_not_fit_one_batch_is_dropped_and_the_share_recomputed(self):
        import base64,struct
        root,target,c,opts=self.setup_run();values=dict(RichRpc.values)
        specs=[(key(70),key(72),key(74),500_000,(-300,300)),(key(71),key(73),key(75),250_000,(-500,500)),(key(76),key(77),key(78),100_000,(-700,700))]
        extra=self.extra_clmm_positions(c,values,[s[:4] for s in specs])
        for (pos,_),(nft,owner,holder,liquidity,(lower,upper)) in zip(extra,specs):
            raw=bytearray(base64.b64decode(values[pos]['data'][0]));struct.pack_into('<ii',raw,73,lower,upper)
            values[pos]={**values[pos],'data':[base64.b64encode(bytes(raw)).decode(),'base64']};self.tick_arrays(c['pool'],lower,upper,liquidity,values)
        # shared 5 + config + the fixture lead's 2 arrays + 4 leads x 3 + 3 own array pairs = 26 > 25: the lowest-weight lead is dropped
        RichRpc.values.update(values);RichRpc.largest[c['pool']]=[c['position']]+[p for p,_ in extra]
        r=start(root,target,**opts);self.assertFalse(r['diagnostics'],r['diagnostics'])
        lead=next(l for l in json.loads((root/'automatic-leads.json').read_text()) if l['pool']==c['pool']);odd=extra[2][0]
        self.assertEqual((lead['census']['dropped_for_one_batch'],lead['census']['sampled'],len(lead['positions'])),([odd],3,3))
        self.assertEqual(lead['census']['sampled_weight_share']['percent_display'],'94.5946')  # 1,750,000 of 1,850,000 counted weight
        facts=json.loads((root/'draft/facts.json').read_text())['facts'];pool=next(f['data'] for f in facts if f['operation']=='pool' and f['data']['pool']==c['pool'])
        self.assertEqual([(row['status'],row['custody']['spending_owner']) for row in pool['positions']],[('observed',c['owner']),('observed',key(72)),('observed',key(73))])
        self.assertIn('94.5946% of liquidity ranking weight',__import__('solana_facts').describe('pool',pool))

    def test_clmm_lead_without_a_resolvable_holder_keeps_its_gap_in_the_row(self):
        root,target,c,opts=self.setup_run();original=RichRpc.__call__
        def refusing(rpc,request):
            if request['method']=='getTokenLargestAccounts' and request['params'][0]==c['nft']:
                raise urllib.error.HTTPError('https://synthetic.invalid',429,'limited',{'Retry-After':'10','x-ratelimit-method-limit':'0'},io.BytesIO(b''))
            return original(rpc,request)
        with unittest.mock.patch.object(RichRpc,'__call__',refusing):r=start(root,target,**opts)
        lead=next(l for l in json.loads((root/'automatic-leads.json').read_text()) if l['pool']==c['pool']);self.assertNotIn('holding',lead['positions'][0]);self.assertTrue(lead['positions'][0].get('holding_gap'))
        facts=json.loads((root/'draft/facts.json').read_text())['facts'];pool=next(f['data'] for f in facts if f['operation']=='pool' and f['data']['pool']==c['pool'])
        row=pool['positions'][0];self.assertEqual(row['status'],'partial');self.assertTrue(any('method_unavailable' in g or 'holder' in g for g in row['gaps']),row['gaps'])
        rows=[d for d in r['diagnostics'] if d.get('category')=='position_census_unavailable'];self.assertEqual(rows[0]['pools'][0]['status'],'sampled_unresolved')

if __name__=='__main__':unittest.main()
