# ModernFlow

**Describe what a diagram *means*; get back an editorial figure that moves — solved geometry, timed beats, and a camera that pushes in on the point.** An agent skill covering 41 diagram types across 7 layout families.

```bash
git clone https://github.com/derek-zhuolin/ModernFlow-Skill ~/.claude/skills/modernflow
```

[![41 diagram types, scrubbable](docs/assets/hero.png)](https://derek-zhuolin.github.io/ModernFlow-Skill/)

*↑ 4 of the 41.* **[▶ Scrub all 41 in the browser](https://derek-zhuolin.github.io/ModernFlow-Skill/)** — nothing to install. One slider drives every figure's timeline at once, so you can watch the build order, catch the camera moves, and flip both style profiles. Every card is that type's **real solver output**, so the page doubles as a smoke test.

[![CI](https://github.com/derek-zhuolin/ModernFlow-Skill/actions/workflows/ci.yml/badge.svg)](https://github.com/derek-zhuolin/ModernFlow-Skill/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.9%2B-black.svg)](https://www.python.org)
[![deps](https://img.shields.io/badge/dependencies-none-black.svg)](#install)
[![License: MIT](https://img.shields.io/badge/License-MIT-black.svg)](./LICENSE)

**English** | [中文](./README.zh-CN.md) — the Chinese doc is the full story; this page is the tour.

---

## What it is

You hand your agent (Claude Code / Codex / Cursor / …) a subject. It reads this skill, writes a spec that says what the figure *means*, and the solver computes every coordinate and every beat from it.

**Nothing in a spec is a coordinate.** That is the whole design:

| You change | What re-solves |
|---|---|
| a label | its box width, both edges into it, the arrowhead angle |
| a node's order | the beat table, and every beat after it |
| the canvas to portrait | the whole layout, not a squashed version of the landscape one |
| the narration rate | every gap — durations stay put, floored at 300ms |
| an accent | which node gets the ring, and where the camera goes |

A hand-placed figure stops being correct the moment its content changes, and still renders. That failure has no error message, which is why this is a solver rather than a template.

## Choosing the type

Pick from the subject's shape, not from taste. The discriminator is one sentence you should be able to say out loud:

| Your sentence | The type |
|---|---|
| "steps with branches, and some path ends" | `flow` |
| "the last step feeds the first, and something accumulates" | `loop` |
| "each level rests on the one below" | `layers` |
| "one parent, many children — containment, not flow" | `tree` |
| "options scored on two axes, position *is* the claim" | `quadrant` |
| "work over calendar time, and the overlap is the point" | `gantt` |
| "sets that share members" | `venn` |
| "a number I want remembered" | `stat-row` |

41 types, 7 geometries. **Eight of them carry their own solver** — `timeline`, `sequence`, `swimlane`, `gantt`, `radar`, `treemap`, `mindmap`, `er` — because the generic family version would state something untrue. A gantt whose bars are all one column long has lost the schedule conflict it was drawn to show.

## Three tiers, one timing table

| The ask | Tier | Needs | Produces |
|---|---|---|---|
| "make me a diagram" | **still** | a browser | `.html` + `.png` |
| "make it animate" | **motion** | a browser | one self-playing `.html` |
| "make a video" | **video** | HyperFrames | `.mp4` |

Still and motion are the **same file** — the animation is pure CSS, so a still is that file screenshotted at a chosen moment. **HyperFrames is only for the MP4 tier.** Everything else needs nothing but Python and a browser.

Any page can be frozen at any instant: append `?t=4.4` to the URL, or call `mfSeek(4.4)` in the console. `build.py --png --at 4.4` uses the same mechanism — which is why a still is reproducible instead of depending on how fast a machine reached four seconds.

## The camera

Motion moves the elements; the camera moves the frame. Fusing them is the usual mistake — scaling up the node you want looked at says *the node grew*, not *you got closer*, and welds the zoom to that node's entrance so it can never be re-cut.

A move is a `push` / `pull` pair that are exact inverses about the same origin, so a dwell of any length exists with no JavaScript and no keyframe percentage. `camera: "auto"` is the default and picks from a seeded die — `punch`, `survey`, `drift`, or none — and **refuses on any figure with fewer than four nodes**, whatever the die says. There is nothing to go and read on a three-node figure, and a camera move with no referent is idle motion in better clothes.

## Variation

Eight scenes built the same way look like eight of the same scene. Varying **by index** is worse than not varying: index 0 is always the same gesture, so every deck ever built shares one rhythm.

Entrances and transitions come from a **seeded permutation** instead — the same spec always yields the same film, because a re-render that quietly became a different cut would desync narration timed to the last one. The dice are constrained: no seam repeats the one before it, and distinct kinds must reach ⌈seams / 2⌉, which adjacent-difference alone does not give you (`A B A B` satisfies it and uses two kinds forever).

## Install

```bash
git clone https://github.com/derek-zhuolin/ModernFlow-Skill ~/.claude/skills/modernflow
python3 ~/.claude/skills/modernflow/scripts/doctor.py
```

**Python 3.9+ and nothing else.** No pip, no npm, no lockfile — every script is standard library. Chrome is needed only to rasterise a PNG; without it you still get the HTML and are told so.

Cloned somewhere else, or run more than one agent? `python3 scripts/install.py` detects Claude Code, Codex, Cursor, Gemini CLI, Crush and OpenCode and installs into each one it finds.

**Same picture on every machine.** The font bundle is committed — 16 subsetted faces covering both profiles, ~1.2MB — so a fresh clone renders offline and identically. A missing glyph does *not* fail: the browser substitutes a system face that usually exists on the machine that authored the page and on nobody else's. `scripts/check_fonts.py` gates against exactly that.

## Quality gates

Each exits non-zero and each catches something that otherwise **renders fine and is wrong**:

- **Budget** — over 9 nodes, 12 edges, or 1 accent per figure; a dangling edge; an unlabelled branch out of a decision; overlapping camera moves. Checked before a single byte is written.
- **Contrast** — every text role against every background it can sit on, at rendered size, to WCAG AA. The pale grey label that defines this register measures ~2.1:1 over a colour field, and the eye does not catch it.
- **Glyph coverage** — every character on the page is in the shipped bundle.
- **Determinism** — `doctor.py` solves the gallery twice and compares hashes.
- **Look at it** — `scripts/playground.py spec.json -o out.html` puts every scene on one scrubbable page. Gate seven is only real if it is cheap.

## Credit

The diagram grammar — shape carries meaning, per-type layout contracts, complexity budgets, one accent per figure — is adapted from [diagram-design](https://github.com/cathrynlavery/diagram-design) (MIT). A reference, not a dependency; see [NOTICE](./NOTICE).

## License

[MIT](./LICENSE)
