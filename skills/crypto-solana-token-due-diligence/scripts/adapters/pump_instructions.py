"""Pinned Pump instruction facts. Intended swaps are not reconciled sales."""
import hashlib
from adapters.binary import Reader
from adapters.pump_common import CURVE_PROGRAM,SWAP_PROGRAM,WSOL,curve_address,pool_authority,pool_address
from solana_common import need,TOKEN_PROGRAM,TOKEN_2022


def tag(name):return hashlib.sha256(('global:'+name).encode()).digest()[:8]


def decode(program,raw,a):
    if program not in (CURVE_PROGRAM,SWAP_PROGRAM):return None
    e={'mint':None,'amount_atomic':None,'participants':{},'quantity_scope':'protocol instruction roles; actual movements and beneficiaries need effect reconciliation'}
    if program==CURVE_PROGRAM and raw[:8] in (tag('create'),tag('create_v2')):
        v2=raw[:8]==tag('create_v2')
        need(len(a)==(16 if v2 else 14),'unsupported Pump create accounts')  # pinned IDL: create_v2 has exactly 16 accounts
        r=Reader(raw);r.take(8)
        texts=[]
        for cap in (256,64,2048):
            n=r.integer(4);need(n<=cap,'Pump metadata string exceeds bound');texts.append(r.take(n).decode('utf-8'))
        creator=r.key();mayhem=False;cashback=None
        if v2:
            flag=r.integer(1);need(flag in (0,1),'invalid create mayhem flag');mayhem=bool(flag)
            flag=r.integer(1);need(flag in (0,1),'invalid create cashback flag');cashback=bool(flag)
        need(r.offset==len(raw),'unsupported Pump create arguments')
        mint,curve=a[0],a[2];need(curve==curve_address(mint),'Pump create curve PDA mismatch')
        token_program=a[7] if v2 else a[9];need(token_program==(TOKEN_2022 if v2 else TOKEN_PROGRAM),'Pump create token program mismatch')
        e.update(kind='launch_initialize',mint=mint,curve=curve,base_holding=a[3],token_program=token_program,
            participants={'mint':mint,'curve':curve,'creator_argument':creator,'payer':a[5] if v2 else a[7]},
            metadata_claim={'name':texts[0],'symbol':texts[1],'uri':texts[2]},is_mayhem_mode=mayhem,is_cashback_coin=cashback,
            quote_mint=None if v2 else WSOL,quote_mint_scope='v2 quote mint is BondingCurve state, not a create argument' if v2 else 'legacy curve quotes in WSOL')
    elif program==CURVE_PROGRAM and raw[:8] in (tag('migrate'),tag('migrate_v2')):
        v2=raw[:8]==tag('migrate_v2');need(len(raw)==8 and len(a)==(27 if v2 else 25),'unsupported Pump migration layout')
        mint=a[2];quote=a[3] if v2 else a[14];curve=a[4] if v2 else a[3];pool=a[10] if v2 else a[9];authority=a[11] if v2 else a[10]
        need(a[9 if v2 else 8]==SWAP_PROGRAM and curve==curve_address(mint),'migration curve/destination program mismatch')
        need(authority==pool_authority(mint) and pool==pool_address(mint,quote),'migration destination pool PDA mismatch')
        if not v2:need(quote==WSOL,'legacy migration quote must be WSOL')
        e.update(kind='launch_migrate',mint=mint,curve=curve,pool=pool,quote_mint=quote,lp_mint=a[15],vaults=a[17:19],
            participants={'curve':curve,'pool':pool,'pool_creator':authority,'caller':a[7] if v2 else a[5]})
    elif program==SWAP_PROGRAM and raw[:8]==tag('create_pool'):
        need(len(a)==18 and len(raw)==60,'unsupported PumpSwap create arguments/accounts')
        r=Reader(raw);r.take(8);index=r.integer(2);base=r.integer(8);quote=r.integer(8);creator=r.key();mayhem=r.integer(1);cashback=r.integer(1)
        need(mayhem in (0,1) and cashback in (0,1),'invalid PumpSwap create flags')
        need(a[0]==pool_address(a[3],a[4],creator=a[2],index=index),'PumpSwap created pool PDA mismatch')
        e.update(kind='pool_initialize',mint=a[3],pool=a[0],quote_mint=a[4],lp_mint=a[5],vaults=a[9:11],index=index,
            requested_base_atomic=str(base),requested_quote_atomic=str(quote),participants={'pool':a[0],'pool_creator':a[2],'coin_creator_argument':creator})
    elif program==SWAP_PROGRAM and raw[:8]==tag('withdraw'):
        need(len(a)==15 and len(raw)==32,'unsupported PumpSwap withdrawal')
        e.update(kind='position_liquidity_remove',pool=a[0],mint=a[5],mints=a[3:5],participants={'holding':a[8],'signer':a[2]},
            lp_units=str(int.from_bytes(raw[8:16],'little')))
    elif program==CURVE_PROGRAM and raw[:8] in (tag('collect_creator_fee'),tag('collect_creator_fee_v2')):
        v2=raw[:8]==tag('collect_creator_fee_v2');need(len(raw)==8 and len(a)==(10 if v2 else 5),'unsupported Pump fee claim')
        e.update(kind='creator_fee_claim',mint=a[4] if v2 else None,participants={'creator':a[0],'vault':a[2] if v2 else a[1],
            'destination':a[1] if v2 else a[0]})
    elif program==SWAP_PROGRAM and raw[:8]==tag('collect_coin_creator_fee'):
        need(len(raw)==8 and len(a)==8,'unsupported PumpSwap fee claim')
        e.update(kind='creator_fee_claim',mint=a[0],participants={'creator':a[2],'vault':a[4],'destination':a[5]})
    elif program==CURVE_PROGRAM and raw[:8] in (tag('sell'),tag('buy'),tag('sell_v2'),tag('buy_v2'),tag('buy_exact_quote_in_v2')):
        legacy=raw[:8] in (tag('sell'),tag('buy'));sell=raw[:8] in (tag('sell'),tag('sell_v2'));exact_quote=raw[:8]==tag('buy_exact_quote_in_v2')
        # Named roles are positional; routers may append remaining accounts. A legacy buy carries its one-byte track_volume flag.
        if raw[:8]==tag('buy'):need(len(raw)==25 and raw[24] in (0,1) and len(a)>=16,'unsupported Pump trade layout')
        else:need(len(raw)==24 and len(a)>=(14 if legacy else 26 if sell else 27),'unsupported Pump trade layout')
        mint=a[2] if legacy else a[1];curve=a[3] if legacy else a[10];need(curve==curve_address(mint),'Pump trade curve mismatch')
        quote_mint=WSOL if legacy else a[2]
        if legacy:participants={'user':a[6],'base_account':a[5],'curve_holding':a[4],'fee_recipient':a[1],'creator_vault':a[8] if sell else a[9]}
        else:participants={'user':a[13],'base_account':a[14],'quote_account':a[15],'curve_holding':a[11],'quote_holding':a[12],'fee_recipient':a[6],'quote_fee_account':a[7],
            'buyback':a[8],'quote_buyback_account':a[9],'creator_vault':a[16],'quote_creator_account':a[17],'rebate':a[20] if sell else a[21]}
        # A SOL quote is paid and received as lamports even on v2 (the quote ATAs exist but the program moves lamports).
        e.update(kind='protocol_trade_instruction',mint=mint,curve=curve,quote_mint=quote_mint,quote_native=legacy or quote_mint==WSOL,
            direction='sell_base' if sell else 'buy_base',mode='exact_in' if sell else 'exact_in_fee_inclusive' if exact_quote else 'exact_out',
            participants=participants,specified_atomic=str(int.from_bytes(raw[8:16],'little')),
            threshold_atomic=str(int.from_bytes(raw[16:24],'little')),sale_verified=False)
    else:return None
    return e
