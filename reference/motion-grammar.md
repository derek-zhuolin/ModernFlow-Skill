# Motion grammar

## Contents

- The timing table
- Scale: the numbers that decide whether it reads as stiff
- Entrances and exits
- Building a figure: the order things arrive
- The camera: push, dwell, pull
- Scene seams
- Syncing to narration
- Pace: dense subjects and rates above 1
- The three gates

Motion here is **pure CSS**. Every animated element carries a class and one
inline `--at` start time. That single number also drives the video tier, so the
standalone HTML and the MP4 cannot drift apart.

```html
<g class="dm mf-pop" style="--at:1.42s"> … </g>
<path class="dm mf-draw mf-flow" style="--at:2.10s" pathLength="1" d="…"/>
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
| `mf-rise` | up from +20px | the headline of scene 1 |
| `mf-settle` | down from -14px | eyebrows, and a headline arriving from above |
| `mf-widen` | scale 0.94 → 1 | a headline that should feel like it expands into place |
| `mf-slide` | in from +22px x | a headline following a leftward exit |
| `mf-pop` | +14px, scale 0.985 | nodes and cards (smaller gesture than a title) |
| `mf-out` | up and out, blurring | **everything**, everywhere |

**Vary entrances, fix exits.** Each scene's headline uses a *different*
entrance from the last; every element in every scene leaves the same way. Entry
is where you create interest, exit is where you create continuity.

`mf-tip` for arrowheads — they land *after* their line arrives, never with it.
`mf-flash` for a single emphasis pulse. Never loop it.

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

## The camera: push, dwell, pull

Everything above moves elements inside a fixed frame. The camera moves the
frame. They are different tools and the most common mistake is to fuse them —
scaling up the one node you want looked at, instead of pushing the frame into
it. The fused version cannot be re-cut: the zoom is welded to that node's
entrance, and the node grows relative to its neighbours, which says the node
got bigger rather than that you got closer.

```html
<g class="mf-cam mf-push" style="--at:3.2s; --zx:678px; --zy:315px; --zk:1.7">
  <g class="mf-cam mf-pull" style="--at:5.4s; --zx:678px; --zy:315px; --zk:1.7">
    … the whole figure …
```

`--zx/--zy` is the point pushed into, `--cx/--cy` where it lands (frame centre,
defaulted per canvas), `--zk` the magnification. **Push and pull are exact
inverses about the same origin**, so the pair composes back to identity: that
is how a dwell of any length exists with no JavaScript and no keyframe
percentage. It also means the two must carry identical `--zx/--zy/--zk`, and
that two moves may not overlap — an overlap leaves the frame permanently
off-centre. `layout.py` enforces both.

**Chrome stays outside the camera.** The headline and the footer belong to the
piece, not to the figure; pushing into a node and dragging the headline
half-off the canvas with it reads as a mistake, not as a move.

### When a camera move is right

- **The figure is legible but the detail is not.** Nine nodes on a portrait
  canvas are readable as a map and not as text. Show the map, then go and read
  one of them. This is the case worth building for.
- **The narration singles something out.** "…and this is the part that
  matters." The frame should do what the sentence does.
- **A wide scene follows a tight one, or the reverse.** The pull becomes the
  seam. It is the strongest transition in the vocabulary because it is the only
  one the viewer experiences as a place rather than an effect.

### When it is wrong

- **To add energy.** A camera move with no referent is the video equivalent of
  a repeating pulse: motion that means nothing, which the viewer learns to
  ignore, taking the meaningful moves with it.
- **On a figure that is already legible.** If the wide shot reads, pushing in
  says there is something more to see and then does not deliver.
- **More than about twice in one scene.** Two are a look; three is a search.

### Numbers

| | Value | Why |
| --- | --- | --- |
| Magnification | **1.5–1.9** | Under 1.4 the viewer is not sure anything happened. Past ~2.2 the strokes and the 4px grid magnify with everything else and the figure starts to look coarse |
| Move duration | **0.55–0.70s** | It is the whole frame, not an element. Element durations do not apply — at 400ms a full-frame move reads as a jump cut |
| Dwell | **≥1.2s**, typically 1.8 | The reason to be there is that something needs reading |
| Ease | `power4.inOut` | A camera accelerates and decelerates. `expo.out` on a frame move starts at full speed and reads as a whip |

**Do not blur a full-frame camera move.** Blur pairs with element movement
because the element is small and the blur costs nothing. A CSS blur over the
whole frame gets clipped to the filter region Chrome derives from the bounding
box, and the clip appears as a straight edge across the artwork — the
card-shadow bug at ten times the size. The camera earns its softness from the
ease curve instead.

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
| `push` | `y: -16` | from `y: +16` |
| `drop` | `y: +16` | from `y: -16` |
| `squeeze` | `x: -20`, `scale .96` | from `x: +22` |
| `blur` | `scale 1.02` | from `scale 0.99` |
| `zoom` | `scale 1.06` | from `scale 0.94` |
| `recede` | `scale 0.94` | from `scale 1.05` |

Six, not four. The coverage rule — at least ⌈seams / 2⌉ distinct kinds — runs
out of vocabulary at around a dozen seams, and a long set built from four
transitions has a rhythm the viewer starts to feel. `layout.py` plans these
from a seeded permutation; see the variation section of `reference/spec.md`.

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

## Pace: dense subjects and rates above 1

A dense subject is not a fast subject. The reflex is to speed the narration up
and leave the picture where it was, and that is precisely backwards: the
picture is what makes density survivable, so it is the thing that has to keep
up.

**Compress the gaps, not the durations.** `--rate` in the spec divides every
beat gap and leaves element durations alone, floored at 300ms. At 1.3 a 350ms
node-to-node gap becomes 270ms, still well inside the readable band, while a
400ms entrance stays 400ms — under about 300 an entrance stops reading as a
move and starts reading as a pop, and a piece full of pops feels rushed no
matter how well the timing lines up.

At **1.3×**, expect:

- ~2.6s of figure per scene instead of ~3.4s
- 4–6 nodes per scene rather than 7–9. The budget of 9 assumes 1.0×; at 1.3×
  the last two never get looked at
- the accent pause held at full length. It is the one beat that must not
  compress — a punchline delivered at 1.3× is a punchline stepped on
- one camera push per scene, not two

**Density belongs in the number of scenes, not in the number of nodes.** Six
scenes of four nodes at 1.3× carry far more than three scenes of nine at 1.0×,
in the same running time, and the viewer keeps up because each scene makes one
claim. This is the single highest-leverage decision in a dense piece and it is
made in step 1 of the decomposition, long before any of this timing matters —
see `reference/spec.md`.

Above ~1.45× stop compressing and cut instead: shorter sentences, more scenes.
Past that point the gaps are too small for the eye to resolve order, the
staggers do nothing, and you are paying for animation the viewer cannot see.

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
