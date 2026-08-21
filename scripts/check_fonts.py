#!/usr/bin/env python3
"""check_fonts.py — every character on the page must be in the shipped bundle.

    python3 scripts/check_fonts.py page.html [more.html ...]

Exit 0 when the bundle covers every CJK character the page uses, 1 when it does
not. Run it before shipping anything you expect someone else to reproduce.

Why this is a gate rather than a note: a character with no glyph in the bundle
does not fail. The browser silently substitutes a system font, and on the
machine that authored the page that system font is usually installed — so the
render looks correct to its author and wrong to everyone else, with different
metrics, different line breaks, and no error anywhere. The failure is invisible
exactly where it matters, which is the definition of something that belongs in
a gate.

Only stdlib. No pip install.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent


def is_cjk(cp: int) -> bool:
    return (0x4E00 <= cp <= 0x9FFF or 0x3400 <= cp <= 0x4DBF
            or 0x3000 <= cp <= 0x303F or 0xFF00 <= cp <= 0xFFEF
            or 0xF900 <= cp <= 0xFAFF)


def page_text(html: str) -> str:
    """Only what is actually drawn: element text and a few attributes. Scanning
    the raw file would flag every Chinese character in a code comment, and the
    resulting noise is how a gate gets switched off."""
    body = re.sub(r"<style[^>]*>.*?</style>", " ", html, flags=re.S | re.I)
    body = re.sub(r"<script[^>]*>.*?</script>", " ", body, flags=re.S | re.I)
    body = re.sub(r"<!--.*?-->", " ", body, flags=re.S)
    out = re.findall(r">([^<>]+)<", body)
    out += re.findall(r'aria-label="([^"]*)"', body)
    out += re.findall(r'<title>([^<]*)</title>', html, flags=re.I)
    return " ".join(out)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pages", nargs="+", type=Path)
    ap.add_argument("--charset", type=Path,
                    default=SKILL_ROOT / "assets/fonts/charset.txt")
    args = ap.parse_args()

    if not args.charset.exists():
        print(f"✗ no font bundle at {args.charset}\n"
              f"  The repo ships one. If it is missing, rebuild it:\n"
              f"    python3 scripts/fetch_fonts.py docs/gallery.json assets/template.html "
              f"--profile all --charset assets/fonts/charset.txt", file=sys.stderr)
        return 2
    covered = set(args.charset.read_text(encoding="utf-8"))

    bad = 0
    for p in args.pages:
        if not p.exists():
            print(f"✗ no such page: {p}", file=sys.stderr)
            bad += 1
            continue
        used = {ch for ch in page_text(p.read_text(encoding="utf-8")) if is_cjk(ord(ch))}
        missing = sorted(used - covered)
        if missing:
            bad += 1
            print(f"✗ {p}: {len(missing)} character(s) with no glyph in the bundle")
            print(f"    {''.join(missing)}")
        else:
            print(f"✓ {p}: {len(used)} CJK characters, all covered")

    if bad:
        print("\nExtend the bundle, then re-run:\n"
              "  python3 scripts/fetch_fonts.py <your page> --profile all \\\n"
              "      --charset assets/fonts/charset.txt", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
