---
name: modernflow
description: Builds editorial diagrams that move — flowcharts, loops and cycles, decision trees, layer stacks, side-by-side comparisons — and ships them as a still PNG, a self-playing HTML animation, or a narrated video. Provides two modern visual profiles, a pure-CSS motion vocabulary, WCAG-AA contrast gating, and glyph-level font subsetting. Use when someone asks for a diagram, flowchart, loop or cycle graphic, process or architecture figure, explainer visual, concept comparison, or a short vertical or landscape video built from diagrams. The still and animated tiers need nothing but a browser; the video tier uses HyperFrames when it is installed.
license: MIT
---

# ModernFlow

Editorial diagrams, animated. One visual system, one motion vocabulary, three
output tiers that share a single timing table so they cannot drift apart.

The diagram grammar — shape carries meaning, one accent per figure, explicit
per-type layout contracts — is adapted from
[diagram-design](https://github.com/cathrynlavery/diagram-design) (MIT). That
project is a **reference, not a dependency**; see `NOTICE`.

## Pick the tier first

| The ask | Tier | Needs | Produces |
| --- | --- | --- | --- |
| "make me a diagram / flowchart / figure" | **still** | nothing (PNG needs Chrome) | `.html` + `.png` |
| "make it animate", "a looping graphic", "something for a slide" | **motion** | nothing | one self-playing `.html` |
| "make a video", "a 20-second explainer", "add narration" | **video** | HyperFrames | `.mp4` |

**still** and **motion** are the same file — the animation is pure CSS, so a
still is just that file screenshotted. Never reach for the video tier when the
user asked for a picture.

If the video tier is requested and HyperFrames is absent: build the **motion**
tier, hand it over, and say plainly that MP4 needs `npm i -g hyperframes`. Do
not silently downgrade and do not invent a rendering pipeline.

## Quick start

```bash
SKILL=path/to/modernflow          # wherever this skill is installed

cp "$SKILL/assets/template.html" figure.html
# edit figure.html: replace the figure, the chrome text, and the --at times

python3 "$SKILL/scripts/fetch_fonts.py" figure.html --profile soft-gradient
python3 "$SKILL/scripts/check_contrast.py" figure.html      # gate — must exit 0
python3 "$SKILL/scripts/build.py" figure.html --png         # self-contained html + png
```

`build.py` inlines the fonts and the stylesheet, so the output `.html` is one
portable file. Open it in any browser and it plays.

## The build loop

Work this list top to bottom. Steps 5 and 6 are gates, not suggestions.

- [ ] **1 · Choose profile and canvas.** `soft-gradient` or `editorial-paper`;
      landscape / portrait / square. → `reference/style-profiles.md`
- [ ] **2 · Choose the diagram type** from the subject, not from taste. A cycle
      that feeds itself is a loop; a path that ends is a flowchart. →
      `reference/diagram-types.md`
- [ ] **3 · Lay out the geometry** on the 4px grid, inside the budget: **≤9
      nodes, ≤12 edges, 1 accent** per figure. Compute edge endpoints from the
      node boxes, never from a fixed gap.
- [ ] **4 · Time it.** Write `--at` on every animated element. With narration,
      derive every `--at` from measured audio, never from an estimate. →
      `reference/motion-grammar.md`
- [ ] **5 · Gate: contrast.** `python3 scripts/check_contrast.py figure.html`
      must exit 0. If it fails, darken the **token**, not the one rule.
- [ ] **6 · Gate: look at it.** Render the PNG and actually read the image.
      Numbers on the page must be real, computed values — never placeholders.
- [ ] **7 · Ship.** `build.py --png` for still/motion.
      For video → `reference/video-pipeline.md`.

## Non-negotiables

**Shape carries type; colour never does.** Stadium = start/end. Rectangle =
step. Diamond = decision. Ring + centre hub = loop. Recolouring a rectangle
does not turn it into a decision.

**One accent per figure.** The accent marks the figure's *organ* — the edge
that closes a loop, the terminal that actually completes. Two accents erase the
signal. Use `--accent-text` for type: in `editorial-paper` the accent measures
2.86:1 as text and is stroke-only.

**Every edge out of a decision is labelled.** An unlabelled branch is a bug.

**Contrast is not a style choice.** The pale-grey label that defines this
register measures ~2.1:1 over a colour field. The gate exists because the eye
does not catch this; the ratio has to be computed.

**Real content, never placeholders.** Grey skeleton bars, lorem text, generic
circles and blocks all read as an unfinished mockup no matter how well styled.
Every label is a readable field; every number is read off the actual artefact.

**Motion performs, then stops.** Everything that enters must also leave (except
on a deliberate end card). Nothing loops idly — a repeating pulse stops reading
as emphasis and starts reading as a nervous tic.

## References

Read only what the task needs.

| File | When |
| --- | --- |
| `reference/style-profiles.md` | Choosing or extending a profile; canvas sizes; building the colour-field background; adapting a landscape layout to vertical |
| `reference/diagram-types.md` | Choosing a diagram type; the layout contract and geometry maths for each |
| `reference/motion-grammar.md` | Timing, entrances and exits, scene seams, syncing to narration, the motion gates |
| `reference/video-pipeline.md` | The MP4 tier: HyperFrames project layout, narration, sound, render |
| `reference/gotchas.md` | Something renders wrong, silently degrades, or fails a gate |
| `evals/` | Three end-to-end scenarios with expected behaviour, for testing changes to this skill |

## Scripts

All stdlib Python 3, no `pip install`.

| Script | Does |
| --- | --- |
| `scripts/fetch_fonts.py` | Downloads only the glyphs the page uses; writes `fonts.css` |
| `scripts/build.py` | Inlines CSS into one portable file; optionally renders a PNG |
| `scripts/check_contrast.py` | WCAG-AA gate over every text role against every background it can sit on |

`build.py --png` finds Chrome on its own. Point it somewhere specific with
`MODERNFLOW_CHROME=/path/to/chrome`. With no Chrome it still writes the
HTML and says so — the deliverable is not lost.
