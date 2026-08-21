# Video pipeline

The MP4 tier. Read this **only** when the deliverable is a video file.

Everything else in this skill works with nothing installed. This tier needs
[HyperFrames](https://hyperframes.heygen.com) (`npm i -g hyperframes`), which
renders HTML compositions to MP4 frame by frame.

**If HyperFrames is not installed:** build the motion tier instead, hand over
the self-playing HTML, and say plainly that MP4 needs it. A browser-based screen
recording of that HTML is a legitimate fallback. Do not improvise a renderer.

## Contents

- What changes from the standalone tier
- Project layout
- Narration first, always
- Deriving the timeline
- Sound
- Render and verify

---

## What changes from the standalone tier

Only the animation driver. The tokens, classes, geometry and timing table are
identical.

| | Standalone | Video |
| --- | --- | --- |
| Animation | CSS `@keyframes` + `--at` | GSAP timeline, seekable |
| Timing source | `--at` inline | the same numbers, passed to GSAP |
| Scenes | one file | one file per scene, mounted by a parent |
| Fonts | inlined once | inlined into **every** scene file |

Frame-by-frame capture means the runtime must be **seekable**: given any time
*t*, the composition must resolve to exactly one state. So no `Date.now()`, no
`Math.random()`, no network calls, no CSS animations (they cannot be seeked).

GSAP core does not parse `cubic-bezier()` strings — pass named eases
(`expo.out`, `power3.in`, `power4.inOut`) or they silently degrade to linear.

---

## Project layout

```
project/
├── index.html                 root timeline; mounts scenes, owns audio tracks
├── compositions/frames/
│   ├── s0.html … s3.html      one per scene, each a <template>
├── src/motion.js              shared motion vocabulary (GSAP)
├── assets/
│   ├── fonts/                 subsetted woff2 + fonts.css
│   ├── vo/                    narration wav + its timing table
│   └── sfx/                   sound effects
└── scripts/                   vo builder, font fetch, index generator
```

Scenes mount with `data-composition-src`. Each scene registers a paused
timeline on `window.__timelines["<id>"]`; the framework seeks it.

Every timed element needs `class="clip"` plus `data-start`, `data-duration`,
`data-track-index`. Every `<audio>` needs an `id` — without one it renders
silent and does not warn.

**Fonts must be inlined into every scene file**, not just the root. Scene files
are validated individually, and a `<link>` breaks as described in
`gotchas.md` § 1.

---

## Narration first, always

Build audio **before** the picture. Frame timings are derived from the audio;
doing it the other way round means re-timing every scene.

Method, and the reason for each step, in `motion-grammar.md` → "Syncing to
narration". In short: split into short lines, synthesise each separately, trim
silence, concatenate with gaps you choose, and record each line's exact start
and duration.

Set act-ending gaps by **how long the picture still needs to perform**. If the
accent beat needs 1.1s after the last word, the gap is 1.1s — not what the
punctuation suggests.

### On synthesised emotion

Voice-cloning endpoints often accept an `emotion` parameter and return success
without applying it. Before relying on one, **verify it does anything**: call
the same text with identical parameters three times and compare output sizes.
If baseline runs vary as much as the parameter changes it, the parameter is
being ignored and any perceived improvement is imagination.

What reliably adds life, in order of effect:

1. **Write spoken sentences.** Short clauses, natural connectives. Largest
   single factor.
2. **Vary the gaps.** Uneven pauses are most of what makes speech sound human.
3. **Nudge pitch and volume** (~1.04 / ~1.08). Brighter and more forward.
4. **Synthesise several takes and pick.** Since synthesis is non-deterministic,
   generate 3 per line and select the one with the widest RMS dynamic range
   (p90 / p50 of voiced frames) — a measurable proxy for expressiveness.

---

## Deriving the timeline

Generate `index.html` from the narration timing table rather than hand-writing
`data-start` values. One script means changing a line of copy cannot leave
sixty attributes stale.

Scene boundary = the scene's last line's end + that line's gap. Add a small
head offset (~0.45s) so the title lands before the first word, and a tail
(~0.9s) so the end card holds.

Inside a scene, pin beats to **line starts**, relative to the scene start.
Changing narration speed changes every anchor — re-pin against the new table,
do not scale the old numbers.

---

## Sound

Give each track a semantic job:

| Track | Carries |
| --- | --- |
| A | ordinary steps — soft clicks |
| B | accents and dead-ends — impacts, errors, pings |
| C | decisions and completions — clicks, chimes, sparkles |
| D | scene transitions — whooshes |

Transitions get their own track because they are the long files and they are
what breaks the spacing arithmetic (`gotchas.md` § 6). Space every cue against
**measured** durations. Limit heavy impacts to two per piece.

---

## Render and verify

```bash
npm run check      # lint + runtime + layout + contrast, in one gate
npx hyperframes render -o renders/out.mp4
```

`check` must be clean before rendering. After rendering, verify the artefact
rather than assuming:

```bash
ffprobe -v error -show_entries stream=codec_name,width,height,r_frame_rate \
        -show_entries format=duration,size -of default=nw=1 renders/out.mp4
ffmpeg -hide_banner -i renders/out.mp4 -af ebur128=peak=true -f null -   # true peak < -1 dBFS
```

Then pull two or three frames out of the **rendered file** — not the preview —
and look at them. Seams and mid-animation states are where problems hide, and
they are invisible in a still preview.

---

## Camera moves and rate in the video tier

The standalone page expresses a camera move as a `mf-push` / `mf-pull` pair of
CSS animations. GSAP has no equivalent trick and does not need one — it has a
timeline, so the dwell is just a gap:

```js
const cam = { zx: 678, zy: 315, k: 1.7 };
tl.to("#cam", { x: cx - cam.zx, y: cy - cam.zy, scale: cam.k,
                transformOrigin: `${cam.zx}px ${cam.zy}px`,
                duration: 0.62, ease: "power4.inOut" }, 3.2)
  .to("#cam", { x: 0, y: 0, scale: 1, duration: 0.62, ease: "power4.inOut" }, 5.4);
```

Two things to carry over rather than re-derive:

- **The origin must match the push.** GSAP's `transformOrigin` is per-tween; set
  it on both, or the pull returns to a different centre than the push left.
- **Named eases only.** The GSAP core does not parse `cubic-bezier()` strings
  and falls back to linear without saying so. `base.css` bakes the curves in as
  cubic-beziers for the CSS tier; the video tier uses the names.

`rate` is not a playback-speed setting. Render at 1× and let `layout.py` bake
the compression into the beats — speeding up the finished MP4 speeds the
narration and the picture together, which is the opposite of the point, and
takes every element duration below its floor on the way.

`layout.py --split` writes one page per scene, which is the shape the video
tier wants: one clip per scene, each starting at its own zero.