# Motion grammar

## Contents

- The timing table
- Scale: the numbers that decide whether it reads as stiff
- Entrances and exits
- Building a figure: the order things arrive
- Scene seams
- Syncing to narration
- The three gates

Motion here is **pure CSS**. Every animated element carries a class and one
inline `--at` start time. That single number also drives the video tier, so the
standalone HTML and the MP4 cannot drift apart.

```html
<g class="dm dm-pop" style="--at:1.42s"> … </g>
<path class="dm dm-draw dm-flow" style="--at:2.10s" pathLength="1" d="…"/>
```

`pathLength="1"` normalises dash units, so `stroke-dasharray: 1` means "one
full path" regardless of geometry — no JavaScript measurement anywhere.

---

## The timing table

Keep the `--at` values as an explicit list while authoring. Every beat is a
decision about what the viewer looks at next; a figure whose elements all
appear at once has no argument, only content.

Rough shape of a 4–6 second figure:

```
0.00–0.30   chrome: eyebrow, headline
0.45–0.80   rules, footer, section number
1.00–3.20   the figure, node by node
3.20–3.60   the accent beat — the one thing you want remembered
3.90        exit (omit on an end card)
```

---

## Scale

These are the numbers that separate "designed" from "stiff". They are not
style preferences.

| | Value | If you break it |
| --- | --- | --- |
| Element duration | **300–500ms** | Under 250 reads as a pop; over 600 reads as syrup |
| Over-600ms actions | **≤25% of all actions** | Everything feels slow |
| Stagger between siblings | **60–100ms** | Under 45 the eye cannot resolve the order, so the stagger did nothing; over 140 it drags |
| Displacement | **≤24px**, typically 14 | More and elements look thrown |
| Blur paired with movement | **always** | Position changing without sharpness changing is exactly what "hard" looks like |

**Blur and displacement resolve together.** If you take one thing from this
file, take that. An element that slides in perfectly sharp reads as a slide
deck; the same element arriving from `blur(6px)` reads as focus landing.

Easing: `expo.out` entering, `power3.in` leaving, `power4.inOut` for pure
position. `base.css` bakes these in as cubic-beziers. In the video tier, use
GSAP's **named** eases — the GSAP core does not parse `cubic-bezier()` strings
and silently falls back to linear.

Only one thing may exceed 600ms: a deliberate hold that lets the viewer finish
reading. It has to earn it.

---

## Entrances and exits

Four entrances, one exit.

| Class | Motion | Use for |
| --- | --- | --- |
| `dm-rise` | up from +20px | the headline of scene 1 |
| `dm-settle` | down from -14px | eyebrows, and a headline arriving from above |
| `dm-widen` | scale 0.94 → 1 | a headline that should feel like it expands into place |
| `dm-slide` | in from +22px x | a headline following a leftward exit |
| `dm-pop` | +14px, scale 0.985 | nodes and cards (smaller gesture than a title) |
| `dm-out` | up and out, blurring | **everything**, everywhere |

**Vary entrances, fix exits.** Each scene's headline uses a *different*
entrance from the last; every element in every scene leaves the same way. Entry
is where you create interest, exit is where you create continuity.

`dm-tip` for arrowheads — they land *after* their line arrives, never with it.
`dm-flash` for a single emphasis pulse. Never loop it.

---

## Building a figure: the order things arrive

Not all at once, and not left-to-right for its own sake. Follow the causal
chain:

1. **The anchor first** — the hub of a loop, the start of a flow.
2. **Node, then its edge, then the arrowhead.** Three beats, ~120–200ms apart.
   The edge draws *toward* the node it points at, which must already exist.
3. **Branch labels with their branch**, not batched at the end.
4. **The accent last**, with a beat of space before it. It is the punchline;
   punchlines need a pause.
5. **Notes and rails after the figure resolves.**

For a loop, walk it in the direction the arrows point. The viewer is learning a
direction, and building anticlockwise while the arrows point clockwise makes
the figure much harder to read than it should be.

---

## Scene seams

A seam is where one scene ends and the next begins. Rules:

- **Adjacent seams must use different transitions.** Across a piece use at
  least ⌈seams / 2⌉ distinct kinds.
- **The exit direction dictates the entrance direction.** Exit upward → the
  next scene enters from below. Exit leftward with a squeeze → the next enters
  from the right.

| Transition | Exit | Entrance |
| --- | --- | --- |
| push-slide | `y: -16`, blur | from `y: +16` |
| squeeze | `x: -20`, `scale .96`, blur | from `x: +22` |
| blur-crossfade | blur 9px, `scale 1.02` | from blur 5px |
| zoom-through | `scale 1.06`, blur | from `scale 0.94` |

**Leave no gap at the seam.** If the outgoing scene finishes leaving at 7.64s
and the incoming one starts arriving at 7.90s, there is a quarter-second of
empty screen and it reads as a blink. Start the incoming scene's first element
at `--at: 0` and let the outgoing exit run right up to the cut.

Give a seam a semantic reason when you can. Going from a loop to a linear
graph, having the loop squeeze out to the left while the graph pushes in from
the right *says* something: one displaced the other.

---

## Syncing to narration

**Derive every `--at` from measured audio. Never from an estimate.**

Estimating from a characters-per-second rate is off by 15–30% because speaking
rate varies with sentence length, punctuation and the synthesiser's own
run-to-run variance. Timing a figure to an estimate puts every beat slightly
wrong, and the error accumulates across scenes.

The reliable method:

1. Split the script into **short lines** — one clause each.
2. Synthesise each line separately.
3. Trim leading and trailing silence from each.
4. Concatenate with **per-line gaps you choose**.
5. Record each line's exact start and duration.

Now every line's start time is a number you constructed rather than one you
predicted, and the picture can be pinned to it exactly.

Two payoffs beyond accuracy:

- **Gaps become a directing tool.** Set an act-ending gap by how long the
  picture still needs to perform, not by the punctuation. If the accent beat
  needs 1.1s after the last word, the gap is 1.1s.
- **Rhythm carries emotion.** Uneven pauses are most of what makes narration
  sound like a person. A fixed gap everywhere sounds like a metronome.

Scene boundaries then fall out of the audio: a scene ends where its last line
ends plus that line's gap, so "the sentence finished" and "the picture cut" are
the same instant and never need hand-nudging.

If the narration changes, re-derive. Do not shift the numbers by hand.

---

## The three gates

Run before shipping. Each is a hard pass/fail.

**1 · Not stiff.** Element durations 300–500ms; over-600ms under 25%; staggers
60–100ms; blur used about as often as displacement; every element has both an
entrance and an exit.

**2 · Seams not repeated.** No two adjacent seams share a transition; total
kinds ≥ ⌈seams / 2⌉; headline entrances vary while exits are uniform.

**3 · Not a mockup.** No grey skeleton bars, no generic circles or blocks, no
lorem. Every row is a readable field with real content; every number is read
off the actual artefact.

These are independent of style. A minimal white figure and a dense neon one
look nothing alike and both must pass.
