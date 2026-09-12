import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("token_router", ROOT / "scripts/route.py")
router = importlib.util.module_from_spec(spec)
spec.loader.exec_module(router)
EVM = "0x4Eb990547BCe4a982432CA88Cf5fae7EED1A2d35"
SOL = "So11111111111111111111111111111111111111112"


def intake(**changes):
    return {"request": "Assess this exact token and its lore", "address": EVM,
            "received_at": 1000, **changes}


def base58(raw):
    n = int.from_bytes(raw, "big")
    text = ""
    while n:
        n, digit = divmod(n, 58)
        text = router.ALPHABET[digit] + text
    return "1" * (len(raw) - len(raw.lstrip(b"\0"))) + text


class RoutingTests(unittest.TestCase):
    def test_evm_without_chain_dispatches_but_does_not_verify(self):
        result = router.route(intake(), now=1002)
        self.assertEqual(result["skill"], "crypto-evm-token-due-diligence")
        self.assertEqual(result["address"], EVM)
        self.assertFalse(result["identity_verified"])
        self.assertNotIn("chain_id", result)

    def test_network_hints_are_preserved_not_defaulted(self):
        for hint in ("Ethereum", "Base", "Robinhood mainnet", "Robinhood testnet", "unknown EVM chain"):
            result = router.route(intake(chain_hint=hint, family_hint="evm"), now=1002)
            self.assertEqual(result["handoff"]["chain_hint"], hint)
            self.assertEqual(result["status"], "routed")
            self.assertFalse(result["identity_verified"])

    def test_solana_candidate_is_case_sensitive(self):
        result = router.route(intake(address=SOL), now=1002)
        self.assertEqual(result["skill"], "crypto-solana-token-due-diligence")
        self.assertEqual(result["address"], SOL)
        self.assertFalse(result["identity_verified"])

    def test_generated_base58_byte_lengths(self):
        for length in (20, 31, 32, 33, 64):
            for byte in (1, 127, 255):
                with self.subTest(length=length, byte=byte):
                    address = base58(bytes([byte]) * length)
                    self.assertEqual(router.candidate_family(address), "solana" if length == 32 else None)

    def test_leading_zero_bytes_count_towards_solana_length(self):
        for zeros in (1, 4, 20, 31):
            self.assertEqual(router.candidate_family(base58(b"\0" * zeros + b"\1" * (32-zeros))), "solana")

    def test_zero_and_known_system_addresses_not_token_candidates(self):
        for address in ("0x" + "0" * 40, "1" * 32):
            self.assertIsNone(router.candidate_family(address))

    def test_malformed_and_transaction_identifiers_do_not_fall_back(self):
        for address in ("0x123", "0x" + "a" * 64, "0X" + "a" * 40,
                        "0x" + "g" * 40, "0x" + "a" * 41, EVM + "z", "_" + EVM,
                        " " + EVM, "0" * 44, "O" * 44, "a" * 44, "1" * 31,
                        base58(b"\xff" * 64), "BTC", "SOL", "coinpump", "bc1qnotatoken"):
            with self.subTest(address=address):
                result = router.route(intake(address=address), now=1002)
                self.assertEqual(result["status"], "clarification_required")
                self.assertIsNone(result["skill"])

    def test_url_not_silently_used_as_token(self):
        for path in ("tx", "pair", "pool", "address", "token"):
            result = router.route(intake(address=f"https://example.com/{path}/{EVM}"), now=1002)
            self.assertEqual(result["status"], "clarification_required")

    def test_conflicting_family_is_not_ignored(self):
        for address, hint in ((EVM, "solana"), (SOL, "evm")):
            self.assertEqual(router.route(intake(address=address, family_hint=hint), now=1002)["status"],
                             "clarification_required")

    def test_explicit_chain_hint_cannot_be_silently_ignored(self):
        result = router.route(intake(chain_hint="Solana"), now=1002)
        self.assertEqual(result["status"], "clarification_required")
        self.assertIsNone(result["skill"])

    def test_other_family_shape_collision_not_solana(self):
        for address in (EVM, SOL):
            result = router.route(intake(address=address, family_hint="other", chain_hint="Other chain"), now=1002)
            self.assertEqual(result["status"], "unsupported_family")
            self.assertIsNone(result["skill"])

    def test_native_scope_not_converted_to_wrapped(self):
        result = router.route(intake(asset_kind="native", address=SOL), now=1002)
        self.assertEqual(result["status"], "native_asset")
        self.assertIsNone(result["skill"])

    def test_missing_and_multiple_targets_require_selection(self):
        for candidates in ([], [EVM, SOL], [EVM, "not-an-address"]):
            result = router.route(intake(address=None, candidates=candidates), now=1002)
            self.assertEqual(result["status"], "clarification_required")

    def test_duplicate_evm_case_does_not_create_second_target(self):
        result = router.route(intake(candidates=[EVM.lower()]), now=1002)
        self.assertEqual(result["status"], "routed")
        self.assertEqual(result["handoff"]["address"], EVM)

    def test_distinct_case_solana_targets_are_not_merged(self):
        a = base58(bytes([127]) * 32)
        b = next(a[:i] + c.swapcase() + a[i+1:] for i, c in enumerate(a)
                 if c.isalpha() and c.swapcase() in router.ALPHABET
                 and router.candidate_family(a[:i] + c.swapcase() + a[i+1:]) == "solana")
        self.assertEqual(router.route(intake(address=None, candidates=[a, b]), now=1002)["status"],
                         "clarification_required")

    def test_full_handoff_is_lossless_and_independent(self):
        packet = intake(request='Flybrain — is its lore true?\n$(touch /tmp/never) `false` "quoted"',
                        urls=["https://x.com/a/status/123?x=1&y=2"],
                        focus={"claims": ["autonomy"], "wallet": SOL}, constraints=["7 minutes"],
                        skill="not-a-real-specialist")
        original = json.loads(json.dumps(packet))
        result = router.route(packet, now=1005)
        for key in original:
            self.assertEqual(result["handoff"][key], original[key])
        result["handoff"]["focus"]["claims"].append("changed")
        self.assertEqual(packet, original)
        self.assertEqual(result["skill"], "crypto-evm-token-due-diligence")

    def test_auxiliary_addresses_in_request_do_not_replace_selected_target(self):
        result = router.route(intake(request=f"Token {EVM}; investigate wallet {SOL}"), now=1002)
        self.assertEqual(result["address"], EVM)
        self.assertIn(SOL, result["handoff"]["request"])

    def test_no_network_or_credential_access(self):
        with patch("socket.socket", side_effect=AssertionError("network")), \
             patch("urllib.request.urlopen", side_effect=AssertionError("network")), \
             patch("pathlib.Path.open", side_effect=AssertionError("file access")):
            self.assertEqual(router.route(intake(address=SOL), now=1002)["network_requests"], 0)

    def test_same_clock_survives_retry_and_family_change(self):
        first = router.route(intake(), now=1005)
        second = router.route({**first["handoff"], "address": SOL}, now=1040)
        self.assertEqual(second["remaining_seconds"], 560)
        self.assertEqual(second["target_remaining_seconds"], 380)
        self.assertEqual(second["handoff"]["received_at"], 1000)
        self.assertEqual(second["handoff"]["deadline_at"], 1600)

    def test_shorter_and_explicit_longer_user_budgets_retained(self):
        for deadline in (1120, 1300, 2500):
            result = router.route(intake(deadline_at=deadline), now=1010)
            self.assertEqual(result["remaining_seconds"], deadline - 1010)
            self.assertLessEqual(result["handoff"]["target_at"], deadline)

    def test_expiry_does_not_start_a_specialist(self):
        for now in (1599.5, 1600, 2000):
            result = router.route(intake(), now=now)
            self.assertEqual(result["status"], "deadline_reached")
            self.assertIsNone(result["skill"])
            self.assertEqual(result["remaining_seconds"], 0)

    def test_invalid_clock_values_fail_closed(self):
        for changes in ({"received_at": 1003}, {"received_at": True}, {"received_at": -1},
                        {"received_at": None}, {"received_at": 10**400}, {"deadline_at": float("nan")},
                        {"target_at": float("inf")}, {"target_at": 1700}, {"deadline_at": 999}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                router.route(intake(**changes), now=1002)

    def test_invalid_packet_shapes_fail_closed(self):
        for packet in ([], None, {}, intake(request=""), intake(family_hint="unknown"),
                       intake(asset_kind="pool"), intake(address=12), intake(candidates=EVM),
                       intake(candidates=[None]), intake(chain_hint=True), intake(chain_hint="")):
            with self.subTest(packet=packet), self.assertRaises(ValueError):
                router.route(packet, now=1002)

    def test_specialist_dependencies_resolve(self):
        for skill in router.SPECIALISTS.values():
            self.assertTrue((ROOT.resolve().parent / skill / "SKILL.md").is_file())


class CLITests(unittest.TestCase):
    def run_cli(self, raw, *args):
        return subprocess.run([sys.executable, str(ROOT / "scripts/route.py"), *args],
                              input=raw, text=True, capture_output=True, timeout=5)

    def test_stdin_routes_full_request_as_data(self):
        packet = intake(received_at=time.time() - 2, request='$(exit 9)\n"original"')
        process = self.run_cli(json.dumps(packet))
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertEqual(json.loads(process.stdout)["handoff"]["request"], packet["request"])

    def test_file_input_supported(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "request.json"
            p.write_text(json.dumps(intake(received_at=time.time()-2, address=SOL)))
            process = self.run_cli("", str(p))
            self.assertEqual(process.returncode, 0, process.stderr)
            self.assertEqual(json.loads(process.stdout)["family"], "solana")

    def test_cli_errors_do_not_echo_intake(self):
        secret = "https://example.invalid/?api_key=do-not-echo"
        for raw in (secret, json.dumps(intake(received_at=True, request=secret)),
                    '{"request":"x","request":"y","received_at":1}'):
            process = self.run_cli(raw)
            self.assertEqual(process.returncode, 2)
            self.assertNotIn(secret, process.stdout + process.stderr)
            self.assertEqual(json.loads(process.stdout)["status"], "invalid_input")

    def test_nonfinite_metadata_and_oversized_input_rejected(self):
        for raw in (json.dumps(intake(received_at=1, metadata=float("nan"))), "x" * 1_000_001):
            process = self.run_cli(raw)
            self.assertEqual(process.returncode, 2)
            self.assertEqual(json.loads(process.stdout)["status"], "invalid_input")

    def test_unicode_handoff_remains_valid_json(self):
        for request in ("Token lore — 蝇脑", "escaped surrogate \ud800"):
            process = self.run_cli(json.dumps(intake(received_at=time.time()-2, request=request)))
            self.assertEqual(process.returncode, 0, process.stderr)
            self.assertEqual(json.loads(process.stdout)["handoff"]["request"], request)

    def test_nonroute_exit_code(self):
        process = self.run_cli(json.dumps(intake(received_at=time.time()-2, address="BTC")))
        self.assertEqual(process.returncode, 2)
        self.assertEqual(json.loads(process.stdout)["status"], "clarification_required")


if __name__ == "__main__":
    unittest.main()
