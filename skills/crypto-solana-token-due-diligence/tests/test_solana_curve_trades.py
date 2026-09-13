from pathlib import Path
import sys,struct,unittest,copy
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from pump_fixture import fixture,receipt,key,CURVE_PROGRAM,TOKEN_PROGRAM
from adapters.pump_instructions import tag
from solana_transactions import decode_transaction,verify_sales,verify_rebuys,classify_receipt,SYSTEM


def legacy_sell(min_out=900,user_post=1000950):
    target,a,_=fixture();m=target['mint'];c=a['curve'];ch=a['curve_holding'];ub,u,fee,cv=key(42),key(43),key(41),key(44)
    accounts=[key(40),fee,m,c,ch,ub,u,SYSTEM,cv,TOKEN_PROGRAM,key(45),CURVE_PROGRAM,key(46),key(47)]
    outer=(CURVE_PROGRAM,accounts,tag('sell')+struct.pack('<QQ',500,min_out));inner=[(TOKEN_PROGRAM,[ub,m,ch,u],struct.pack('<BQB',12,500,6))]
    p,b=receipt(target,outer,inner,balances=[(ub,m,u,1000,500),(ch,m,c,500,1000)],native={c:(10000000,9999000),u:(1000000,user_post),fee:(1000000,1000040),cv:(1000000,1000010)})
    return target,a,u,p,b


def legacy_buy(max_cost=1000,extra=None):
    target,a,_=fixture();m=target['mint'];c=a['curve'];ch=a['curve_holding'];ub,u,fee,cv=key(42),key(43),key(41),key(44)
    accounts=[key(40),fee,m,c,ch,ub,u,SYSTEM,TOKEN_PROGRAM,cv,key(45),CURVE_PROGRAM,key(48),key(49),key(46),key(47)]
    outer=(CURVE_PROGRAM,accounts,tag('buy')+struct.pack('<QQ',500,max_cost)+b'\x00')
    inner=[(SYSTEM,[u,c],struct.pack('<IQ',2,900)),(SYSTEM,[u,fee],struct.pack('<IQ',2,40)),(SYSTEM,[u,cv],struct.pack('<IQ',2,10)),(TOKEN_PROGRAM,[ch,m,ub,c],struct.pack('<BQB',12,500,6))]
    user_post=999050
    if extra:inner.append((SYSTEM,[u,extra],struct.pack('<IQ',2,100)));user_post-=100
    p,b=receipt(target,outer,inner,balances=[(ub,m,u,0,500),(ch,m,c,1000,500)],native={c:(10000000,10000900),u:(1000000,user_post),fee:(1000000,1000040),cv:(1000000,1000010),**({extra:(1000000,1000100)} if extra else {})})
    return target,a,u,p,b


def v2_native_buy_exact_quote():
    target,a,_=fixture();m=target['mint'];c=a['curve'];ch=a['curve_holding'];u,ub,fee=key(43),key(42),key(41)
    from solana_transactions import WSOL as W
    accounts=[key(40),m,W,TOKEN_PROGRAM,TOKEN_PROGRAM,key(51),fee,key(52),key(53),key(54),c,ch,key(55),u,ub,key(56),key(44),key(57),key(58),key(59),key(60),key(61),key(46),key(47),SYSTEM,key(45),CURVE_PROGRAM]
    outer=(CURVE_PROGRAM,accounts,tag('buy_exact_quote_in_v2')+struct.pack('<QQ',1000,400))  # specified quote spent, threshold minimum base out
    inner=[(TOKEN_PROGRAM,[ch,m,ub,c],struct.pack('<BQB',12,500,6))]  # curve holding -> user base account
    p,b=receipt(target,outer,inner,balances=[(ub,m,u,0,500),(ch,m,c,1000,500)],native={c:(10000000,10000000),u:(1000000,1000000),fee:(1000000,1000000)})
    return target,a,u,p,b


def v2_sell():
    target,a,_=fixture();m=target['mint'];q=key(3);c=a['curve'];ch=a['curve_holding'];u,ub,uq,qh=key(43),key(42),key(56),key(55);fee,afee,bb,abb,cv,acv=key(41),key(52),key(53),key(54),key(44),key(57)
    accounts=[key(40),m,q,TOKEN_PROGRAM,TOKEN_PROGRAM,key(51),fee,afee,bb,abb,c,ch,qh,u,ub,uq,cv,acv,key(58),key(59),key(60),key(46),key(47),SYSTEM,key(45),CURVE_PROGRAM]
    outer=(CURVE_PROGRAM,accounts,tag('sell_v2')+struct.pack('<QQ',500,900))
    inner=[(TOKEN_PROGRAM,[ub,m,ch,u],struct.pack('<BQB',12,500,6)),(TOKEN_PROGRAM,[qh,q,uq,c],struct.pack('<BQB',12,950,6)),(TOKEN_PROGRAM,[qh,q,afee,c],struct.pack('<BQB',12,40,6)),
           (TOKEN_PROGRAM,[qh,q,abb,c],struct.pack('<BQB',12,5,6)),(TOKEN_PROGRAM,[qh,q,acv,c],struct.pack('<BQB',12,10,6))]
    balances=[(ub,m,u,1000,500),(ch,m,c,500,1000),(qh,q,c,2000,995),(uq,q,u,0,950),(afee,q,fee,0,40),(abb,q,bb,0,5),(acv,q,cv,0,10)]
    p,b=receipt(target,outer,inner,balances=balances);return target,a,u,p,b


def v2_native_sell(wrap=True):
    """A v2 sell with a SOL quote: the curve pays lamports to the user and the three native fee recipients; the user then
    creates a temporary WSOL account, wraps the proceeds into it and closes it (the common router pattern)."""
    target,a,_=fixture();m=target['mint'];c=a['curve'];ch=a['curve_holding'];u,ub=key(43),key(42);fee,bb,cv=key(41),key(53),key(44);wsol_tmp=key(61)
    from solana_transactions import WSOL as W
    accounts=[key(40),m,W,TOKEN_PROGRAM,TOKEN_PROGRAM,key(51),fee,key(52),bb,key(54),c,ch,key(55),u,ub,key(56),cv,key(57),key(58),key(59),key(60),key(46),key(47),SYSTEM,key(45),CURVE_PROGRAM]
    outer=(CURVE_PROGRAM,accounts,tag('sell_v2')+struct.pack('<QQ',500,900));inner=[(TOKEN_PROGRAM,[ub,m,ch,u],struct.pack('<BQB',12,500,6))]
    native={c:(10000000,9998900),u:(1000000,1001000),fee:(1000000,1000040),bb:(1000000,1000050),cv:(1000000,1000010)}  # the wrap-and-close returns the rent and the 950
    p,b=receipt(target,outer,inner,balances=[(ub,m,u,1000,500),(ch,m,c,500,1000)],native=native)
    if wrap:  # append the user's own wrap-and-close lifecycle after the trade: create, transfer, sync, close
        tx=p['response']['result'];msg=tx['transaction']['message'];keys=msg['accountKeys']
        for k in (wsol_tmp,):
            keys.append(k);tx['meta']['preBalances'].append(0);tx['meta']['postBalances'].append(0)
        from solana_common import b58encode,base58_bytes
        ix=lambda program,accs,raw:{'programIdIndex':keys.index(program),'accounts':[keys.index(x) for x in accs],'data':b58encode(raw)}
        msg['instructions']+=[ix(SYSTEM,[u,wsol_tmp],struct.pack('<IQQ',0,1488440,165)+base58_bytes(TOKEN_PROGRAM,32)),ix(TOKEN_PROGRAM,[wsol_tmp,W],bytes([18])+base58_bytes(u,32)),
            ix(SYSTEM,[u,wsol_tmp],struct.pack('<IQ',2,950)),ix(TOKEN_PROGRAM,[wsol_tmp],b'\x11'),ix(TOKEN_PROGRAM,[wsol_tmp,u,u],b'\x09')]
    return target,a,u,p,b


class CurveTradeTests(unittest.TestCase):
    def test_v2_sol_quote_sell_is_native_and_nets_the_traders_wrap_lifecycle(self):
        for wrap in (False,True):
            target,a,u,p,b=v2_native_sell(wrap=wrap);e=decode_transaction(target,p,b);self.assertEqual(e['gaps'],[],wrap)
            trade=next(x for x in e['effects'] if x['kind']=='protocol_trade_instruction');self.assertTrue(trade['quote_native'])
            row=verify_sales(target,[{'pool':a['curve'],'execution':e}])['receipts'][0]
            self.assertEqual((row['status'],row['seller'],row['input_atomic'],row['output_atomic'],row.get('quote')),('verified_sale',u,'500','1000','native_sol'),(wrap,row['gaps']))
            self.assertEqual([(f['amount_atomic'],f['destination']) for f in row['protocol_fees_atomic']],[('40',key(41)),('50',key(53)),('10',key(44))])
            self.assertEqual(row['native_proceeds']['other_native_delta_lamports'],'0')  # create, wrap and closure net to zero
        # A wrapped amount the user spent elsewhere (a WSOL transfer out of the temporary account) is not returned by the closure.
        target,a,u,p,b=v2_native_sell(wrap=True);tx=p['response']['result'];msg=tx['transaction']['message'];keys=msg['accountKeys']
        from solana_common import b58encode
        sink=key(62);keys.append(sink);tx['meta']['preBalances'].append(0);tx['meta']['postBalances'].append(950)
        close=msg['instructions'].pop();msg['instructions'].append({'programIdIndex':keys.index(TOKEN_PROGRAM),'accounts':[keys.index(key(61)),keys.index(sink),keys.index(u)],'data':b58encode(bytes([3])+(950).to_bytes(8,'little'))});msg['instructions'].append(close)
        tx['meta']['postBalances'][keys.index(u)]=1000050  # the user keeps only the rent back
        e=decode_transaction(target,p,b);row=verify_sales(target,[{'pool':a['curve'],'execution':e}])['receipts'][0]
        self.assertEqual((row['status'],row['native_proceeds']['other_native_delta_lamports'],row['counter_asset_realization'],row['route']),('verified_sale','-950','native_lamports_to_wallet','direct'),row['gaps'])
        # The same wrap feeding another decoded leg of the route is a conversion, not lamports kept by the wallet.
        e['effects'].append({'kind':'swap_instruction','adapter':'x','id':'swap2','locator':{'outer_index':9,'inner_index':None},'pool':key(90),'input_account':key(61),'output_account':key(91),'vaults':[sink,key(92)],'mints':[],'mode':'exact_in','specified_amount_atomic':'950','threshold_atomic':'1','participants':{}})
        row=verify_sales(target,[{'pool':a['curve'],'execution':e}])['receipts'][0]
        self.assertEqual((row['status'],row['counter_asset_realization'],row['route']),('verified_sale','converted_within_route','aggregated'),row['gaps']);self.assertIn('re-wrapped',row['native_proceeds']['scope'])

    def test_legacy_native_sell_verifies_from_lamport_deltas(self):
        target,a,u,p,b=legacy_sell();e=decode_transaction(target,p,b);self.assertEqual(e['gaps'],[])
        self.assertEqual((classify_receipt(target,p,a['curve'])['swap'],classify_receipt(target,p,a['curve'])['direction']),(True,'sell'))
        row=verify_sales(target,[{'pool':a['curve'],'execution':e}])['receipts'][0]
        self.assertEqual((row['status'],row['seller'],row['input_atomic'],row['output_atomic'],row['quote'],row['route']),('verified_sale',u,'500','950','native_sol','direct'),row['gaps'])
        self.assertEqual([(f['amount_atomic'],f['destination']) for f in row['protocol_fees_atomic']],[('40',key(41)),('10',key(44))])
        self.assertEqual((row['native_proceeds']['gross_sale_lamports'],row['native_proceeds']['seller_network_fee_lamports'],row['native_proceeds']['observed_seller_native_delta_lamports']),('950','0','950'))
        self.assertEqual(verify_rebuys(target,[{'pool':a['curve'],'execution':e}])['verified_receipts'],0)  # a sale is not a rebuy
        target,a,u,p,b=legacy_sell(min_out=1000);row=verify_sales(target,[{'pool':a['curve'],'execution':decode_transaction(target,p,b)}])['receipts'][0]
        self.assertEqual(row['status'],'unverified');self.assertIn('below the instruction minimum',row['gaps'][0])
        target,a,u,p,b=legacy_sell(user_post=1000900);row=verify_sales(target,[{'pool':a['curve'],'execution':decode_transaction(target,p,b)}])['receipts'][0]
        self.assertEqual(row['status'],'unverified');self.assertIn('does not reconcile',row['gaps'][0]);self.assertIn('residual -50 lamports',row['gaps'][0])
        # The base leg is reconciled against both accounts' historical balances, not only the instruction amount.
        target,a,u,p,b=legacy_sell();tx=p['response']['result'];keys=tx['transaction']['message']['accountKeys']
        for r in tx['meta']['postTokenBalances']:
            if r['accountIndex']==keys.index(key(42)):r['uiTokenAmount']['amount']='600'
        row=verify_sales(target,[{'pool':a['curve'],'execution':decode_transaction(target,p,b)}])['receipts'][0]
        self.assertEqual(row['status'],'unverified');self.assertIn('historical token delta disagree',row['gaps'][0])

    def test_legacy_native_buy_verifies_from_explicit_lamport_transfers(self):
        target,a,u,p,b=legacy_buy();e=decode_transaction(target,p,b);self.assertEqual(e['gaps'],[])
        self.assertEqual(classify_receipt(target,p,a['curve'])['direction'],'buy')
        row=verify_rebuys(target,[{'pool':a['curve'],'execution':e}])['receipts'][0]
        self.assertEqual((row['status'],row['buyer'],row['input_atomic'],row['output_atomic'],row['quote']),('verified_rebuy',u,'900','500','native_sol'),row['gaps'])
        self.assertEqual([(f['amount_atomic'],f['destination']) for f in row['protocol_fees_atomic']],[('40',key(41)),('10',key(44))])
        target,a,u,p,b=legacy_buy(max_cost=940);row=verify_rebuys(target,[{'pool':a['curve'],'execution':decode_transaction(target,p,b)}])['receipts'][0]
        self.assertEqual(row['status'],'unverified');self.assertIn('above the instruction maximum',row['gaps'][0])
        target,a,u,p,b=legacy_buy(extra=key(50));row=verify_rebuys(target,[{'pool':a['curve'],'execution':decode_transaction(target,p,b)}])['receipts'][0]
        self.assertEqual(row['status'],'unverified');self.assertIn('leave the trade accounts',row['gaps'][0])

    def test_v2_native_exact_quote_in_buy_is_refused_with_a_clear_message(self):
        target,a,u,p,b=v2_native_buy_exact_quote();e=decode_transaction(target,p,b);self.assertEqual(e['gaps'],[])
        trade=next(x for x in e['effects'] if x['kind']=='protocol_trade_instruction');self.assertEqual((trade['quote_native'],trade['mode']),(True,'exact_in_fee_inclusive'))
        row=verify_rebuys(target,[{'pool':a['curve'],'execution':e}])['receipts'][0]
        self.assertEqual(row['status'],'unverified');self.assertIn('exact-quote-in curve buy',row['gaps'][0])  # not the misleading 'base amount and instruction disagree'

    def test_v2_token_quote_sell_verifies_as_an_ordinary_leg(self):
        target,a,u,p,b=v2_sell();e=decode_transaction(target,p,b);self.assertEqual(e['gaps'],[])
        trade=next(x for x in e['effects'] if x['kind']=='protocol_trade_instruction');self.assertEqual((trade['quote_native'],trade['mode'],trade['participants']['rebate']),(False,'exact_in',key(60)))
        row=verify_sales(target,[{'pool':a['curve'],'execution':e}])['receipts'][0]
        self.assertEqual((row['status'],row['seller'],row['input_atomic'],row['output_atomic'],row['counter_mint']),('verified_sale',u,'500','950',key(3)),row['gaps'])
        self.assertEqual(sorted(f['amount_atomic'] for f in row['protocol_fees_atomic']),['10','40','5'])


if __name__=='__main__':unittest.main()
