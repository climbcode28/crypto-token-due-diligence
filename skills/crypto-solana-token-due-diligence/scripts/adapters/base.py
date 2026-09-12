"""Pool adapter contract: full account evidence, scoped arithmetic and sampled custody."""
from solana_common import need, pubkey, target_identity, TOKEN_PROGRAM, TOKEN_2022
from solana_accounts import decode_mint, decode_holding, ratio
from solana_programs import observed_account, decode_program
from solana_discovery import MAINNET
from solana_session import encoded

VERSION = 1


def capability(name, program, revision, *, model, dependencies):
    return {"schema_version": VERSION, "id": name, "version": "1.0.0", "program": program,
            "genesis_hash": MAINNET, "source_revision": revision, "principal_model": model,
            "required_dependencies": dependencies, "custody": "bounded_observed_accounts",
            "quote": False, "locks": [], "network_scope_requires_bundle_verification": True}


class Sample:
    def __init__(self, target, pool, observations, descriptor):
        self.target = target_identity(target)
        need(self.target["genesis_hash"] == descriptor["genesis_hash"], "unsupported adapter network")
        self.pool, self.observations = pubkey(pool), observations
        need(isinstance(observations, dict) and len(observations) <= 100, "bounded account sample required")
        self.used = {}
        self.result = {"adapter": descriptor, "target": self.target, "pool": pool,
            "status": "partial", "vaults": [], "mint_accounts": {}, "reserves_atomic": None, "lp_custody": None,
            "program_control": None, "evidence": [], "contexts": [], "gaps": [],
            "all_principal_locked": None, "exit_executable": None,
            "reserve_quantity_scope": "public base balances; confidential quantities and executable exits excluded",
            "scope": "account layout observations; genesis/header/recheck binding required by bundle"}

    def account(self, address):
        need(address in self.observations, "missing dependency: "+address)
        value, meta = observed_account(address, self.observations[address])
        need(value is not None and not meta["sliced"], "full dependency account required: "+address)
        self.used[address] = meta
        return value

    def same_bank(self, addresses):
        need(all(a in self.used for a in addresses), "unobserved arithmetic dependency")
        packets = [self.observations[a] for a in addresses]
        # Equal slots from separate RPC reads need not mean one atomic sample.
        need(len({encoded(p) for p in packets}) == 1, "reserve/custody dependencies require one account batch")

    def vault(self, address, mint, program, authority):
        account = self.account(address)
        row = decode_holding(account, mint=mint, token_program=program)
        need(row["spending_owner"] == authority and row["state"] != "uninitialized", "vault authority/state mismatch")
        row.update(address=address, **self.used[address])
        self.result["vaults"].append(row)
        return row

    def mint(self, address, program, decimals=None):
        account = self.account(address)
        need(account["owner"] == program and program in (TOKEN_PROGRAM, TOKEN_2022), "mint token program mismatch")
        row = decode_mint(account)
        need(decimals is None or row["decimals"] == decimals, "mint decimals mismatch")
        self.result["mint_accounts"][address] = {**row, **self.used[address]}
        if not row["extensions_valid"] or row["unknown_extensions"]:
            self.result["gaps"].append("mint_extension_execution_semantics_unresolved: "+address)
        return row

    def controls(self, program):
        try:
            packet = self.observations[program]
            initial = decode_program(program, packet)
            pd = initial.get("programdata_address")
            self.result["program_control"] = decode_program(program, packet, self.observations.get(pd))
            self.account(program)
            if pd in self.observations:
                # Metadata-only ProgramData is enough for control observation.
                _, meta = observed_account(pd, self.observations[pd])
                self.used[pd] = meta
            if self.result["program_control"]["upgradeability"] == "unknown":
                self.result["gaps"].append("program_upgrade_authority_unresolved")
        except (KeyError, ValueError):
            self.result["gaps"].append("program_control_not_observed")

    def finish(self):
        state = self.result.get("state", {})
        for key in ("lp_supply", "protocol_fees", "fund_fees", "creator_fees", "pending_pnl"):
            if key in state:
                state[key] = list(map(str, state[key])) if isinstance(state[key], list) else str(state[key])
        custody = self.result.get("lp_custody")
        if custody and custody["missing"]:
            self.result["gaps"].append("some_requested_lp_holdings_unresolved")
        self.result["controller_roots"] = [
            {"address": row[role], "role": role, "holding": row["address"], "evidence": row["evidence"]}
            for row in (custody or {}).get("accounts", [])
            for role in ("spending_owner", "delegate", "close_authority") if row[role] is not None]
        self.result["evidence"] = sorted({e for m in self.used.values() for e in m["evidence"]})
        self.result["contexts"] = [{"address": a, **m} for a, m in self.used.items()]
        self.result["status"] = "observed" if self.result["reserves_atomic"] is not None and not self.result["gaps"] else "partial"
        return self.result


def lp_custody(sample, mint_address, authority, accounting_supply, addresses, *, pool_dependencies, decimals=None):
    need(isinstance(addresses, list) and len(addresses) <= 20 and len(set(addresses)) == len(addresses), "bounded unique LP holdings required")
    mint = sample.mint(mint_address, TOKEN_PROGRAM, decimals)
    need(mint["mint_authority"] == authority and mint["freeze_authority"] is None, "LP mint authority mismatch")
    supply = int(mint["supply_atomic"])
    need(type(accounting_supply) is int and 0 <= supply <= accounting_supply < 2**64, "LP supply/accounting relationship invalid")
    rows, missing, total = [], [], 0
    for address in addresses:
        try:
            value = decode_holding(sample.account(address), mint=mint_address, token_program=TOKEN_PROGRAM)
            need(value["state"] != "uninitialized", "LP holding uninitialized")
            sample.same_bank([*pool_dependencies, mint_address, address])
            amount = int(value["amount_atomic"])
            total += amount
            rows.append({"address": address, **value, **sample.used[address],
                "mint_supply_share": ratio(amount, supply), "pool_accounting_share": ratio(amount, accounting_supply)})
        except ValueError as exc:
            missing.append({"address": address, "reason": str(exc)})
    need(total <= supply, "LP sample exceeds mint supply")
    sample.same_bank([*pool_dependencies, mint_address])
    return {"mint": mint_address, "mint_supply_atomic": str(supply),
        "pool_accounting_supply_atomic": str(accounting_supply), "observed_atomic": str(total),
        "accounting_minus_mint_supply_atomic": str(accounting_supply-supply),
        "difference_reason": "unresolved; initialization retention, burns and history are distinct",
        "sample_mint_share": ratio(total, supply), "sample_pool_share": ratio(total, accounting_supply),
        "accounts": rows, "missing": missing, "enumeration": "explicit_subset_not_exhaustive",
        "locked_share": None, "unsupported_lock_paths": "No locker or burn-label proof; controller graph is separate."}


def dependencies(pool, state):
    addresses = [pool, *state["mints"], *state["vaults"], state["lp_mint"]]
    addresses += [state[k] for k in ("config", "open_orders", "market") if state.get(k)]
    return list(dict.fromkeys(addresses))
