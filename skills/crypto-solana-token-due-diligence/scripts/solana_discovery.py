"""Offline, exact-mint discovery from retained public captures. No ticker lookup."""
from decimal import Decimal, InvalidOperation
import json
from pathlib import Path
import re

from urllib.parse import urlsplit

from solana_common import need, pubkey, target_identity, sha, signature
from solana_transport import unique_object, invalid_constant
from solana_web_capture import clean_url

ASSETS = Path(__file__).resolve().parents[1]/"assets"
MAINNET = "5eykt4UsFv8P8NJdTREpY1vzqKqZKvdpKuc147dw2N9d"


def registry(name):
    need(name in ("network", "protocol"), "unknown registry")
    return json.loads((ASSETS/(name+"-registry.json")).read_text())


def source_plan(target, *, surface="pools", program=None):
    target = target_identity(target)
    if surface == "pools":
        need(target["genesis_hash"] == MAINNET, "public market index supports mainnet only")
        mint = target["mint"]
        return {"primary": "https://api.dexscreener.com/token-pairs/v1/solana/"+mint,
                "alternate": "https://api.geckoterminal.com/api/v2/networks/solana/tokens/"+mint+"/pools?page=1"}
    if surface == "token_info":
        need(target["genesis_hash"] == MAINNET, "public token index supports mainnet only")
        return {"primary": "https://api.geckoterminal.com/api/v2/networks/solana/tokens/"+target["mint"]+"/info"}
    need(surface in ("program_metadata", "source_verification"), "unsupported discovery surface")
    pubkey(program)
    need(target["genesis_hash"] == MAINNET, "program metadata route requires explicit mainnet target")
    if surface == "program_metadata":
        return {"primary": "https://idl-one.vercel.app/api/idl?programId="+program+"&cluster=mainnet-beta",
                "alternate": "https://explorer.solana.com/address/"+program}
    return {"primary": "https://verify.osec.io/status/"+program,
            "alternate": "https://explorer.solana.com/address/"+program}


def captured_json(record, raw, *, expected_url):
    need(record.get("status") == "ok" and record.get("http_status") == 200 and not record.get("shell_suspected"), "capture is not a usable API observation")
    need(clean_url(record["url"]) == clean_url(expected_url), "capture request subject/route mismatch")
    need(clean_url(record.get("final_url", record["url"])) == clean_url(expected_url), "API redirected outside its verified route")
    need(type(raw) is bytes and record.get("sha256") == sha(raw) and record.get("bytes") == len(raw), "captured bytes mismatch")
    return json.loads(raw, object_pairs_hook=unique_object, parse_float=Decimal, parse_constant=invalid_constant)


def quantity(value):
    if value is None:
        return None
    need(type(value) in (str, int, Decimal), "market quantity must be finite decimal")
    try:
        parsed = Decimal(value)
    except InvalidOperation as exc:
        raise ValueError("invalid market quantity") from exc
    need(parsed.is_finite() and parsed >= 0 and len(str(value)) <= 128, "invalid market quantity")
    return str(parsed)


def nested(value, key):
    if value is None:
        return None
    need(isinstance(value, dict), "invalid optional market object")
    return value.get(key)


def _dedupe(candidates):
    output, seen, duplicates = [], {}, []
    for row in candidates:
        key = (row["genesis_hash"], row["target_mint"], row["program"], row["pool"])
        if key in seen:
            original = seen[key]
            conflicts = [k for k in ("base_mint", "quote_mint", "dex_label", "liquidity_usd", "price_usd") if row.get(k) != original.get(k)]
            duplicates.append({"pool": row["pool"], "conflicting_fields": conflicts})
            if conflicts:
                original["conflicts"].append({"source": row["source"], "fields": conflicts, "claim": row})
            if row["source"] not in original["sources"]:
                original["sources"].append(row["source"])
            continue
        row = {**row, "sources": [row["source"]], "conflicts": []}
        output.append(row)
        seen[key] = row
    return output, duplicates


def pools(record, raw, target, *, source="dexscreener"):
    target = target_identity(target)
    plan = source_plan(target)
    need(source in ("dexscreener", "geckoterminal"), "unsupported pool source")
    value = captured_json(record, raw, expected_url=plan["primary" if source == "dexscreener" else "alternate"])
    if source == "geckoterminal":
        need(isinstance(value, dict), "JSON API object required")
    rows = value if source == "dexscreener" else value.get("data")
    need(isinstance(rows, list) and len(rows) <= 500, "invalid or oversized pool discovery response")
    candidates, rejected, links = [], [], []
    for index, row in enumerate(rows):
        try:
            need(isinstance(row, dict), "invalid pool row")
            if source == "dexscreener":
                need(row.get("chainId") == "solana", "cross-network pool candidate")
                address, base, quote = pubkey(row["pairAddress"]), pubkey(row["baseToken"]["address"]), pubkey(row["quoteToken"]["address"])
                dex = row.get("dexId")
                liquidity, price = nested(row.get("liquidity"), "usd"), row.get("priceUsd")
                volume = nested(row.get("volume"), "h24")
                info = row.get("info") or {}
                need(isinstance(info, dict), "invalid project-link object")
                proposed = (info.get("websites") or [])+(info.get("socials") or [])
            else:
                attributes, relationships = row["attributes"], row["relationships"]
                address = pubkey(attributes["address"])
                need(row["id"] == "solana_"+address and row["type"] == "pool", "pool identity/network mismatch")
                def token(role):
                    data = relationships[role]["data"]
                    need(data["type"] == "token" and data["id"].startswith("solana_"), "token network/type mismatch")
                    return pubkey(data["id"][7:])
                base, quote = token("base_token"), token("quote_token")
                dex = relationships.get("dex", {}).get("data", {}).get("id")
                liquidity, price, volume = attributes.get("reserve_in_usd"), attributes.get("base_token_price_usd"), nested(attributes.get("volume_usd"), "h24")
                proposed = []
            need(target["mint"] in (base, quote) and base != quote, "wrong-mint pool candidate")
            need(dex is None or isinstance(dex, str) and 0 < len(dex) <= 100, "invalid DEX label")
            row_links = []
            need(isinstance(proposed, list) and len(proposed) <= 50, "project-link list exceeds bound")
            for link in proposed:
                try:
                    row_links.append(clean_url(link["url"]))
                except (ValueError, KeyError, TypeError):
                    continue
            candidate = {"genesis_hash": target["genesis_hash"], "target_mint": target["mint"],
                "pool": address, "program": None, "base_mint": base, "quote_mint": quote, "dex_label": dex,
                "liquidity_usd": quantity(liquidity), "price_usd": quantity(price), "volume_h24_usd": quantity(volume),
                "price_denominator_mint": base, "source": source, "evidence": [record["id"]],
                "captured_at": record["captured_at"], "identity_status": "indexed_candidate_requires_rpc"}
            candidates.append(candidate)
            # Dexscreener info belongs to the base token, even in quote-token searches.
            if base == target['mint']:
                links.extend({"url": url, "source": source, "evidence": [record["id"]],
                              "ownership_status": "indexer_claim_requires_project_verification"} for url in row_links)
        except (ValueError, KeyError, TypeError, IndexError) as exc:
            rejected.append({"index": index, "reason": str(exc) if isinstance(exc, ValueError) else "malformed_pool_row"})
    candidates, duplicates = _dedupe(candidates)
    return {"target": target, "source": source, "status": "partial" if rejected else "captured_discovery",
            "candidates": candidates, "rejected": rejected, "duplicates": duplicates,
            "project_links": list({r["url"]: r for r in links}.values()), "evidence": [record["id"]],
            "scope": "one bounded indexer response; not exhaustive pool or custody verification"}


def trades_url(pool):
    return "https://api.geckoterminal.com/api/v2/networks/solana/pools/"+pubkey(pool)+"/trades"


def trades(record, raw, pool):
    """Indexer-listed recent trades at one exact pool: candidate signatures only, each still verified on chain."""
    pool = pubkey(pool)
    value = captured_json(record, raw, expected_url=trades_url(pool))
    need(isinstance(value, dict), "JSON API object required")
    rows = value.get("data")
    need(isinstance(rows, list) and len(rows) <= 500, "invalid or oversized trade listing")
    out, seen = [], set()
    for row in rows:
        try:
            need(isinstance(row, dict) and row.get("type") == "trade", "invalid trade row")
            a = row["attributes"]
            sig = signature(a["tx_hash"]); kind = a.get("kind")
            need(kind in ("buy", "sell") and type(a.get("block_number")) is int and a["block_number"] >= 0, "invalid trade attributes")
            if sig in seen:
                continue
            seen.add(sig)
            out.append({"signature": sig, "kind": kind, "block_number": a["block_number"], "trader": pubkey(a["tx_from_address"]) if a.get("tx_from_address") else None})
        except (ValueError, KeyError, TypeError):
            continue
    out.sort(key=lambda r: -r["block_number"])
    return {"pool": pool, "source": "geckoterminal", "evidence": [record["id"]], "captured_at": record["captured_at"], "trades": out,
            "scope": "indexer-listed candidates; a receipt establishes the swap, never this listing"}


def link_identity(url):
    """Comparable identity of a project link: a social handle or a registered host, lowercased."""
    parts = urlsplit(clean_url(url))
    host = (parts.hostname or "").lower().removeprefix("www.")
    segments = [s for s in parts.path.split("/") if s]
    if host in ("x.com", "twitter.com", "mobile.twitter.com") and segments:
        return ("twitter", segments[0].lower().lstrip("@"))
    if host in ("t.me", "telegram.me") and segments:
        return ("telegram", segments[0].lower().lstrip("@"))
    if host in ("discord.gg", "discord.com") and segments:
        return ("discord", segments[-1].lower())
    return ("host", host)


def token_info(record, raw, target):
    """GeckoTerminal token-info publication for the exact mint: a second indexer's project links."""
    target = target_identity(target)
    value = captured_json(record, raw, expected_url=source_plan(target, surface="token_info")["primary"])
    need(isinstance(value, dict) and isinstance(value.get("data"), dict), "token info object required")
    data = value["data"]
    attributes = data.get("attributes") or {}
    need(data.get("id") == "solana_"+target["mint"] and data.get("type") == "token" and attributes.get("address") == target["mint"], "token info identity mismatch")
    identities, links = [], []
    for url in attributes.get("websites") or []:
        try:
            cleaned = clean_url(url)
        except (ValueError, TypeError):
            continue
        links.append(cleaned)
        identities.append(link_identity(cleaned))
    for key, kind in (("twitter_handle", "twitter"), ("telegram_handle", "telegram")):
        handle = attributes.get(key)
        if isinstance(handle, str) and handle.strip():
            identities.append((kind, handle.strip().lower().lstrip("@")))
    discord = attributes.get("discord_url")
    if isinstance(discord, str) and discord.strip():
        try:
            identities.append(link_identity(clean_url(discord)))
        except (ValueError, TypeError):
            pass
    return {"target": target, "source": "geckoterminal", "evidence": [record["id"]], "captured_at": record["captured_at"],
            "name": attributes.get("name"), "symbol": attributes.get("symbol"), "websites": links,
            "identities": sorted(set(identities)), "scope": "indexer publication; not project verification"}


def corroborate_links(links, infos):
    """Indexer project links are auto-captured only when a second indexer names the same identity."""
    known = {identity for info in infos for identity in info["identities"]}
    decided, seen = [], set()
    for link in links:
        url = link["url"]
        if url in seen:
            continue
        seen.add(url)
        identity = link_identity(url)
        corroborated = identity in known
        decided.append({"url": url, "source": link.get("source"), "evidence": link.get("evidence", []), "identity": list(identity),
                        "status": "corroborated" if corroborated else "unverified_indexer_profile",
                        "basis": "second indexer names the same identity" if corroborated else "single indexer claim; not fetched automatically"})
    return decided


def repository_urls(repo, revision=None):
    need(isinstance(repo, str) and re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo), "exact owner/repository required")
    need(all(part not in (".", "..") for part in repo.split("/")), "unsafe repository name")
    base = "https://api.github.com/repos/"+repo
    if revision is None:
        return {"metadata": base, "revision": base+"/commits/HEAD"}
    need(isinstance(revision, str) and re.fullmatch("[0-9a-f]{40}", revision), "immutable repository revision required")
    return {"tree": base+"/git/trees/"+revision+"?recursive=1"}


def repository_metadata(record, raw, repo):
    value = captured_json(record, raw, expected_url=repository_urls(repo)["metadata"])
    need(isinstance(value, dict) and value.get("full_name", "").lower() == repo.lower(), "repository identity mismatch")
    need(type(value.get("archived")) is bool and type(value.get("fork")) is bool, "repository lifecycle metadata missing")
    need(clean_url(value["html_url"]).lower() == ("https://github.com/"+repo).lower(), "repository publication URL mismatch")
    return {"repository": value["full_name"], "url": clean_url(value["html_url"]),
        "default_branch": value.get("default_branch"), "archived": value["archived"], "fork": value["fork"],
        "license": nested(value.get("license"), "spdx_id"), "pushed_at": value.get("pushed_at"),
        "evidence": [record["id"]], "scope": "repository metadata does not prove token utility or deployed code"}


def repository_revision(record, raw, repo):
    value = captured_json(record, raw, expected_url=repository_urls(repo)["revision"])
    need(isinstance(value, dict), "revision object required")
    revision = value.get("sha")
    need(isinstance(revision, str) and re.fullmatch("[0-9a-f]{40}", revision), "invalid repository revision")
    tree_sha = value["commit"]["tree"]["sha"]
    need(isinstance(tree_sha, str) and re.fullmatch("[0-9a-f]{40}", tree_sha), "invalid root tree SHA")
    return {"repository": repo, "revision": revision, "tree_sha": tree_sha, "evidence": [record["id"]]}


def repository_tree(record, raw, revision_record):
    repo, revision, tree_sha = (revision_record[k] for k in ("repository", "revision", "tree_sha"))
    need(re.fullmatch("[0-9a-f]{40}", revision) and revision_record.get("evidence"), "captured revision binding required")
    value = captured_json(record, raw, expected_url=repository_urls(repo, tree_sha)["tree"])
    need(isinstance(value, dict), "tree object required")
    need(value.get("sha") == tree_sha and type(value.get("truncated")) is bool and isinstance(value.get("tree"), list), "repository tree identity/schema mismatch")
    need(len(value["tree"]) <= 10000, "tree exceeds local response bound")
    paths = []
    for row in value["tree"]:
        path = row["path"]
        need(isinstance(path, str) and not path.startswith("/") and "\\" not in path and all(p not in ("", ".", "..") for p in path.split("/")), "unsafe repository tree path")
        need(row["type"] in ("blob", "tree", "commit") and re.fullmatch("[0-9a-f]{40}", row["sha"]), "invalid tree entry")
        paths.append({"path": path, "type": row["type"], "sha": row["sha"], "mode": row.get("mode")})
    return {"repository": repo, "revision": revision, "paths": paths, "truncated": value["truncated"],
            "tree_sha": tree_sha, "status": "partial" if value["truncated"] else "captured_tree", "evidence": revision_record["evidence"]+[record["id"]]}


def select_pools(packets, target, *, maximum=3, primary_source="dexscreener"):
    """Rank indexed USD claims explicitly; retain unpriced and conflicting candidates."""
    target = target_identity(target)
    need(isinstance(packets, list) and len(packets) <= 2 and type(maximum) is int and 1 <= maximum <= 3, "bounded primary/alternate pool selection required")
    grouped, rejected = {}, []
    for packet in packets:
        need(packet.get("target") == target and len(packet.get("candidates", [])) <= 500, "pool selection subject/bound mismatch")
        for row in packet["candidates"]:
            need(row["genesis_hash"] == target["genesis_hash"] and row["target_mint"] == target["mint"] and target["mint"] in (row["base_mint"], row["quote_mint"]), "candidate identity mismatch")
            grouped.setdefault(pubkey(row["pool"]), []).append(row)
        rejected.extend(packet.get("rejected", []))
    ranked, excluded = [], []
    for address, rows in grouped.items():
        chosen = next((r for r in rows if r["source"] == primary_source), rows[0])
        entry = {"pool": address, "basis_source": chosen["source"], "basis_evidence": chosen["evidence"],
            "liquidity_usd": chosen["liquidity_usd"], "claims": rows}
        if any(r.get("conflicts") for r in rows) or len({(r["base_mint"], r["quote_mint"]) for r in rows}) > 1:
            excluded.append({**entry, "reason": "conflicting_pool_identity_or_duplicate_claims"})
        elif chosen["liquidity_usd"] is None:
            excluded.append({**entry, "reason": "unpriced_candidate"})
        else:
            ranked.append(entry)
    ranked.sort(key=lambda r: (-Decimal(quantity(r["liquidity_usd"])), r["pool"]))
    selected = [{**row, "role": "principal" if i == 0 else "side"} for i, row in enumerate(ranked[:maximum])]
    excluded += [{**row, "reason": "declared_pool_cap"} for row in ranked[maximum:]]
    return {"target": target, "selected": selected, "excluded": excluded, "rejected_rows": rejected,
            "basis": "descending indexed USD liquidity, primary source preferred; address tie-break",
            "canonical_status": "not_asserted", "scope": "bounded discovery responses; all candidates require RPC recognition"}


def launch_leads(target,documents):
    """Exact-mint retained publications supply leads, never suffix-based recognition."""
    from adapters.pump_common import curve_address
    target=target_identity(target)
    need(isinstance(documents,list) and len(documents)<=2,'one primary and one alternate launch document')
    publications=[]
    for record,raw in documents:
        need(record.get('status')=='ok' and record.get('http_status')==200,'successful launch document required')
        need(type(raw) is bytes and len(raw)==record['bytes'] and sha(raw)==record['sha256'],'launch document digest mismatch')
        url=clean_url(record['url']);final=clean_url(record['final_url'])
        content=raw.decode('utf-8',errors='replace')
        exact=re.search(r'(?<![1-9A-HJ-NP-Za-km-z])'+re.escape(target['mint'])+r'(?![1-9A-HJ-NP-Za-km-z])',content+' '+final)
        if exact:publications.append({'url':url,'final_url':final,'evidence':[record['id']],
            'relationship':'publication_mentions_exact_mint','platform_or_creator_verified':False})
    return {'target':target,'documents':publications,'candidate_curve':curve_address(target['mint']),
        'candidate_scope':'deterministic address to read; existence, ownership and launch stage unverified',
        'unsupported_products':['raydium_launchlab','meteora_dbc'],
        'scope':'captured exact-mint leads only; project/creator affiliation needs explicit evidence'}
