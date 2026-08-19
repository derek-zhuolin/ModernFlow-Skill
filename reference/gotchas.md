# Gotchas

Every entry here is a failure that shipped looking fine. They share a shape:
**the page still renders**, so nothing alerts you. Each one is listed with how
it presents, why it happens, and the fix.

## Contents

1. Fonts silently fall back to system fonts
2. The pale grey label fails accessibility
3. Card shadows clip, or vanish under the animation
4. Large soft gradients band into rings
5. Loop arcs float free of their nodes
6. Sound effects overlap on the same track
7. The contrast checker flags an element mid-fade
8. A short line with a Latin word trips a duration check
9. A vertical layout leaves the bottom third empty
10. Placeholder numbers survive to the render

---

## 1 · Fonts silently fall back to system fonts

**Presents as:** looks right on your machine, different on someone else's.
Nothing errors.

**Why:** `fonts.css` writes `url(assets/fonts/…)` relative to the **HTML
document**. Loaded with `<link>`, the browser resolves those paths against the
CSS file's own directory instead — `assets/fonts/assets/fonts/…` — and every
face 404s. The page renders in a system font and looks plausible.

Static linters miss it too: they parse one file and do not follow `<link>`.

**Fix:** inline the font CSS into the page. `scripts/build.py` does this. Never
`<link>` a stylesheet whose `url()` paths are document-relative.

---

## 2 · The pale grey label fails accessibility

**Presents as:** a finished-looking page that fails an accessibility review.

**Why:** the pale label is the signature move of this design register. Over a
warm colour field it measures around **2.1:1** against a 4.5:1 requirement. The
eye does not catch it — contrast is a computed ratio, not an impression.

**Fix:** run `scripts/check_contrast.py`, which tests every text role against
the paper *and* against each colour field at full strength. Darken the token,
not the individual rule, so the set stays one family. Both shipped profiles
needed this; the gate is what found it.

---

## 3 · Card shadows clip, or vanish under the animation

**Presents as:** a straight hard edge partway through a soft shadow, or the
shadow disappearing entirely once the element animates.

**Why:** two separate problems that look similar.
- CSS `filter: drop-shadow()` on an SVG element clips to that element's default
  filter region (`-10%` / `+120%`), cutting a wide soft shadow.
- The entrance animation animates the CSS `filter` property. A CSS drop-shadow
  on the same element is simply overwritten.

**Fix:** define an SVG `<filter>` with a generous region (`x=-40% y=-40%
width=180% height=200%`) and apply it to the **shape** with
`filter="url(#dm-lift)"`, while the animation classes go on the **parent
group**. They then never touch the same property.

---

## 4 · Large soft gradients band into rings

**Presents as:** faint concentric rings across the background, most visible
after video encoding.

**Why:** two causes stack. A radial gradient with three stops interpolates
linearly between them, and 8-bit encoding quantises a gradient this gradual
into steps.

**Fix:** both at once. Eight stops on a `(1 - t²)²` falloff, plus a static
`feTurbulence` grain at ~4.5% opacity over the whole canvas. The grain is
dithering, not texture. Use a fixed `seed` so every frame is identical; it
costs some bitrate and is worth it.

---

## 5 · Loop arcs float free of their nodes

**Presents as:** an arc that starts 70px away from the card it should leave,
looking like a stray line.

**Why:** placing arcs with a fixed angular gap (e.g. 22° either side of each
station). That works on a circle with small nodes. On a tall ellipse with wide
cards, the same 22° lands far outside the card boundary.

**Fix:** solve for the angle at which the ellipse crosses the card's own edge
(`sin θ = (y_edge - cy)/ry`, `cos θ = (x_edge - cx)/rx`) and start the arc
there. Worked example in `reference/diagram-types.md` → Loop.

---

## 6 · Sound effects overlap on the same track

**Presents as:** the composition checker rejects the project with
`overlapping_clips_same_track`, often by only a few milliseconds.

**Why:** spacing cues by feel while the files differ in length by an order of
magnitude. A whoosh is 0.575s, a click 0.366s, a chime 2.5s. Two "short"
clicks 0.35s apart overlap; a whoosh followed 0.4s later by a click overlaps.

**Fix:** space against the **measured** file durations, and give each track a
semantic job (steps / accents / decisions / transitions) rather than filling
whatever is free. Put transition sounds on their own track — they are the long
ones and they are what breaks the arithmetic.

---

## 7 · The contrast checker flags an element mid-fade

**Presents as:** a contrast failure on an element that is obviously fine.

**Why:** the checker samples at fixed times. If a sample lands while an element
is 17% through its fade-in, it measures the half-transparent state.

**How to tell:** change the element's opacity and re-measure. If the reported
ratio moves by the same factor, you are looking at a sampling artefact, not a
defect. Then compute the settled state by hand — e.g. `rgba(255,255,255,.8)`
over `#17181a` is **12.0:1**.

**Fix:** nothing. Do not darken a design to satisfy a mis-sampled reading —
verify first, then leave it alone and say why.

---

## 8 · A short line with a Latin word trips a duration check

**Presents as:** a sanity check that is meant to catch truncated audio rejects
every take of certain lines.

**Why:** counting characters to predict a spoken duration. "Loop" is four
characters but one syllable. In a mostly-CJK line, per-letter counting inflates
the expected duration and the real audio looks impossibly short.

**Fix:** count each Latin run as roughly two character-equivalents
(`re.sub(r"[A-Za-z0-9]+", "AA", text)`) before dividing by a
characters-per-second rate.

---

## 9 · A vertical layout leaves the bottom third empty

**Presents as:** a portrait render that looks unfinished, with content crowded
into the top.

**Why:** a landscape composition re-cropped rather than re-laid-out. It also
happens when the source design had a slot for a portrait video window that you
do not have footage for.

**Fix:** push the figure down and enlarge it (target `y` 250–760 of a 960
viewBox), re-proportion round figures to be tall rather than wide, and drop one
node. Leave the empty slot empty and let the figure grow into it — never fill
it with a placeholder.

---

## 10 · Placeholder numbers survive to the render

**Presents as:** a confident-looking figure stating something false.

**Why:** a node count, duration or dimension written while drafting and never
revisited.

**Fix:** read every number off the artefact before shipping — count the nodes,
probe the file, measure the render. If a spec row's value cannot be read from
something real, delete the row. This is the one gotcha with no technical cause
and the highest cost.
