#!/usr/bin/env python3
"""install.py — put this skill where your agent will find it.

    python3 scripts/install.py            # install into every agent found
    python3 scripts/install.py --link     # symlink instead of copy
    python3 scripts/install.py --list     # just show what was detected

You do not need this if you cloned straight into a skills directory, which is
the shortest path and what the README leads with. It exists for the case where
you have more than one agent installed, or cloned somewhere else first.

Copies by default rather than symlinking: a symlink into a clone you later move
or delete leaves the agent with a skill that half-exists, and the failure shows
up as strange behaviour rather than as a missing file. Use --link when you are
developing the skill itself and want edits to take effect everywhere at once.

Only stdlib. No pip install.
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NAME = "modernflow"
HOME = Path.home()

# Where each agent looks for skills. Only directories that already exist are
# offered — creating one for an agent that is not installed would leave dead
# folders around someone's home directory.
AGENTS = [
    ("Claude Code", HOME / ".claude/skills"),
    ("Codex", HOME / ".codex/skills"),
    ("Cursor", HOME / ".cursor/skills"),
    ("Gemini CLI", HOME / ".gemini/skills"),
    ("Crush", HOME / ".crush/skills"),
    ("OpenCode", HOME / ".config/opencode/skills"),
]

# Everything the skill needs at runtime. Build outputs are left behind.
KEEP = ["SKILL.md", "README.md", "LICENSE", "NOTICE",
        "assets", "reference", "scripts", "docs", "evals"]
SKIP_SUFFIX = (".built.html", ".pyc")


def copy_into(dest: Path, link: bool) -> None:
    if dest.is_symlink() or dest.exists():
        if dest.is_symlink() or dest.is_file():
            dest.unlink()
        else:
            shutil.rmtree(dest)
    if link:
        dest.symlink_to(ROOT, target_is_directory=True)
        return
    dest.mkdir(parents=True)
    for name in KEEP:
        src = ROOT / name
        if not src.exists():
            continue
        if src.is_dir():
            shutil.copytree(src, dest / name, ignore=shutil.ignore_patterns(
                "__pycache__", "*.pyc", "*.built.html", ".DS_Store"))
        else:
            shutil.copy2(src, dest / name)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--link", action="store_true", help="symlink instead of copy")
    ap.add_argument("--list", action="store_true", help="detect only, change nothing")
    ap.add_argument("--to", type=Path, help="install into this directory instead")
    a = ap.parse_args()

    targets = [("explicit", a.to)] if a.to else [
        (label, d) for label, d in AGENTS if d.exists()]

    if not targets:
        print("No agent skills directory found. Looked in:", file=sys.stderr)
        for label, d in AGENTS:
            print("  %-12s %s" % (label, d), file=sys.stderr)
        print("\nEither create one, or pass --to <dir>.", file=sys.stderr)
        return 1

    for label, d in targets:
        dest = d / NAME
        if a.list:
            print("  %-12s %s%s" % (label, dest, "  (present)" if dest.exists() else ""))
            continue
        d.mkdir(parents=True, exist_ok=True)
        copy_into(dest, a.link)
        print("  ✓ %-12s %s%s" % (label, dest, "  (symlink)" if a.link else ""))

    if not a.list:
        print("\nCheck it over:  python3 %s/scripts/doctor.py" % ROOT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
