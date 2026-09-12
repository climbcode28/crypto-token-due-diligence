#!/usr/bin/env python3
"""Copy the reviewed public-file allowlist into a fresh directory, with no Git history."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def relative(value):
    path = Path(value)
    if path.is_absolute() or not path.parts or '..' in path.parts:
        raise ValueError(f'Unsafe manifest path: {value}')
    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('destination', type=Path, help='New directory; existing paths are refused')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    manifest = json.loads((root / 'sharing/export-manifest.json').read_text())
    destination = args.destination.absolute()
    if destination.exists() or destination.is_symlink():
        parser.error('Destination must not already exist')
    entries = []
    seen = set()
    # Check everything before creating the export. Hashes freeze the reviewed file set.
    for row in manifest['files']:
        source = root / relative(row['source'])
        target = relative(row['destination'])
        if source.is_symlink() or not source.resolve().is_relative_to(root):
            parser.error(f'Source escapes checkout: {row["source"]}')
        if target.as_posix() in seen:
            parser.error(f'Duplicate output: {target}')
        seen.add(target.as_posix())
        if digest(source) != row['sha256']:
            parser.error(f'Changed since sharing review: {row["source"]}; review and refresh manifest')
        entries.append((source, target, row['sha256']))
    destination.mkdir(parents=True)
    for source, target, _ in entries:
        output = destination / target
        output.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, output)
    link = destination / '.agents/skills/crypto-evm-token-due-diligence'
    link.parent.mkdir(parents=True, exist_ok=True)
    link.symlink_to('../../skills/crypto-evm-token-due-diligence', target_is_directory=True)
    assert link.resolve() == destination.resolve() / 'skills/crypto-evm-token-due-diligence'
    (destination / 'FILES.sha256').write_text(''.join(
        f'{sha}  {target.as_posix()}\n' for _, target, sha in entries))
    print(f'Exported {len(entries)} files, one relative skill symlink and FILES.sha256 to {destination}')


if __name__ == '__main__':
    main()
