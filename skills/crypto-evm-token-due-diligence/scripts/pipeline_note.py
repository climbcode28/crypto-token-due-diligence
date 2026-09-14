#!/usr/bin/env python3
"""The pipeline's own note: factual findings written from facts.json, composed with zero model turns.

Every finding here is a deterministic restatement of pinned evidence the pipeline collected
(numbers, addresses, statuses), cited by alias. It carries no signal and no topic: the
coordinator assigns judgement through the `signals` block of its note. Findings are only
emitted when their evidence exists, and all text is bounded to what the evidence shows.
"""
import argparse
import json
import sys
from pathlib import Path

from backend_common import Invalid, need, read_json
from facts import decimal_string, holder_summary

LANE = "pipeline"


def _pct(value):
    return f"{value:.2f}%" if isinstance(value, (int, float)) else "an unknown share"


def _short(addr):
    return addr[:10] + "…" + addr[-4:] if isinstance(addr, str) and len(addr) >= 14 else str(addr)


def _number(value):
    return f"{value:,}" if type(value) in (int, float) else "unavailable"


def _implementation_text(contract):
    if contract.get("eip1967_implementation"):
        return contract["eip1967_implementation"]
    return "zero" if contract.get("eip1967_implementation_raw") == 0 else "unavailable"


def _owners_text(owner):
    addresses = owner.get("safe_owners") or []
    count = owner.get("safe_owner_count")
    count_text = str(count) if type(count) is int else "at least " + str(len(addresses))
    text = f"getOwners() reports {count_text} owner addresses; getThreshold() value {_number(owner.get('safe_threshold'))}"
    modules = owner.get("safe_modules")
    if "getModulesPaginated" in (owner.get("reverted") or []):
        text += "; getModulesPaginated() reverts"
    elif modules is not None:
        text += f"; getModulesPaginated() lists {len(modules)} module" + ("" if len(modules) == 1 else "s") + (f" ({', '.join(modules)})" if modules else "")
    if owner.get("safe_guard_read"):
        text += "; guard slot " + (owner["safe_guard"] if owner.get("safe_guard") else "zero (no guard)")
    return text


def _getter_value(decoded):
    if not isinstance(decoded, dict):
        return "unavailable"
    for key in ("address", "string", "int", "bool"):
        if key in decoded:
            return str(decoded[key])
    return "empty" if decoded.get("empty") else str(decoded.get("raw", "unavailable"))[:40]


def _finding(fid, dimension, text, evidence, claim="state_observation", subject=None, execution=None, dimensions=None):
    item = {"id": fid, "dimension": dimension, "claim": claim, "strength": "strongly_supported", "confidence": "high", "impact": "neutral",
            "text": text[:1900], "evidence": list(dict.fromkeys(e for e in evidence if e))}
    if dimensions:
        item.pop("dimension")
        item["dimensions"] = dimensions
    if subject:
        item["subject"] = subject
    if execution is not None:
        item["execution"] = execution
    return item


def receipts_from_draft(run, draft, facts):
    """Receipts collected after start (presets) become pipeline facts too: creation role by hash, sales decoded like the pipeline does."""
    from sale_decode import decode_sale
    import presets
    from facts import transfers as decode_transfers
    known = {r["tx"] for r in facts.get("receipts") or []}
    pools = {p["pair"] for p in facts.get("pools") or [] if not p.get("is_pool_id")}
    if any(p.get("is_pool_id") or p.get("version") == "v4" for p in facts.get("pools") or []):
        manager = (presets.registry(facts["target"]["chain_id"]).get("uniswap_v4") or {}).get("pool_manager")
        if manager:
            pools.add(manager)
    decimals = (facts.get("metadata") or {}).get("decimals")
    out = []
    for e in draft.get("evidence", []):
        if e.get("kind") != "rpc" or e.get("query", {}).get("method") != "eth_getTransactionReceipt" or e.get("observation_status", "ok") != "ok":
            continue
        tx = str(e.get("tx_hash") or "").lower()
        if not tx or tx in known:
            continue
        try:
            receipt = read_json(Path(run) / "draft" / e["artifact"])["response"]["result"]
        except (OSError, ValueError, KeyError, TypeError):
            continue
        if not isinstance(receipt, dict):
            continue
        item = {"tx": tx, "status": int(receipt.get("status", "0x0"), 16), "block": int(receipt["blockNumber"], 16),
                "from": (receipt.get("from") or "").lower() or None, "to": (receipt.get("to") or "").lower() or None,
                "logs": len(receipt.get("logs", [])), "transfers": decode_transfers(receipt)[:20], "evidence": e["id"],
                "role": "creation" if tx == (facts.get("creation") or {}).get("tx") else "sale_candidate"}
        if item["role"] == "sale_candidate":
            item["sale"] = decode_sale(facts["target"]["address"], receipt, item, pools, decimals, pool_details=facts.get("pools"))
        known.add(tx)
        out.append(item)
    return out


def _int24(word):
    """A tick returned as a 256-bit word is a signed int24: values at or above 2**255 are negative."""
    return word - 2 ** 256 if word >= 2 ** 255 else word


def positions_from_draft(run, draft, facts):
    """Positions read after start (the positions preset) join the pipeline's own: owner from ownerOf, operator from getApproved,
    liquidity, pair and ticks from positions(), matched to a read pool by token pair and fee; when that pool's tick and liquidity
    were read at the pin the in-range flag and share of active liquidity follow start's own arithmetic, otherwise they stay
    unknown."""
    import re
    known = {p.get("id") for p in facts.get("positions") or []}
    rows = {}
    for e in draft.get("evidence", []):
        # Imported rows carry a collection prefix on their id; the preset's alias survives in the provenance.
        alias = (e.get("collection_provenance") or {}).get("evidence_id") or str(e.get("id") or "")
        m = re.fullmatch(r"(?:positions|pos)-(\d+)-(ownerOf|positions|getApproved)", alias)
        if not m or e.get("kind") != "rpc" or e.get("observation_status", "ok") != "ok":
            continue
        pid = int(m.group(1))
        if pid in known:
            continue
        try:
            result = read_json(Path(run) / "draft" / e["artifact"])["response"]["result"]
        except (OSError, ValueError, KeyError, TypeError):
            continue
        if not isinstance(result, str) or not re.fullmatch(r"0x[0-9a-fA-F]*", result):
            continue
        row = rows.setdefault(pid, {"id": pid, "owner": None, "approved": None, "liquidity": None, "pool": None, "in_range": None, "pct_of_pool_active_liquidity": None, "source": "preset", "evidence": {}})
        words = [int(result[2 + 64 * i:66 + 64 * i], 16) for i in range((len(result) - 2) // 64)]
        if m.group(2) == "ownerOf" and words:
            row["owner"] = "0x" + format(words[0], "040x") if 0 < words[0] < 2 ** 160 else None
            row["evidence"]["owner"] = alias
        elif m.group(2) == "getApproved" and words:
            row["approved"] = "0x" + format(words[0], "040x") if 0 < words[0] < 2 ** 160 else None
            row["approved_raw"] = words[0]
            row["evidence"]["approved"] = alias
        elif m.group(2) == "positions" and len(words) >= 8:
            token0, token1, fee, liquidity = "0x" + format(words[2], "040x"), "0x" + format(words[3], "040x"), words[4], words[7]
            lower, upper = _int24(words[5]), _int24(words[6])
            row.update(liquidity=liquidity, token0=token0, token1=token1, fee=fee, tickLower=lower, tickUpper=upper)
            row["evidence"]["positions"] = alias
            pool = next((p for p in facts.get("pools") or [] if {p.get("token0"), p.get("token1")} == {token0, token1} and p.get("fee") == fee), None)
            row["pool"] = pool["pair"] if pool else None
            tick = ((pool or {}).get("slot0") or {}).get("tick")
            if pool and isinstance(tick, int) and pool.get("liquidity"):
                row["in_range"] = lower <= tick < upper
                row["pct_of_pool_active_liquidity"] = round(liquidity / pool["liquidity"] * 100, 4) if row["in_range"] else 0.0
    return [rows[pid] for pid in sorted(rows) if rows[pid]["owner"] or rows[pid]["liquidity"] is not None]


def build_pipeline_note(facts, draft, run=None):
    if run is not None:
        later = positions_from_draft(run, draft, facts)
        if later:
            from broad_collect import goplus_facts
            facts = {**facts, "positions": list(facts.get("positions") or []) + later}
            if (facts.get("goplus") or {}).get("status") == "ok":
                facts["goplus"] = goplus_facts(facts["goplus"], facts["positions"], facts.get("top_holders"), facts.get("balances"), facts.get("pools"))
    from scaffold import scope_entries
    target = facts["target"]
    pin = facts.get("pin") or {}
    metadata = facts.get("metadata") or {}
    decimals = metadata.get("decimals")
    supply = metadata.get("total_supply")
    symbol = metadata.get("symbol") or "the token"
    controls = facts.get("controls") or {}
    source = facts.get("source") or {}
    findings = []
    scope = scope_entries(facts, draft)
    scope_ids = {s["address"]: s["id"] for s in scope}
    scope_ids.update({s["address"]: s["id"] for s in draft.get("scope", [])})

    # ---- token controls ---------------------------------------------------------------
    getters = controls.get("getters") or {}
    evidence = ["runtime", *((source.get("evidence") or []) if source.get("status") in ("matched", "mismatch") else []),
                *("token-eip1967-" + k for k in (controls.get("eip1967") or {}))]
    slots = controls.get("eip1967") or {}
    parts = []
    if source.get("status") == "matched":
        parts.append(f"The deployed runtime matches the published source ({source.get('contract') or 'verified contract'}, compiler {source.get('compiler') or 'unknown'}).")
    elif source.get("status") == "mismatch":
        parts.append("The deployed runtime does NOT match the published source.")
    else:
        parts.append(f"Published source status: {source.get('status') or 'not attempted'}; the runtime was read and hashed at the pin.")
    if slots:
        zero = [k for k, v in slots.items() if v is None]
        parts.append(f"EIP-1967 slots {', '.join(sorted(slots))}: {'all zero' if len(zero) == len(slots) else 'set: ' + ', '.join(k + '=' + str(v) for k, v in slots.items() if v)}.")
    if "owner" in getters:
        parts.append(f"owner() returns {controls.get('owner')}.")
        evidence.append("token-owner")
    elif "owner" in (controls.get("reverted_getters") or []):
        parts.append("owner() reverts at the pin; owner authority is not established by this probe.")
    if "paused" in getters:
        parts.append(f"paused() is {controls.get('paused')}.")
        evidence.append("token-paused")
    if supply is not None and decimals is not None:
        parts.append(f"totalSupply is {decimal_string(supply, decimals)} {symbol}.")
        evidence.append("metadata-total_supply")
    interesting = [name for name in getters if any(k in name.lower() for k in ("restriction", "launchblock", "maxtx", "tax", "fee", "limit", "blacklist", "whitelist"))][:6]
    for name in interesting:
        decoded = getters[name].get("decoded") or {}
        value = decoded.get("address") or decoded.get("int") if decoded else None
        if value is not None:
            parts.append(f"{name}() = {value}" + (" (raw decoded integer)." if isinstance(value, int) else "."))
            evidence.append(getters[name].get("evidence") or ("token-" + name))
    if controls.get("code_bytes"):
        parts.append(f"Runtime is {controls['code_bytes']} bytes; clone status {((controls.get('clone') or {}).get('status'))}.")
    g = facts.get("goplus") or {}
    if g.get("status") == "ok":
        flags = g.get("flags") or {}
        named = ", ".join(f"{k}={'yes' if v else 'no'}" for k, v in flags.items() if k in ("is_honeypot", "is_mintable", "is_proxy", "is_open_source", "transfer_pausable", "is_blacklisted", "hidden_owner") and v is not None)
        parts.append(f"GoPlus corroboration (third-party claims, not a source match): {named or 'no control flags returned'}; buy tax {g.get('buy_tax') or 'n/a'}, sell tax {g.get('sell_tax') or 'n/a'}.")
        evidence.append(g.get("evidence"))
    findings.append(_finding("pipeline-token-controls", "token_controls", " ".join(parts), evidence, claim="source_analysis" if source.get("status") == "matched" else "state_observation"))

    # ---- launch execution ---------------------------------------------------------------
    creation = facts.get("creation") or {}
    receipts = list(facts.get("receipts") or []) + (receipts_from_draft(run, draft, facts) if run else [])
    launch = next((r for r in receipts if r.get("role") == "creation"), None)
    if launch:
        pool_addrs = {p["pair"] for p in facts.get("pools") or [] if not p.get("is_pool_id")}
        mints = [t for t in launch.get("transfers", []) if t["asset"] == target["address"] and int(t["from"], 16) == 0]
        seeds = [t for t in launch.get("transfers", []) if t["asset"] == target["address"] and t["to"] in pool_addrs]
        buys = [t for t in launch.get("transfers", []) if t["asset"] == target["address"] and t["from"] in pool_addrs]
        text = (f"Creation transaction {launch['tx']} {'succeeded' if launch['status'] == 1 else 'reverted'} at block {launch['block']:,} (status {launch['status']}), sent by {launch.get('from')} to {launch.get('to')}; "
                f"{launch.get('logs')} logs.")
        if mints and supply:
            minted = sum(t["amount_raw"] for t in mints)
            text += f" Minted {decimal_string(minted, decimals)} {symbol} ({_pct(minted / supply * 100)} of supply) to {', '.join(_short(t['to']) for t in mints[:3])}."
        if seeds and supply:
            seeded = sum(t["amount_raw"] for t in seeds)
            text += f" {decimal_string(seeded, decimals)} {symbol} ({_pct(seeded / supply * 100)}) was placed into pool {_short(seeds[0]['to'])} in the same transaction."
        if buys and supply:
            bought = sum(t["amount_raw"] for t in buys)
            text += f" {decimal_string(bought, decimals)} {symbol} ({_pct(bought / supply * 100)}) left the pool to {', '.join(_short(t['to']) for t in buys[:2])} within the launch transaction."
        if launch.get("nfpm_position_ids"):
            text += f" Liquidity position NFT(s) {', '.join(str(i) for i in launch['nfpm_position_ids'])} were minted."
        evidence = [launch["evidence"], launch["evidence"].replace("receipt-", "tx-", 1), "runtime"]
        if creation.get("tx_source") == "sourcify_deployment":
            text += " The creation transaction was named by Sourcify's deployment record because the explorer named none" + ("; the explorer's creator field is unknown." if not creation.get("creator") else ".")
            if "sourcify-correspondence" in ((facts.get("source") or {}).get("evidence") or []):
                evidence.append("sourcify-correspondence")
        if creation.get("deployment_tx_conflict"):
            text += f" Sourcify's deployment record names a different transaction ({creation['deployment_tx_conflict']}); the two sources disagree and the conflict is unresolved."
        for a in facts.get("architecture") or []:
            if a["address"] in (launch.get("to"), creation.get("creator")):
                evidence.append((a.get("evidence") or {}).get("runtime"))
        actors = facts.get("actors") or {}
        if "creator" in actors:
            evidence.append(actors["creator"].get("evidence"))
        findings.append(_finding("pipeline-launch-execution", "historical_launch_integrity", text, evidence, claim="historical_execution",
                                 execution={"result": "success" if launch["status"] == 1 else "reverted"}))

    # ---- launch position custody ----------------------------------------------------------
    # Positions that hold liquidity in the canonical pool are described first (start's own reads before a later preset's, larger
    # first), then positions in other read pools; a position with no liquidity and no read pool is closed or emptied and is
    # counted, never described as custody, so the finding is always anchored on a pool or custodian that was read at the pin.
    # A pool id (v4 state view) is no address and has no runtime read, so it can never anchor the finding.
    canonical_pool = next((p for p in facts.get("pools") or [] if p.get("read") == "v3" and p.get("target_in_pool")), None) \
        or next((p for p in facts.get("pools") or [] if not p.get("is_pool_id")), None)
    canonical_pair = (canonical_pool or {}).get("pair")
    all_positions = facts.get("positions") or []
    live = [p for p in all_positions if p.get("pool") or (p.get("liquidity") or 0) > 0]
    closed = [p for p in all_positions if not p.get("pool") and p.get("liquidity") == 0]
    unread = [p for p in all_positions if not p.get("pool") and p.get("liquidity") is None]
    positions = sorted(live, key=lambda p: (0 if canonical_pair and p.get("pool") == canonical_pair else 1 if p.get("pool") else 2,
                                            1 if p.get("source") == "preset" else 0, -(p.get("liquidity") or 0), p.get("id") or 0))
    # With no live position the closed or unread ones are described (start's own first): an emptied launch position and its
    # custodian are the finding, not a silence.
    described = positions[:3] if positions else sorted(closed + unread, key=lambda p: (1 if p.get("source") == "preset" else 0, p.get("id") or 0))[:3]
    owners = facts.get("owners") or {}
    if described:
        parts, evidence = [], []
        actors = facts.get("actors") or {}
        for pos in described:
            owner = pos.get("owner")
            owner_code = next((a.get("code_bytes") for a in actors.values() if a.get("address") == owner), None)
            kind = "a code-bearing address" if owner_code else "a no-code address" if owner_code == 0 else "an address of unread code"
            share = pos.get("pct_of_pool_active_liquidity")
            approved = pos.get("approved") or ("none" if pos.get("approved_raw") == 0 else "unavailable")
            standing = ("holds no liquidity (closed or emptied)" if pos.get("liquidity") == 0 and not pos.get("pool")
                        else "its positions() read did not answer (unread, not absent)" if pos.get("liquidity") is None and not pos.get("pool")
                        else f"{_pct(share)} of the pool's active liquidity at the pin")
            parts.append(f"Position {pos['id']} is owned by {owner or 'an unread owner address'} ({kind}), approved operator {approved}, "
                         f"{'in range' if pos.get('in_range') else 'out of range' if pos.get('in_range') is False else 'range unknown'}, "
                         f"{standing}.")
            ev = pos.get("evidence") or {}
            evidence += [ev.get("owner"), ev.get("positions"), ev.get("approved")]
            if pos.get("pool"):
                pool = next((p for p in facts.get("pools") or [] if p.get("pair") == pos["pool"]), None)
                if pool:
                    evidence.append((pool.get("evidence") or {}).get("liquidity"))
            owner_actor = next((a for a in actors.values() if a.get("address") == owner), None)
            if owner_actor:
                evidence.append(owner_actor.get("evidence"))
                answered = owner_actor.get("getters") or {}
                reverted = owner_actor.get("reverted") or []
                if answered:
                    parts.append("Custodian getters answered: " + ", ".join(f"{k}() = {_getter_value(v.get('decoded'))}" for k, v in answered.items())
                                 + (f"; reverted: {', '.join(reverted)}" if reverted else "") + ".")
                    evidence += [v.get("evidence") for v in answered.values()]
                elif reverted:
                    parts.append(f"Every probed custodian getter reverted ({', '.join(reverted)}); withdrawal terms are not exposed under those names.")
                elif owner_actor.get("role") == "position_custodian" and owner_actor.get("getters_read") is False:
                    parts.append("The custodian's withdrawal getters were not read (the collection did not run); their terms are unread, not absent.")
        rest_closed = [p for p in closed if p not in described]
        rest_unread = [p for p in unread if p not in described]
        if rest_closed:
            parts.append(f"{len(rest_closed)} further position(s) read ({', '.join(str(p.get('id')) for p in rest_closed[:6])}{'…' if len(rest_closed) > 6 else ''}) hold no liquidity and match no read pool: closed or emptied, not custody.")
            evidence += [(p.get("evidence") or {}).get("positions") for p in rest_closed[:6]]
        if rest_unread:
            parts.append(f"{len(rest_unread)} listed position(s) ({', '.join(str(p.get('id')) for p in rest_unread[:6])}{'…' if len(rest_unread) > 6 else ''}) were not read: their positions() call did not answer, so they are unread, not absent.")
            evidence += [(p.get("evidence") or {}).get("owner") for p in rest_unread[:6]]
        for name, o in owners.items():
            if o.get("safe_owners"):
                parts.append(f"{name} is owned by {o['address']}; {_owners_text(o)}.")
                ev = o.get("evidence") or {}
                evidence += [e for e in (ev.get("getOwners"), ev.get("getThreshold"), ev.get("getModulesPaginated"), ev.get("guard")) if e]
        g = facts.get("goplus") or {}
        if g.get("status") == "ok" and g.get("lp_holders"):
            listed = "; ".join(f"{_short(r['address'])} {_pct(r.get('share_pct'))} of LP value" + (", locked" if r.get("is_locked") else ", not flagged locked") + (", contract" if r.get("is_contract") else "")
                               + (f", verified as position {', '.join(str(v['id']) for v in r['verified_positions'])}" if r.get("verified_positions") else "") for r in g["lp_holders"][:6])
            parts.append(f"GoPlus counts {g.get('lp_holder_count') or 'an unknown number of'} LP holders and lists {len(g['lp_holders'])} (third-party claim; {g.get('lp_holders_verified')} verified against positions the pipeline read): {listed}."
                         + (f" Unread listed position ids: {', '.join(str(i) for i in g['unread_lp_nft_ids'])}." if g.get("unread_lp_nft_ids") else ""))
            evidence.append(g.get("evidence"))
        first_owner = described[0].get("owner")
        owner_actor = next((a for a in actors.values() if a.get("address") == first_owner), None)
        subject = first_owner if owner_actor else (described[0].get("pool") or canonical_pair)
        if subject and subject != first_owner:
            pool = next((p for p in facts.get("pools") or [] if p.get("pair") == subject), None)
            evidence.append((pool or {}).get("evidence", {}).get("runtime") or ((pool or {}).get("prefix", "pool1") + "-runtime"))
        # Without a custodian actor or an address-bearing pool read at the pin there is nothing the validator can bind the finding to.
        if subject:
            findings.append(_finding("pipeline-launch-position-custody", "canonical_lp_principal_custody", " ".join(parts), evidence, subject=subject))

    # ---- pool depth and quotes -------------------------------------------------------------
    pools = facts.get("pools") or []
    quotes = facts.get("quotes") or []
    main = pools[0] if pools else None
    if main and (quotes or main.get("counter_balance") is not None):
        parts, evidence = [], []
        if main.get("target_balance") is not None:
            parts.append(f"Pool {main.get('prefix')} ({main.get('dex')} {main.get('version')}, counter {main.get('counter_symbol')}) holds {main['target_balance']} {symbol} "
                         f"({_pct(main.get('target_balance_pct_supply'))} of supply)" + (f" and {main['counter_balance']} {main.get('counter_symbol')}" if main.get("counter_balance") is not None else "") + " at the pin.")
            evidence += [(main.get("evidence") or {}).get("target_balance"), (main.get("evidence") or {}).get("counter_balance"), (main.get("evidence") or {}).get("liquidity")]
        good = [q for q in quotes if q.get("amount_out") is not None]
        if good:
            parts.append("Read-only QuoterV2 quotes: " + "; ".join(f"{q['size_tokens']:,} {symbol} -> {q['amount_out']} ({_pct(q.get('impact_vs_smallest_pct')) if q.get('impact_vs_smallest_pct') is not None else 'baseline'} vs smallest)" for q in good) + ".")
            evidence += [q.get("evidence") for q in good]
        if main.get("liquidity_usd") is not None:
            parts.append(f"Indexer-reported liquidity USD {main['liquidity_usd']:,} (document evidence, not an RPC read).")
            evidence.append("doc-dexscreener-pairs")
        evidence.append((main.get("evidence") or {}).get("runtime") or (str(main.get("prefix")) + "-runtime"))
        findings.append(_finding("pipeline-pool-depth", "sellability_exit_depth", " ".join(parts), evidence, subject=main.get("pair") if not main.get("is_pool_id") else None))

    # ---- verified sale --------------------------------------------------------------------
    sale_receipts = [r for r in receipts if r.get("role") == "sale_candidate" and (r.get("sale") or {}).get("verified")][:2]
    import presets as _presets
    v4_manager = ((_presets.registry(target["chain_id"]).get("uniswap_v4") or {}).get("pool_manager") or "").lower()
    for n, receipt in enumerate(sale_receipts, 1):
        sale = receipt["sale"]
        got = ", ".join(f"{r['amount_raw']} raw units of {_short(r['asset'])}" for r in sale.get("received", []))
        received = f"the transfer source received {got}" if got else "no matching direct counter-asset transfer from the pool to the transfer source was established (proceeds may be native or routed)"
        amount = sale.get("amount") if sale.get("amount") is not None else f"{sale.get('amount_raw')} raw units of"
        destination = "the Uniswap v4 PoolManager" if sale["pool"] == v4_manager else f"pool {_short(sale['pool'])}"
        text = (f"Sale receipt {receipt['tx']} at block {receipt['block']:,}: {sale['seller']} moved {amount} {symbol} into {destination} "
                f"with {sale.get('swap_logs')} Swap event(s); {received}. The receipt status is success and the seller "
                f"{'is' if sale.get('seller_is_sender') else 'is not'} the transaction sender.")
        if sale.get("pool_id"):
            text += f" The Swap pool ID {sale['pool_id']} is associated with the target through captured indexer currency data; that currency association is not independently proven by the receipt."
        evidence = [receipt["evidence"], receipt["evidence"].replace("receipt-", "tx-", 1), "runtime"]
        actors = facts.get("actors") or {}
        seller_actor = next((a for a in actors.values() if a.get("address") == sale["seller"]), None)
        if seller_actor:
            evidence.append(seller_actor.get("evidence"))
        pool = next((p for p in pools if p.get("pair") == sale["pool"]), None)
        if pool:
            evidence.append((pool.get("evidence") or {}).get("runtime") or (pool.get("prefix") + "-runtime"))
            evidence.extend((pool.get("evidence") or {}).get(k) for k in ("token0", "token1"))
        if sale.get("pool_id"):
            evidence.append("doc-dexscreener-pairs")
        findings.append(_finding(f"pipeline-verified-sale-{n}", "sellability_exit_depth", text, evidence, claim="historical_execution",
                                 execution={"result": "success"}))

    # ---- holder distribution --------------------------------------------------------------
    balances = facts.get("balances") or {}
    top = facts.get("top_holders") or []
    if balances or top:
        parts, evidence = [], []
        dead = balances.get("dead")
        if dead and dead.get("pct_supply") is not None:
            parts.append(f"The dead address holds {dead['decimal']} {symbol} ({_pct(dead['pct_supply'])}).")
            evidence.append(dead.get("evidence"))
        pool_pct = [b for k, b in balances.items() if k.startswith("pool") and b.get("pct_supply") is not None]
        if pool_pct:
            parts.append(f"{len(pool_pct)} readable pools hold {_pct(sum(b['pct_supply'] for b in pool_pct))} between them.")
            evidence += [b.get("evidence") for b in pool_pct]
        if top:
            aggregate = holder_summary(top, supply)
            share = aggregate['pct_supply']
            parts.append(f"The selected indexed-holder sample has {aggregate['read_count']}/{aggregate['selected_count']} readable unique balances, "
                         + (f"totaling {share}% of total supply" if share is not None else "with aggregate share unavailable")
                         + f" ({aggregate['missing_count']} missing balance reads). The sum uses atomic RPC balances, not rounded percentages.")
            if aggregate['largest']:
                largest = aggregate['largest']
                parts.append(f"Largest sampled balance: {largest['address']} "
                             + (f"holds {largest['pct_supply']}%." if largest['pct_supply'] is not None else "has an unknown supply share."))
            counts = aggregate['account_counts']
            parts.append(f"Runtime classes: {counts['no_code']} no-code, {counts['delegated_account']} delegated accounts, "
                         f"{counts['code_bearing']} other code-bearing, {counts['unknown']} unknown. "
                         "Code presence does not prove protocol custody or common beneficial ownership.")
            parts.append("Selection excludes target, dead and separately requested balances; it is not a global top-ten or circulating-float measure.")
            labeled = [h for h in top if h.get('indexer_name')]
            if labeled:
                parts.append("Indexer labels (not ownership proof): " + "; ".join(
                    f"{_short(h['address'])} {h['indexer_name']} ({holder_summary([h], supply)['pct_supply']}% of supply)"
                    for h in labeled[:4]) + ".")
            if type(supply) is int and supply > 0:
                evidence.append("metadata-total_supply")
            for h in top:
                evidence += [(h.get("evidence") or {}).get("balance"), (h.get("evidence") or {}).get("runtime")]
        counters = (facts.get("indexed") or {}).get("counters") or {}
        if counters.get("holders_count"):
            parts.append(f"The explorer indexes {counters['holders_count']:,} holders; transfer count {_number(counters.get('transfers_count'))} (document evidence).")
            evidence.append("doc-explorer-counters")
        g = facts.get("goplus") or {}
        if g.get("status") == "ok" and g.get("holders"):
            top_listed = g["holders"][0]
            parts.append(f"GoPlus lists {g.get('holder_count') or 'an unknown number of'} holders (third-party claim); its top listed holder {_short(top_listed['address'])} at {_pct(top_listed.get('share_pct'))}"
                         + (", flagged contract" if top_listed.get("is_contract") else "") + f"; {g.get('holders_verified')} of {len(g['holders'])} listed holders sit in the pipeline's balance sample.")
            evidence.append(g.get("evidence"))
        evidence.append("runtime")
        findings.append(_finding("pipeline-holder-distribution", "current_concentration", " ".join(parts), evidence))

    # ---- side pools -------------------------------------------------------------------------
    side = [p for p in pools[1:] if p.get("target_balance") is not None or p.get("liquidity") is not None]
    if side:
        text = f"{len(side)} further indexed pools were read at the pin: " + "; ".join(
            f"{p.get('prefix')} {p.get('dex')} {p.get('version')} vs {p.get('counter_symbol')} " + (
                f"has active liquidity {p.get('liquidity')} (v4: reserves sit in the pool manager, not readable per pool)" if p.get("is_pool_id") or p.get("version") == "v4"
                else f"holds {p.get('target_balance') or 'unread'} {symbol}")
            + (f" and {p['counter_balance']} {p.get('counter_symbol')}" if p.get("counter_balance") is not None else "")
            + (f" (indexed USD {p['liquidity_usd']:,})" if p.get("liquidity_usd") is not None else "") for p in side[:5]) + ". Position custody of these pools was not read by the pipeline."
        evidence = ["runtime"]
        for p in side[:5]:
            ev = p.get("evidence") or {}
            evidence += [ev.get("target_balance"), ev.get("liquidity"), ev.get("counter_balance")]
        findings.append(_finding("pipeline-side-pools", "side_pool_removal_risk", text, evidence))

    # ---- admin authority --------------------------------------------------------------------
    arch = [a for a in facts.get("architecture") or [] if a.get("code_bytes") and not a["label"].startswith("quote-")]
    if arch or owners:
        parts, evidence = [], ["runtime"]
        for a in arch[:8]:
            ev = a.get("evidence") or {}
            owner_note = "owner() reverts" if "owner" in (a.get("reverted") or []) else f"owner() = {a.get('owner')}" if a.get("owner") else "owner() address unavailable"
            parts.append(f"{a['label']} {a['address']} ({a['code_bytes']} bytes): {owner_note}; EIP-1967 implementation {_implementation_text(a)}.")
            evidence += [ev.get("runtime"), ev.get("implementation_slot")] + ([ev.get("owner")] if a.get("owner") else [])
        for name, o in owners.items():
            ev = o.get("evidence") or {}
            if o.get("safe_owners"):
                parts.append(f"The owner of {name}, {o['address']}: {_owners_text(o)}; sampled addresses: {', '.join(o['safe_owners'])}.")
                evidence += [e for e in (ev.get("runtime"), ev.get("getOwners"), ev.get("getThreshold"), ev.get("getModulesPaginated"), ev.get("guard")) if e]
            else:
                parts.append(f"The owner of {name}, {o['address']}, has {o.get('code_bytes')} bytes of code" + ("; getOwners() reverts, so the signer set is not established." if "getOwners" in (o.get("reverted") or []) else "."))
                evidence.append(ev.get("runtime"))
        findings.append(_finding("pipeline-admin-authority", "admin_treasury_reward_custody", " ".join(parts), evidence))

    # ---- external dependencies ---------------------------------------------------------------
    quote_assets = [a for a in facts.get("architecture") or [] if a["label"].startswith("quote-") and a.get("code_bytes")]
    if quote_assets:
        parts, evidence = [], ["runtime"]
        for a in quote_assets:
            ev = a.get("evidence") or {}
            parts.append(f"Quote asset {a.get('symbol') or a['label']} {a['address']}: {a['code_bytes']} bytes, EIP-1967 implementation {_implementation_text(a)}, "
                         + ("owner() reverts" if "owner" in (a.get("reverted") or []) else f"owner() = {a.get('owner')}" if a.get("owner") else "owner() address unavailable") + ".")
            evidence += [ev.get("runtime"), ev.get("implementation_slot")] + ([ev.get("owner")] if a.get("owner") else [])
        findings.append(_finding("pipeline-dependencies", "external_dependencies", " ".join(parts), evidence))

    # ---- maturity context ---------------------------------------------------------------------
    maturity = facts.get("maturity") or {}
    if maturity.get("age_days") is not None or maturity.get("holders_count"):
        parts, evidence = [], ["runtime"]
        if maturity.get("age_days") is not None:
            parts.append(f"The token was created at block {maturity.get('launch_block'):,} ({maturity.get('launch_time_utc')}), {maturity['age_days']} days before the pin.")
            if launch:
                evidence.append(launch["evidence"])
        if maturity.get("holders_count"):
            parts.append(f"The explorer indexes {maturity['holders_count']:,} holders; transfer count {_number(maturity.get('transfers_count'))}.")
            evidence.append("doc-explorer-counters")
        if maturity.get("indexed_pools"):
            txns = maturity.get("indexed_txns_h24") or {}
            parts.append(f"Dexscreener indexes {maturity['indexed_pools']} pools; aggregate liquidity USD {_number(maturity.get('indexed_liquidity_usd'))}, 24h volume USD {_number(maturity.get('indexed_volume_h24_usd'))} "
                         f"({_number(txns.get('buys'))} buys / {_number(txns.get('sells'))} sells)" + (f", market cap USD {maturity['indexed_market_cap_usd']:,}" if maturity.get("indexed_market_cap_usd") else "") + ".")
            evidence.append("doc-dexscreener-pairs")
        if main and main.get("counter_balance") is not None:
            evidence.append((main.get("evidence") or {}).get("counter_balance"))
        parts.append("Indexer figures are document evidence; age is anchored to the captured creation block.")
        findings.append(_finding("pipeline-maturity-context", "development_disclosure", " ".join(parts), evidence))

    # ---- creator activity (document evidence; inference) -------------------------------------
    activity = facts.get("creator_activity") or {}
    if activity.get("status") in ("ok", "partial") and creation.get("signer"):
        text = (f"Explorer view of the launch signer {creation['signer']}: {activity.get('transactions_captured', 0)} transactions captured"
                f"{' (more pages exist)' if activity.get('transactions_more') else ''}, {activity.get('calls_to_launch_factory', 0)} of them to the launch factory, "
                f"{activity.get('contracts_created', 0)} contract creations; {activity.get('token_transfers_captured', 0)} token transfers captured"
                f"{' (more pages exist)' if activity.get('token_transfers_more') else ''}: {activity.get('target_outbound', 0)} outbound and {activity.get('target_inbound', 0)} inbound {symbol} transfers, "
                f"{activity.get('other_tokens_touched', 0)} other tokens touched. Indexer data, not RPC-verified; specific hashes need receipt reads.")
        item = _finding("pipeline-creator-activity", "historical_launch_integrity", text, ["runtime", "doc-explorer-signer-transactions", "doc-explorer-signer-token-transfers"], claim="inference")
        item.update(strength="inference", confidence="medium")
        findings.append(item)

    # Only cite aliases the draft can resolve and that succeeded; drop unresolved aliases rather than fail the whole note.
    aliases, failed = set(), set()
    for e in draft.get("evidence", []):
        parts = e["id"].split("-")
        names = {e["id"]} | ({"-".join(parts[2:])} if parts[0] == "c" and len(parts) > 2 else set())
        aliases |= names
        if e.get("observation_status", "ok") != "ok":
            failed |= names
    for f in findings:
        f["evidence"] = [a for a in f["evidence"] if (a in aliases or a.startswith("doc-")) and a not in failed]
    findings = [f for f in findings if f["evidence"]]
    return {"note_schema_version": 1, "lane": LANE, "requests_used": 0, "scope": scope, "findings": findings}


def write_and_compose(run):
    """Write notes/pipeline.json from facts.json and compose it into the draft; returns a compact result."""
    from bundle_assemble import read_draft
    from compose import compose
    run = Path(run)
    facts = read_json(run / "facts.json")
    draft = read_draft(run / "draft")
    import re
    note = build_pipeline_note(facts, draft, run)
    path = run / "notes" / "pipeline.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    dropped = []
    for _ in range(4):
        path.write_text(json.dumps(note, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        result = compose(run / "draft", path, lane=LANE, final=False)
        if not result.get("errors"):
            break
        # Compose is atomic: one failing finding rejects the note. Drop the failing ones and keep the rest.
        failing = {m.group(1) for e in result["errors"] for m in [re.match(r"finding ([A-Za-z0-9_-]+)", e)] if m}
        if not failing or not any(f["id"] in failing for f in note["findings"]):
            break
        dropped += sorted(failing)
        note["findings"] = [f for f in note["findings"] if f["id"] not in failing]
    return {"note": str(path), "findings": [f["id"] for f in note["findings"]], "dropped": dropped, "errors": result.get("errors", []),
            "warnings": [w for w in result.get("warnings", []) if "downgraded" in w or "derived" in w][:6]}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("run", type=Path)
    args = p.parse_args()
    try:
        print(json.dumps(write_and_compose(args.run), sort_keys=True, indent=1))
        return 0
    except (Invalid, ValueError, OSError, KeyError) as exc:
        print("Pipeline note failed: " + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
