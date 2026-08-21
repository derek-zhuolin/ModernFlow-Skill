#!/usr/bin/env python3
"""layout.py — turn a semantic spec into a modernflow figure.

    python3 scripts/layout.py spec.json -o figure.html
    python3 scripts/layout.py spec.json --split -o out/      # one file per scene
    python3 scripts/layout.py spec.json --json               # geometry + beats only
    python3 scripts/layout.py spec.json --rate 1.3           # narration at 1.3x

Nothing in a spec is a coordinate. The spec says what the figure *means* — the
nodes, what connects to what, which one is the point — and this computes where
everything goes and when it arrives. Change a label, add a node, swap the
canvas to portrait, and the whole layout re-solves. A hand-placed figure
silently stops being correct the moment its content changes; a solved one
cannot.

The same applies to time. `--rate` compresses every gap in the beat table
without touching element durations, because durations have a floor (under
~300ms an entrance reads as a pop, not a move) while gaps do not. Narrating at
1.3x and leaving the picture at 1.0x is the single most common way one of these
goes out of sync.

Gates run before anything is written: budget, dangling edges, unlabelled
branches out of a decision. A spec that violates them is an error, not a
warning — the figure would render fine and be wrong.

Only stdlib. No pip install.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
import zlib
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent

# ───────────────────────────────────────────────────────────────── canvas ──

CANVAS = {
    "landscape": dict(vb=(960, 540), stage=(1920, 1080)),
    "portrait":  dict(vb=(540, 960), stage=(1080, 1920)),
    "square":    dict(vb=(720, 720), stage=(1080, 1080)),
}

# Margins carve the figure box out of the canvas: chrome sits above and below.
CHROME = {
    "landscape": dict(l=60, r=60, t=170, b=120),
    "portrait":  dict(l=44, r=44, t=210, b=180),
    "square":    dict(l=56, r=56, t=180, b=150),
}

# ──────────────────────────────────────────────────────────────── families ──
# 41 named types, 7 layout engines. A type is a *reading contract* — what the
# reader is meant to conclude — laid on top of a geometry. Adding a type is
# usually a row here plus a paragraph in reference/diagram-types.md, not new
# geometry code.

FAMILY = {
    # chain — an ordered path along one axis, with optional side lanes
    "flow": "chain", "flowchart": "chain", "steps": "chain", "pipeline": "chain",
    "sequence": "chain", "timeline": "chain", "journey": "chain",
    "state-machine": "chain", "data-flow": "chain",
    # radial — stations on an ellipse, optional hub at the centre
    "loop": "radial", "cycle": "radial", "wheel": "radial", "orbit": "radial",
    "radar": "radial",
    # stack — full-width bands, one resting on the next
    "layers": "stack", "pyramid": "stack", "funnel": "stack",
    "medallion": "stack", "tiers": "stack",
    # tree — levels, children spread under their parent
    "tree": "tree", "org": "tree", "breakdown": "tree", "mindmap": "tree",
    "taxonomy": "tree", "decision-tree": "tree",
    # grid — r×c cells, position carries meaning or just tabulates
    "matrix": "grid", "quadrant": "grid", "comparison": "grid", "bento": "grid",
    "table": "grid", "spec-rows": "grid", "swimlane": "grid", "gantt": "grid",
    "er": "grid",
    # field — position is a claim about the node, not about the order
    "venn": "field", "network": "field", "cluster": "field", "scatter": "field",
    "treemap": "field",
    # row — one line, stated big; a headline that happens to be a figure
    "equation": "row", "stat-row": "row", "kpi": "row",
}

# Which types default to a hub, a taper, axes, and so on.
TYPE_DEFAULTS = {
    "loop": dict(hub=True), "cycle": dict(hub=True), "wheel": dict(hub=True),
    "orbit": dict(hub=True), "radar": dict(hub=False),
    "pyramid": dict(taper="up"), "funnel": dict(taper="down"),
    "quadrant": dict(axes=True), "matrix": dict(axes=True),
    "scatter": dict(axes=True),
    "timeline": dict(rail=True), "gantt": dict(rail=True),
}

SHAPE = {
    "start": "stadium", "end": "stadium", "terminal": "stadium",
    "step": "rect", "thing": "rect", "node": "rect",
    "decision": "diamond", "branch": "diamond",
    "hub": "store", "store": "store", "state": "store",
    "exit": "ghost", "ghost": "ghost", "dead": "ghost", "external": "ghost",
    "set": "set",
}

# ────────────────────────────────────────────────────────────────── helpers ──

def q(v: float) -> float:
    """Snap to the 4px grid. Node boxes only — snapping an arc endpoint breaks
    the tangency the arrowhead angle is derived from."""
    return round(v / 4.0) * 4.0

def n(v: float) -> str:
    return ("%.1f" % v).rstrip("0").rstrip(".")

def sgn(v: float) -> int:
    return 1 if v > 0 else (-1 if v < 0 else 0)

def center(b):
    return b["x"] + b["w"] / 2.0, b["y"] + b["h"] / 2.0

def anchor(b, side):
    x, y, w, h = b["x"], b["y"], b["w"], b["h"]
    return {"l": (x, y + h / 2), "r": (x + w, y + h / 2),
            "t": (x + w / 2, y), "b": (x + w / 2, y + h)}[side]

def esc(s) -> str:
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;"))

def text_w(label: str, size: float) -> float:
    """Rough advance width. CJK is full-width, latin averages ~0.56em. Used only
    to size a box around its own label, which is the one place a fixed width is
    a bug: a 150-unit box around a 22-character label overflows silently."""
    w = 0.0
    for ch in str(label):
        w += size * (1.0 if ord(ch) > 0x2E7F else 0.56)
    return w

# ────────────────────────────────────────────────────────────────── routing ──

def elbow(s, e, first: str, r: float = 12.0) -> str:
    sx, sy = s
    ex, ey = e
    if first == "h":
        r = min(r, abs(ex - sx), abs(ey - sy))
        cx = ex - r * sgn(ex - sx)
        cy = sy + r * sgn(ey - sy)
        return "M %s %s L %s %s Q %s %s %s %s L %s %s" % (
            n(sx), n(sy), n(cx), n(sy), n(ex), n(sy), n(ex), n(cy), n(ex), n(ey))
    r = min(r, abs(ex - sx), abs(ey - sy))
    cy = ey - r * sgn(ey - sy)
    cx = sx + r * sgn(ex - sx)
    return "M %s %s L %s %s Q %s %s %s %s L %s %s" % (
        n(sx), n(sy), n(sx), n(cy), n(sx), n(ey), n(cx), n(ey), n(ex), n(ey))

def route(a, b, gap: float = 4.0, prefer: str | None = None):
    """Edge from box a to box b. Endpoints come off the boxes, never from a
    fixed offset — that is the single geometry rule that breaks most often when
    a label grows and its box with it."""
    acx, acy = center(a)
    bcx, bcy = center(b)
    dx, dy = bcx - acx, bcy - acy

    if abs(dy) < 3 and abs(dx) > 3:                      # same row
        s = anchor(a, "r" if dx > 0 else "l")
        e = anchor(b, "l" if dx > 0 else "r")
        tip = e
        e = (e[0] - gap * sgn(dx), e[1])
        return "M %s %s L %s %s" % (n(s[0]), n(s[1]), n(e[0]), n(e[1])), \
               (tip[0], tip[1], 0.0 if dx > 0 else 180.0)

    if abs(dx) < 3 and abs(dy) > 3:                      # same column
        s = anchor(a, "b" if dy > 0 else "t")
        e = anchor(b, "t" if dy > 0 else "b")
        tip = e
        e = (e[0], e[1] - gap * sgn(dy))
        return "M %s %s L %s %s" % (n(s[0]), n(s[1]), n(e[0]), n(e[1])), \
               (tip[0], tip[1], 90.0 if dy > 0 else -90.0)

    horiz = abs(dx) >= abs(dy) if prefer is None else (prefer == "h")
    if horiz:
        s = anchor(a, "r" if dx > 0 else "l")
        e = anchor(b, "t" if dy > 0 else "b")
        tip = e
        e = (e[0], e[1] - gap * sgn(dy))
        return elbow(s, e, "h"), (tip[0], tip[1], 90.0 if dy > 0 else -90.0)
    s = anchor(a, "b" if dy > 0 else "t")
    e = anchor(b, "l" if dx > 0 else "r")
    tip = e
    e = (e[0] - gap * sgn(dx), e[1])
    return elbow(s, e, "v"), (tip[0], tip[1], 0.0 if dx > 0 else 180.0)

# ──────────────────────────────────────────────────────────── layout engines ──

def box_for(node, size, pad_x=28.0, min_w=110.0, min_h=46.0):
    shape = node["shape"]
    w = max(min_w, q(text_w(node["label"], size) + pad_x * 2))
    h = min_h
    if node.get("sub"):
        h = max(h, 46.0)
    if shape == "diamond":
        w = max(w + 40, 170.0)
        h = 80.0
    return w, h

def lay_chain(scene, nodes, box, vertical):
    spine = [x for x in nodes if not x.get("lane")]
    lanes = [x for x in nodes if x.get("lane")]
    for x in nodes:
        x["w"], x["h"] = box_for(x, 17.0)

    if vertical:
        sx = box["x"] + box["w"] * 0.38
        total = sum(x["h"] for x in spine)
        gap = max(34.0, (box["h"] - total) / max(1, len(spine) - 1)) if len(spine) > 1 else 0
        gap = min(gap, 92.0)
        y = box["y"] + max(0.0, (box["h"] - (total + gap * (len(spine) - 1))) / 2.0)
        for x in spine:
            x["x"], x["y"] = q(sx - x["w"] / 2), q(y)
            y += x["h"] + gap
        lane_x = box["x"] + box["w"] * 0.84
        for x in lanes:
            src = next((s for s in spine if s["id"] == x.get("from")), spine[0])
            x["x"] = q(min(lane_x - x["w"] / 2, box["x"] + box["w"] - x["w"]))
            x["y"] = q(center(src)[1] - x["h"] / 2 + (x["lane"] * 0))
    else:
        total = sum(x["w"] for x in spine)
        gap = max(38.0, (box["w"] - total) / max(1, len(spine) - 1)) if len(spine) > 1 else 0
        gap = min(gap, 96.0)
        x0 = box["x"] + max(0.0, (box["w"] - (total + gap * (len(spine) - 1))) / 2.0)
        cy = box["y"] + box["h"] * 0.58
        for x in spine:
            x["x"], x["y"] = q(x0), q(cy - x["h"] / 2)
            x0 += x["w"] + gap
        for x in lanes:
            src = next((s for s in spine if s["id"] == x.get("from")), spine[0])
            x["x"] = q(center(src)[0] - x["w"] / 2)
            # dead ends go ABOVE the spine so the eye reads the spine unbroken
            x["y"] = q(box["y"] + (0 if x["lane"] < 0 else box["h"] - x["h"]))
            if x["lane"] < 0:
                x["y"] = q(box["y"])

def lay_radial(scene, nodes, box, opts):
    stations = [x for x in nodes if x["shape"] != "store"]
    hubs = [x for x in nodes if x["shape"] == "store"]
    cx, cy = box["x"] + box["w"] / 2, box["y"] + box["h"] / 2
    for x in nodes:
        x["w"], x["h"] = box_for(x, 16.0, pad_x=20.0, min_w=118.0)
    k = len(stations)
    # Portrait wants a tall ellipse; carrying a landscape ratio into portrait
    # leaves the bottom third empty. Derive from the box, do not hardcode.
    # 22, not 6: the accent ring is drawn 18 units outside its card, so a
    # radius that only clears the card clips the ring against the margin.
    rx = box["w"] / 2 - max(x["w"] for x in stations) / 2 - 22
    ry = box["h"] / 2 - max(x["h"] for x in stations) / 2 - 22
    # A landscape figure box is much wider than it is tall, and letting the
    # ellipse take all of it gives a 4:1 oval that no longer reads as a cycle —
    # the stations at the ends look like the ends of a line. Cap the aspect and
    # give the width back to the margins.
    rx = min(rx, ry * 2.2)
    ry = min(ry, rx * 2.2)
    for i, x in enumerate(stations):
        th = math.radians(-90 + i * 360.0 / k)
        x["theta"] = th
        x["x"] = q(cx + rx * math.cos(th) - x["w"] / 2)
        x["y"] = q(cy + ry * math.sin(th) - x["h"] / 2)
    for h in hubs:
        h["w"] = max(h["w"], 132.0)
        h["x"], h["y"] = q(cx - h["w"] / 2), q(cy - h["h"] / 2)
    scene["_ellipse"] = (cx, cy, rx, ry)

def arc_between(a, b, ell):
    """Arc hugging the ellipse from card a to card b. The angle is solved for
    where the ellipse actually crosses each card's boundary — a fixed angular
    gap looks right on a circle with small cards and hangs 70 units off the
    cards on a tall ellipse with wide ones."""
    cx, cy, rx, ry = ell
    def exit_angle(card, th, forward):
        cands = []
        for edge, val, fn in (("b", card["y"] + card["h"], "sin"),
                              ("t", card["y"], "sin"),
                              ("r", card["x"] + card["w"], "cos"),
                              ("l", card["x"], "cos")):
            if fn == "sin":
                s = (val - cy) / ry
                if -1 <= s <= 1:
                    for cand in (math.asin(s), math.pi - math.asin(s)):
                        cands.append(cand)
            else:
                c = (val - cx) / rx
                if -1 <= c <= 1:
                    for cand in (math.acos(c), -math.acos(c)):
                        cands.append(cand)
        best, bestd = th, 9e9
        for cand in cands:
            d = (cand - th) % (2 * math.pi)
            if not forward:
                d = (th - cand) % (2 * math.pi)
            if 0.02 < d < bestd:
                px = cx + rx * math.cos(cand)
                py = cy + ry * math.sin(cand)
                if (card["x"] - 2 <= px <= card["x"] + card["w"] + 2 and
                        card["y"] - 2 <= py <= card["y"] + card["h"] + 2):
                    best, bestd = cand, d
        return best
    ta = exit_angle(a, a["theta"], True)
    tb = exit_angle(b, b["theta"], False)
    ax, ay = cx + rx * math.cos(ta), cy + ry * math.sin(ta)
    bx, by = cx + rx * math.cos(tb), cy + ry * math.sin(tb)
    d = "M %s %s A %s %s 0 0 1 %s %s" % (n(ax), n(ay), n(rx), n(ry), n(bx), n(by))
    rot = math.degrees(math.atan2(ry * math.cos(tb), -rx * math.sin(tb)))
    return d, (bx, by, rot)

def lay_stack(scene, nodes, box, opts):
    taper = opts.get("taper")
    k = len(nodes)
    gap = 14.0
    h = min(78.0, (box["h"] - gap * (k - 1)) / k)
    y = box["y"] + (box["h"] - (h * k + gap * (k - 1))) / 2
    for i, x in enumerate(nodes):
        f = 1.0
        if taper == "up":
            f = 0.40 + 0.60 * (i + 1) / k
        elif taper == "down":
            f = 1.0 - 0.55 * i / max(1, k - 1)
        x["w"], x["h"] = q(box["w"] * f), q(h)
        x["x"] = q(box["x"] + (box["w"] - x["w"]) / 2)
        x["y"] = q(y)
        y += h + gap

def lay_tree(scene, nodes, box, opts):
    """Children sit under their own parent. Spreading each level evenly across
    the canvas is the tempting shortcut and it silently re-parents the figure:
    a leaf drawn under the wrong branch says something false about the subject,
    and the arrow pointing at it from elsewhere reads as a mistake rather than
    as the claim it is."""
    byid = {x["id"]: x for x in nodes}
    kids = {x["id"]: [] for x in nodes}
    parent = {}
    for e in scene.get("edges", []):
        if e["from"] in kids and e["to"] in byid and e["to"] not in parent:
            kids[e["from"]].append(e["to"])
            parent[e["to"]] = e["from"]
    for x in nodes:
        if x.get("parent") and x["parent"] in kids and x["id"] not in parent:
            kids[x["parent"]].append(x["id"])
            parent[x["id"]] = x["parent"]
    roots = [x["id"] for x in nodes if x["id"] not in parent]

    for x in nodes:
        x["w"], x["h"] = box_for(x, 16.0, pad_x=20.0, min_w=104.0)

    depth = {}
    def dive(i, d):
        depth[i] = d
        for c in kids[i]:
            dive(c, d + 1)
    for rid in roots:
        dive(rid, 0)
    for x in nodes:                       # explicit level wins, if given
        if "level" in x:
            depth[x["id"]] = int(x["level"])

    levels = max(depth.values()) + 1 if depth else 1
    vgap = min(150.0, (box["h"] - 46.0) / max(1, levels - 1)) if levels > 1 else 0

    slot = [box["x"]]
    gap = 24.0
    def place(i):
        x = byid[i]
        if kids[i]:
            for c in kids[i]:
                place(c)
            first, last = byid[kids[i][0]], byid[kids[i][-1]]
            cx = (first["x"] + first["w"] / 2 + last["x"] + last["w"] / 2) / 2
            x["x"] = q(cx - x["w"] / 2)
        else:
            x["x"] = q(slot[0])
            slot[0] += x["w"] + gap
        x["y"] = q(box["y"] + depth[i] * vgap)
    for rid in roots:
        place(rid)
        slot[0] += gap

    # Centre the whole thing: the leaf walk lays out from the left margin, so a
    # narrow tree ends up hugging the left edge of a wide canvas.
    xs = [x["x"] for x in nodes]
    xe = [x["x"] + x["w"] for x in nodes]
    shift = q(box["x"] + (box["w"] - (max(xe) - min(xs))) / 2 - min(xs))
    for x in nodes:
        x["x"] = q(x["x"] + shift)
    scene["_tree"] = True

def tree_edge(a, b, gap=4.0):
    """Parent bottom, down to the midline, across, down into the child's top.
    An elbow that arrives at the child's side reads as a cross-link, not as
    descent, and in a figure whose whole claim is containment that is the one
    thing the geometry must not say."""
    sx, sy = anchor(a, "b")
    ex, ey = anchor(b, "t")
    my = (sy + ey) / 2
    if abs(ex - sx) < 3:
        return ("M %s %s L %s %s" % (n(sx), n(sy), n(ex), n(ey - gap)),
                (ex, ey, 90.0))
    r = min(12.0, abs(ex - sx) / 2, abs(my - sy), abs(ey - my))
    d = ("M %s %s L %s %s Q %s %s %s %s L %s %s Q %s %s %s %s L %s %s"
         % (n(sx), n(sy), n(sx), n(my - r),
            n(sx), n(my), n(sx + r * sgn(ex - sx)), n(my),
            n(ex - r * sgn(ex - sx)), n(my),
            n(ex), n(my), n(ex), n(my + r),
            n(ex), n(ey - gap)))
    return d, (ex, ey, 90.0)

def lay_grid(scene, nodes, box, opts):
    cols = int(opts.get("cols") or scene.get("cols") or
               max(1, math.ceil(math.sqrt(len(nodes)))))
    rows = math.ceil(len(nodes) / cols)
    gx, gy = 16.0, 16.0
    cw = (box["w"] - gx * (cols - 1)) / cols
    ch = min(box["h"] / rows - gy, 128.0)
    # Walk a cursor instead of divmod: a span-2 cell has to consume two columns.
    # Indexing by position alone widens the cell and leaves the next one sitting
    # on top of it — which still renders, and reads as a z-index bug rather than
    # as the layout error it is.
    placed = [x for x in nodes if "pos" not in x]
    rows = 0
    c = 0
    for x in placed:
        span = min(cols, int(x.get("span", 1)))
        if c + span > cols:
            rows += 1
            c = 0
        x["_cell"] = (rows, c, span)
        c += span
        if c >= cols:
            rows += 1
            c = 0
    rows = max(1, rows + (1 if c else 0))
    ch = min(box["h"] / rows - gy, 128.0)
    y = box["y"] + (box["h"] - (ch * rows + gy * (rows - 1))) / 2
    for x in nodes:
        if "pos" in x:                       # matrix / quadrant: position IS the claim
            px, py = x["pos"]
            x["w"], x["h"] = box_for(x, 15.0, pad_x=16.0, min_w=96.0)
            x["x"] = q(box["x"] + px * (box["w"] - x["w"]))
            x["y"] = q(box["y"] + (1 - py) * (box["h"] - x["h"]))
            continue
        r, c, span = x["_cell"]
        x["w"] = q(cw * span + gx * (span - 1))
        x["h"] = q(ch)
        x["x"] = q(box["x"] + c * (cw + gx))
        x["y"] = q(y + r * (ch + gy))

def convex_hull(pts):
    """Andrew's monotone chain. A bounding box round each group would be easier
    and would claim a rectangular region the data does not occupy — with two
    groups near each other the boxes overlap where the points do not, and the
    figure says they mix when they do not."""
    pts = sorted(set(pts))
    if len(pts) <= 2:
        return pts
    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lower = []
    for pt in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], pt) <= 0:
            lower.pop()
        lower.append(pt)
    upper = []
    for pt in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], pt) <= 0:
            upper.pop()
        upper.append(pt)
    return lower[:-1] + upper[:-1]


def rounded_poly(pts, r=22.0):
    """A hull with hard corners reads as a container someone drew; rounded, it
    reads as a region the points imply."""
    k = len(pts)
    if k < 3:
        return ""
    a, b = [], []
    for i in range(k):
        p0, p1, p2 = pts[i - 1], pts[i], pts[(i + 1) % k]
        for src, dst in ((p0, a), (p2, b)):
            vx, vy = src[0] - p1[0], src[1] - p1[1]
            ln = math.hypot(vx, vy) or 1.0
            d = min(r, ln / 2)
            dst.append((p1[0] + vx / ln * d, p1[1] + vy / ln * d))
    out = ["M %s %s" % (n(a[0][0]), n(a[0][1]))]
    for i in range(k):
        out.append("Q %s %s %s %s" % (n(pts[i][0]), n(pts[i][1]),
                                      n(b[i][0]), n(b[i][1])))
        j = (i + 1) % k
        out.append("L %s %s" % (n(a[j][0]), n(a[j][1])))
    return " ".join(out) + " Z"


def lay_field(scene, nodes, box, opts):
    k = len(nodes)
    r0 = min(box["w"], box["h"]) * 0.42
    for i, x in enumerate(nodes):
        if x["shape"] == "set":
            r = float(x.get("r", r0))
            x["w"] = x["h"] = q(r * 2)
        else:
            x["w"], x["h"] = box_for(x, 15.0, pad_x=16.0, min_w=96.0)
        if "pos" in x:
            px, py = x["pos"]
        else:                                # ring fallback, evenly spaced
            th = -math.pi / 2 + i * 2 * math.pi / k
            px, py = 0.5 + 0.38 * math.cos(th), 0.5 - 0.38 * math.sin(th)
        x["x"] = q(box["x"] + px * box["w"] - x["w"] / 2)
        x["y"] = q(box["y"] + (1 - py) * box["h"] - x["h"] / 2)

    # A cluster without hulls is a scatter plot with no axes: the grouping is
    # the argument and the points are only the evidence, so leaving the hulls
    # out deletes the claim and keeps the supporting material.
    groups = {}
    for x in nodes:
        if x.get("group"):
            groups.setdefault(x["group"], []).append(x)
    if groups:
        pad = 22.0
        hulls = []
        for name, members in groups.items():
            pts = []
            for m in members:
                for cx0 in (m["x"] - pad, m["x"] + m["w"] + pad):
                    for cy0 in (m["y"] - pad, m["y"] + m["h"] + pad):
                        pts.append((cx0, cy0))
            hull = convex_hull(pts)
            hulls.append((name, rounded_poly(hull),
                          min(pt[0] for pt in hull), min(pt[1] for pt in hull)))
        scene["_hulls"] = hulls

def lay_row(scene, nodes, box, opts):
    for x in nodes:
        x["_stat"] = True
        x["w"], x["h"] = box_for(x, 46.0, pad_x=30.0, min_w=160.0, min_h=112.0)
    total = sum(x["w"] for x in nodes)
    gap = max(36.0, (box["w"] - total) / max(1, len(nodes) - 1)) if len(nodes) > 1 else 0
    gap = min(gap, 110.0)
    x0 = box["x"] + (box["w"] - (total + gap * (len(nodes) - 1))) / 2
    cy = box["y"] + box["h"] / 2
    for x in nodes:
        x["x"], x["y"] = q(x0), q(cy - x["h"] / 2)
        x0 += x["w"] + gap


# ────────────────────────────────────────────── type-specific geometry ──
# Some types are a lie when drawn with their family's generic geometry. A gantt
# without duration bars, a radar without a polygon, a treemap whose tiles are
# all the same size — each still renders, and each says something false about
# the subject. Those get their own solver here; the rest ride the family.

def lay_timeline(scene, nodes, box, opts):
    """Events hang off a drawn rail, alternating sides. Alternating is not
    decoration: dates and labels on the same side of a horizontal rail collide
    as soon as two events are close together, and closeness is exactly what a
    timeline is drawn to show."""
    for x in nodes:
        x["w"], x["h"] = box_for(x, 16.0, pad_x=18.0, min_w=112.0)
    cy = box["y"] + box["h"] * 0.5
    k = len(nodes)
    step = box["w"] / max(1, k - 1) if k > 1 else 0
    for i, x in enumerate(nodes):
        x["x"] = q(min(box["x"] + i * step - x["w"] / 2,
                       box["x"] + box["w"] - x["w"]))
        x["x"] = q(max(x["x"], box["x"]))
        x["y"] = q(cy - x["h"] - 26 if i % 2 == 0 else cy + 26)
        x["_tick"] = (box["x"] + i * step, cy)
    scene["_rail"] = (box["x"], cy, box["x"] + box["w"], cy)

def lay_sequence(scene, nodes, box, opts):
    """Actors are columns, time runs down, and every edge is a message. The
    nodes are the actors — not the messages — which is the part that trips
    people: a sequence diagram with one node per message is a flowchart."""
    for x in nodes:
        x["w"], x["h"] = box_for(x, 15.0, pad_x=16.0, min_w=104.0, min_h=42.0)
    k = len(nodes)
    total = sum(x["w"] for x in nodes)
    gap = max(30.0, (box["w"] - total) / max(1, k - 1)) if k > 1 else 0
    x0 = box["x"] + (box["w"] - (total + gap * (k - 1))) / 2
    for x in nodes:
        x["x"], x["y"] = q(x0), q(box["y"])
        x0 += x["w"] + gap
    scene["_lifelines"] = [(center(x)[0], box["y"] + x["h"], box["y"] + box["h"])
                           for x in nodes]
    scene["_msg_top"] = box["y"] + nodes[0]["h"] + 34
    scene["_msg_step"] = min(46.0, (box["h"] - nodes[0]["h"] - 48) /
                             max(1, len(scene.get("edges", []))))

def lay_swimlane(scene, nodes, box, opts):
    """Rows are owners, columns are stages. The lane label is a rail, not a
    cell — making it a cell puts the owner's name in the same visual class as
    the work, and the reader stops being able to tell who from what."""
    lanes = []
    for x in nodes:
        ln = x.get("lane", "")
        if ln not in lanes:
            lanes.append(ln)
    cols = max(int(x.get("col", 0)) for x in nodes) + 1
    rail = 116.0
    cw = (box["w"] - rail) / cols
    ch = min(70.0, box["h"] / max(1, len(lanes)) - 12)
    y0 = box["y"] + (box["h"] - (ch + 12) * len(lanes) + 12) / 2
    for x in nodes:
        r = lanes.index(x.get("lane", ""))
        c = int(x.get("col", 0))
        x["w"], x["h"] = q(cw - 14), q(ch)
        x["x"] = q(box["x"] + rail + c * cw)
        x["y"] = q(y0 + r * (ch + 12))
    scene["_lanes"] = [(ln, box["x"], y0 + i * (ch + 12) + ch / 2,
                        box["x"] + box["w"], y0 + i * (ch + 12) + ch + 6)
                       for i, ln in enumerate(lanes)]
    scene["_lane_rail"] = box["x"] + rail - 12

def lay_gantt(scene, nodes, box, opts):
    """Bar length is duration and overlap is the claim, so both come off the
    real numbers. Rounding a bar to whole columns is where the schedule
    conflict the chart was drawn to show quietly disappears."""
    lo = min(float(x.get("start", 0)) for x in nodes)
    hi = max(float(x.get("end", 1)) for x in nodes)
    span = max(1e-6, hi - lo)
    rail = 128.0
    plot = box["w"] - rail
    ch = min(48.0, box["h"] / max(1, len(nodes)) - 12)
    y0 = box["y"] + (box["h"] - (ch + 12) * len(nodes) + 12) / 2
    for i, x in enumerate(nodes):
        a, b = float(x.get("start", 0)), float(x.get("end", 1))
        x["x"] = q(box["x"] + rail + (a - lo) / span * plot)
        x["w"] = max(28.0, q((b - a) / span * plot))
        x["y"], x["h"] = q(y0 + i * (ch + 12)), q(ch)
        x["_anchor"] = "start"
    scene["_gantt"] = (box["x"] + rail, y0 - 22, box["x"] + box["w"],
                       y0 + (ch + 12) * len(nodes) - 12, lo, hi)

def lay_radar(scene, nodes, box, opts):
    """A polygon through scored vertices. The enclosed shape is the claim, so
    the vertices carry no cards — a box at each point competes with the shape
    and the reader reads the boxes."""
    cx, cy = box["x"] + box["w"] / 2, box["y"] + box["h"] / 2
    r = min(box["w"], box["h"]) / 2 - 34
    k = len(nodes)
    pts, rim = [], []
    for i, x in enumerate(nodes):
        th = math.radians(-90 + i * 360.0 / k)
        sc = max(0.0, min(1.0, float(x.get("score", 0.6))))
        pts.append((cx + r * sc * math.cos(th), cy + r * sc * math.sin(th)))
        rim.append((cx + r * math.cos(th), cy + r * math.sin(th)))
        x["shape"] = "none"
        x["w"], x["h"] = 0.0, 0.0
        x["x"] = q(cx + (r + 26) * math.cos(th))
        x["y"] = q(cy + (r + 26) * math.sin(th))
    scene["_radar"] = (cx, cy, r, pts, rim)

def lay_treemap(scene, nodes, box, opts):
    """Area is proportional to the value. Slice and dice, alternating the axis
    at each cut so the tiles stay near-square — long thin tiles make two equal
    values look unequal, which is the one thing area encoding must not do."""
    items = [(x, max(1e-6, float(x.get("value", 1)))) for x in nodes]
    items.sort(key=lambda t: -t[1])

    def cut(items, x, y, w, h, horiz):
        if not items:
            return
        if len(items) == 1:
            n0 = items[0][0]
            n0["x"], n0["y"] = q(x), q(y)
            n0["w"], n0["h"] = q(w - 6), q(h - 6)
            n0["_anchor"] = "start"
            return
        tot = sum(v for _, v in items)
        acc, i = 0.0, 0
        while i < len(items) - 1 and acc + items[i][1] < tot / 2:
            acc += items[i][1]
            i += 1
        head, tail = items[:i + 1], items[i + 1:]
        f = sum(v for _, v in head) / tot
        if horiz:
            cut(head, x, y, w * f, h, not horiz)
            cut(tail, x + w * f, y, w * (1 - f), h, not horiz)
        else:
            cut(head, x, y, w, h * f, not horiz)
            cut(tail, x, y + h * f, w, h * (1 - f), not horiz)

    cut(items, box["x"], box["y"], box["w"], box["h"], box["w"] >= box["h"])

def lay_mindmap(scene, nodes, box, opts):
    """Root in the centre, branches alternating right and left, curved edges
    and no arrowheads — a mindmap has no direction, and a head invents one.

    Alternating sides rather than sweeping an arc: an arc from -160° to +160°
    puts two of three branches on the same side and stacks their children on
    top of each other, which is how a diagram about spreading out ends up
    looking like a pile."""
    byid = {x["id"]: x for x in nodes}
    kids = {x["id"]: [] for x in nodes}
    parent = {}
    for e in scene.get("edges", []):
        if e["from"] in kids and e["to"] not in parent:
            kids[e["from"]].append(e["to"])
            parent[e["to"]] = e["from"]
    roots = [x["id"] for x in nodes if x["id"] not in parent]
    root = byid[roots[0]] if roots else nodes[0]
    for x in nodes:
        x["w"], x["h"] = box_for(x, 16.0, pad_x=18.0, min_w=100.0)

    cx, cy = box["x"] + box["w"] / 2, box["y"] + box["h"] / 2
    root["x"], root["y"] = q(cx - root["w"] / 2), q(cy - root["h"] / 2)

    branch = kids.get(root["id"], [])
    sides = ([branch[0::2], 1], [branch[1::2], -1])
    row = 58.0
    for group, dirn in sides:
        blocks = [max(1, len(kids.get(cid, []))) for cid in group]
        total = sum(blocks) * row
        y = cy - total / 2 + row / 2
        for cid, nb in zip(group, blocks):
            c = byid[cid]
            c["y"] = q(y + (nb - 1) * row / 2 - c["h"] / 2)
            c["x"] = q(cx + dirn * (root["w"] / 2 + 76) - (0 if dirn > 0 else c["w"]))
            gy = y
            for gid in kids.get(cid, []):
                g = byid[gid]
                g["y"] = q(gy - g["h"] / 2)
                gx = c["x"] + (c["w"] + 48 if dirn > 0 else -48 - g["w"])
                g["x"] = q(min(max(gx, box["x"]), box["x"] + box["w"] - g["w"]))
                gy += row
            y += nb * row
    # Alternating sides rarely comes out even, so the drawn extent is not
    # centred on the root. Centre the extent, not the root: the reader sees the
    # picture, not the node the algorithm started from.
    xs = min(x["x"] for x in nodes)
    xe = max(x["x"] + x["w"] for x in nodes)
    shift = q(box["x"] + (box["w"] - (xe - xs)) / 2 - xs)
    for x in nodes:
        x["x"] = q(x["x"] + shift)
    scene["_curved"] = True

def lay_er(scene, nodes, box, opts):
    """Entities carry their fields. An entity box with only a name is a node in
    a network diagram — the fields are what make the relation checkable."""
    for x in nodes:
        f = x.get("fields", [])
        w = max([text_w(x["label"], 16.0)] + [text_w(t, 12.0) for t in f]) + 44
        x["w"], x["h"] = q(max(150.0, w)), q(46 + 19 * len(f))
    cols = min(len(nodes), 3)
    rows = math.ceil(len(nodes) / cols)
    gx = (box["w"] - sum(x["w"] for x in nodes[:cols])) / max(1, cols - 1) if cols > 1 else 0
    gx = min(max(gx, 40.0), 150.0)
    for i, x in enumerate(nodes):
        r, c = divmod(i, cols)
        row = nodes[r * cols:(r + 1) * cols]
        tw = sum(y["w"] for y in row) + gx * (len(row) - 1)
        x0 = box["x"] + (box["w"] - tw) / 2 + sum(y["w"] + gx for y in row[:c])
        x["x"] = q(x0)
        x["y"] = q(box["y"] + r * (box["h"] / rows) +
                   (box["h"] / rows - x["h"]) / 2)

def lay_table(scene, nodes, box, opts):
    """Rows and rules, not a grid of cards. A table drawn as cards is a bento:
    equal boxes say the cells are peers, when the whole point of a table is that
    a row is one thing and a column is one property of it."""
    cols = max(len(x.get("cells", [])) for x in nodes)
    widths = scene.get("colw") or [1.0] * cols
    tot = sum(widths[:cols])
    xs, acc = [], 0.0
    for w in widths[:cols]:
        xs.append(box["x"] + acc / tot * box["w"])
        acc += w
    rh = min(52.0, box["h"] / max(1, len(nodes)))
    y = box["y"] + (box["h"] - rh * len(nodes)) / 2
    for i, x in enumerate(nodes):
        x["shape"] = "row"
        x["_cells"] = list(x.get("cells", [x.get("label", "")]))
        x["_colx"] = xs
        x["_head"] = x.get("kind") == "header" or i == 0 and scene.get("header", True)
        x["x"], x["y"] = q(box["x"]), q(y)
        x["w"], x["h"] = q(box["w"]), q(rh)
        y += rh

SPECIAL = {
    "table": lay_table, "spec-rows": lay_table,
    "timeline": lay_timeline, "sequence": lay_sequence, "swimlane": lay_swimlane,
    "gantt": lay_gantt, "radar": lay_radar, "treemap": lay_treemap,
    "mindmap": lay_mindmap, "er": lay_er,
}

LAYOUTS = {
    "chain": lambda sc, nd, bx, op: lay_chain(sc, nd, bx, op.get("vertical", False)),
    "radial": lay_radial, "stack": lay_stack, "tree": lay_tree,
    "grid": lay_grid, "field": lay_field, "row": lay_row,
}

# ──────────────────────────────────────────────────────────────── the gates ──

class SpecError(Exception):
    pass

def normalise(scene, canvas):
    t = scene.get("type", "flow")
    if t not in FAMILY:
        near = ", ".join(sorted(k for k in FAMILY if k[0] == t[:1])) or "see FAMILY"
        raise SpecError("scene %r: unknown type %r. Close matches: %s"
                        % (scene.get("id", "?"), t, near))
    fam = FAMILY[t]
    opts = dict(TYPE_DEFAULTS.get(t, {}))
    opts.update(scene.get("options", {}))
    opts.setdefault("vertical", canvas != "landscape")

    nodes = []
    for raw in scene.get("nodes", []):
        x = dict(raw)
        kind = x.get("kind", "step")
        x["kind"] = kind
        x["shape"] = x.get("shape") or SHAPE.get(kind, "rect")
        x["label"] = x.get("label", x.get("id", ""))
        nodes.append(x)

    ids = [x["id"] for x in nodes]
    dupes = {i for i in ids if ids.count(i) > 1}
    if dupes:
        raise SpecError("scene %r: duplicate node ids %s" % (scene.get("id"), sorted(dupes)))

    edges = [dict(e) for e in scene.get("edges", [])]
    for e in edges:
        for end in ("from", "to"):
            if e.get(end) not in ids:
                raise SpecError("scene %r: edge %s->%s points at %r, which is not a node"
                                % (scene.get("id"), e.get("from"), e.get("to"), e.get(end)))

    # Budget. Over budget the figure still renders; it just stops being readable,
    # which is exactly why this is a gate and not a note.
    if len(nodes) > 9:
        raise SpecError("scene %r: %d nodes, budget is 9. Split into an overview "
                        "plus a detail scene." % (scene.get("id"), len(nodes)))
    if len(edges) > 12:
        raise SpecError("scene %r: %d edges, budget is 12." % (scene.get("id"), len(edges)))

    acc = [x for x in nodes if x.get("accent")] or \
          [x for x in nodes if x["id"] == scene.get("accent")]
    if len(acc) > 1:
        raise SpecError("scene %r: %d accents. One accent per figure — two erase "
                        "the signal." % (scene.get("id"), len(acc)))
    for x in acc:
        x["shape"] = "focal" if x["shape"] == "rect" else x["shape"]
        x["is_accent"] = True

    # Every edge out of a decision carries a label. An unlabelled branch is a bug.
    decisions = {x["id"] for x in nodes if x["shape"] == "diamond"}
    for e in edges:
        if e["from"] in decisions and not e.get("label"):
            raise SpecError("scene %r: branch %s->%s out of a decision has no label."
                            % (scene.get("id"), e["from"], e["to"]))
    return t, fam, opts, nodes, edges

# ──────────────────────────────────────────────────────────────── the beats ──

BEATS = dict(
    eyebrow=0.10, title=0.24, rule=0.45, rule2=0.55, num=0.60, tag=0.67,
    brand=0.74, tagline=0.81, figure=1.00,
    node_step=0.35,     # one node to the next
    node_edge=0.20,     # node -> the edge leaving it
    edge_head=0.26,     # edge -> its arrowhead
    edge_label=0.30,    # edge -> its label
    accent_pause=0.30,  # extra beat before the punchline
    accent_mark=0.35,   # punchline -> the ring around it
)

def schedule(nodes, edges, rate: float, first_at: float = None):
    """Assign --at to every element. Gaps compress with `rate`; durations do
    not, because a 0.40s entrance at rate 1.3 is 0.31s and still inside the
    300–500ms band, while a gap has no floor to protect."""
    r = max(0.5, float(rate))
    g = lambda v: v / r
    t0 = first_at if first_at is not None else g(BEATS["figure"])
    at = {}
    cursor = t0
    order = [x["id"] for x in nodes]
    for i, x in enumerate(nodes):
        if x.get("is_accent"):
            cursor += g(BEATS["accent_pause"])
        at["node:" + x["id"]] = round(cursor, 2)
        if x.get("is_accent"):
            at["mark:" + x["id"]] = round(cursor + g(BEATS["accent_mark"]), 2)
        cursor += g(BEATS["node_step"]) + (0.04 if x["shape"] == "diamond" else 0.0)
    for e in edges:
        src = at.get("node:" + e["from"], t0)
        dst = at.get("node:" + e["to"], t0)
        # The edge draws toward a node that already exists, and its head lands
        # after both. Drawing into empty space reads as the arrow inventing its
        # own destination.
        base = max(src + g(BEATS["node_edge"]), dst - g(0.14))
        e["_at"] = round(base, 2)
        e["_at_head"] = round(base + g(BEATS["edge_head"]), 2)
        e["_at_label"] = round(base + g(BEATS["edge_label"]), 2)
    end = max([v for v in at.values()] + [e["_at_head"] for e in edges] + [t0]) + g(0.45)
    return at, round(end, 2), order

def resolve_camera(scene, at, end, rate, seed=""):
    """Camera moves, resolved against the beat table. `auto` punches into the
    accent node just after it lands and pulls back out after a dwell — which is
    the only camera move most figures need, and the one worth having by
    default."""
    r = max(0.5, float(rate))
    spec = scene.get("camera", "auto")
    if not spec or spec == "none":
        return []
    if spec == "auto":
        acc = next((k for k in at if k.startswith("mark:")), None)
        order = [k.split(":", 1)[1] for k in at if k.startswith("node:")]
        # Nothing to go and read, so nothing to go there for. A camera move on
        # a three-node figure is motion with no referent, which is the same
        # failure as a looping pulse wearing a better coat.
        if not acc or len(order) < 4:
            return []
        target = acc.split(":", 1)[1]
        mode = CAM_MODES[dice(seed, "cam", scene.get("id", "")) % len(CAM_MODES)]
        if mode == "none":
            return []
        if mode == "drift":
            spec = [dict(focus=target, zoom=1.32, dwell=2.4)]
        elif mode == "survey" and len(order) >= 5:
            # Go and read one thing early, come back, then land on the point.
            first = order[1] if order[1] != target else order[2]
            spec = [dict(focus=first, zoom=1.55, dwell=1.0),
                    dict(focus=target, zoom=1.75, dwell=1.5)]
        else:
            spec = [dict(focus=target, zoom=1.7, dwell=1.8)]
    if isinstance(spec, dict):
        spec = [spec]
    moves = []
    for m in spec:
        fid = m.get("focus")
        if fid and ("node:" + fid) not in at:
            raise SpecError("camera focus %r is not a node in this scene" % fid)
        beat = at.get("node:" + str(fid), 0.0)
        a = m.get("at")
        a = (beat + 0.25 / r) if a is None else float(a) / (r if m.get("scaled", True) else 1)
        dwell = float(m.get("dwell", 1.8)) / r
        rel = m.get("release")
        rel = (a + dwell) if rel is None else float(rel) / (r if m.get("scaled", True) else 1)
        moves.append(dict(focus=fid, at=round(a, 2), release=round(rel, 2),
                          zoom=float(m.get("zoom", 1.7))))
    moves.sort(key=lambda m: m["at"])
    if scene.get("camera", "auto") == "auto":
        # An auto plan lays its own moves end to end rather than failing: the
        # author did not choose these times, so refusing them would be refusing
        # the author's spec for a decision they never made.
        for i in range(1, len(moves)):
            lag = moves[i - 1]["release"] + 0.62 + 0.2 - moves[i]["at"]
            if lag > 0:
                moves[i]["at"] = round(moves[i]["at"] + lag, 2)
                moves[i]["release"] = round(moves[i]["release"] + lag, 2)
    for i in range(len(moves) - 1):
        if moves[i]["release"] > moves[i + 1]["at"] + 1e-6:
            raise SpecError(
                "camera moves overlap: one releases at %.2fs, the next starts at "
                "%.2fs. Push and pull are inverses of each other, so an overlap "
                "leaves the frame permanently off-centre."
                % (moves[i]["release"], moves[i + 1]["at"]))
    return moves

# ───────────────────────────────────────────────────────────────── emitting ──

HEAD_PTS = "0,0 -11,-5.2 -11,5.2"
SEAMS = ["push", "squeeze", "blur", "zoom", "drop", "recede"]
ENTRANCES = ["rise", "settle", "widen", "slide"]
CAM_MODES = ("punch", "survey", "drift", "none")


def dice(*parts) -> int:
    """A deterministic die. Not random: the same spec must produce the same
    film every time, or a re-render silently becomes a different cut and the
    narration no longer lands where the picture does. Varying by index instead
    is what makes every deck feel like the same deck — index 0 is always the
    same entrance, so a five-scene piece has one rhythm forever."""
    return zlib.crc32("|".join(str(p) for p in parts).encode())


def choose(options, seed_parts, prev, used, slots_left, need_total):
    """One pick from `options` that is never the previous pick, and that
    reaches `need_total` distinct kinds across the run. Adjacent-different
    alone is not enough: A B A B satisfies it and uses two kinds forever."""
    start = dice(*seed_parts) % len(options)
    order = [options[(start + k) % len(options)] for k in range(len(options))]
    fresh = [o for o in order if o != prev and o not in used]
    forced = (len(used) + slots_left) <= need_total
    if fresh and (forced or dice(*seed_parts, "f") % 3):
        return fresh[0]
    return next((o for o in order if o != prev), order[0])


def plan_variation(spec, builds):
    """Entrance per scene and transition per seam, varied but reproducible."""
    seed = str(spec.get("seed", spec.get("title", "")))
    n = len(builds)
    need_e = max(1, (n + 1) // 2)
    need_s = max(1, ((n - 1) + 1) // 2)
    ents, seams, ue, us = [], [], set(), set()
    for i, b in enumerate(builds):
        sid = b["scene"].get("id", i)
        e = b["scene"].get("enter") or choose(
            ENTRANCES, (seed, "enter", sid), ents[-1] if ents else None,
            ue, n - i, need_e)
        ents.append(e); ue.add(e)
        if i < n - 1:
            sm = b["scene"].get("seam") or choose(
                SEAMS, (seed, "seam", sid), seams[-1] if seams else None,
                us, (n - 1) - i, need_s)
            seams.append(sm); us.add(sm)
    return ents, seams

def shape_svg(x):
    cx, cy = center(x)
    lift = ' filter="url(#mf-lift)"'
    s = x["shape"]
    if s == "set":
        # A venn without circles is three floating labels. The whole claim of
        # the figure is which regions exist, and only the outlines say that.
        out = ['<circle class="mf-set" cx="%s" cy="%s" r="%s" />'
               % (n(cx), n(cy), n(x["w"] / 2))]
        out.append('<text class="mf-node" x="%s" y="%s">%s</text>'
                   % (n(cx), n(x["y"] + 34), esc(x["label"])))
        if x.get("sub"):
            out.append('<text class="mf-sub" x="%s" y="%s">%s</text>'
                       % (n(cx), n(x["y"] + 49), esc(x["sub"])))
        return "".join(out)
    if s == "row":
        cls = "mf-tag" if x.get("_head") else "mf-node"
        out = []
        for i, cell in enumerate(x["_cells"]):
            if i >= len(x["_colx"]):
                break
            out.append('<text class="%s" x="%s" y="%s" text-anchor="start">%s</text>'
                       % (cls, n(x["_colx"][i] + 2), n(cy + (5 if x.get("_head") else 6)),
                          esc(cell)))
        out.append('<line class="mf-rule" x1="%s" y1="%s" x2="%s" y2="%s" />'
                   % (n(x["x"]), n(x["y"] + x["h"]), n(x["x"] + x["w"]), n(x["y"] + x["h"])))
        return "".join(out)
    if s == "none":
        # A radar vertex has no card: a box at each point competes with the
        # polygon, and the polygon is the argument.
        out = ['<text class="mf-edge" x="%s" y="%s">%s</text>'
               % (n(x["x"]), n(x["y"]), esc(x["label"]))]
        if x.get("sub"):
            out.append('<text class="mf-sub" x="%s" y="%s">%s</text>'
                       % (n(x["x"]), n(x["y"] + 14), esc(x["sub"])))
        return "".join(out)
    if x.get("fields"):
        out = ['<rect class="mf-card-lined" x="%s" y="%s" width="%s" height="%s" rx="6" />'
               % (n(x["x"]), n(x["y"]), n(x["w"]), n(x["h"])),
               '<line class="mf-rule" x1="%s" y1="%s" x2="%s" y2="%s" />'
               % (n(x["x"]), n(x["y"] + 34), n(x["x"] + x["w"]), n(x["y"] + 34)),
               '<text class="mf-node" x="%s" y="%s" text-anchor="start">%s</text>'
               % (n(x["x"] + 14), n(x["y"] + 23), esc(x["label"]))]
        for i, t in enumerate(x["fields"]):
            out.append('<text class="mf-edge" x="%s" y="%s" text-anchor="start">%s</text>'
                       % (n(x["x"] + 14), n(x["y"] + 53 + i * 19), esc(t)))
        return "".join(out)
    if s == "diamond":
        pts = "%s,%s %s,%s %s,%s %s,%s" % (
            n(cx), n(x["y"]), n(x["x"] + x["w"]), n(cy),
            n(cx), n(x["y"] + x["h"]), n(x["x"]), n(cy))
        body = '<polygon class="mf-card"%s points="%s" />' % (lift, pts)
    else:
        cls, rx, filt = "mf-card", 10.0, lift
        if s == "stadium":
            rx = x["h"] / 2
        elif s == "store":
            cls, rx, filt = "mf-store", 6.0, ""
        elif s == "ghost":
            cls, rx, filt = "mf-ghost", 8.0, lift
        elif s == "focal":
            cls, rx, filt = "mf-focal", 10.0, ""
        body = '<rect class="%s"%s x="%s" y="%s" width="%s" height="%s" rx="%s" />' % (
            cls, filt, n(x["x"]), n(x["y"]), n(x["w"]), n(x["h"]), n(rx))
    inv = "-inv" if s == "store" else ""
    out = [body]
    if x.get("_anchor") == "start":
        # A bar or a tile is read from its left edge, where the eye already is.
        out.append('<text class="mf-node%s" x="%s" y="%s" text-anchor="start">%s</text>'
                   % (inv, n(x["x"] + 14), n(cy + (6 if not x.get("sub") else -1)),
                      esc(x["label"])))
        if x.get("sub"):
            out.append('<text class="mf-sub%s" x="%s" y="%s" text-anchor="start">%s</text>'
                       % (inv, n(x["x"] + 14), n(cy + 14), esc(x["sub"])))
        return "".join(out)
    if x.get("_stat"):
        # In the row family the number is the figure. Set at node size it reads
        # as a label that happens to be numeric, which is the opposite of what
        # the form is for.
        out.append('<text class="mf-stat" x="%s" y="%s">%s</text>'
                   % (n(cx), n(cy + 6 if not x.get("sub") else cy - 2), esc(x["label"])))
        if x.get("sub"):
            out.append('<text class="mf-statsub" x="%s" y="%s">%s</text>'
                       % (n(cx), n(cy + 26), esc(x["sub"])))
        return "".join(out)
    if x.get("sub"):
        out.append('<text class="mf-node%s" x="%s" y="%s">%s</text>'
                   % (inv, n(cx), n(cy - 1), esc(x["label"])))
        out.append('<text class="mf-sub%s" x="%s" y="%s">%s</text>'
                   % (inv, n(cx), n(cy + 14), esc(x["sub"])))
    else:
        out.append('<text class="mf-node%s" x="%s" y="%s">%s</text>'
                   % (inv, n(cx), n(cy + 6), esc(x["label"])))
    return "".join(out)

def axes_svg(scene, opts, box, at0, ind):
    """Named axes for the types where position is the claim. Without them the
    reader can see that one node is up and right of another and cannot know
    what up and right mean — which makes the figure's only argument unreadable
    while it still looks finished."""
    ax = scene.get("axes")
    if not ax or not opts.get("axes"):
        return ""
    x0, y0 = box["x"], box["y"]
    x1, y1 = box["x"] + box["w"], box["y"] + box["h"]
    cx, cy = x0 + box["w"] / 2, y0 + box["h"] / 2
    cross = scene.get("type") in ("quadrant",)
    L = []
    if cross:
        L.append('%s<line class="dm mf-draw mf-axis" style="--at:%ss" pathLength="1" '
                 'x1="%s" y1="%s" x2="%s" y2="%s" />' % (ind, n(at0), n(x0), n(cy), n(x1), n(cy)))
        L.append('%s<line class="dm mf-draw mf-axis" style="--at:%ss" pathLength="1" '
                 'x1="%s" y1="%s" x2="%s" y2="%s" />' % (ind, n(at0 + 0.06), n(cx), n(y0), n(cx), n(y1)))
        ends = [(ax.get("x", ["", ""])[0], x0, cy - 10, "start"),
                (ax.get("x", ["", ""])[1], x1, cy - 10, "end"),
                (ax.get("y", ["", ""])[0], cx + 10, y1, "start"),
                (ax.get("y", ["", ""])[1], cx + 10, y0 + 12, "start")]
    else:
        L.append('%s<path class="dm mf-draw mf-axis" style="--at:%ss" pathLength="1" '
                 'd="M %s %s L %s %s L %s %s" />'
                 % (ind, n(at0), n(x0), n(y0), n(x0), n(y1), n(x1), n(y1)))
        ends = [(ax.get("x", ["", ""])[0], x0 + 4, y1 + 18, "start"),
                (ax.get("x", ["", ""])[1], x1, y1 + 18, "end"),
                (ax.get("y", ["", ""])[0], x0 - 8, y1, "end"),
                (ax.get("y", ["", ""])[1], x0 - 8, y0 + 12, "end")]
    for i, (label, lx, ly, anch) in enumerate(ends):
        if not label:
            continue
        L.append('%s<text class="dm mf-widen mf-tag" style="--at:%ss" x="%s" y="%s" '
                 'text-anchor="%s">%s</text>'
                 % (ind, n(at0 + 0.10 + i * 0.05), n(lx), n(ly), anch, esc(label)))
    return "\n".join(L)

def extras_svg(scene, nodes, box, at0, ind):
    """Rails, lifelines, lane rules, time ticks, radar rings. Not ornament:
    each of these is the thing that turns a set of boxes into the claim the
    type is supposed to be making."""
    L, t = [], at0
    def draw(cls, d, dt, extra=""):
        L.append('%s<path class="dm mf-draw %s" style="--at:%ss" pathLength="1" '
                 'd="%s"%s />' % (ind, cls, n(t + dt), d, extra))
    def tag(txt, x, y, dt, anch="middle"):
        L.append('%s<text class="dm mf-widen mf-tag" style="--at:%ss" x="%s" y="%s" '
                 'text-anchor="%s">%s</text>' % (ind, n(t + dt), n(x), n(y), anch, esc(txt)))

    if scene.get("_rail"):
        x0, y0, x1, _ = scene["_rail"]
        draw("mf-rail", "M %s %s L %s %s" % (n(x0), n(y0), n(x1), n(y0)), 0)
        for i, x in enumerate(nodes):
            tx, ty = x["_tick"]
            L.append('%s<circle class="dm mf-pop mf-head" style="--at:%ss" cx="%s" cy="%s" r="3.5" />'
                     % (ind, n(t + 0.05 + i * 0.04), n(tx), n(ty)))

    if scene.get("_lifelines"):
        for i, (lx, y0, y1) in enumerate(scene["_lifelines"]):
            draw("mf-dash", "M %s %s L %s %s" % (n(lx), n(y0 + 8), n(lx), n(y1)), 0.05 + i * 0.04)

    if scene.get("_lanes"):
        for i, (name, x0, ly, x1, ry) in enumerate(scene["_lanes"]):
            draw("mf-rule", "M %s %s L %s %s" % (n(x0), n(ry), n(x1), n(ry)), 0.04 * i)
            L.append('%s<text class="dm mf-widen mf-tag" style="--at:%ss" x="%s" y="%s" '
                     'text-anchor="start">%s</text>'
                     % (ind, n(t + 0.06 + 0.04 * i), n(x0), n(ly + 4), esc(name)))
        rx = scene["_lane_rail"]
        draw("mf-axis", "M %s %s L %s %s" % (n(rx), n(scene["_lanes"][0][2] - 40),
                                             n(rx), n(scene["_lanes"][-1][4])), 0)

    if scene.get("_gantt"):
        x0, ytop, x1, ybot, lo, hi = scene["_gantt"]
        draw("mf-rail", "M %s %s L %s %s" % (n(x0), n(ytop), n(x1), n(ytop)), 0)
        marks = scene.get("ticks") or []
        for i, m in enumerate(marks):
            mx = x0 + (float(m["at"]) - lo) / max(1e-6, hi - lo) * (x1 - x0)
            draw("mf-dash", "M %s %s L %s %s" % (n(mx), n(ytop), n(mx), n(ybot)), 0.05 + i * 0.04)
            tag(m["label"], mx, ytop - 10, 0.08 + i * 0.04)

    if scene.get("_hulls"):
        for i, (name, d, hx, hy) in enumerate(scene["_hulls"]):
            if not d:
                continue
            L.append('%s<path class="dm mf-ink mf-set" style="--at:%ss" d="%s" />'
                     % (ind, n(t + 0.04 * i), d))
            tag(name, hx + 14, hy + 20, 0.08 + 0.04 * i, "start")

    if scene.get("_radar"):
        cx, cy, r, pts, rim = scene["_radar"]
        for i, f in enumerate((0.5, 1.0)):
            ring = " ".join("%s,%s" % (n(cx + r * f * math.cos(math.radians(-90 + j * 360.0 / len(rim)))),
                                       n(cy + r * f * math.sin(math.radians(-90 + j * 360.0 / len(rim)))))
                            for j in range(len(rim)))
            L.append('%s<polygon class="dm mf-ink mf-axis" style="--at:%ss" points="%s" />'
                     % (ind, n(t + 0.04 * i), ring))
        for i, (rxp, ryp) in enumerate(rim):
            draw("mf-axis", "M %s %s L %s %s" % (n(cx), n(cy), n(rxp), n(ryp)), 0.06 + i * 0.03)
        poly = " ".join("%s,%s" % (n(a), n(b)) for a, b in pts)
        L.append('%s<polygon class="dm mf-widen mf-focal" style="--at:%ss" points="%s" />'
                 % (ind, n(t + 0.34), poly))
    return "\n".join(L)

def figure_svg(scene, fam, opts, nodes, edges, at, box=None, ind="          "):
    L = []
    byid = {x["id"]: x for x in nodes}
    if box:
        node_beats = [v for k, v in at.items() if k.startswith("node:")]
        t0 = max(0.30, min(node_beats) - 0.18)
        for chunk in (axes_svg(scene, opts, box, t0, ind),
                      extras_svg(scene, nodes, box, t0, ind)):
            if chunk:
                L.append(chunk)

    if scene.get("_ellipse"):
        # Family is not enough to decide: radar is radial and has no ellipse to
        # hang arcs on, because its stations are vertices of a polygon.
        ell = scene["_ellipse"]
        for e in edges:
            a, b = byid[e["from"]], byid[e["to"]]
            if e.get("kind") == "spoke" or b["shape"] == "store" or a["shape"] == "store":
                d, tip = route(a, b)
                e["_d"], e["_tip"], e["_cls"] = d, tip, "mf-dash"
            else:
                d, tip = arc_between(a, b, ell)
                e["_d"], e["_tip"] = d, tip
                e["_cls"] = "mf-flow-a" if e.get("kind") == "accent" else "mf-flow"
    elif scene.get("_lifelines"):
        # A message runs between two lifelines at its own row. Time is the
        # vertical axis here, so the row index IS the ordering — routing these
        # like ordinary edges would let two messages share a height and lose it.
        top, step = scene["_msg_top"], scene["_msg_step"]
        for i, e in enumerate(edges):
            ax = center(byid[e["from"]])[0]
            bx = center(byid[e["to"]])[0]
            y = top + i * step
            gap = 5.0 * sgn(bx - ax)
            e["_d"] = "M %s %s L %s %s" % (n(ax), n(y), n(bx - gap), n(y))
            e["_tip"] = (bx, y, 0.0 if bx > ax else 180.0)
            e["_cls"] = "mf-flow-a" if e.get("kind") == "accent" else (
                "mf-dash" if e.get("kind") in ("dashed", "return") else "mf-flow")
            e["_ly"] = y - 9
    else:
        for e in edges:
            a, b = byid[e["from"]], byid[e["to"]]
            if scene.get("_curved"):
                # No arrowheads: a mindmap has no direction, and a head invents one.
                acx, acy = center(a)
                bcx, bcy = center(b)
                sx = a["x"] + (a["w"] if bcx >= acx else 0)
                ex = b["x"] + (0 if bcx >= acx else b["w"])
                d = "M %s %s Q %s %s %s %s" % (n(sx), n(acy), n((sx + ex) / 2), n(acy),
                                               n(ex), n(bcy))
                e["_d"], e["_tip"], e["kind"] = d, (ex, bcy, 0.0), "spoke"
                e["_cls"] = "mf-flow"
                continue
            if scene.get("_tree") and a["y"] + a["h"] <= b["y"]:
                d, tip = tree_edge(a, b)
            else:
                d, tip = route(a, b, prefer=e.get("prefer"))
            e["_d"], e["_tip"] = d, tip
            e["_cls"] = {"accent": "mf-flow-a", "dashed": "mf-dash",
                         "spoke": "mf-dash"}.get(e.get("kind"), "mf-flow")

    for e in edges:
        head_cls = "mf-head-a" if e["_cls"] == "mf-flow-a" else "mf-head"
        anim = "mf-ink" if e["_cls"] == "mf-dash" else "mf-draw"
        plen = "" if anim == "mf-ink" else ' pathLength="1"'
        L.append('%s<path class="dm %s %s" style="--at:%ss"%s d="%s" />'
                 % (ind, anim, e["_cls"], n(e["_at"]), plen, e["_d"]))
        if e.get("kind") != "spoke":
            tx, ty, rot = e["_tip"]
            L.append('%s<g transform="translate(%s,%s) rotate(%s)">'
                     '<polygon class="dm mf-tip %s" style="--at:%ss" points="%s" /></g>'
                     % (ind, n(tx), n(ty), n(rot), head_cls, n(e["_at_head"]), HEAD_PTS))
        if e.get("label"):
            a, b = byid[e["from"]], byid[e["to"]]
            acx, acy = center(a)
            bcx, bcy = center(b)
            mx, my = (acx + bcx) / 2, (acy + bcy) / 2
            if e.get("_ly") is not None:
                lx, ly, anch = mx, e["_ly"], "middle"
            elif abs(bcx - acx) >= abs(bcy - acy):
                lx, ly, anch = mx, my - 12, "middle"
            else:
                lx, ly, anch = mx + 14, my + 4, "start"
            L.append('%s<text class="dm mf-widen mf-edge" style="--at:%ss" x="%s" y="%s" '
                     'text-anchor="%s">%s</text>'
                     % (ind, n(e["_at_label"]), n(lx), n(ly), anch, esc(e["label"])))

    for x in nodes:
        L.append('%s<g class="dm mf-pop" style="--at:%ss">%s</g>'
                 % (ind, n(at["node:" + x["id"]]), shape_svg(x)))
        if x.get("is_accent"):
            cx, cy = center(x)
            if x["w"] > x["h"] * 2.4:
                # A circle drawn round a wide band has to be wider than the band
                # to enclose it, which on a full-width band means wider than the
                # canvas. Trace the shape instead of circling it.
                mk = ('<rect class="mf-mark" x="%s" y="%s" width="%s" height="%s" '
                      'rx="%s" transform="rotate(-0.4 %s %s)" filter="url(#mf-sketch)" />'
                      % (n(x["x"] - 9), n(x["y"] - 8), n(x["w"] + 18), n(x["h"] + 16),
                         n(min(20.0, x["h"] / 2 + 8)), n(cx), n(cy)))
            else:
                mk = ('<ellipse class="mf-mark" cx="%s" cy="%s" rx="%s" ry="%s" '
                      'transform="rotate(-3 %s %s)" filter="url(#mf-sketch)" />'
                      % (n(cx), n(cy), n(x["w"] / 2 + 18), n(x["h"] / 2 + 14),
                         n(cx), n(cy)))
            L.append('%s<g class="dm mf-flash" style="--at:%ss">%s</g>'
                     % (ind, n(at["mark:" + x["id"]]), mk))
    return "\n".join(L)

def chrome_svg(scene, vb, rate, enter=None, ind="          "):
    W, H = vb
    r = max(0.5, float(rate))
    g = lambda v: round(v / r, 2)
    m = 60 if W >= 960 else 44
    L = []
    if scene.get("watermark"):
        L.append('%s<text class="mf-watermark" x="%s" y="%s" text-anchor="middle">%s</text>'
                 % (ind, n(W / 2), n(H * 0.61), esc(scene["watermark"])))
    ent = scene.get("enter") or enter or "rise"
    if scene.get("eyebrow"):
        L.append('%s<text class="dm mf-settle mf-eyebrow" style="--at:%ss" x="%s" y="%s">%s</text>'
                 % (ind, n(g(BEATS["eyebrow"])), m, 64 if H <= 720 else 96, esc(scene["eyebrow"])))
    title = scene.get("title")
    if title:
        lines = title if isinstance(title, list) else [title]
        y0 = 112 if H <= 720 else 150
        for i, ln in enumerate(lines):
            L.append('%s<text class="dm mf-%s mf-title" style="--at:%ss" x="%s" y="%s">%s</text>'
                     % (ind, ent, n(g(BEATS["title"] + i * 0.06)), m, y0 + i * 58, esc(ln)))
        rule_y = y0 + len(lines) * 58 - 20
        L.append('%s<line class="dm mf-draw mf-rule" style="--at:%ss" pathLength="1" '
                 'x1="%s" y1="%s" x2="%s" y2="%s" />'
                 % (ind, n(g(BEATS["rule"])), m, rule_y, W - m, rule_y))
    foot_y = H - 100
    L.append('%s<line class="dm mf-draw mf-rule" style="--at:%ss" pathLength="1" '
             'x1="%s" y1="%s" x2="%s" y2="%s" />'
             % (ind, n(g(BEATS["rule2"])), m, foot_y, W - m, foot_y))
    if scene.get("num"):
        L.append('%s<text class="dm mf-rise mf-num" style="--at:%ss" x="%s" y="%s">%s</text>'
                 % (ind, n(g(BEATS["num"])), m, foot_y + 46, esc(scene["num"])))
    if scene.get("tag"):
        L.append('%s<text class="dm mf-rise mf-tag" style="--at:%ss" x="%s" y="%s">%s</text>'
                 % (ind, n(g(BEATS["tag"])), m, foot_y + 66, esc(scene["tag"])))
    if scene.get("brand"):
        L.append('%s<text class="dm mf-rise mf-tag" style="--at:%ss" x="%s" y="%s" '
                 'text-anchor="end">%s</text>'
                 % (ind, n(g(BEATS["brand"])), W - m, foot_y + 46, esc(scene["brand"])))
    if scene.get("tagline"):
        L.append('%s<text class="dm mf-rise mf-tag" style="--at:%ss" x="%s" y="%s" '
                 'text-anchor="end">%s</text>'
                 % (ind, n(g(BEATS["tagline"])), W - m, foot_y + 64, esc(scene["tagline"])))
    return "\n".join(L)

def wrap_camera(inner, moves, vb, ind="        "):
    """Nest a push/pull pair per move. The pair are exact inverses about the
    same origin, so after the pull the frame is back to identity with no
    accumulated drift — which is what lets an arbitrary dwell exist without a
    keyframe percentage or a line of JavaScript."""
    W, H = vb
    body = inner
    for m in reversed(moves):
        v = ("--zx:%spx; --zy:%spx; --zk:%s; --cx:%spx; --cy:%spx"
             % (n(m["_zx"]), n(m["_zy"]), n(m["zoom"]), n(W / 2), n(H * 0.56)))
        body = ('%s<g class="mf-cam mf-push" style="--at:%ss; %s">\n'
                '%s  <g class="mf-cam mf-pull" style="--at:%ss; %s">\n'
                '%s\n'
                '%s  </g>\n%s</g>'
                % (ind, n(m["at"]), v, ind, n(m["release"]), v, body, ind, ind))
    return body

# ─────────────────────────────────────────────────────────────── assembling ──

def build_scene(scene, canvas, rate, idx, seed=""):
    vb = CANVAS[canvas]["vb"]
    W, H = vb
    t, fam, opts, nodes, edges = normalise(scene, canvas)
    cm = CHROME[canvas]
    box = dict(x=float(cm["l"]), y=float(cm["t"]),
               w=float(W - cm["l"] - cm["r"]), h=float(H - cm["t"] - cm["b"]))
    (SPECIAL.get(t) or LAYOUTS[fam])(scene, nodes, box, opts)
    at, end, order = schedule(nodes, edges, rate)
    moves = resolve_camera(scene, at, end, rate, seed)
    byid = {x["id"]: x for x in nodes}
    for m in moves:
        f = byid.get(m["focus"])
        m["_zx"], m["_zy"] = center(f) if f else (W / 2, H / 2)
        # A zoom whose focus sits near an edge would push the figure off frame.
        # Pull the target point inward so the magnified view stays inside.
        half_w, half_h = W / (2 * m["zoom"]), H / (2 * m["zoom"])
        m["_zx"] = min(max(m["_zx"], half_w), W - half_w)
        m["_zy"] = min(max(m["_zy"], half_h), H - half_h)
    # `settle` is the first moment nothing is moving: the last beat has landed
    # and the camera has finished pulling back. A scene must reach it — a
    # camera still pulling back while the seam fires gives the scene no resting
    # frame at all, so there is nothing to screenshot and the next scene lands
    # on top of a picture in motion.
    settle = max([end] + [m["release"] + 0.62 for m in moves])
    end = settle + 0.25 + 0.42          # rest, then room for the seam
    return dict(scene=scene, type=t, family=fam, opts=opts, nodes=nodes, edges=edges,
                at=at, settle=round(settle, 2), end=round(end, 2),
                moves=moves, vb=vb, box=box, idx=idx)

def scene_svg(b, rate, seam=None, entrance=None, offset=0.0, ind="        "):
    sc = b["scene"]
    fig = figure_svg(sc, b["family"], b["opts"], b["nodes"], b["edges"], b["at"],
                     b["box"], ind + "    ")
    body = wrap_camera(fig, b["moves"], b["vb"], ind + "  ")
    chrome = chrome_svg(sc, b["vb"], rate, b.get("enter"), ind + "  ")
    inner = "%s\n%s" % (chrome, body)
    cls, style = [], []
    if entrance:
        cls.append("mf-scene mf-in-" + entrance)
        style.append("--at:%ss" % n(offset))
    if seam:
        # Exit runs right up to the cut. A gap here reads as a blink.
        wrapper = ('%s<g class="mf-scene mf-exit-%s" style="--at:%ss">\n%s\n%s</g>'
                   % (ind, seam, n(offset + b["end"] - 0.42), inner, ind))
        inner = wrapper
    if cls:
        inner = ('%s<g class="%s" style="%s">\n%s\n%s</g>'
                 % (ind, " ".join(cls), "; ".join(style), inner, ind))
    if offset:
        inner = shift_times(inner, offset)
    return inner

TIME_RE = re.compile(r"--at:(-?[\d.]+)s")

def shift_times(svg: str, offset: float) -> str:
    seen = {"first": True}
    def rep(m):
        # The scene wrapper's own --at is already absolute; everything inside is
        # scene-relative. Wrappers are emitted first, so skip them by depth, not
        # by guessing: they are the lines carrying mf-scene.
        return "--at:%ss" % n(float(m.group(1)) + offset)
    out = []
    for line in svg.split("\n"):
        if "mf-scene" in line:
            out.append(line)
        else:
            out.append(TIME_RE.sub(rep, line))
    return "\n".join(out)

FIELD = {
    "landscape": '<ellipse cx="150" cy="90"  rx="300" ry="200" fill="url(#mf-warm)" />\n'
                 '            <ellipse cx="740" cy="430" rx="320" ry="240" fill="url(#mf-cool)" />',
    "portrait":  '<ellipse cx="110" cy="150" rx="300" ry="260" fill="url(#mf-warm)" />\n'
                 '            <ellipse cx="440" cy="760" rx="320" ry="300" fill="url(#mf-cool)" />',
    "square":    '<ellipse cx="120" cy="120" rx="300" ry="250" fill="url(#mf-warm)" />\n'
                 '            <ellipse cx="580" cy="580" rx="320" ry="270" fill="url(#mf-cool)" />',
}

def page(spec, builds, rate) -> str:
    canvas = spec.get("canvas", "landscape")
    profile = spec.get("profile", "soft-gradient")
    vb = CANVAS[canvas]["vb"]
    stage = CANVAS[canvas]["stage"]
    shell = (SKILL_ROOT / "assets" / "page.html").read_text()

    ents, seams = plan_variation(spec, builds)
    parts, offset = [], 0.0
    total = len(builds)
    for i, b in enumerate(builds):
        b["enter"] = ents[i]
        seam = None if i == total - 1 else seams[i]
        entrance = None if i == 0 else seams[i - 1]
        parts.append(scene_svg(b, rate, seam=seam, entrance=entrance, offset=offset))
        offset = round(offset + b["end"] - (0.42 if seam else 0.0), 2)

    r = max(0.5, float(rate))
    stagevars = "--dur:%ss; --dur-fast:%ss" % (
        n(max(0.30, round(0.40 / r, 2))), n(max(0.26, round(0.30 / r, 2))))
    alt = spec.get("alt") or builds[0]["scene"].get("alt") or (
        "%s diagram: %s" % (builds[0]["type"],
                            ", ".join(x["label"] for x in builds[0]["nodes"])))
    out = (shell
           .replace("@TITLE@", esc(spec.get("title", "modernflow figure")))
           .replace("@PROFILE@", profile)
           .replace("@STAGEVARS@", stagevars)
           .replace("@STAGEW@", str(stage[0])).replace("@STAGEH@", str(stage[1]))
           .replace("@VBW@", str(vb[0])).replace("@VBH@", str(vb[1]))
           .replace("@ALT@", esc(alt))
           .replace("@FIELD_SHAPES@", FIELD[canvas])
           .replace("@BODY@", "\n".join(parts)))
    return out

# Every id the defs block declares. A fragment carries its own copy, so the ids
# have to be made unique — otherwise the second stage on a page silently uses
# the first stage's gradients, and if the two are on different profiles its
# colour field comes out of the wrong palette.
DEF_IDS = ("mf-warm", "mf-cool", "mf-soften", "mf-grain", "mf-lift", "mf-sketch",
           "mf-field")

def fragment(spec, b, rate) -> str:
    """One scene as a standalone `<div class="mf-stage">`, starting at t=0.

    For putting several figures in one document — a contact sheet, a
    playground — where each keeps its own timeline instead of following the one
    before it. The colour field is left in place: `base.css` turns it off under
    editorial-paper by rule, so a stage can change profile after it is written.
    """
    shell = page(spec, [b], rate)
    i = shell.index('<div class="mf-stage"')
    j = shell.rindex("</div>") + 6
    frag = shell[i:j]
    sid = b["scene"].get("id") or ("s%d" % b["idx"])
    for d in DEF_IDS:
        frag = frag.replace('id="%s"' % d, 'id="%s-%s"' % (d, sid))
        frag = frag.replace("url(#%s)" % d, "url(#%s-%s)" % (d, sid))
    return frag

# ───────────────────────────────────────────────────────────────────── main ──

def main() -> int:
    ap = argparse.ArgumentParser(description="semantic spec -> modernflow figure")
    ap.add_argument("spec", type=Path)
    ap.add_argument("-o", "--out", type=Path)
    ap.add_argument("--rate", type=float, default=None,
                    help="narration rate; compresses gaps, not durations")
    ap.add_argument("--scene", help="render only this scene id")
    ap.add_argument("--split", action="store_true", help="one file per scene")
    ap.add_argument("--json", action="store_true", help="print geometry and beats")
    a = ap.parse_args()

    try:
        spec = json.loads(a.spec.read_text())
    except json.JSONDecodeError as e:
        print("spec is not valid JSON: %s" % e, file=sys.stderr)
        return 1

    canvas = spec.get("canvas", "landscape")
    if canvas not in CANVAS:
        print("unknown canvas %r; pick one of %s" % (canvas, ", ".join(CANVAS)),
              file=sys.stderr)
        return 1
    rate = a.rate if a.rate is not None else float(spec.get("rate", 1.0))

    scenes = spec.get("scenes") or [spec]
    if a.scene:
        scenes = [s for s in scenes if s.get("id") == a.scene]
        if not scenes:
            print("no scene with id %r" % a.scene, file=sys.stderr)
            return 1

    try:
        seed = str(spec.get("seed", spec.get("title", "")))
        builds = [build_scene(s, canvas, rate, i, seed) for i, s in enumerate(scenes)]
    except SpecError as e:
        print("spec error: %s" % e, file=sys.stderr)
        return 1

    if a.json:
        print(json.dumps([{
            "id": b["scene"].get("id"), "type": b["type"], "family": b["family"],
            "end": b["end"], "camera": b["moves"],
            "nodes": [{k: x.get(k) for k in ("id", "label", "shape", "x", "y", "w", "h")}
                      for x in b["nodes"]],
            "beats": b["at"],
        } for b in builds], indent=2, ensure_ascii=False))
        return 0

    if a.split:
        outdir = a.out or Path("out")
        outdir.mkdir(parents=True, exist_ok=True)
        for b in builds:
            p = outdir / ("%s.html" % (b["scene"].get("id") or "scene%d" % b["idx"]))
            p.write_text(page(spec, [b], rate))
            print("%s  %s  runs %ss  still at --at %s"
                  % (p, b["type"], n(b["end"]), n(b["settle"] + 0.12)))
        return 0

    out = a.out or a.spec.with_suffix(".html")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page(spec, builds, rate))
    # The resting moment of each scene: after its camera has pulled back and
    # before the seam takes it away. Screenshotting the default 4s on a page
    # with a camera move lands mid-push and the still comes out zoomed.
    rest, off = [], 0.0
    for i, b in enumerate(builds):
        last = i == len(builds) - 1
        # The rest window, not the scene's last frame: during a seam both
        # scenes are on screen at once, which is right in motion and useless as
        # a still.
        rest.append(round(off + b["settle"] + 0.12, 2))
        off = round(off + b["end"] - (0.0 if last else 0.42), 2)
    print("%s  %d scene(s)  ~%ss at rate %s" % (out, len(builds), n(off), n(rate)))
    print("still frames: %s" % "  ".join("--at %s" % n(t) for t in rest))
    print("next: python3 scripts/build.py %s --png --at %s" % (out, n(rest[0])))
    return 0

if __name__ == "__main__":
    sys.exit(main())
