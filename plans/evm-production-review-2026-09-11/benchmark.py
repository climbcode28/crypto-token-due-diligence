"""Offline same-fixture benchmark; pass skill roots. Never performs network requests."""
import argparse
import contextlib
import importlib.util
import io
import json
import pathlib
import statistics
import sys
import tempfile
import time
from unittest.mock import patch

parser = argparse.ArgumentParser()
parser.add_argument('skill', type=pathlib.Path)
parser.add_argument('--fixture-root', type=pathlib.Path, required=True)
parser.add_argument('--runs', type=int, default=7)
args = parser.parse_args()
sys.path[:0] = [str(args.skill / 'scripts'), str(args.fixture_root / 'tests')]
# Load the same current fixture under each engine, without its local sys.path override.
source = (args.fixture_root / 'tests/test_broad_collect.py').read_text()
source = source.replace('sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))', '')
fixture = {'__file__': str(args.fixture_root / 'tests/test_broad_collect.py'), '__name__': 'benchmark_fixture'}
exec(compile(source, fixture['__file__'], 'exec'), fixture)
from pipeline_note import write_and_compose
from scaffold import scaffold_note
from web_capture import capture
from investigation import Investigation
from test_pipeline_helpers import FakeOpener

runs = []
for _ in range(args.runs):
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        started = time.perf_counter()
        facts, rpc, status = fixture['BroadCollectTests']().run_pipeline(root)
        composed = write_and_compose(root)
        scaffolded = scaffold_note(root / 'draft', root / 'notes' / 'coordinator.json')
        assert not composed.get('errors'), composed
        elapsed = time.perf_counter() - started
        requests = sorted(json.dumps({'method': r['method'], 'params': r['params']}, sort_keys=True) for r in rpc.calls)
        with contextlib.closing(Investigation.create(root / 'web-session.sqlite', 20, 60)) as session:
            items = [{'id': str(i), 'url': 'https://synthetic.invalid/' + str(i)} for i in range(20)]
            opener = FakeOpener({i['url']: (b'{"synthetic":true}',) for i in items})
            started_web = time.perf_counter()
            with patch('web_capture.urllib.request.build_opener', return_value=opener):
                records = capture(items, root / 'captures', session=session)
            web_elapsed = time.perf_counter() - started_web
            assert len(opener.requests) == 20 and session.status()['started_attempts'] == 20
        runs.append({'pipeline_compose_scaffold_seconds': elapsed, 'rpc_requests': len(rpc.calls),
                     'charged_attempts': status['started_attempts'], 'normalized_requests': requests,
                     'web_twenty_captures_seconds': web_elapsed,
                     'pipeline_findings': len(composed.get('finding_ids', []))})
print(json.dumps({'skill': str(args.skill), 'runs': runs,
                  'median_pipeline_seconds': statistics.median(r['pipeline_compose_scaffold_seconds'] for r in runs),
                  'median_web_seconds': statistics.median(r['web_twenty_captures_seconds'] for r in runs)}, indent=2))
