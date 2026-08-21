#!/usr/bin/env python3
"""build.py — turn a marker-bearing page into one self-contained file, and
optionally into a PNG.

    python3 scripts/build.py page.html                    # inline -> page.built.html
    python3 scripts/build.py page.html --png              # also render a PNG
    python3 scripts/build.py page.html -o out/final.html --png out/final.png

The page must contain two markers inside its <style> block:

    /* @FONTS@ */        replaced with assets/fonts/fonts.css   (if present)
    /* @BASE_CSS@ */     replaced with assets/base.css

Re-running is safe: previously injected blocks are replaced, not appended.

Why inline rather than <link>: fonts.css writes url() paths relative to the
HTML document. Under <link> the browser resolves them against the CSS file's
own directory instead, every face 404s, and the page silently falls back to a
system font — it still renders, so nothing looks broken until two machines
disagree. Inlining removes the whole class of failure, and makes the output a
single portable file.

PNG rendering needs a Chrome/Chromium binary. This script looks in the usual
places and tells you what to do if it finds none. Nothing else is required —
no Node, no build tool, no video framework.
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent

MARKERS = [
    ("/* @FONTS@ */", "/* @FONTS:BEGIN@ */", "/* @FONTS:END@ */", "assets/fonts/fonts.css", False),
    ("/* @BASE_CSS@ */", "/* @BASE:BEGIN@ */", "/* @BASE:END@ */", "assets/base.css", True),
]

# Ordered by how likely each is to be a real, headless-capable Chrome.
CHROME_CANDIDATES = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/usr/bin/google-chrome",
    "/usr/bin/chromium",
    "/usr/bin/chromium-browser",
    "C:/Program Files/Google/Chrome/Application/chrome.exe",
]
# Playwright and Puppeteer both cache a Chromium; so does the HyperFrames CLI.
CHROME_GLOBS = [
    (Path.home() / ".cache/ms-playwright", "**/chrome-*/chrome*"),
    (Path.home() / ".cache/puppeteer", "**/chrome*"),
    (Path.home() / ".cache/hyperframes/chrome", "**/chrome-headless-shell*"),
]

DEFAULT_VIEWPORT = (1920, 1080)
# Fonts, the blurred colour fields and the grain filter all need a beat to
# settle before the screenshot. Four seconds also lets a short entrance
# animation finish, so the PNG shows the resolved figure rather than a
# half-faded one.
#
# It is a virtual clock, not a wall clock: the frame is whatever the page looks
# like at that instant on its own timeline. Anything with a camera move or more
# than one scene needs the moment chosen rather than defaulted, because 4s may
# land mid-push or inside a seam. `--at` picks it; layout.py prints the resting
# time for the figure it just wrote.
SETTLE_MS = 4000


def find_chrome() -> str | None:
    if env := os.environ.get("MODERNFLOW_CHROME"):
        return env if Path(env).exists() else None
    for name in ("google-chrome", "chromium", "chrome"):
        if found := shutil.which(name):
            return found
    for path in CHROME_CANDIDATES:
        if Path(path).exists():
            return path
    for root, pattern in CHROME_GLOBS:
        if root.exists():
            for hit in sorted(root.glob(pattern)):
                if hit.is_file() and os.access(hit, os.X_OK):
                    return str(hit)
    return None


def inject(html: str, marker: str, begin: str, end: str, css: str) -> str:
    payload = f"{begin}\n{css.strip()}\n{end}"
    if begin in html and end in html:
        a, b = html.index(begin), html.index(end) + len(end)
        return html[:a] + payload + html[b:]
    if marker in html:
        return html.replace(marker, payload, 1)
    return html


def inline(page: Path, skill_root: Path) -> tuple[str, list[str]]:
    html = page.read_text(encoding="utf-8")
    notes: list[str] = []
    for marker, begin, end, rel, required in MARKERS:
        src = skill_root / rel
        if not src.exists():
            if required:
                raise FileNotFoundError(
                    f"{rel} is missing from the skill directory ({skill_root}). "
                    f"The page cannot be styled without it.")
            notes.append(f"no {rel} yet — run scripts/fetch_fonts.py first if the "
                         f"page uses Inter / Geist / Noto")
            continue
        if marker not in html and begin not in html:
            notes.append(f"page has no {marker} — skipping {rel}")
            continue
        html = inject(html, marker, begin, end, src.read_text(encoding="utf-8"))
    return html, notes


def render_png(chrome: str, html_path: Path, png_path: Path, size: tuple[int, int],
               at: float | None = None, settle_ms: int = SETTLE_MS) -> None:
    png_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        chrome, "--headless", "--disable-gpu", "--hide-scrollbars",
        "--force-device-scale-factor=1",
        f"--window-size={size[0]},{size[1]}",
        f"--screenshot={png_path}",
        f"--virtual-time-budget={settle_ms}",
        html_path.resolve().as_uri() + ("?t=%g" % at if at is not None else ""),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if not png_path.exists():
        raise RuntimeError(
            "Chrome ran but wrote no PNG.\n"
            f"  command: {' '.join(cmd[:3])} …\n"
            f"  stderr: {(proc.stderr or '').strip()[:400]}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("page", type=Path)
    ap.add_argument("-o", "--out", type=Path, help="default: <page>.built.html")
    ap.add_argument("--png", nargs="?", const=True, default=False,
                    help="render a PNG; optionally give the path")
    ap.add_argument("--size", default="1920x1080", help="viewport, e.g. 1080x1920")
    ap.add_argument("--at", type=float, default=SETTLE_MS / 1000.0,
                    help="moment on the page's own timeline to capture, in "
                         "seconds. Default 4. A page with a camera move or "
                         "more than one scene needs this chosen, not defaulted "
                         "— layout.py prints the resting time for its output.")
    ap.add_argument("--skill-root", type=Path, default=SKILL_ROOT)
    args = ap.parse_args()

    if not args.page.exists():
        print(f"✗ no such page: {args.page}", file=sys.stderr)
        return 1
    try:
        w, h = (int(v) for v in args.size.lower().split("x"))
    except ValueError:
        print(f"✗ --size must look like 1920x1080, got {args.size!r}", file=sys.stderr)
        return 1

    try:
        html, notes = inline(args.page, args.skill_root)
    except FileNotFoundError as e:
        print(f"✗ {e}", file=sys.stderr)
        return 2

    out = args.out or args.page.with_suffix(".built.html")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    for note in notes:
        print(f"  · {note}")
    print(f"✓ {out}  ({len(html)/1024:.1f}KB, self-contained)")

    if not args.png:
        return 0

    chrome = find_chrome()
    if not chrome:
        print("\n✗ no Chrome or Chromium found, so no PNG was rendered.\n"
              "  The HTML above is complete — open it in any browser and it plays.\n"
              "  For an automated PNG, install Chrome, or point at one you have:\n"
              "      export MODERNFLOW_CHROME=/path/to/chrome", file=sys.stderr)
        return 3

    png = Path(args.png) if isinstance(args.png, str) else out.with_suffix(".png")
    try:
        render_png(chrome, out, png, (w, h), args.at)
    except RuntimeError as e:
        print(f"✗ {e}", file=sys.stderr)
        return 4
    print(f"✓ {png}  ({png.stat().st_size/1024:.1f}KB, {w}x{h})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
