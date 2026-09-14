import json,time,threading,copy,base64,io,urllib.error
from solana_fixture import Rpc,response
from pool_fixture import fixture,key,holding
from solana_discovery import MAINNET
from test_solana_web_capture import Response
from adapters.meteora_common import CLOCK
from meteora_fixture import clock


def program_accounts(program,authority=None,slot=50):
    """An upgradeable program account plus its ProgramData PDA (metadata: slot and an upgrade authority)."""
    from solana_fixture import account
    from solana_common import base58_bytes
    from solana_addresses import find_program_address
    from solana_programs import UPGRADEABLE
    pd=find_program_address([base58_bytes(program,32)],UPGRADEABLE)[0]
    prog={**account(bytes([2,0,0,0])+base58_bytes(pd,32)),'owner':UPGRADEABLE,'executable':True}
    auth=authority or key(93)
    data={**account(bytes([3,0,0,0])+slot.to_bytes(8,'little')+b'\1'+base58_bytes(auth,32)),'owner':UPGRADEABLE}
    return {program:prog,pd:data}


class RichRpc(Rpc):
    values={};pool=None;target=None;largest={}
    @classmethod
    def reset(cls):
        target,a,v=fixture();cls.target=target;cls.pool=a;cls.values=copy.deepcopy(v);cls.values[CLOCK]=clock(timestamp=int(time.time()))
        cls.values[key(7)]=holding(target['mint'],key(8),10000);cls.largest={target['mint']:[key(7)],a['lp']:[a['holder']]}
        from metadata_fixture import metadata_account
        cls.metadata=metadata_account(target['mint'],update_authority=key(90),creators=[(key(91),True,60),(key(92),False,40)]);cls.values[cls.metadata['address']]=cls.metadata['account']
        cls.calls=[];cls.active=cls.peak=0;cls.mode='normal';cls.stamp=int(time.time());cls.receipt=None;cls.receipts={};Web.token_info=True;Web.pairs=None;Web.trades=None;Web.rugcheck=None;return target
    def __call__(self,req):
        cls=type(self)
        with cls.lock:cls.calls.append(copy.deepcopy(req));cls.active+=1;cls.peak=max(cls.peak,cls.active)
        try:
            if cls.mode=='timeout':raise TimeoutError('fixture timeout')
            m,p=req['method'],req['params']
            if m=='getGenesisHash':value=key(3) if cls.mode=='wrong_network' else MAINNET
            elif m in ('getAccountInfo','getMultipleAccounts'):
                keys=p[0] if m=='getMultipleAccounts' else [p[0]];vals=[copy.deepcopy(cls.values.get(k)) for k in keys]
                value={'context':{'slot':100},'value':vals if m=='getMultipleAccounts' else vals[0]}
            elif m=='getEpochInfo':value={'absoluteSlot':100,'blockHeight':80,'epoch':1,'slotIndex':10,'slotsInEpoch':90}
            elif m=='getTokenLargestAccounts':
                if cls.mode=='largest_refused':raise urllib.error.HTTPError('https://synthetic.invalid',429,'limited',{'Retry-After':'10','x-ratelimit-method-limit':'0'},io.BytesIO(b''))
                from solana_accounts import decode_holding,decode_mint
                decimals=decode_mint(cls.values[p[0]])['decimals']
                value={'context':{'slot':100},'value':[{'address':a,'amount':decode_holding(cls.values[a])['amount_atomic'],'decimals':decimals} for a in cls.largest.get(p[0],[])]}
            elif m=='getProgramAccounts':
                mint_key=p[1]['filters'][1]['memcmp']['bytes'];part=p[1].get('dataSlice');rows=[]
                for a in cls.largest.get(mint_key,[]):
                    acct=copy.deepcopy(cls.values[a]);raw=base64.b64decode(acct['data'][0])
                    if part:acct['data']=[base64.b64encode(raw[part['offset']:part['offset']+part['length']]).decode(),'base64']
                    rows.append({'pubkey':a,'account':acct})
                value={'context':{'slot':100},'value':rows}
            elif m=='getBlock':value={'blockhash':key(20),'previousBlockhash':key(21),'parentSlot':p[0]-1,'blockTime':cls.stamp}
            elif m=='getBlockTime':value=cls.stamp
            elif m=='getSignaturesForAddress':
                # Optional extra receipts (signature -> transaction) precede the swap receipt in the recent page.
                rows=[{'signature':sig,'slot':100,'err':None,'memo':None,'blockTime':cls.stamp} for sig in cls.receipts]
                value=rows+([{'signature':cls.receipt['transaction']['signatures'][0],'slot':100,'err':None,'memo':None,'blockTime':cls.stamp}] if cls.receipt else [])
            elif m=='getTransaction':
                value=cls.receipts.get(p[0],cls.receipt)
                if isinstance(value,BaseException):raise value  # One signature's receipt fails at the transport.
                value=copy.deepcopy(value)
            else:value=None
            result=response(req,value);self.local.response_bytes=len(json.dumps(result).encode());return result
        finally:
            with cls.lock:cls.active-=1


class Web:
    calls=[];blocked=False;token_info=True;pairs=None;trades=None;rugcheck=None  # pairs overrides the single default DEX Screener pair; trades feeds every pool's trade listing; rugcheck: None default report, False refused, or a body
    def open(self,request,timeout):
        cls=type(self);cls.calls.append(request.full_url);url=request.full_url
        if cls.blocked:return Response(b'Unavailable',403,{'Content-Type':'text/plain'})
        if 'api.dexscreener.com' in url:
            value=cls.pairs if cls.pairs is not None else [{'chainId':'solana','pairAddress':RichRpc.pool['pool'],'baseToken':{'address':RichRpc.target['mint']},'quoteToken':{'address':key(3)},'dexId':'raydium',
              'liquidity':{'usd':'1000000'},'priceUsd':'2','volume':{'h24':'500000'},'info':{'websites':[{'url':'https://project.example/token'}]}}]
        elif 'geckoterminal' in url and url.endswith('/info'):
            value={'data':{'id':'solana_'+RichRpc.target['mint'],'type':'token','attributes':{'address':RichRpc.target['mint'],'name':'Coin','symbol':'COIN','websites':['https://project.example/'],'twitter_handle':None,'telegram_handle':None,'discord_url':None}}} if cls.token_info else {'data':{}}
        elif 'api.rugcheck.xyz' in url:
            from solana_accounts import decode_mint
            if cls.rugcheck is False:return Response(b'rate limited',429,{'Content-Type':'text/plain'})
            supply=int(decode_mint(RichRpc.values[RichRpc.target['mint']])['supply_atomic'])
            value=cls.rugcheck or {'mint':RichRpc.target['mint'],'token':{'supply':supply,'decimals':decode_mint(RichRpc.values[RichRpc.target['mint']])['decimals']},'tokenMeta':{'name':'Coin','symbol':'COIN'},
                'score':1200,'score_normalised':12,'rugged':False,'totalHolders':321,'graphInsidersDetected':7,'detectedAt':'2026-09-01T00:00:00Z',
                'insiderNetworks':[{'id':'knotty-yellow-snail','size':5,'type':'transfer','tokenAmount':supply//5,'activeAccounts':5},{'id':'vast-mango','size':2,'type':'transfer','tokenAmount':supply//50,'activeAccounts':2}],
                'topHolders':[{'address':key(7),'owner':key(8),'amount':10000,'decimals':9,'pct':0.01,'insider':False},{'address':key(70),'owner':key(71),'amount':5000,'decimals':9,'pct':0.005,'insider':True}],
                'lockers':{key(72):{'owner':key(73),'type':'streamflow','usdcLocked':1000}},'lockerOwners':{},'totalLPProviders':1,
                'markets':[{'pubkey':RichRpc.pool['pool'],'marketType':'raydium_cpmm'}],'creator':key(90),'creatorTokens':[],'mintAuthority':None,'freezeAuthority':None,
                'risks':[{'name':'Low amount of LP Providers','level':'warn','score':300,'description':'x'}],'verification':None}
        elif 'geckoterminal' in url and url.endswith('/trades'):value={'data':cls.trades or []}
        elif 'geckoterminal' in url:value={'data':[]}
        elif 'lite-api.jup.ag' in url:
            from urllib.parse import urlsplit,parse_qsl
            from solana_accounts import decode_mint
            q=dict(parse_qsl(urlsplit(url).query));out=q['outputMint'];amount=int(q['amount']);scale=10**decode_mint(RichRpc.values[RichRpc.target['mint']])['decimals']
            # Half the input back, less a shortfall that grows with the size in whole tokens: 50 tokens quote at 0.4995, 5000 at 0.45.
            quoted=str(amount*5//10-amount*(amount//scale)//100000);threshold=str(int(quoted)*997//1000)
            value={'inputMint':q['inputMint'],'outputMint':out,'inAmount':q['amount'],'outAmount':quoted,'otherAmountThreshold':threshold,'slippageBps':int(q['slippageBps']),'swapMode':'ExactIn',
                   'priceImpactPct':'0.0012','contextSlot':100,'swapUsdValue':'1.5','routePlan':[{'swapInfo':{'ammKey':RichRpc.pool['pool'],'label':'Raydium','inputMint':q['inputMint'],'outputMint':out,'inAmount':q['amount'],'outAmount':quoted,'feeAmount':'3','feeMint':q['inputMint']},'percent':100}]}
        else:value={'mint':RichRpc.target['mint'],'claim':'Dated public project description; runtime remains separately verified.'}
        return Response(json.dumps(value).encode())
