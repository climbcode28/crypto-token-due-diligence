"""Bounded read plans. Discovery and sample contexts remain separate observations."""
import base64

from solana_common import need, pubkey, TOKEN_PROGRAM
from solana_session import label
from solana_wire import validate_request

ACCOUNT_BATCH = 25
RESPONSE_LIMIT = 1_000_000
SCAN_SLICE = {"offset": 0, "length": 72}  # mint, spending owner and amount of an SPL token account
LEAD_LIMIT = 20


def settings(floor=None):
    value = {"commitment": "finalized", "encoding": "base64"}
    if floor is not None:
        value["minContextSlot"] = floor
    return value


def read(name, method, params, *, depends=(), critical=False):
    label(name)
    validate_request({"jsonrpc": "2.0", "id": name, "method": method, "params": params})
    for parent in depends:
        label(parent)
    need(type(critical) is bool, "critical read flag required")
    return {"name": name, "method": method, "params": params, "depends": list(depends), "critical": critical}


def account_batches(addresses, *, prefix="accounts", floor=None, depends=(), critical=False,
                    account_bytes=4096, max_response_bytes=RESPONSE_LIMIT):
    """Bound both array length and estimated encoded response size; hard wire cap still applies."""
    need(type(account_bytes) is int and 1 <= account_bytes <= 1_000_000, "invalid account estimate")
    need(type(max_response_bytes) is int and 1024 <= max_response_bytes <= 16_000_000, "invalid response bound")
    need(isinstance(addresses, list) and len(addresses) <= 100, "bounded address list required")
    addresses = list(dict.fromkeys(pubkey(a) for a in addresses))
    count = min(ACCOUNT_BATCH, (max_response_bytes-512)//(4*((account_bytes+2)//3)+512))
    need(count > 0, "account cannot fit response allowance")
    return [read(prefix+"_"+str(i//count), "getMultipleAccounts", [addresses[i:i+count], settings(floor)],
                 depends=depends, critical=critical) for i in range(0, len(addresses), count)]


def mint_baseline(mint, *, largest=True, metadata=False):
    pubkey(mint)
    rows = [read("mint", "getAccountInfo", [mint, settings()], critical=True),
            read("epoch", "getEpochInfo", [{"commitment": "finalized"}])]
    if largest:
        rows.append(read("largest", "getTokenLargestAccounts", [mint, {"commitment": "finalized"}]))
    if metadata:
        # The Metaplex metadata PDA: absent for many Token-2022 mints, so a null answer is an answer, not a gap.
        from solana_metadata import metadata_address
        rows.append(read("metadata", "getAccountInfo", [metadata_address(mint), settings()]))
    return rows


def holder_scan(mint, token_program=TOKEN_PROGRAM, *, name="holderscan"):
    """Bounded census of one SPL mint's fixed-size token accounts: a discovery lead, never a balance sample.

    Used only when the provider refuses getTokenLargestAccounts. Token-2022 holdings have
    variable sizes, so they keep an explicit gap instead of a partial filter.
    """
    pubkey(mint)
    need(token_program == TOKEN_PROGRAM, "holder scan supports fixed-size SPL token accounts only")
    return read(name, "getProgramAccounts", [token_program, {**settings(), "withContext": True, "dataSlice": dict(SCAN_SLICE),
                 "filters": [{"dataSize": 165}, {"memcmp": {"offset": 0, "bytes": mint}}]}])


def discovery_leads(mint, req, checked, limit=LEAD_LIMIT):
    """Ranked holding leads from either discovery method; amounts are discovery-time observations."""
    pubkey(mint)
    if req["method"] == "getTokenLargestAccounts":
        need(req["params"][0] == mint, "wrong discovery mint")
        rows = [{"address": r["address"], "amount": r["amount"]} for r in checked["result"]["value"]]
    else:
        need(req["method"] == "getProgramAccounts", "unsupported holder discovery method")
        options = req["params"][1]
        need(options.get("dataSlice") == SCAN_SLICE and options["filters"][1]["memcmp"] == {"offset": 0, "bytes": mint}, "scan must target the exact mint prefix")
        rows = []
        for address, item in zip(checked["addresses"], checked["result"]["value"]):
            raw = base64.b64decode(item["account"]["data"][0], validate=True)
            need(len(raw) == SCAN_SLICE["length"], "scan row is not the requested slice")
            rows.append({"address": address, "amount": str(int.from_bytes(raw[64:72], "little"))})
        rows.sort(key=lambda r: (-int(r["amount"]), r["address"]))
    return rows if limit is None else rows[:limit]


def holding_sample(mint, discovery_observation):
    """Discovery rank and later balances remain distinct, with mint supply in each batch."""
    from solana_wire import validate_response
    pubkey(mint)
    req = discovery_observation["request"]
    need(discovery_observation.get("status") == "ok" and req["method"] in ("getTokenLargestAccounts", "getProgramAccounts"), "exact-mint holder discovery required")
    checked = validate_response(req, discovery_observation["response"])
    need(checked["status"] == "ok", "holder discovery unresolved")
    return account_batches([mint]+[r["address"] for r in discovery_leads(mint, req, checked)],
                           prefix="holdings", floor=checked["context_slot"])


def validate_plan(rows):
    need(isinstance(rows, list) and len(rows) <= 40, "read plan exceeds bound")
    names = set()
    for row in rows:
        need(isinstance(row, dict) and set(row) == {"name", "method", "params", "depends", "critical"}, "invalid read plan entry")
        read(row["name"], row["method"], row["params"], depends=row["depends"], critical=row["critical"])
        need(row["name"] not in names, "duplicate plan entry")
        names.add(row["name"])
    done = set()
    while len(done) < len(rows):
        ready = {r["name"] for r in rows if r["name"] not in done and set(r["depends"]) <= done}
        need(ready, "unknown or cyclic plan dependency")
        done.update(ready)
    return rows


def pool_sample(adapter_id, pool, pool_packet, *, related=None, lp_accounts=None):
    """Derive one bounded atomic dependency batch from verified raw pool leads."""
    from adapters import pool_adapter
    from adapters.base import dependencies
    from adapters import raydium_amm_v4
    from solana_programs import observed_account
    module = pool_adapter(adapter_id)
    value, context = observed_account(pool, pool_packet)
    need(not context["sliced"], "full pool discovery required")
    state = module.decode_pool(value)
    addresses = dependencies(pool, state)
    if module is raydium_amm_v4 and state["legacy_orderbook_enabled"] and related and state["market"] in related:
        market, meta = observed_account(state["market"], related[state["market"]])
        need(not meta["sliced"], "full market discovery required")
        addresses.append(module.decode_market(state["market"], market, state["mints"])["event_queue"])
    lp_accounts = lp_accounts or []
    need(isinstance(lp_accounts, list) and len(lp_accounts) <= 6, "initial LP holder sample capped at six")
    addresses = list(dict.fromkeys(addresses+lp_accounts))
    need(len(addresses) <= ACCOUNT_BATCH, "pool dependency sample exceeds one atomic batch")
    return account_batches(addresses, prefix="pool_dependencies", floor=context["context_slot"], critical=True,
                           account_bytes=24000)


def position_sample(adapter_id, pool, pool_packet, position_leads, position_observations):
    """One atomic pool/position/dependency batch per named lead; no global scans."""
    from adapters import pool_adapter
    from solana_programs import observed_account
    module = pool_adapter(adapter_id)
    need(adapter_id in ('raydium_clmm', 'orca_whirlpool', 'meteora_dlmm', 'meteora_damm_v2'), "supported position adapter required")
    need(isinstance(position_leads, list) and len(position_leads) <= 6, "position lead cap exceeded")
    need(len({pubkey(v['position']) for v in position_leads}) == len(position_leads), "duplicate position lead")
    account, meta = observed_account(pool, pool_packet)
    need(not meta['sliced'], "full pool lead required")
    state = module.decode_pool(pool, account)
    plans = [];groups = []  # (addresses, floor) per atomic batch; leads share a batch while their dependency union fits
    for i, lead in enumerate(position_leads):
        address = pubkey(lead['position'])
        need(address in position_observations, "full position lead not captured")
        account, position_meta = observed_account(address, position_observations[address])
        need(not position_meta['sliced'], "full position lead required")
        position = module.decode_position(address, account, pool, lead)
        addresses = [pool, *state['mints'], *state['vaults'], address]
        if adapter_id.startswith('meteora_'):
            from adapters.meteora_common import CLOCK
            addresses.append(CLOCK)
            if adapter_id == 'meteora_dlmm':
                addresses += [module.bin_array_address(pool, t) for t in (position['lower_bin_id'],position['upper_bin_id'])]
            else:
                addresses.append(position['position_mint'])
                vestings=lead.get('vestings',[])
                need(isinstance(vestings,list) and len(vestings)<=6 and len(set(vestings))==len(vestings), 'bounded unique external vestings required')
                addresses += [pubkey(v) for v in vestings]
        else:
            addresses += [state['config'],position['position_mint']]
            addresses += [module.tick_array_address(pool, t, state['tick_spacing']) for t in (position['lower_tick'], position['upper_tick'])]
        if lead.get('holding'): addresses.append(pubkey(lead['holding']))
        if lead.get('bundle'): addresses.append(pubkey(lead['bundle']))
        need(len(set(addresses)) <= ACCOUNT_BATCH, 'position dependencies exceed one atomic batch')
        floor = max(meta['context_slot'], position_meta['context_slot'])
        if groups and len(set(groups[-1][0]+addresses)) <= ACCOUNT_BATCH:
            last = groups[-1];groups[-1] = (list(dict.fromkeys(last[0]+addresses)), max(last[1], floor))
        else:
            groups.append((list(dict.fromkeys(addresses)), floor))
    for g, (addresses, floor) in enumerate(groups):
        plans += account_batches(addresses, prefix='position_'+str(g), floor=floor, critical=True, account_bytes=12000)
    return plans


def historical_sample(signatures):
    """At most two receipt reads. Headers are derived after actual returned slots."""
    from solana_common import signature
    need(isinstance(signatures,list) and len(signatures)<=2 and len(set(signatures))==len(signatures), 'at most two unique historical receipts')
    return [read('receipt_'+str(i),'getTransaction',[signature(sig),{'commitment':'finalized','encoding':'json','maxSupportedTransactionVersion':0}]) for i,sig in enumerate(signatures)]


def historical_headers(packets):
    from solana_wire import validate_response
    need(isinstance(packets,list) and len(packets)<=2,'at most two transaction packets')
    slots=set()
    for packet in packets:
        need(packet['request']['method']=='getTransaction','transaction receipt required')
        if packet.get('status')!='ok':continue
        checked=validate_response(packet['request'],packet['response'])
        if checked['status']=='ok':slots.add(checked['result']['slot'])
    return [read('receipt_header_'+str(slot),'getBlock',[slot,{'commitment':'finalized','transactionDetails':'none','rewards':False}]) for slot in sorted(slots)]


def quote_sample(adapter_id,pool,pool_packet):
    from adapters import pool_adapter
    from adapters.meteora_common import CLOCK
    from solana_programs import observed_account
    need(adapter_id=='raydium_cpmm','local quote dependency preset unsupported for this protocol')
    module=pool_adapter(adapter_id);value,meta=observed_account(pool,pool_packet)
    need(not meta['sliced'],'full pool lead required')
    state=module.decode_pool(value)
    addresses=[pool,state['config'],*state['mints'],*state['vaults'],CLOCK]
    return account_batches(addresses,prefix='quote_state',floor=meta['context_slot'],critical=True,account_bytes=4096)


def pump_sample(adapter_id,target,observations):
    from adapters import pump_curve,pump_swap
    from adapters.pump_common import curve_address,fee_address
    from solana_addresses import associated_token_address
    from solana_programs import observed_account
    from solana_common import target_identity
    target=target_identity(target)
    need(adapter_id in ('pump_curve','pumpswap'),'Pump preset needs specific product')
    if adapter_id=='pumpswap':
        pool=observations['pool'];packet=observations['packets'][pool]
        plan=pool_sample(adapter_id,pool,packet,lp_accounts=observations.get('lp_accounts',[]))
        addresses=plan[0]['params'][0]+[fee_address(pump_swap.PROGRAM),pump_swap.PROGRAM]  # fee tables and program control
        return account_batches(addresses,prefix='pump_swap_dependencies',floor=plan[0]['params'][1].get('minContextSlot'),critical=True)
    pool=curve_address(target['mint']);packets=observations['packets']
    account,meta=observed_account(pool,packets[pool]);state=pump_curve.decode_pool(account)
    need(not meta['sliced'],'full curve lead required')
    mint,mmeta=observed_account(target['mint'],packets[target['mint']]);need(mint and not mmeta['sliced'],'full mint lead required')
    # The curve program account itself is a dependency (program control), like every other adapter's program.
    addresses=[pool,pump_curve.GLOBAL,target['mint'],associated_token_address(pool,target['mint'],mint['owner'])[0],fee_address(pump_curve.PROGRAM),pump_curve.PROGRAM]
    if state['quote_mint']!=pump_curve.WSOL:
        quote=state['quote_mint'];qa,qmeta=observed_account(quote,packets[quote]);need(qa and not qmeta['sliced'],'quote mint lead required')
        addresses += [quote,associated_token_address(pool,quote,qa['owner'])[0]]
    return account_batches(addresses,prefix='pump_curve_dependencies',floor=meta['context_slot'],critical=True)


def creator_history(keys,*,before=None):
    need(isinstance(keys,list) and len(keys)<=2 and len(set(keys))==len(keys),'creator history capped at two unique attributed keys')
    before=before or {}
    from solana_common import signature
    return [read('creator_history_'+str(i),'getSignaturesForAddress',[pubkey(key),{'commitment':'finalized','limit':25,
        **({'before':signature(before[key])} if key in before else {})}]) for i,key in enumerate(keys)]
