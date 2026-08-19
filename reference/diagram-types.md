# Diagram types

## Contents

- How to choose (the discriminators)
- Universal rules
- Flowchart — a path that ends
- Loop — a cycle that feeds itself
- Comparison — two figures, one argument
- Steps — a linear process
- Layers — a stack
- Tree — a hierarchy
- Matrix — two axes
- Equation row — the punchline form
- Spec rows — the fact table
- Types not covered here

Layout is **parametric**: the inputs fix the geometry. Same inputs, same
coordinates. Do not nudge things by eye — change an input and recompute.

---

## How to choose

Pick from the subject's shape, not from what looks good.

| The subject | Type | The discriminator |
| --- | --- | --- |
| Steps with branches, ending at outcomes | **Flowchart** | It *ends*. Some path terminates. |
| Work that returns to its own first step | **Loop** | The last step feeds the first, and a centre accumulates state |
| Two approaches, one question | **Comparison** | The reader must hold both at once |
| Ordered stages, no branching | **Steps** | Nothing decides; it just proceeds |
| Things stacked on things | **Layers** | Each level rests on the one below |
| One parent, many children | **Tree** | Containment or reporting, not flow |
| Options scored on two axes | **Matrix** | Position *is* the claim |
| A single relation, stated big | **Equation row** | It is a headline, not a figure |
| Facts about the artefact itself | **Spec rows** | Metadata, not argument |

Two are easy to confuse. A **Loop** without a hub is just a circular
**Steps** — the write-back spokes to the centre are what make it a loop. A
**Flowchart** whose last node points back at the first is a **Loop** drawn
badly.

---

## Universal rules

**Budget per figure:** ≤9 nodes, ≤12 edges, 1 accent (2 absolute maximum). Two
figures side by side each get their own budget. Over budget → split into an
overview plus a detail figure.

**Shape carries type:**

| Shape | Means | Class |
| --- | --- | --- |
| Stadium (`rx` = half height) | start / end | `dm-card` + `rx=23` |
| Rectangle (`rx` 6–13) | a step, a thing | `dm-card` |
| Diamond | a decision | `dm-card` as `<polygon>` |
| Dark filled box | shared state, the hub | `dm-store` |
| Ghost box (3% fill, 30% stroke) | inert / dead-end / external | `dm-ghost` |
| Accent-tinted box | **the** focal node | `dm-focal` |

**Grid:** every coordinate divisible by 4.

**Edge endpoints come from the node boxes.** Never place an arrow with a fixed
gap and hope. See "Loop" below for the worked case — it is where this bites
hardest.

**Every edge out of a decision carries a label.**

---

## Flowchart — a path that ends

**Inputs:** spine axis (vertical for portrait, horizontal for landscape),
node list with `kind` ∈ {start, step, decision, end, exit}, branch labels.

**Layout (portrait, viewBox 540×960):**

```
spine_x    = 210            # left of centre, leaving a column for side exits
node_w     = 150            # steps; decisions get 200–210
node_h     = 46             # 80 for decisions (they need two text lines)
v_gap      = 58             # between the bottom of one box and the top of the next
exit_x     = 425            # centre of the side-exit column
```

Node *n* on the spine: `cy = first_cy + n * (node_h + v_gap)`.

Edges:

```
down    M spine_x (prev_bottom) L spine_x (next_top - 4)
        head at (spine_x, next_top) rotate(90)
branch  M (diamond_right) cy L (exit_left - 4) cy
        head at (exit_left, cy)
```

Label the down-edge from a decision at `(spine_x + 16, midpoint_y)`, the
branch label above its arrow at `(midway_x, cy - 10)`.

**Accent:** the terminal that actually completes. Not the decision.

**Landscape variant:** swap the axes; `h_gap` 46–71 between boxes; put dead-end
exits *above* the spine so the eye reads left→right uninterrupted.

---

## Loop — a cycle that feeds itself

**Inputs:** 3–8 stations clockwise from top, exactly one hub, ellipse radii.

**Layout:** stations sit on an ellipse. With `n` stations the angle of station
*i* is `θᵢ = -90° + i · 360/n`, and

```
x = cx + rx·cos θ        y = cy + ry·sin θ
```

Portrait wants a tall ellipse (`rx` 182 / `ry` 200 on a 540×960 canvas);
landscape wants a wide one (`rx` 118 / `ry` 94 on 960×540). Do not carry a
near-circular landscape ratio into portrait — it leaves the lower third empty.

**The arc endpoints are the part that goes wrong.** A fixed angular gap (say
22° either side of each station) *looks* right on a circle with small nodes and
leaves arcs hanging 70px off the cards on a tall ellipse with wide ones. Solve
for the angle where the ellipse crosses the card's own boundary:

```
card bottom edge at y = yb   →   sin θ = (yb - cy)/ry    →   θ = asin(...)
card left  edge at x = xl    →   cos θ = (xl - cx)/rx    →   θ = acos(...)
```

Take whichever boundary the ellipse actually meets first, and start the arc
there. Worked example, station cards 140×54 on `rx=182, ry=200` centred
(270, 520):

```
card A (top,   centre 270,320)  bottom y=347  → θ = -60°
card B (right, centre 428,620)  top    y=593  → θ =  21°
arc A→B :  M 361 346.8  A 182 200 0 0 1 439.9 591.7
```

Arrowhead angle is the ellipse tangent at the endpoint:

```
dx = -rx·sin θ      dy = ry·cos θ      rotation = atan2(dy, dx)
```

**Hub:** a dark box at the centre with dashed spokes from each station. The
spokes are the loop's signature — remove them and it is a circular Steps.

**Accent:** the arc that closes the loop (last station → first). That edge is
the whole reason the figure is a loop.

---

## Comparison — two figures, one argument

The strongest form in this system: let the *shapes* differ so the reader gets
the point before reading a word.

**Landscape (960×540):** a hairline divider at `x=480` from `y=176` to `y=436`;
left figure centred at 258, right at 702; each gets its own eyebrow at `y=180`
and a claim line at `y=204`; three note rows per side at `y=460/478/496`.

**Portrait:** stack the two figures instead, or — better for ≤30s video — show
them in consecutive scenes and only bring them together on the end card.

**Accent:** one per side, and it must be the *same colour*. The two accents
mark equivalent organs (e.g. the loop's return edge, the graph's completing
terminal), so the reader reads them as a pair, not as two unrelated highlights.

---

## Steps — a linear process

Boxes on one axis, arrows between, no branching. Number them (`01`, `02`, …) in
`dm-num` — the numbering is the structure. Cap at 6; beyond that the reader
stops counting and it should become Layers or a Tree.

Optional: a rail of short notes alongside, one per step, entering with its step.

---

## Layers — a stack

Full-width bars, tallest concern at the bottom. `bar_h` 56–72, `gap` 8–12,
label left-aligned inside at `x = bar_x + 20`, a right-aligned tag for the role.
No arrows: adjacency *is* the relation. Accent the layer under discussion.

---

## Tree — a hierarchy

Parent centred over its children; children evenly spaced. Elbow connectors, not
diagonals:

```
M px py  V (py + drop/2)  H cx  V cy
```

Keep to two levels plus root. Three levels on a 540-wide canvas makes leaves
too small to label.

---

## Matrix — two axes

Square canvas. Axis lines through the centre, axis labels at the four ends in
`dm-eyebrow`. Items are dots plus labels; the quadrant they land in is the
claim, so place them from real values, not from where they look tidy. Optionally
tint the one quadrant you are arguing for with `--accent-tint`.

---

## Equation row — the punchline form

The end-card workhorse. Three parts on one baseline:

```
left term   (dm-display, text-anchor=end,  x = 196)
arrow       (drawn path + head, accent, y = baseline - 16)
right term  (dm-display, x = 272)
sublabel    (dm-lede, x = 272, y = baseline + 32)
hairline    (dm-rule, full width, y = baseline + 64)
```

Two or three rows stacked. The arrow is **drawn**, never a typed `→` — a real
path can be animated and matches the figure's other arrows.

---

## Spec rows — the fact table

The opening-card pattern: a label/value pair per row with a hairline under each.

```
label  (dm-node, x = 48)          value  (dm-lede, x = 140)
hairline full width, 22px below the baseline
row pitch 70
```

Use it for facts about the artefact itself — duration, aspect, method, source.
**Read the values off the real thing.** A spec row with an invented number is
worse than no spec row.

---

## Types not covered here

diagram-design documents ~28, including sequence, ER, state machine, Gantt,
swimlane, radar, treemap, Venn, pyramid, medallion and data-flow. When one of
those is the right answer, read its `type-*.md` there for the layout contract,
then render it with **this** skill's tokens, classes and motion vocabulary —
the grammar transfers, the palette and type do not.
