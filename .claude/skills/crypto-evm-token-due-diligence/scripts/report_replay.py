#!/usr/bin/env python3
"""Freeze and verify a reporting engine; execute local snapshots only by explicit opt-in."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import tempfile

from validate_bundle import REPORTING_ENGINE_VERSION, file_in, need, read_json, sha
from report_profile import CURRENT_PROFILE, LEGACY_PROFILE

FILES = ("render_report.py", "render_legacy_v1.py", "validate_bundle.py", "report_profile.py", "rpc_wire.py", "evm_decode.py")


def freeze_snapshot(root):
    root = Path(root)
    directory = root / "reporting-engine"
    directory.mkdir()  # Frozen output must be new; never repair an existing snapshot.
    sources = {}
    for name in FILES:
        content = (Path(__file__).parent / name).read_bytes()
        (directory / name).write_bytes(content)
        sources[name] = sha(content)
    report = read_json(root / "report.json")
    snapshot = {"schema_version": 1, "reporting_engine_version": REPORTING_ENGINE_VERSION,
                "validation_profile": report.get("validation_profile", LEGACY_PROFILE),
                "source_sha256": sources,
                "artifact_sha256": {name: sha((root / name).read_bytes()) for name in ("manifest.json", "report.json", "report.md")}}
    (directory / "snapshot.json").write_text(json.dumps(snapshot, sort_keys=True, indent=2) + "\n")
    return snapshot


def verify(root):
    root = Path(root).resolve()
    snapshot = read_json(file_in(root, "reporting-engine/snapshot.json"))
    need(set(snapshot) == {"schema_version", "reporting_engine_version", "validation_profile", "source_sha256", "artifact_sha256"}
         and type(snapshot["schema_version"]) is int and snapshot["schema_version"] == 1, "unsupported reporting snapshot")
    need(snapshot["validation_profile"] in (CURRENT_PROFILE, LEGACY_PROFILE), "unsupported frozen profile")
    need(set(snapshot["source_sha256"]) == set(FILES), "snapshot dependency set differs")
    need(set(snapshot["artifact_sha256"]) == {"manifest.json", "report.json", "report.md"}, "snapshot input set differs")
    for name, digest in snapshot["source_sha256"].items():
        need(sha(file_in(root, "reporting-engine/" + name).read_bytes()) == digest, "reporting source changed")
    for name, digest in snapshot["artifact_sha256"].items():
        need(sha(file_in(root, name).read_bytes()) == digest, "frozen report input/output changed")
    manifest = read_json(file_in(root, "manifest.json"))
    for evidence in manifest["evidence"]:
        need(sha(file_in(root, evidence["artifact"]).read_bytes()) == evidence["sha256"], "registered evidence changed")
    return snapshot


def replay(root, trust_frozen_engine=False, allow_synthetic=False):
    snapshot = verify(root)
    need(trust_frozen_engine, "replay executes Python; explicitly trust this locally reviewed frozen engine")
    root = Path(root).resolve()
    with tempfile.TemporaryDirectory(prefix="evm-report-replay-") as temp:
        output = Path(temp) / "report.md"
        engine = Path(temp) / "engine"
        engine.mkdir()
        for name, digest in snapshot["source_sha256"].items():
            content = file_in(root, "reporting-engine/" + name).read_bytes()
            need(sha(content) == digest, "reporting source changed during replay")
            (engine / name).write_bytes(content)
        # Copy only verified sources into a clean directory: -B prevents bytecode
        # writes but does not stop imports of stale pycache or unlisted shadow modules.
        command = [sys.executable, "-B", "-I", "-c",
                   "import runpy,sys;sys.path.insert(0,sys.argv[1]);sys.argv=sys.argv[2:];runpy.run_path(sys.argv[0],run_name='__main__')",
                   str(engine), str(engine / "render_report.py"), str(root),
                   "--profile", snapshot["validation_profile"], "--output", str(output)]
        if allow_synthetic:
            command.append("--allow-synthetic")
        completed = subprocess.run(command, capture_output=True, text=True, timeout=60)
        need(completed.returncode == 0, "frozen reporting validation/render failed")
        need(output.read_bytes() == (root / "report.md").read_bytes(), "frozen replay differs")
    return {"status": "reproduced", "reporting_engine_version": snapshot["reporting_engine_version"],
            "validation_profile": snapshot["validation_profile"], "report_sha256": snapshot["artifact_sha256"]["report.md"]}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("action", choices=("freeze", "verify", "replay"))
    p.add_argument("bundle", type=Path)
    p.add_argument("--trust-frozen-engine", action="store_true")
    p.add_argument("--allow-synthetic", action="store_true")
    args = p.parse_args()
    try:
        result = freeze_snapshot(args.bundle) if args.action == "freeze" else verify(args.bundle) if args.action == "verify" else replay(args.bundle, args.trust_frozen_engine, args.allow_synthetic)
        print(json.dumps(result, sort_keys=True))
        return 0
    except (ValueError, OSError, KeyError, TypeError, subprocess.SubprocessError) as exc:
        print("Reporting replay unavailable: " + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
