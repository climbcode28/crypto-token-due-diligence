"""The installed Solana implementation must not rely on an EVM sibling."""
import ast
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"


class ImportTests(unittest.TestCase):
    def test_all_top_level_imports_and_provider_preflight_standalone(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)/"solana"
            shutil.copytree(SCRIPTS, root)
            script = "import importlib,sys; sys.addaudithook(lambda event,args: (_ for _ in ()).throw(AssertionError('network')) if event.startswith('socket.') else None); "
            script += ";".join("importlib.import_module("+repr(p.stem)+")" for p in sorted(root.glob("*.py")))
            result = subprocess.run([sys.executable, "-E", "-B", "-c", script], cwd=root, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            before = sorted(str(p.relative_to(root)) for p in root.rglob("*"))
            result = subprocess.run([sys.executable, "-E", "-B", str(root/"solana_collect.py"), "--check-availability"],
                                    cwd=root, env={"PYTHONDONTWRITEBYTECODE": "1"}, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)["network_requests"], 0)
            self.assertEqual(before, sorted(str(p.relative_to(root)) for p in root.rglob("*")))

    def test_no_sibling_sys_path_mutation(self):
        for path in SCRIPTS.glob("*.py"):
            source = path.read_text()
            for node in ast.walk(ast.parse(source)):
                # Runtime modules cannot alter their caller's import path. Trusted
                # replay's isolated-child bootstrap string is covered separately.
                if isinstance(node, ast.Call):
                    self.assertNotIn(ast.unparse(node.func), ("sys.path.insert", "sys.path.append", "sys.path.extend"), path.name)
                if isinstance(node, ast.ImportFrom):
                    self.assertNotIn(node.module, ("rpc_collect", "backend_common", "investigation", "validate_bundle"))


if __name__ == "__main__":
    unittest.main()
