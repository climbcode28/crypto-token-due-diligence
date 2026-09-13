from pathlib import Path
import sys,unittest,base64,struct
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'));sys.path.insert(0,str(Path(__file__).resolve().parent))
from solana_common import b58encode,base58_bytes
from solana_positions import census_read,census_leads,LAYOUTS,LEAD_CAP
from adapters.binary import discriminator
from adapters import raydium_clmm,meteora_dlmm


def key(n):return b58encode(bytes([n])*32)


def clmm_slice(pool,nft,liquidity):
    raw=bytearray(97);raw[:8]=discriminator('PersonalPositionState');raw[8]=250;raw[9:41]=base58_bytes(nft,32);raw[41:73]=base58_bytes(pool,32)
    struct.pack_into('<ii',raw,73,-100,100);raw[81:97]=liquidity.to_bytes(16,'little');return bytes(raw)


def dlmm_slice(pool,owner,shares):
    raw=bytearray(1192);raw[:8]=discriminator('PositionV2');raw[8:40]=base58_bytes(pool,32);raw[40:72]=base58_bytes(owner,32)
    for i,s in enumerate(shares):raw[72+16*i:88+16*i]=s.to_bytes(16,'little')
    return bytes(raw)


def packet(adapter,pool,rows,program):
    req=census_read(adapter,pool);request={'jsonrpc':'2.0','id':'census0_positions_0','method':req['method'],'params':req['params']}
    value=[{'pubkey':a,'account':{'owner':program,'executable':False,'lamports':1,'space':LAYOUTS[adapter]['size'],'data':[base64.b64encode(raw).decode(),'base64']}} for a,raw in rows]
    return {'request':request,'status':'ok','response':{'jsonrpc':'2.0','id':request['id'],'result':{'context':{'slot':500},'value':value}}}


class CensusTests(unittest.TestCase):
    def test_reads_are_bounded_pool_filters_with_a_ranking_slice(self):
        for adapter in ('raydium_clmm','meteora_dlmm'):
            r=census_read(adapter,key(60));options=r['params'][1];layout=LAYOUTS[adapter]
            self.assertEqual((options['filters'][0]['dataSize'],options['filters'][1]['memcmp'],options['dataSlice']),(layout['size'],{'offset':layout['pool_offset'],'bytes':key(60)},{'offset':0,'length':layout['slice']}))
            self.assertTrue(options['withContext'])
        with self.assertRaisesRegex(ValueError,'unsupported'):census_read('raydium_cpmm',key(60))

    def test_clmm_leads_rank_by_liquidity_and_carry_the_position_mint(self):
        pool=key(60);rows=[(key(11),clmm_slice(pool,key(21),5)),(key(12),clmm_slice(pool,key(22),900)),(key(13),clmm_slice(pool,key(23),0)),(key(14),clmm_slice(pool,key(24),95))]
        leads,summary=census_leads('raydium_clmm',pool,packet('raydium_clmm',pool,rows,raydium_clmm.PROGRAM))
        self.assertEqual([l['position'] for l in leads],[key(12),key(14),key(11)]);self.assertEqual(leads[0]['position_mint'],key(22));self.assertEqual(leads[0]['kind'],'census')
        self.assertEqual((summary['positions_counted'],summary['positions_with_liquidity'],summary['sampled'],summary['context_slot']),(4,3,3,500))
        self.assertEqual(summary['sampled_weight_share']['percent_display'],'100.0000');self.assertEqual(leads[0]['evidence'],['census0_positions_0'])

    def test_dlmm_leads_rank_by_summed_shares_and_carry_the_owner_and_cap_applies(self):
        pool=key(60);rows=[(key(10+i),dlmm_slice(pool,key(30+i),[i+1,i+1,0])) for i in range(6)]
        leads,summary=census_leads('meteora_dlmm',pool,packet('meteora_dlmm',pool,rows,meteora_dlmm.PROGRAM))
        self.assertEqual(len(leads),LEAD_CAP);self.assertEqual(leads[0]['position'],key(15));self.assertEqual(leads[0]['spending_owner'],key(35))
        self.assertEqual(summary['positions_counted'],6);self.assertEqual(summary['ranking'],'summed_bin_shares_u128_from_72')
        self.assertEqual(summary['sampled_weight_share']['percent_display'],'85.7143')  # (6+5+4+3)/(6+5+4+3+2+1) doubled shares cancel

    def test_rows_with_another_discriminator_are_counted_as_other_layouts_not_positions(self):
        pool=key(60);good=clmm_slice(pool,key(21),5);other=bytearray(good);other[:8]=discriminator('TickArrayState')
        leads,summary=census_leads('raydium_clmm',pool,packet('raydium_clmm',pool,[(key(11),good),(key(12),bytes(other))],raydium_clmm.PROGRAM))
        self.assertEqual(([l['position'] for l in leads],summary['positions_counted'],summary['other_layouts_skipped']),([key(11)],1,1))

    def test_out_of_range_clmm_ticks_are_counted_as_invalid_rows_not_leads(self):
        pool=key(60);bad=bytearray(clmm_slice(pool,key(21),5));struct.pack_into('<ii',bad,73,-2**31,100)
        leads,summary=census_leads('raydium_clmm',pool,packet('raydium_clmm',pool,[(key(11),clmm_slice(pool,key(22),7)),(key(12),bytes(bad))],raydium_clmm.PROGRAM))
        self.assertEqual(([l['position'] for l in leads],summary['positions_counted'],summary['invalid_rows_skipped']),([key(11)],1,1))

    def test_foreign_pool_rows_and_wrong_pool_requests_are_refused(self):
        pool=key(60);other=key(61)
        bad=packet('raydium_clmm',pool,[(key(11),clmm_slice(other,key(21),5))],raydium_clmm.PROGRAM)
        with self.assertRaises(ValueError):census_leads('raydium_clmm',pool,bad)
        with self.assertRaisesRegex(ValueError,'not this pool census'):census_leads('raydium_clmm',other,packet('raydium_clmm',pool,[],raydium_clmm.PROGRAM))
        empty=packet('raydium_clmm',pool,[],raydium_clmm.PROGRAM);leads,summary=census_leads('raydium_clmm',pool,empty)
        self.assertEqual((leads,summary['positions_counted'],summary['sampled_weight_share']),([],0,None))


if __name__=='__main__':unittest.main()
