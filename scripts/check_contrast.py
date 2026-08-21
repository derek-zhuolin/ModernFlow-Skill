#!/usr/bin/env python3
"""check_contrast.py — WCAG AA gate for a diagram page.

    python3 scripts/check_contrast.py page.html
    python3 scripts/check_contrast.py page.html --scale 2 --json

Exit code 0 when every text colour clears AA against every background it can
sit on, 1 when something fails. Wire it into the build loop and do not skip it.

Why this exists: a pale grey label is the signature move of this design
register, and on a warm colour field it measures around 2:1. The page looks
finished and fails an accessibility review. Eyeballing does not catch it —
the failure is a ratio, so it has to be computed.

What gets checked: every CSS rule that declares a font (so, every text role),
against the paper colour and — for profiles with colour fields — against each
field at full strength composited over that paper. Backgrounds are taken as
worst case, because a headline may sit anywhere on the canvas.

Large-text allowance follows WCAG: 3.0:1 once the RENDERED size reaches 24px,
or 18.66px at weight 700+. Sizes in the page are viewBox units, so pass the
render scale (default 2 — these templates author at half the output size).

Only stdlib. No pip install.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent

AA_NORMAL = 4.5
AA_LARGE = 3.0
LARGE_PX = 24.0          # WCAG: 18pt
LARGE_PX_BOLD = 18.66    # WCAG: 14pt at weight >= 700


# ─────────────────────────────────────────────────────────── colour math ────

def parse_color(value: str) -> tuple[float, float, float, float] | None:
    """Return (r, g, b, alpha) in 0..255 / 0..1, or None if unparseable."""
    v = value.strip().lower()
    if m := re.fullmatch(r"#([0-9a-f]{3})", v):
        return (*(int(c * 2, 16) for c in m.group(1)), 1.0)
    if m := re.fullmatch(r"#([0-9a-f]{6})", v):
        h = m.group(1)
        return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), 1.0)
    if m := re.fullmatch(r"rgba?\(([^)]+)\)", v):
        parts = [p.strip() for p in m.group(1).replace("/", ",").split(",") if p.strip()]
        try:
            r, g, b = (float(p) for p in parts[:3])
        except ValueError:
            return None
        a = float(parts[3]) if len(parts) > 3 else 1.0
        return (r, g, b, a)
    if v == "white":
        return (255.0, 255.0, 255.0, 1.0)
    if v == "black":
        return (0.0, 0.0, 0.0, 1.0)
    return None


def over(fg: tuple[float, float, float, float],
         bg: tuple[float, float, float, float]) -> tuple[float, float, float, float]:
    """Composite fg onto an opaque bg."""
    a = fg[3]
    return (fg[0] * a + bg[0] * (1 - a),
            fg[1] * a + bg[1] * (1 - a),
            fg[2] * a + bg[2] * (1 - a), 1.0)


def luminance(c: tuple[float, float, float, float]) -> float:
    def ch(x: float) -> float:
        s = x / 255.0
        return s / 12.92 if s <= 0.04045 else ((s + 0.055) / 1.055) ** 2.4
    return 0.2126 * ch(c[0]) + 0.7152 * ch(c[1]) + 0.0722 * ch(c[2])


def ratio(a: tuple, b: tuple) -> float:
    la, lb = luminance(a), luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def darken_until_pass(fg: tuple, bg: tuple, need: float) -> str | None:
    """Walk the colour toward black until it clears `need`. Returns hex or None."""
    r, g, b, a = fg
    for step in range(1, 101):
        k = 1 - step / 100.0
        cand = over((r * k, g * k, b * k, a), bg)
        if ratio(cand, bg) >= need:
            return "#%02x%02x%02x" % (round(r * k), round(g * k), round(b * k))
    return None


# ──────────────────────────────────────────────────────────────── parsing ────

def load_tokens(profile: str) -> dict[str, str]:
    data = json.loads((SKILL_ROOT / "assets/tokens.json").read_text(encoding="utf-8"))
    prof = data["profiles"].get(profile)
    if not prof:
        raise KeyError(f"unknown profile {profile!r}; "
                       f"known: {', '.join(sorted(data['profiles']))}")
    return dict(prof["color"])


def resolve(value: str, tokens: dict[str, str], depth: int = 0):
    """Resolve var(--name) one hop at a time; give up rather than loop forever."""
    v = value.strip()
    if depth > 5:
        return None
    if m := re.fullmatch(r"var\(\s*--([\w-]+)\s*(?:,[^)]*)?\)", v):
        nxt = tokens.get(m.group(1))
        return resolve(nxt, tokens, depth + 1) if nxt else None
    return parse_color(v)


def css_blocks(html: str) -> list[tuple[str, str]]:
    """(selector, body) for every rule inside <style> tags."""
    out = []
    for style in re.findall(r"<style[^>]*>(.*?)</style>", html, re.S | re.I):
        # Comments go, except the @on: annotation — that one is data, not prose.
        style = re.sub(r"/\*(?!\s*@on:).*?\*/", "", style, flags=re.S)
        for sel, body in re.findall(r"([^{}]+)\{([^{}]*)\}", style):
            out.append((sel.strip(), body))
    return out


def decl(body: str, prop: str) -> str | None:
    m = re.search(rf"(?<![-\w]){re.escape(prop)}\s*:\s*([^;]+)", body)
    return m.group(1).strip() if m else None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("page", type=Path)
    ap.add_argument("--scale", type=float, default=2.0,
                    help="viewBox unit -> output px factor (default 2)")
    ap.add_argument("--profile", help="override the page's data-profile")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if not args.page.exists():
        print(f"✗ no such page: {args.page}", file=sys.stderr)
        return 2
    html = args.page.read_text(encoding="utf-8")

    # The page may not have been through build.py yet, in which case its
    # <style> still holds the marker instead of the stylesheet. Pull base.css
    # in directly so the gate works whichever order the caller runs things in.
    if "/* @BASE_CSS@ */" in html:
        base = SKILL_ROOT / "assets/base.css"
        if base.exists():
            html = html.replace("/* @BASE_CSS@ */", base.read_text(encoding="utf-8"), 1)

    profile = args.profile
    if not profile:
        # Look outside <style>: the token blocks are `[data-profile="…"] { }`
        # rules, and they come before the element that actually sets it, so
        # searching the whole document always answers with the first profile
        # base.css happens to define.
        markup = re.sub(r"<style[^>]*>.*?</style>", "", html, flags=re.S | re.I)
        m = re.search(r'data-profile\s*=\s*["\']([\w-]+)["\']', markup)
        profile = m.group(1) if m else "soft-gradient"
    try:
        tokens = load_tokens(profile)
    except (KeyError, OSError) as e:
        print(f"✗ {e}", file=sys.stderr)
        return 2

    paper = parse_color(tokens.get("paper", "#ffffff")) or (255.0, 255.0, 255.0, 1.0)
    backgrounds: list[tuple[str, tuple]] = [("paper", paper)]
    # Colour fields are worst-case backgrounds: any text may end up over one.
    for key, peak in (("glow-warm", 0.95), ("glow-cool", 0.80)):
        if key in tokens and (c := parse_color(tokens[key])):
            backgrounds.append((key, over((c[0], c[1], c[2], peak), paper)))

    rows, failures = [], 0
    for sel, body in css_blocks(html):
        fill = decl(body, "fill") or decl(body, "color")
        if not fill:
            continue
        # A rule is a text role when it also sizes or names a font.
        size_raw, family = decl(body, "font-size"), decl(body, "font-family")
        if not size_raw and not family:
            continue
        fg = resolve(fill, tokens)
        if not fg:
            continue

        size_px = float(m.group(1)) * args.scale if (m := re.match(r"([\d.]+)px", size_raw or "")) else 17.0 * args.scale
        weight_raw = decl(body, "font-weight") or "400"
        weight = int(wm.group(1)) if (wm := re.match(r"(\d+)", weight_raw)) else 400
        is_large = size_px >= LARGE_PX or (weight >= 700 and size_px >= LARGE_PX_BOLD)
        need = AA_LARGE if is_large else AA_NORMAL

        # A role that only ever sits on one known fill says so, and is checked
        # against that instead of the worst-case canvas. Without this the label
        # on the dark hub is measured against white paper, fails at 1.00:1, and
        # the only way to "fix" it is to make it unreadable where it actually
        # sits. The annotation is a claim the author has to be right about, so
        # keep it to fills the page really does guarantee.
        if (om := re.search(r"/\*\s*@on:\s*([\w-]+)\s*\*/", body)):
            tok = om.group(1)
            if (c := resolve("var(--%s)" % tok, tokens)):
                these = [(tok, over(c, paper))]
            else:
                print(f"✗ {sel}: @on:{tok} is not a token in {profile}", file=sys.stderr)
                return 2
        else:
            these = backgrounds

        for bg_name, bg in these:
            got = ratio(over(fg, bg), bg)
            ok = got >= need
            failures += 0 if ok else 1
            rows.append({"selector": sel, "on": bg_name, "ratio": round(got, 2),
                         "need": need, "px": round(size_px, 1), "weight": weight,
                         "pass": ok,
                         "suggest": None if ok else darken_until_pass(fg, bg, need)})

    if args.json:
        print(json.dumps({"profile": profile, "scale": args.scale,
                          "failures": failures, "checks": rows,
                          "empty": not rows},
                         ensure_ascii=False, indent=2))
        return 2 if not rows else (1 if failures else 0)

    if not rows:
        print("✗ nothing to check — no CSS rule in this page both sets a fill and\n"
              "  names or sizes a font, so no text role was found.\n"
              "  A gate with zero checks is not a pass. Likely causes:\n"
              "    · the stylesheet has not been inlined yet — run scripts/build.py\n"
              "    · the page styles text with presentation attributes instead of CSS",
              file=sys.stderr)
        return 2

    print(f"contrast · profile {profile} · scale {args.scale}x · "
          f"{len(rows)} checks against {len(backgrounds)} background(s)")
    for r in sorted(rows, key=lambda x: x["ratio"]):
        if r["pass"]:
            continue
        print(f"  ✗ {r['selector']:<28} on {r['on']:<10} {r['ratio']:>5.2f}:1 "
              f"(need {r['need']}, {r['px']:.0f}px/{r['weight']})"
              + (f"  → try {r['suggest']}" if r["suggest"] else "  → no darker value passes; change the background"))
    if failures:
        print(f"\n✗ {failures} failing pair(s). Darken the token, not the individual rule — "
              f"the whole set should stay one family.")
        return 1
    print(f"✓ all {len(rows)} pass WCAG AA")
    return 0


if __name__ == "__main__":
    sys.exit(main())
