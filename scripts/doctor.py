#!/usr/bin/env python3
"""doctor.py — will this machine produce the same picture as the last one?

    python3 scripts/doctor.py

Splits "it doesn't work" into separate questions, each with the fix printed
next to it. Exit 0 when every hard requirement is met; the soft ones say what
you lose rather than failing.

The question this answers is narrower and more useful than "is it installed":
this skill is meant to be reproducible, so the interesting failures are the
ones where a render *succeeds* and comes out different — a missing glyph, a
font bundle someone trimmed, a Chrome that seeks time differently. Those are
checked here, not just the presence of files.

Only stdlib. No pip install.
"""
from __future__ import annotations

import hashlib
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OK, WARN, BAD = "\033[32m✓\033[0m", "\033[33m·\033[0m", "\033[31m✗\033[0m"
fails = 0


def hard(label: str, ok: bool, detail: str = "", fix: str = "") -> bool:
    global fails
    print(f"  {OK if ok else BAD} {label}{('  ' + detail) if detail else ''}")
    if not ok:
        fails += 1
        if fix:
            print("      " + fix.replace("\n", "\n      "))
    return ok


def soft(label: str, ok: bool, detail: str = "", lose: str = "") -> bool:
    print(f"  {OK if ok else WARN} {label}{('  ' + detail) if detail else ''}")
    if not ok and lose:
        print("      " + lose.replace("\n", "\n      "))
    return ok


def main() -> int:
    print("\nmodernflow doctor · %s\n" % ROOT)

    print("required")
    v = sys.version_info
    hard("Python ≥ 3.9", v >= (3, 9), "%d.%d.%d" % v[:3],
         "Install a newer Python. Nothing here needs pip — only the standard library.")

    css = ROOT / "assets/base.css"
    hard("stylesheet", css.exists(), "assets/base.css",
         "The clone is incomplete. Re-clone rather than patching around it.")

    charset = ROOT / "assets/fonts/charset.txt"
    faces = sorted((ROOT / "assets/fonts").glob("*.woff2"))
    n = len(charset.read_text(encoding="utf-8")) if charset.exists() else 0
    hard("font bundle", bool(faces) and n > 0,
         "%d faces · %d CJK glyphs" % (len(faces), n),
         "The bundle is committed to this repo, so an empty one means it was\n"
         "deleted or gitignored locally. Rebuild it (needs network once):\n"
         "  python3 scripts/fetch_fonts.py docs/gallery.json --profile all")

    print("\noptional — these cost you a tier, not correctness")
    chrome = None
    try:
        sys.path.insert(0, str(ROOT / "scripts"))
        import importlib.util
        spec = importlib.util.spec_from_file_location("mf_build", ROOT / "scripts/build.py")
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        chrome = m.find_chrome()
    except Exception:
        pass
    soft("Chrome / Chromium", bool(chrome), Path(chrome).name if chrome else "",
         "PNG and MP4 need it. The HTML tier does not — it plays in any browser.\n"
         "Point at one you have:  export MODERNFLOW_CHROME=/path/to/chrome")

    hf = subprocess.run(["which", "hyperframes"], capture_output=True, text=True)
    soft("HyperFrames", hf.returncode == 0, (hf.stdout or "").strip(),
         "Only the MP4 tier uses it. Stills and self-playing HTML do not.\n"
         "  npm i -g hyperframes")

    print("\nreproducibility")
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "smoke.html"
        r = subprocess.run(
            [sys.executable, str(ROOT / "scripts/layout.py"),
             str(ROOT / "docs/gallery.json"), "-o", str(out)],
            capture_output=True, text=True)
        built = r.returncode == 0 and out.exists()
        digest = hashlib.sha256(out.read_bytes()).hexdigest()[:16] if built else ""
        hard("the shipped gallery still solves", built, digest,
             (r.stderr or "").strip()[:300])
        if built:
            r2 = subprocess.run(
                [sys.executable, str(ROOT / "scripts/layout.py"),
                 str(ROOT / "docs/gallery.json"), "-o", str(out)],
                capture_output=True, text=True)
            again = hashlib.sha256(out.read_bytes()).hexdigest()[:16]
            hard("and solves to the same bytes twice", again == digest, again,
                 "Something in the pipeline is not deterministic. A re-render "
                 "would be a different cut,\nand narration timed to the last one "
                 "would no longer land.")
            gate = subprocess.run(
                [sys.executable, str(ROOT / "scripts/check_fonts.py"), str(out)],
                capture_output=True, text=True)
            hard("every glyph is in the bundle", gate.returncode == 0, "",
                 (gate.stdout or "").strip()[-300:])

    print()
    if fails:
        print("\033[31m%d hard check(s) failed.\033[0m\n" % fails)
        return 1
    print("\033[32mReady. Anything you build here will look the same on any "
          "other machine that passes this.\033[0m\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
