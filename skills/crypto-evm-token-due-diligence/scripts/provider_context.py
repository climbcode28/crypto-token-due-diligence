#!/usr/bin/env python3
"""Locate local guidance before provider selection; never read secrets or grant approval."""
import json
from pathlib import Path


def context_files():
    cwd = Path.cwd().resolve()
    roots = []
    # Run from the user's workspace before entering downloaded research checkouts.
    for candidate in (cwd, *cwd.parents):
        if (candidate / "AGENTS.md").is_file() or (candidate / ".git").exists():
            roots.append(candidate)
            break
    # Installed skill symlinks may point into a different canonical checkout. The skill may
    # live under <checkout>/skills/ or a project-level <checkout>/.claude/skills/.
    skill = Path(__file__).resolve().parents[1]
    if skill.parent.name == "skills":
        root = skill.parent.parent
        if root.name == ".claude":
            root = root.parent
        if (root / "AGENTS.md").is_file() and root not in roots:
            roots.append(root)
    paths = []
    for root in roots:
        # HANDOFF.local.md is the untracked, personal companion of docs/provider-setup.md (standing
        # authorizations for one machine); it never leaves the checkout through git.
        for name in ("AGENTS.md", "README.md", "docs/provider-setup.md", "HANDOFF.local.md"):
            path = root / name
            if path.is_file() and str(path) not in paths:
                paths.append(str(path))
    return paths


def _first_section(path, limit):
    try:
        text = Path(path).read_text(encoding="utf-8")
    except OSError:
        return None
    sections = text.split("\n## ")
    return text[:limit] if len(sections) < 2 else ("## " + sections[1])[:limit]


def policy_source(paths):
    """The file whose first second-level section is the current policy: a personal HANDOFF.local.md wins over the tracked docs/provider-setup.md."""
    for suffix in ("HANDOFF.local.md", "docs/provider-setup.md"):
        for path in paths:
            if path.endswith(suffix):
                return path
    return None


def policy_excerpt(paths, limit=6000):
    """Return the current-policy section (first second-level heading) of the trusted policy file.

    Paths only come from context_files(); the excerpt is prose to read, never credentials.
    """
    path = policy_source(paths)
    return _first_section(path, limit) if path else None


if __name__ == "__main__":
    import sys
    paths = context_files()
    result = {"context_files": paths, "network_requests": 0, "next_action": "read_trusted_local_context"}
    if "--policy" in sys.argv[1:]:
        source = policy_source(paths)
        excerpt = policy_excerpt(paths)
        result["policy_source"] = source
        print(json.dumps(result, sort_keys=True))
        label = "personal HANDOFF.local.md (untracked)" if source and source.endswith("HANDOFF.local.md") else "trusted docs/provider-setup.md"
        print("\n--- current provider policy (from " + label + "; read before any RPC attempt) ---\n")
        print(excerpt or "No docs/provider-setup.md found; standalone copy: use only this user's available configuration and permission.")
    else:
        print(json.dumps(result, sort_keys=True))
