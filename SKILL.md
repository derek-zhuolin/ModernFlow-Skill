---
name: modernflow
description: Builds editorial diagrams that move — flowcharts, loops and cycles, decision trees, layer stacks, timelines, matrices, funnels, comparisons, 41 types across 7 layout families — and ships them as a still PNG, a self-playing HTML animation, or a narrated video. Figures are solved from a semantic spec rather than hand-placed, so labels, geometry, beats and camera moves re-derive together. Provides two modern visual profiles, a pure-CSS motion and camera vocabulary, frame-exact seeking, WCAG-AA contrast gating, and glyph-level font subsetting. Use when someone asks for a diagram, flowchart, loop or cycle graphic, process or architecture figure, explainer visual, concept comparison, or a short vertical or landscape video built from diagrams — especially a dense subject that needs to zoom in on its own detail. The still and animated tiers need nothing but a browser; the video tier uses HyperFrames when it is installed.
license: MIT
---

# ModernFlow

Editorial diagrams, animated. One visual system, one motion vocabulary, three
output tiers that share a single timing table so they cannot drift apart.

Figures are **solved, not placed**: a spec says what the figure means — nodes,
edges, which one is the point, where the camera looks — and `scripts/layout.py`
computes every coordinate and every beat from it. Change a label and the box,
the edges into it, the timing and the camera all follow. That is what makes the
figure survive an edit; a hand-placed one is wrong the moment its content
changes, and still renders.

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

# 1. write spec.json — meaning, not coordinates. See reference/spec.md.
python3 "$SKILL/scripts/layout.py" spec.json -o figure.html
#    prints the running time and the resting moment of each scene

python3 "$SKILL/scripts/fetch_fonts.py" figure.html --profile soft-gradient
python3 "$SKILL/scripts/check_contrast.py" figure.html      # gate — must exit 0
python3 "$SKILL/scripts/build.py" figure.html --png --at 4.4
```

`build.py` inlines the fonts and the stylesheet, so the output `.html` is one
portable file. Open it in any browser and it plays; append `?t=4.4` to freeze
it at any moment, or call `mfSeek(4.4)` in the console.

`assets/template.html` is still there for a one-off figure whose geometry you
genuinely want to hand-place. Everything else should go through a spec.

## The build loop

Work this list top to bottom. Steps 6 and 7 are gates, not suggestions.

- [ ] **1 · Cut the text into scenes** at its turns, not its paragraphs, and
      name the shape of each scene's subject in one sentence. →
      `reference/spec.md`
- [ ] **2 · Choose the diagram type** by reading it off that sentence, not from
      taste. A cycle that feeds itself is a loop; a path that ends is a
      flowchart. 41 types, 7 families. → `reference/diagram-types.md`
- [ ] **3 · Choose profile and canvas.** `soft-gradient` or `editorial-paper`;
      landscape / portrait / square. → `reference/style-profiles.md`
- [ ] **4 · Write the spec** — nodes, edges, one accent, camera. Budget **≤9
      nodes, ≤12 edges, 1 accent** per scene; at rate 1.3 make that ≤6 nodes.
      `layout.py` gates all of it before it writes anything.
- [ ] **5 · Set the rate.** With narration, derive it from measured audio, never
      from an estimate; `rate` compresses gaps, not durations. →
      `reference/motion-grammar.md`
- [ ] **6 · Gate: contrast.** `python3 scripts/check_contrast.py figure.html`
      must exit 0. If it fails, darken the **token**, not the one rule.
- [ ] **7 · Gate: look at it.** `python3 scripts/playground.py spec.json -o
      playground.html` puts every scene on one page with a scrubber; open it
      and drag through. For a single figure, render the PNG **at the resting
      moment `layout.py` printed**. Numbers on the page must be real, computed
      values, never placeholders.
- [ ] **8 · Ship.** `build.py --png` for still/motion.
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

**The camera moves the frame; entrances move the elements.** They are different
tools. Scaling up the node you want looked at says the node grew. Pushing the
frame into it says you got closer, and it can be re-cut without touching the
figure. Every push has a pull, and a move with nothing to read at the end of it
is idle motion wearing a better coat.

## References

Read only what the task needs.

| File | When |
| --- | --- |
| `reference/spec.md` | Writing the spec; decomposing text into scenes; the schema; frame seeking |
| `reference/style-profiles.md` | Choosing or extending a profile; canvas sizes; building the colour-field background; adapting a landscape layout to vertical |
| `reference/diagram-types.md` | Choosing a diagram type; the layout contract and geometry maths for each |
| `reference/motion-grammar.md` | Timing, entrances and exits, camera moves, scene seams, syncing to narration, pace at rates above 1, the motion gates |
| `reference/video-pipeline.md` | The MP4 tier: HyperFrames project layout, narration, sound, render |
| `reference/gotchas.md` | Something renders wrong, silently degrades, or fails a gate |
| `docs/gallery.json` | One scene per family, as a worked example and as the fixture the playground opens with |
| `evals/` | Three end-to-end scenarios with expected behaviour, for testing changes to this skill |

## Scripts

All stdlib Python 3, no `pip install`.

| Script | Does |
| --- | --- |
| `scripts/layout.py` | Solves a spec into a page: geometry, beats, camera. Gates the budget first |
| `scripts/playground.py` | Every scene of a spec on one scrubbable page, for gate 7 |
| `scripts/fetch_fonts.py` | Downloads only the glyphs the page uses; writes `fonts.css` |
| `scripts/build.py` | Inlines CSS into one portable file; optionally renders a PNG |
| `scripts/check_contrast.py` | WCAG-AA gate over every text role against every background it can sit on |

`build.py --png` finds Chrome on its own. Point it somewhere specific with
`MODERNFLOW_CHROME=/path/to/chrome`. With no Chrome it still writes the
HTML and says so — the deliverable is not lost.

`build.py --at 4.4` captures second 4.4 of the page's own timeline by seeking
the animations, not by waiting. Anything with a camera move or more than one
scene needs that number chosen; `layout.py` prints it.
