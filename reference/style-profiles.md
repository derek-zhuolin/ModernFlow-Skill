# Style profiles

## Contents

- The two profiles and when each fits
- Canvas and the 2x rule
- soft-gradient: building the colour field
- editorial-paper: flat paper
- Typography roles
- The grey ramp is darker than it looks — and why
- Adapting a landscape layout to vertical
- Adding a third profile

Machine-readable values live in `assets/tokens.json`; the CSS that implements
them is `assets/base.css`. This file is the reasoning.

---

## The two profiles

| | `soft-gradient` | `editorial-paper` |
| --- | --- | --- |
| Register | current, warm, product-launch | calm, printed, technical essay |
| Paper | `#fbfdfd` near-white | `#f5f5f5` warm grey |
| Ink | `#17181a` | `#2d3142` |
| Accent | `#0071ec` blue | `#eb6c36` orange (`#a33f14` as text) |
| Display type | Inter 900, tight tracking, often uppercase | Instrument Serif 400 |
| Cards | white, floating on a soft shadow | white, drawn with a hairline border |
| Background | two or three blurred colour fields | flat, optional dot grid |
| Motion | quick — 300–420ms | measured — 380–500ms |
| Best at | vertical social, product explainers | landscape figures, architecture, decision docs |

Switch with `data-profile="…"` on the stage element. Nothing else changes:
same classes, same motion vocabulary, same scripts.

---

## Canvas and the 2x rule

**Author in viewBox units at half the output size, render at 2x.**

| Orientation | viewBox | Output |
| --- | --- | --- |
| landscape | `0 0 960 540` | 1920×1080 |
| portrait | `0 0 540 960` | 1080×1920 |
| square | `0 0 720 720` | 1080×1080 |

So `font-size: 54px` in the SVG lands as 108px in the render. Every coordinate
divisible by 4.

Why halve it: the numbers stay small enough to hold in your head while doing
layout maths, and one multiplier converts the whole figure to any output size.

`check_contrast.py --scale` must match, because WCAG's large-text allowance is
defined in rendered pixels.

---

## soft-gradient: building the colour field

Three parts, in this order, behind everything:

1. **Paper.** Flat `--paper` on the stage.
2. **Colour fields.** Two or three big blurred ellipses. One warm
   (`--glow-warm`), one or two cool (`--glow-cool`). Push them to the edges so
   they bleed off-canvas — a field fully inside the frame reads as a blob;
   one that runs off the edge reads as light.
3. **Grain.** A full-canvas `feTurbulence` desaturated to grey at `opacity
   0.045`.

**Each gradient needs eight stops, not three.** A field this large and this low
in contrast shows concentric banding when interpolated across three stops.
Follow a `(1 - t²)²` falloff:

```
t     0     .15    .30    .45    .60    .75    .90   1
mul  1.00   .955   .828   .638   .410   .191   .036  0
```

Multiply by the field's peak opacity (0.95 warm, 0.80 cool) for the stop values.

**The grain is not texture, it is dithering.** Smooth stops fix the SVG side;
8-bit video encoding still quantises a gradient this gradual into rings. Static
noise breaks the quantisation boundaries. Use a fixed `seed` so every frame is
identical — animated noise destroys deterministic rendering and costs bitrate.

The field never moves. A slowly drifting background is idle wobble.

---

## editorial-paper: flat paper

No fields, no grain. Optional 22×22 dot pattern at 10% ink, at ~55% opacity —
use it for long-form hero figures, not by default.

Cards are **drawn**, not floated: `dm-card-lined` (white fill, 1px ink stroke),
no shadow. Mixing the two card treatments in one figure looks like an accident.

The `primitive-sketchy` displacement filter belongs here: `feTurbulence`
`baseFrequency 0.02` + `feDisplacementMap scale 1.2–1.4` over the stroke layer
gives lines a drawn-by-hand quality. Keep the scale under ~3 or it starts
chewing glyphs.

---

## Typography roles

Both profiles fill the same slots; only the families change.

| Class | Role | soft-gradient | editorial-paper |
| --- | --- | --- | --- |
| `dm-display` | the big word | Inter 900 · 86px | Instrument Serif 400 |
| `dm-title` | headline | Noto Sans SC 900 · 54px | Instrument Serif 400 |
| `dm-eyebrow` | section label | Inter 500 · 11px · `.2em` · caps | Geist Mono 500 |
| `dm-node` | node name | Noto Sans SC 700 · 17px | Geist 600 |
| `dm-sub` | node sublabel | Inter 500 · 9px · `.14em` · caps | Geist Mono 400 |
| `dm-edge` | edge label | 12px | Geist Mono |
| `dm-lede` / `dm-tag` / `dm-num` | body / corner tag / section number | — | — |

Three families maximum: one display, one text, one mono. A fourth reads as
indecision.

**CJK has no glyphs in Inter, Geist or Instrument Serif.** Every stack must
carry a Noto fallback or the text silently drops to a system font and the
render stops being reproducible. The stacks in `base.css` already do this.

---

## The grey ramp is darker than it looks — and why

Reference imagery in this register uses very pale grey labels. Sampled and
measured, a pale label over a warm colour field lands near **2.1:1** — it fails
WCAG AA by a wide margin.

Both profiles ship **corrected** values:

| Token | Naive value | Shipped | Why |
| --- | --- | --- | --- |
| `soft` (soft-gradient) | `#9aa0a6` | `#585c60` | 2.12:1 over the warm field |
| `soft` (editorial-paper) | `#7a8399` | `#586377` | 3.48:1 on paper |
| accent as text (editorial-paper) | `#eb6c36` | `#a33f14` | 2.86:1 as text |

The look survives the correction. What carries this register is the **weight
contrast** (900 display against 500 labels), the wide tracking, the generous
whitespace and the colour fields — not how pale the small text is.

`--accent` is for strokes and fills; `--accent-text` is the only accent value
allowed on type. In `soft-gradient` they coincide; in `editorial-paper` they
must not. Always reference `--accent-text` for type so switching profiles
cannot break the gate.

---

## Adapting a landscape layout to vertical

Do not just re-crop. A landscape figure moved to 1080×1920 leaves the bottom
third empty and reads as unfinished.

1. **Push the figure down and enlarge it.** Target `y` 250–760 of a 960-tall
   viewBox, not 200–500.
2. **Re-proportion round figures.** A loop's ellipse goes from wide
   (`rx > ry`) to tall (`ry > rx`).
3. **Move side rails under or into the figure.** A right-hand note rail costs
   width you no longer have.
4. **Cut a node.** Vertical carries roughly one fewer node at readable size.
5. **Keep the chrome anchored** — eyebrow at `y=92`, footer rule at `y=800`,
   section number at `y=846`. Fixed chrome slots are what make a set of scenes
   look like one piece.

If the design has a slot for footage or a portrait video window and there is no
footage: leave it empty and enlarge the figure to fill the space. Do not put a
placeholder there.

---

## Adding a third profile

1. Add the block to `assets/tokens.json` — every key the existing two have.
2. Add the matching `[data-profile="…"]` block to `assets/base.css`.
3. Add its families to `PROFILE_FAMILIES` in `scripts/fetch_fonts.py`.
4. Run `check_contrast.py --profile <new>` against the template and correct the
   ramp until it exits 0 **before** using it for anything.

Step 4 is not optional. Both shipped profiles needed correcting, and the gate
is what found it.
