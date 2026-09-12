"""Repeatable synthetic full-collector comparison; never a live provider benchmark."""
import json
import platform
import statistics
import tempfile
import time
from pathlib import Path

from backend_fixtures import FakeRpc
from backend_common import Cache
from rpc_collect import Collector
from test_collector_runtime import balance_plan


class WaveReference(Collector):
    def request_many(self, requests, validate_result=None):
        for start in range(0, len(requests), self.workers):
            super().request_many(requests[start:start + self.workers], validate_result)


def benchmark(trials=3):
    results = {}
    for name, cls in (("wave_reference", WaveReference), ("rolling", Collector)):
        values = []
        for _ in range(trials):
            with tempfile.TemporaryDirectory() as tmp:
                root, rpc = Path(tmp), FakeRpc()
                def balance(request):
                    number = int(request["params"][0], 16)
                    time.sleep(0.08 if number in (1, 5) else 0.005)
                    return hex(number)
                rpc.overrides["eth_getBalance"] = balance
                cache = Cache(root / "cache.sqlite")
                try:
                    started = time.monotonic()
                    collection = cls(root / "run", cache, rpc, "synthetic-benchmark").collect(balance_plan(8))
                    elapsed = time.monotonic() - started
                    assert collection["status"] == "complete"
                    assert collection["statistics"]["network_attempts"] == 11
                    values.append(round(elapsed, 6))
                finally:
                    cache.close()
        results[name] = {"seconds": values, "median_seconds": statistics.median(values), "method_attempts_per_trial": 11}
    return {"synthetic": True, "python": platform.python_version(), "trials": trials,
            "workload": "Eight distinct balances: two 80ms and six 5ms replies; four workers; full collection and evidence packaging",
            "results": results, "limitations": "Wave reference chunks the same collector in groups of four. Fixture latency only; no live speed or accuracy claim."}


if __name__ == "__main__":
    print(json.dumps(benchmark(), indent=2, sort_keys=True))
