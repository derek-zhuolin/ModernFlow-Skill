#!/usr/bin/env python3
"""playground.py — every scene of a spec on one scrubbable page.

    python3 scripts/playground.py docs/gallery.json -o docs/playground.html

Gate 7 of the build loop is "look at it", and looking at it one PNG at a time
is expensive enough that it quietly stops happening. This puts every figure in
the spec on a single self-contained page, each on its own timeline, with one
slider driving all of them — so a timing change or a token change is inspected
across the whole set in one glance instead of seven renders.

Scrubbing works by seeking the animations, not by waiting on a clock: every
animation is held paused and its currentTime set directly. The same mechanism
the published pages use for `?t=`, and the reason a frame is reproducible.

Fonts are embedded as data URIs from the bundle the repo ships, which covers
both profiles — so the file can be moved to any machine and still renders, and
so the profile toggle is honest rather than falling back to a system face on
one side.

No network needed: the bundle is committed. Only stdlib.
"""
from __future__ import annotations

import argparse
import base64
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent

_spec = importlib.util.spec_from_file_location("mf_layout", SKILL_ROOT / "scripts/layout.py")
L = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(L)


def fonts_inline(offline: bool) -> str:
    """The shipped bundle, with the faces embedded as data URIs.

    Reads what the repo ships rather than re-subsetting: running fetch_fonts
    here would overwrite the committed bundle with a subset of whatever page
    happened to be built last, and the next person to clone would get fonts
    trimmed to someone else's diagram. Extend the bundle deliberately, with
    fetch_fonts --charset, not as a side effect of building a page.
    """
    css = SKILL_ROOT / "assets/fonts/fonts.css"
    if not css.exists():
        if offline:
            return ""
        r = subprocess.run(
            [sys.executable, str(SKILL_ROOT / "scripts/fetch_fonts.py"),
             str(SKILL_ROOT / "assets/template.html"), "--profile", "all",
             "--out", str(SKILL_ROOT / "assets/fonts")],
            capture_output=True, text=True)
        if r.returncode != 0 or not css.exists():
            print("  · no font bundle and none could be fetched; the page will "
                  "fall back to system faces", file=sys.stderr)
            return ""
    parts, seen = [], set()
    for block in re.findall(r"@font-face\s*\{[^}]*\}", css.read_text()):
        m = re.search(r"url\(([^)]+)\)", block)
        if not m or m.group(1) in seen:
            continue
        seen.add(m.group(1))
        f = SKILL_ROOT / m.group(1)
        if not f.exists():
            continue
        uri = "data:font/woff2;base64," + base64.b64encode(f.read_bytes()).decode()
        parts.append(block.replace(m.group(1), uri))
    return "\n".join(parts)


SHELL = """<!doctype html>
<html lang="zh">
<head>
<meta charset="UTF-8" />
<title>@TITLE@</title>
<style>
@FONTS@
@BASE@

:root { --bg:#0b0b0c; --panel:#151517; --line:#2a2a2e; --fg:#e9e9ec; --dim:#8b8b93; --hi:#0071ec; }
* { box-sizing: border-box; }
html,body { margin:0; background:var(--bg); color:var(--fg);
  font:14px/1.5 ui-sans-serif,-apple-system,"PingFang SC",system-ui,sans-serif; }

.bar { position:sticky; top:0; z-index:10; display:flex; gap:18px; align-items:center;
  padding:14px 22px; background:rgba(11,11,12,.92); backdrop-filter:blur(12px);
  border-bottom:1px solid var(--line); }
.bar h1 { font-size:14px; font-weight:600; margin:0; letter-spacing:-.01em; }
.bar .sub { color:var(--dim); font-size:12px; }
.bar .grow { flex:1; }
button, .seg { background:var(--panel); color:var(--fg); border:1px solid var(--line);
  border-radius:7px; padding:6px 12px; font:inherit; font-size:12px; cursor:pointer; }
button:hover { border-color:#3d3d44; }
button[aria-pressed="true"] { background:var(--hi); border-color:var(--hi); color:#fff; }
input[type=range] { width:min(420px,34vw); accent-color:var(--hi); }
.t { font-variant-numeric:tabular-nums; color:var(--dim); font-size:12px; min-width:96px; }

.fams { display:flex; gap:8px; flex-wrap:wrap; padding:16px 22px 0; }
.fams button { font-size:12px; }
.grid { display:grid; gap:22px; padding:22px;
  grid-template-columns:repeat(auto-fill,minmax(520px,1fr)); }
.card { background:var(--panel); border:1px solid var(--line); border-radius:12px;
  overflow:hidden; }
.card.solo { grid-column:1/-1; }
.card header { display:flex; gap:10px; align-items:baseline; padding:11px 14px;
  border-bottom:1px solid var(--line); cursor:pointer; }
.card header b { font-size:13px; font-weight:600; }
.card header span { color:var(--dim); font-size:11.5px; letter-spacing:.02em; }
.card header .r { margin-left:auto; color:var(--dim); font-size:11.5px;
  font-variant-numeric:tabular-nums; }
.view { position:relative; width:100%; overflow:hidden; }
.view .mf-stage { position:absolute; top:0; left:0; transform-origin:0 0; }
.note { padding:6px 22px 26px; color:var(--dim); font-size:12px; }
kbd { background:var(--panel); border:1px solid var(--line); border-radius:4px;
  padding:1px 5px; font-size:11px; }
</style>
</head>
<body>
<div class="bar">
  <h1>@TITLE@</h1>
  <span class="sub">@SUB@</span>
  <button id="play" aria-pressed="false">▶ 播放</button>
  <input id="scrub" type="range" min="0" max="@MAX@" step="0.01" value="@MAX@" />
  <span class="t"><span id="now">0.00</span> / @MAX@s</span>
  <span class="grow"></span>
  <button id="prof" aria-pressed="false">editorial-paper</button>
  <button id="rest">跳到静止帧</button>
</div>
<div class="fams" id="fams">@FAMS@</div>
<div class="grid" id="grid">@CARDS@</div>
<p class="note">点卡片标题可以放大到整行。<kbd>空格</kbd> 播放/暂停，<kbd>←</kbd> <kbd>→</kbd> 逐 0.1s。
每张图各走各的时间线，滑杆同时驱动全部——所以对齐的不是内容，是节拍。</p>

<script>
const REST = @REST@;
const MAX = @MAX@;
const grid = document.getElementById("grid");
const scrub = document.getElementById("scrub");
const now = document.getElementById("now");
const play = document.getElementById("play");

/* Hold every animation paused and drive currentTime by hand. Playing by
   letting them run and scrubbing by seeking would be two mechanisms that
   disagree the moment one of them is a frame off. */
function seek(t) {
  document.getAnimations().forEach(a => { try { a.pause(); a.currentTime = t * 1000; } catch (e) {} });
  now.textContent = t.toFixed(2);
}
function set(t) { t = Math.max(0, Math.min(MAX, t)); scrub.value = t; seek(t); }

let raf = null, t0 = 0, base = 0;
function tick(ts) {
  if (!t0) t0 = ts;
  const t = base + (ts - t0) / 1000;
  if (t >= MAX) { set(MAX); stop(); return; }
  set(t);
  raf = requestAnimationFrame(tick);
}
function stop() { cancelAnimationFrame(raf); raf = null; t0 = 0; play.textContent = "▶ 播放";
  play.setAttribute("aria-pressed", "false"); }
play.onclick = () => {
  if (raf) return stop();
  base = parseFloat(scrub.value) >= MAX ? 0 : parseFloat(scrub.value);
  t0 = 0; play.textContent = "❚❚ 暂停"; play.setAttribute("aria-pressed", "true");
  raf = requestAnimationFrame(tick);
};
scrub.oninput = () => { stop(); seek(parseFloat(scrub.value)); };
document.getElementById("rest").onclick = () => { stop(); set(REST); };
document.getElementById("prof").onclick = e => {
  const on = e.target.getAttribute("aria-pressed") !== "true";
  e.target.setAttribute("aria-pressed", on);
  e.target.textContent = on ? "soft-gradient" : "editorial-paper";
  document.querySelectorAll(".mf-stage").forEach(s =>
    s.setAttribute("data-profile", on ? "editorial-paper" : "soft-gradient"));
  seek(parseFloat(scrub.value));
};
document.querySelectorAll("#fams button").forEach(btn => btn.onclick = () => {
  const f = btn.dataset.fam;
  document.querySelectorAll("#fams button").forEach(b2 =>
    b2.setAttribute("aria-pressed", b2 === btn));
  grid.querySelectorAll(".card").forEach(c =>
    c.style.display = (f === "*" || c.dataset.fam === f) ? "" : "none");
  fit();
});
grid.querySelectorAll(".card header").forEach(h =>
  h.onclick = () => { h.parentElement.classList.toggle("solo"); fit(); });
addEventListener("keydown", e => {
  if (e.code === "Space") { e.preventDefault(); play.click(); }
  if (e.code === "ArrowLeft") { stop(); set(parseFloat(scrub.value) - 0.1); }
  if (e.code === "ArrowRight") { stop(); set(parseFloat(scrub.value) + 0.1); }
});

/* The stage is authored at its real pixel size; the card scales it down. Doing
   this in JS rather than CSS because the factor depends on the column width,
   which changes with the viewport and when a card goes solo. */
function fit() {
  grid.querySelectorAll(".view").forEach(v => {
    const st = v.querySelector(".mf-stage");
    const k = v.clientWidth / parseFloat(st.dataset.w);
    st.style.transform = "scale(" + k + ")";
    v.style.height = (parseFloat(st.dataset.h) * k) + "px";
  });
}
addEventListener("resize", fit);
document.fonts.ready.then(() => { fit(); set(REST); });
fit(); set(REST);
</script>
</body>
</html>
"""


def main() -> int:
    ap = argparse.ArgumentParser(description="every scene of a spec on one scrubbable page")
    ap.add_argument("spec", type=Path)
    ap.add_argument("-o", "--out", type=Path, default=Path("playground.html"))
    ap.add_argument("--rate", type=float)
    ap.add_argument("--no-fonts", action="store_true", help="do not embed any faces")
    ap.add_argument("--offline", action="store_true",
                    help="never reach the network, even if the bundle is missing")
    a = ap.parse_args()

    spec = json.loads(a.spec.read_text())
    canvas = spec.get("canvas", "landscape")
    rate = a.rate if a.rate is not None else float(spec.get("rate", 1.0))
    scenes = spec.get("scenes") or [spec]

    seed = str(spec.get("seed", spec.get("title", "")))
    try:
        builds = [L.build_scene(s, canvas, rate, i, seed) for i, s in enumerate(scenes)]
    except L.SpecError as e:
        print("spec error: %s" % e, file=sys.stderr)
        return 1
    # Each card runs on its own clock, so there are no seams — but the headline
    # entrance still has to vary, or forty cards share one gesture.
    ents, _ = L.plan_variation(spec, builds)
    for b, e in zip(builds, ents):
        b["enter"] = e

    vb = L.CANVAS[canvas]["vb"]
    stage = L.CANVAS[canvas]["stage"]
    cards = []
    for b in builds:
        frag = L.fragment(spec, b, rate)
        frag = frag.replace('<div class="mf-stage"',
                            '<div class="mf-stage" data-w="%d" data-h="%d" '
                            'style="width:%dpx;height:%dpx"' % (stage * 2), 1)
        sc = b["scene"]
        cam = {0: "—"}.get(len(b["moves"]),
                           "推 ×%d · %s" % (len(b["moves"]),
                                            "/".join(L.n(m["zoom"]) + "×" for m in b["moves"])))
        cards.append(
            '<section class="card" data-fam="%s" data-end="%s">\n'
            '  <header><b>%s</b><span>%s</span>'
            '<span class="r">%d 节点 · %ss · 相机 %s</span></header>\n'
            '  <div class="view">%s</div>\n</section>'
            % (b["family"], b["settle"], sc.get("id", b["type"]), b["family"],
               len(b["nodes"]), L.n(b["end"]), cam, frag))

    fams = []
    for b in builds:
        if b["family"] not in fams:
            fams.append(b["family"])
    fam_html = ('<button data-fam="*" aria-pressed="true">全部 %d</button>' % len(builds)) + "".join(
        '<button data-fam="%s">%s %d</button>'
        % (f, f, sum(1 for b in builds if b["family"] == f)) for f in fams)

    mx = max(b["end"] for b in builds)
    rest = max(b["settle"] for b in builds) + 0.12

    fonts = "" if a.no_fonts else fonts_inline(a.offline)

    html = (SHELL
            .replace("@BASE@", (SKILL_ROOT / "assets/base.css").read_text())
            .replace("@FONTS@", fonts)
            .replace("@TITLE@", L.esc(spec.get("title", "modernflow playground")))
            .replace("@SUB@", "%d 场 · %s · rate %s" % (len(builds), canvas, L.n(rate)))
            .replace("@CARDS@", "\n".join(cards))
            .replace("@FAMS@", fam_html)
            .replace("@MAX@", L.n(round(mx, 2)))
            .replace("@REST@", L.n(round(rest, 2))))

    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(html)
    print("%s  (%.0fKB, self-contained)  %d scenes  max %ss" %
          (a.out, len(html) / 1024, len(builds), L.n(round(mx, 2))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
