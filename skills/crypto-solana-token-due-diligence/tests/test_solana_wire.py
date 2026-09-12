import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"scripts"))
from solana_wire import validate_request, validate_response, consistency
from solana_common import base58_bytes, b58encode
from solana_presets import settings, read, validate_plan, account_batches
from solana_fixture import KEY, OTHER, GENESIS, SIG, TARGET, account, request, response


class WireTests(unittest.TestCase):
    def test_exact_array_indices_and_null_members(self):
        req = request("getMultipleAccounts", [[KEY, OTHER], settings(20)])
        value = {"context": {"slot": 21}, "value": [account(), None]}
        checked = validate_response(req, response(req, value))
        self.assertEqual(checked["address_indices"], {KEY: 0, OTHER: 1})
        self.assertEqual(checked["missing_indices"], [1])
        for rows in ([account()], [account(), None, None], {KEY: account()}):
            with self.subTest(rows=type(rows)), self.assertRaises(ValueError):
                validate_response(req, response(req, {**value, "value": rows}))

    def test_wrong_id_ambiguous_envelope_and_context_floor(self):
        req = request("getAccountInfo", [KEY, settings(20)])
        valid = response(req, {"context": {"slot": 20}, "value": account()})
        for mutation in ({**valid, "id": "other"}, {**valid, "error": {"code": 1}},
                         {**valid, "result": {"context": {"slot": 19}, "value": account()}}):
            with self.assertRaises(ValueError):
                validate_response(req, mutation)
        self.assertEqual(validate_response(req, response(req, None))["status"], "null")
        self.assertEqual(validate_response(req, {"jsonrpc": "2.0", "id": "r", "error": {"code": -1, "message": "gap"}})["status"], "rpc_error")

    def test_strict_account_envelopes(self):
        req = request("getAccountInfo", [KEY, settings()])
        for changes in ({"owner": "bad"}, {"executable": 0}, {"lamports": True}, {"space": 1}, {"data": ["!!", "base64"]}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                validate_response(req, response(req, {"context": {"slot": 10}, "value": {**account(), **changes}}))

    def test_disallowed_requests_and_bounded_discovery(self):
        invalid = [request(m, []) for m in ("sendTransaction", "simulateTransaction", "requestAirdrop")]
        invalid += [request("getMultipleAccounts", [[KEY, KEY], settings()]),
                    request("getAccountInfo", [KEY, {"encoding": "jsonParsed", "commitment": "processed"}]),
                    request("getProgramAccounts", [KEY, settings()]),
                    request("getSignaturesForAddress", [KEY, {"commitment": "finalized", "limit": 26}])]
        for req in invalid:
            with self.subTest(method=req["method"]), self.assertRaises(ValueError):
                validate_request(req)

    def test_owner_and_program_filters_reject_wrong_subject(self):
        raw = base58_bytes(KEY, 32)+base58_bytes(OTHER, 32)+bytes(101)
        req = request("getTokenAccountsByOwner", [OTHER, {"mint": KEY}, settings()])
        result = {"context": {"slot": 10}, "value": [{"pubkey": GENESIS, "account": account(raw)}]}
        self.assertEqual(validate_response(req, response(req, result))["addresses"], [GENESIS])
        wrong = copy.deepcopy(result)
        wrong["value"][0]["account"] = account(bytes(165))
        with self.assertRaisesRegex(ValueError, "unrequested"):
            validate_response(req, response(req, wrong))
        params = [account()["owner"], {**settings(), "withContext": True,
                  "filters": [{"dataSize": 165}, {"memcmp": {"offset": 0, "bytes": KEY}}]}]
        req = request("getProgramAccounts", params)
        validate_response(req, response(req, result))
        with self.assertRaises(ValueError):
            validate_response(req, response(req, wrong))

    def test_history_keeps_signature_slot_version_and_null_metadata(self):
        req = request("getTransaction", [SIG, {"commitment": "finalized", "encoding": "json", "maxSupportedTransactionVersion": 0}])
        value = {"slot": 9, "blockTime": None, "version": 0, "meta": None,
                 "transaction": {"signatures": [SIG], "message": {"accountKeys": [KEY]}}}
        self.assertEqual(validate_response(req, response(req, value))["historical_slot"], 9)
        self.assertEqual(validate_response(req, response(req, {**value, "version": 1}))["status"], "unsupported")
        value["transaction"]["signatures"] = [b58encode(bytes([8])*64)]
        with self.assertRaises(ValueError):
            validate_response(req, response(req, value))

    def test_all_network_and_header_observations_are_scanned(self):
        req = request("getGenesisHash", [])
        packets = [{"request": req, "response": response(req, GENESIS), "status": "ok"}]
        consistency(packets, TARGET)
        packets.append({"request": req, "response": response(req, OTHER), "status": "ok"})
        with self.assertRaisesRegex(ValueError, "network"):
            consistency(packets, TARGET)
        req = request("getAccountInfo", [KEY, settings()])
        a = {"request": req, "response": response(req, {"context": {"slot": 2}, "value": account()}), "status": "ok"}
        b = copy.deepcopy(a)
        b["response"]["result"]["value"]["lamports"] += 1
        with self.assertRaisesRegex(ValueError, "contradictory account"):
            consistency([a, b], TARGET)

    def test_batches_are_ordered_bounded_and_dependency_cycles_fail(self):
        addresses = [b58encode(bytes([i])*32) for i in range(1, 61)]
        rows = account_batches(addresses+addresses[:2])
        self.assertEqual([len(r["params"][0]) for r in rows], [25, 25, 10])
        self.assertEqual([a for r in rows for a in r["params"][0]], addresses)
        self.assertGreater(len(account_batches(addresses, account_bytes=100000)), 3)
        with self.assertRaises(ValueError):
            validate_plan([read("a", "getGenesisHash", [], depends=["b"]), read("b", "getGenesisHash", [], depends=["a"])])


if __name__ == "__main__":
    unittest.main()
