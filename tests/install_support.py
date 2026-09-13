"""Build a distributable working-tree snapshot and install only into a test home."""
import os
from pathlib import Path
import shutil
import subprocess

REPO = Path(__file__).resolve().parents[1]


def export_package(destination):
    paths = subprocess.check_output(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"], cwd=REPO
    ).decode().split("\0")
    for name in dict.fromkeys(p for p in paths if p):
        src, dst = REPO / name, destination / name
        if not src.exists() and not src.is_symlink():
            continue  # A working-tree deletion must not reappear in the package.
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.is_symlink():
            dst.symlink_to(os.readlink(src))
        else:
            shutil.copy2(src, dst)
    return destination


def test_environment(test_home):
    # The isolated child process deliberately has its own home. The maintainer's
    # process environment, credentials and actual Personal registrations are untouched.
    return {"HOME": str(test_home), "PATH": os.defpath, "PYTHONDONTWRITEBYTECODE": "1",
            "LANG": "en_US.UTF-8"}


def install(package, test_home, mode="link"):
    args = ["/bin/sh", str(package / "install.sh")]
    if mode != "link":
        args.append("--" + mode)
    return subprocess.run(args, cwd=package, env=test_environment(test_home),
                          capture_output=True, text=True, check=True)
