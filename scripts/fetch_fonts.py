#!/usr/bin/env python3
"""fetch_fonts.py — download only the glyphs this diagram actually uses.

Why subset instead of linking Google Fonts directly: a rendered diagram must
look the same on every machine and with no network. Subsetting to the exact
characters in the file keeps that self-contained bundle small — a page with 300
Chinese characters lands around 300KB instead of the ~9MB a full CJK family
costs.

    python3 scripts/fetch_fonts.py page.html [more.html ...] \
        --profile soft-gradient --out assets/fonts

Writes `<out>/*.woff2` plus `<out>/fonts.css`.

IMPORTANT — the url() paths in fonts.css are relative to the *HTML document*,
not to fonts.css itself. Inline that CSS into the page (scripts/build.py does
this). Loading it with <link> makes the browser resolve url() against the CSS
file's own location, which silently 404s every face and falls back to a system
font — the page still renders, so the failure is invisible until you compare
two machines.

Only stdlib. No pip install.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

# Chrome UA is required: without it Google's CSS2 endpoint serves a TTF branch
# and no woff2 URLs come back at all.
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
CSS2 = "https://fonts.googleapis.com/css2"
HTTP_TIMEOUT = 30      # Google's font endpoint answers well inside 30s
MAX_RETRIES = 3        # transient DNS/TLS blips almost always clear by retry 2

# Latin side: ship all printable ASCII rather than subsetting it. It is 95
# characters and saves a couple of KB at most, while a missed punctuation mark
# costs a visible tofu box.
LATIN = "".join(chr(c) for c in range(0x20, 0x7F))

def families_for(profile: str):
    if profile == "all":
        seen, out = set(), []
        for fams in PROFILE_FAMILIES.values():
            for f in fams:
                key = (f[0], tuple(f[1]))
                if key not in seen:
                    seen.add(key)
                    out.append(f)
        return out
    return PROFILE_FAMILIES[profile]


PROFILE_FAMILIES = {
    "soft-gradient": [
        ("Inter", [500, 700, 900], "latin"),
        ("Noto Sans SC", [500, 700, 900], "cjk"),
    ],
    "editorial-paper": [
        ("Geist", [400, 500, 600], "latin"),
        ("Geist Mono", [400, 500], "latin"),
        ("Instrument Serif", [400], "latin"),
        ("Noto Sans SC", [400, 500, 600], "cjk"),
        ("Noto Serif SC", [400, 600], "cjk"),
    ],
}


def is_cjk(cp: int) -> bool:
    return (0x4E00 <= cp <= 0x9FFF or 0x3400 <= cp <= 0x4DBF
            or 0x3000 <= cp <= 0x303F or 0xFF00 <= cp <= 0xFFEF
            or 0xF900 <= cp <= 0xFAFF)


def collect_cjk(paths: list[Path]) -> str:
    """Every CJK character in the sources, deduped and sorted.

    Tags and comments are scanned too. Over-collecting costs a few hundred
    bytes; missing one character costs a tofu box in the render.
    """
    found: set[str] = set()
    for p in paths:
        try:
            text = p.read_text(encoding="utf-8")
        except OSError as e:
            print(f"  ! skipping {p}: {e}", file=sys.stderr)
            continue
        found.update(ch for ch in text if is_cjk(ord(ch)))
    return "".join(sorted(found))


def http_get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    last: Exception | None = None
    for attempt in range(MAX_RETRIES):
        try:
            with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as r:
                return r.read()
        except (urllib.error.URLError, TimeoutError) as e:
            last = e
    raise RuntimeError(f"could not fetch after {MAX_RETRIES} tries: {url}\n  {last}")


def parse_faces(css: str) -> list[dict]:
    """Split a Google CSS2 response into (weight, url, unicode-range) triples."""
    faces = []
    for block in css.split("@font-face")[1:]:
        weight = re.search(r"font-weight:\s*(\d+)", block)
        url = re.search(r"url\((https:[^)]+)\)", block)
        rng = re.search(r"unicode-range:\s*([^;]+);", block)
        if weight and url and rng:
            faces.append({"weight": weight.group(1), "url": url.group(1),
                          "range": rng.group(1).strip()})
    return faces


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("sources", nargs="+", type=Path, help="HTML/SVG files to scan")
    ap.add_argument("--profile", default="soft-gradient",
                    choices=sorted(PROFILE_FAMILIES) + ["all"],
                    help="'all' bundles both profiles — what the repo ships, so a "
                         "fresh clone renders either one with no network")
    ap.add_argument("--charset", type=Path,
                    help="extra characters to cover, one file of text. Unioned with "
                         "whatever the sources use, so the shipped bundle stays a "
                         "superset instead of shrinking to the last page built")
    ap.add_argument("--out", type=Path, default=Path("assets/fonts"))
    ap.add_argument("--href-prefix", default="assets/fonts",
                    help="path prefix written into url(), relative to the HTML document")
    args = ap.parse_args()

    sources = [p for p in args.sources if p.exists()]
    if not sources:
        print("✗ none of the given source files exist", file=sys.stderr)
        return 1

    cjk = set(collect_cjk(sources))
    if args.charset and args.charset.exists():
        cjk |= {ch for ch in args.charset.read_text(encoding="utf-8") if is_cjk(ord(ch))}
    cjk = "".join(sorted(cjk))
    args.out.mkdir(parents=True, exist_ok=True)
    print(f"scanning {len(sources)} file(s) · profile {args.profile} · "
          f"{len(cjk)} CJK + {len(LATIN)} latin characters")

    css_out = [
        "/* fonts.css — generated by scripts/fetch_fonts.py. Do not hand-edit.",
        f" * Character set: {len(cjk)} CJK + {len(LATIN)} latin. Re-run after any copy change.",
        " *",
        " * url() is relative to the HTML DOCUMENT, not to this file. Inline this",
        " * CSS into the page. A <link> makes the browser resolve url() against",
        " * this file's own directory, which 404s every face and silently falls",
        " * back to a system font.",
        " *",
        " * font-display is block, not swap: frame-by-frame capture would freeze",
        " * the fallback font into the opening frames of a render.",
        " */",
        "",
    ]

    total = 0
    for family, weights, side in families_for(args.profile):
        text = cjk if side == "cjk" else LATIN
        if not text:
            continue
        slug = family.lower().replace(" ", "-")
        query = urllib.parse.urlencode({
            "family": f"{family}:wght@{';'.join(str(w) for w in weights)}",
            "text": text, "display": "block",
        })
        try:
            faces = parse_faces(http_get(f"{CSS2}?{query}").decode("utf-8"))
        except RuntimeError as e:
            print(f"✗ {family}: {e}", file=sys.stderr)
            return 2
        if not faces:
            print(f"✗ {family}: no @font-face blocks in the response — "
                  f"check the family name spelling", file=sys.stderr)
            return 2

        for face in faces:
            data = http_get(face["url"])
            name = f"{slug}-{face['weight']}.woff2"
            (args.out / name).write_bytes(data)
            total += len(data)
            print(f"  {name}  {len(data)/1024:.1f}KB")
            css_out += [
                "@font-face {", f"  font-family: '{family}';",
                "  font-style: normal;", f"  font-weight: {face['weight']};",
                "  font-display: block;",
                f"  src: url({args.href_prefix}/{name}) format('woff2');",
                f"  unicode-range: {face['range']};", "}", "",
            ]

    (args.out / "fonts.css").write_text("\n".join(css_out), encoding="utf-8")
    # Record exactly what the bundle covers. Without this the only way to know
    # a character is missing is to look at the render and spot a tofu box, and
    # a fallback glyph that happens to exist locally looks fine on the machine
    # that built it and wrong on every other one. scripts/check_fonts.py gates
    # against this file.
    (args.out / "charset.txt").write_text(cjk, encoding="utf-8")
    print(f"{total/1024:.1f}KB total → {args.out}/fonts.css  ({len(cjk)} CJK covered)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
