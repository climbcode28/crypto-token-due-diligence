"""Immutable, explicitly selected captured observations; never a current-state cache."""
import json
import time
from pathlib import Path

from solana_common import need, sha, write_new, target_identity
from solana_session import encoded, label
from solana_wire import validate_response, header


class ObservationCache:
    def __init__(self, root, *, investigation_id, namespace, target, synthetic):
        self.root = Path(root)
        label(investigation_id)
        label(namespace)
        need(type(synthetic) is bool, "explicit synthetic mode required")
        self.identity = {"investigation_id": investigation_id, "namespace": namespace,
                         "target": target_identity(target), "synthetic": synthetic}

    def capture(self, sample_id, packet, *, captured_at, block=None):
        label(sample_id)
        need(type(captured_at) in (int, float) and 0 <= captured_at <= time.time()+1, "invalid capture time")
        need(packet.get("status") == "ok", "failed observations cannot be cached")
        checked = validate_response(packet["request"], packet["response"])
        need(checked["status"] == "ok", "unsuccessful wire observation")
        if packet["request"]["method"] == "getGenesisHash":
            need(checked["result"] == self.identity["target"]["genesis_hash"], "cache network mismatch")
        if "historical_slot" in checked:
            need(block is not None, "historical reuse requires its original header")
            header(block, checked["historical_slot"])
        value = {**self.identity, "sample_id": sample_id, "captured_at": captured_at,
                 "packet": packet, "context_slot": checked.get("context_slot"),
                 "historical_slot": checked.get("historical_slot"), "block": block}
        digest = sha(encoded(value).encode())
        write_new(self.root / (sample_id+".json"), {"sha256": digest, "observation": value})
        return digest

    def reuse(self, sample_id, *, digest, method, params, max_age, now=None, purpose="captured"):
        """The caller selects a named observation/digest and an explicit freshness bound."""
        label(sample_id)
        need(purpose in ("captured", "current", "recheck"), "invalid reuse purpose")
        if purpose != "captured":
            return None
        need(type(max_age) in (int, float) and 0 <= max_age <= 86400, "explicit bounded freshness required")
        path = self.root / (sample_id+".json")
        if not path.exists():
            return None
        need(path.is_file() and not path.is_symlink(), "unsafe cache reference")
        saved = json.loads(path.read_text())
        value = saved["observation"]
        need(saved["sha256"] == digest == sha(encoded(value).encode()), "cache digest mismatch")
        need(all(value.get(k) == v for k, v in self.identity.items()), "cache identity mismatch")
        need(value["sample_id"] == sample_id, "cache sample mismatch")
        request = value["packet"]["request"]
        need(request["method"] == method and request["params"] == params, "cache request mismatch")
        checked = validate_response(request, value["packet"]["response"])
        need(checked["status"] == value["packet"]["status"] == "ok", "invalid cached observation")
        need(checked.get("context_slot") == value["context_slot"] and checked.get("historical_slot") == value["historical_slot"], "cache context mismatch")
        if value["historical_slot"] is not None:
            header(value["block"], value["historical_slot"])
        age = (time.time() if now is None else now)-value["captured_at"]
        return value if 0 <= age <= max_age else None
