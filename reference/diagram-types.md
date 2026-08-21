# Diagram types

## Contents

- The registry — 41 types, 7 layout families
- How to choose (the discriminators)
- Universal rules
- **Family: chain** — flow, steps, pipeline, sequence, timeline, journey, state-machine, data-flow
- **Family: radial** — loop, cycle, wheel, orbit, radar
- **Family: stack** — layers, pyramid, funnel, medallion, tiers
- **Family: tree** — tree, org, breakdown, mindmap, taxonomy, decision-tree
- **Family: grid** — matrix, quadrant, comparison, bento, table, spec-rows, swimlane, gantt, er
- **Family: field** — venn, network, cluster, scatter, treemap
- **Family: row** — equation, stat-row, kpi
- Adding a type

Layout is **parametric**: the inputs fix the geometry. Same inputs, same
coordinates. Do not nudge things by eye — change an input and recompute.
`scripts/layout.py` does the recomputing; see `reference/spec.md`.

## The registry

A type is a **reading contract** — what the reader is supposed to conclude —
sitting on top of a **geometry**. Many types share a geometry, so there are 41
types and 7 engines, not 41 engines.

That ratio is the whole point. The older version of this file documented nine
types by hand and pointed at an upstream project for the rest, which meant the
other thirty were unavailable unless you had that repo. Factoring by geometry
makes all of them reachable, and makes a new type a row in a table rather than
a new page of coordinate maths.

| Family | Geometry | Types | The reader concludes |
| --- | --- | --- | --- |
| **chain** | boxes along one axis, optional side lanes | flow, flowchart, steps, pipeline, sequence, timeline, journey, state-machine, data-flow | order, and where it ends |
| **radial** | stations on an ellipse, optional centre hub | loop, cycle, wheel, orbit, radar | it comes back round |
| **stack** | full-width bands, one resting on the next | layers, pyramid, funnel, medallion, tiers | each rests on the one below |
| **tree** | levels, children under their own parent | tree, org, breakdown, mindmap, taxonomy, decision-tree | containment, not flow |
| **grid** | r×c cells, or free position on two axes | matrix, quadrant, comparison, bento, table, spec-rows, swimlane, gantt, er | position is the claim |
| **field** | position derived from the node itself | venn, network, cluster, scatter, treemap | proximity is the claim |
| **row** | one line, stated big | equation, stat-row, kpi | it is a headline |

Set the type; the family follows. `layout.py` refuses an unknown type rather
than guessing, because a wrong family is a wrong argument, not a wrong style.

**Eight types are a lie when drawn with their family's generic geometry**, and
carry their own solver: `timeline`, `sequence`, `swimlane`, `gantt`, `radar`,
`treemap`, `mindmap`, `er`. A gantt whose bars are all one column length, a
radar with no polygon, a treemap whose tiles are equal — each renders, and each
says something false about the subject. That is the test for whether a type
needs its own geometry: not "does it look different" but "would the family
version state something untrue".

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
| Dated events with no branching | **Timeline** | The axis is time, and time is the argument |
| Who calls whom, in order | **Sequence** | Actors are columns; the vertical axis is time |
| Modes a thing can be in | **State-machine** | Edges are triggers; a node can be re-entered |
| Where the data goes | **Data-flow** | Stores and processes, not steps |
| Volume narrowing at each stage | **Funnel** | The width *is* the number |
| Rank from broad base to point | **Pyramid** | Each tier depends on the one under it |
| Lanes owning parts of one process | **Swimlane** | The row says who, the column says when |
| Work over calendar time | **Gantt** | Bar length is duration; overlap is the claim |
| Sets that share members | **Venn** | The overlap is the whole point |
| Things related without direction | **Network** | Adjacency, no order |
| Scores on two continuous axes | **Scatter** | Both coordinates are measured, not chosen |
| One relation, stated as a headline | **Equation** | It reads as a sentence, not a figure |
| Numbers that are the argument | **Stat-row / KPI** | The reader remembers a number |

Two are easy to confuse. A **Loop** without a hub is just a circular
**Steps** — the write-back spokes to the centre are what make it a loop. A
**Flowchart** whose last node points back at the first is a **Loop** drawn
badly.

## Universal rules

**Budget per figure:** ≤9 nodes, ≤12 edges, 1 accent (2 absolute maximum). Two
figures side by side each get their own budget. Over budget → split into an
overview plus a detail figure.

**Shape carries type:**

| Shape | Means | Class |
| --- | --- | --- |
| Stadium (`rx` = half height) | start / end | `mf-card` + `rx=23` |
| Rectangle (`rx` 6–13) | a step, a thing | `mf-card` |
| Diamond | a decision | `mf-card` as `<polygon>` |
| Dark filled box | shared state, the hub | `mf-store` |
| Ghost box (3% fill, 30% stroke) | inert / dead-end / external | `mf-ghost` |
| Accent-tinted box | **the** focal node | `mf-focal` |

**Grid:** every coordinate divisible by 4.

**Edge endpoints come from the node boxes.** Never place an arrow with a fixed
gap and hope. See "Loop" below for the worked case — it is where this bites
hardest.

**Every edge out of a decision carries a label.**

## Family: chain — an ordered path along one axis

### Flowchart — a path that ends

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

### Steps — a linear process

Boxes on one axis, arrows between, no branching. Number them (`01`, `02`, …) in
`mf-num` — the numbering is the structure. Cap at 6; beyond that the reader
stops counting and it should become Layers or a Tree.

Optional: a rail of short notes alongside, one per step, entering with its step.

---

### The rest of the chain family

Same spine, same edge maths, different reading contract. Only the deltas:

| Type | Delta from flowchart |
| --- | --- |
| **steps** | No decisions, so no side lane. Number the boxes — with nothing branching, the ordinal is the only thing carrying order. |
| **pipeline** | Steps, but the edge is the subject: label every edge with what passes along it, not what happens next. |
| **sequence** | Actors become columns and the axis rotates: time runs down, each message is a labelled horizontal edge between two columns. Use `lane` per actor. |
| **timeline** | The spine becomes a drawn rail with the dates on it. Boxes hang off the rail, alternating sides on landscape so labels never collide. |
| **journey** | Timeline plus a sentiment row — one `sub` per step saying how it felt. That row is the argument; without it this is just steps. |
| **state-machine** | Nodes are modes, edges are triggers, and a node may be entered more than once. Self-loops sit above their node as a small arc. If the last state points back at the first, it is a **loop**, not a chain. |
| **data-flow** | Stores (`kind: "store"`) and processes alternate. An edge always runs between a store and a process, never store→store; if you have drawn store→store you have hidden a process. |

**Portrait:** the spine goes vertical and side lanes go right. **Landscape:**
the spine goes horizontal and dead ends go *above* it, so the eye reads the
spine left→right without stepping over anything.

---

## Family: radial — stations on an ellipse

### Loop — a cycle that feeds itself

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

### The rest of the radial family

| Type | Delta from loop |
| --- | --- |
| **cycle** | A loop with no hub. Honest when there is no accumulating state — but check first: if something *is* accumulating, hiding it makes the figure weaker, not simpler. |
| **wheel** | Hub is the subject and the stations serve it. Spokes become solid and directed *inward*; the rim arcs go dashed or disappear. The opposite emphasis to a loop. |
| **orbit** | Two rings at different radii around one hub, for near-term and far-term, or core and periphery. Never three rings — the third is unreadable at this size. |
| **radar** | Not cards on an ellipse but a polygon through scored vertices. Axes are spokes with labels at the rim; the shape enclosed is the claim. Cap at 6 axes. |

---

## Family: stack — bands resting on each other

### Layers — a stack

Full-width bars, tallest concern at the bottom. `bar_h` 56–72, `gap` 8–12,
label left-aligned inside at `x = bar_x + 20`, a right-aligned tag for the role.
No arrows: adjacency *is* the relation. Accent the layer under discussion.

---

### The rest of the stack family

| Type | Delta from layers |
| --- | --- |
| **pyramid** | Band width tapers upward, narrowest at the top. The taper is the argument: each tier is *supported by* the one below, so the widths must be monotonic. |
| **funnel** | Taper downward. Width should be proportional to a real number — a funnel drawn with even steps while the numbers are 100/40/3 is a lie the reader can check. |
| **medallion** | Bronze / silver / gold tiers. Only the top tier takes the accent. |
| **tiers** | Pricing or capability tiers side by side rather than stacked; that is really a **grid** with one column each. Use `grid` and say so. |

---

## Family: tree — children under their own parent

### Tree — a hierarchy

Parent centred over its children; children evenly spaced. Elbow connectors, not
diagonals:

```
M px py  V (py + drop/2)  H cx  V cy
```

Keep to two levels plus root. Three levels on a 540-wide canvas makes leaves
too small to label.

---

### The rest of the tree family

| Type | Delta from tree |
| --- | --- |
| **org** | Same geometry, reporting lines. Dotted edges for dotted-line reports — that distinction is usually the reason the chart was asked for. |
| **breakdown** | Leaves carry numbers that sum to the parent. Show the sum; a breakdown whose children do not add up is the one error a reader will find. |
| **mindmap** | Root in the centre, children radiating both ways. Edges are curved and unarrowed — a mindmap has no direction, and an arrowhead invents one. |
| **taxonomy** | Levels are *kinds*, not steps. Label the levels down the left margin; without that the reader cannot tell which rank they are looking at. |
| **decision-tree** | Every branch is labelled with its condition, exactly as in a flowchart. Leaves are outcomes, and one of them gets the accent. |

`layout.py` reads parenthood from the edges, or from a `parent` field, and
places each child under its own parent. Spreading a level evenly across the
canvas — the obvious shortcut — silently re-parents the figure.

---

## Family: grid — position is the claim

### Comparison — two figures, one argument

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

### Matrix — two axes

Square canvas. Axis lines through the centre, axis labels at the four ends in
`mf-eyebrow`. Items are dots plus labels; the quadrant they land in is the
claim, so place them from real values, not from where they look tidy. Optionally
tint the one quadrant you are arguing for with `--accent-tint`.

---

### Spec rows — the fact table

The opening-card pattern: a label/value pair per row with a hairline under each.

```
label  (mf-node, x = 48)          value  (mf-lede, x = 140)
hairline full width, 22px below the baseline
row pitch 70
```

Use it for facts about the artefact itself — duration, aspect, method, source.
**Read the values off the real thing.** A spec row with an invented number is
worse than no spec row.

---

### The rest of the grid family

| Type | Delta |
| --- | --- |
| **quadrant** | A matrix with the two axes named at both ends and the winning quadrant tinted. Only one quadrant may be tinted. |
| **bento** | Uneven cells via `span`. Reserve the big cell for the thing that deserves it; a bento where every cell is the same size is a table. |
| **table** | Header row in `mf-tag`, body rows in `mf-node`. Rules between rows, never a border box around everything. |
| **swimlane** | Rows are owners, columns are stages, and a cell holds the step that owner performs then. The lane label is a left rail, not a cell. |
| **gantt** | Bar `x` and width come from real dates. Overlap is the whole point, so never round bars to whole columns — that is where the schedule conflict disappears. |
| **er** | Entities as boxes with their fields listed; the edge carries the cardinality (`1—n`) as its label. An unlabelled ER edge is as broken as an unlabelled branch. |

---

## Family: field — proximity is the claim

Position comes from the node itself, not from its order. Give each node a
`pos: [x, y]` in 0–1; `layout.py` falls back to an even ring when you do not.

| Type | Contract |
| --- | --- |
| **venn** | Two or three circles, `mf-ghost` fill so the overlaps read. The overlap label is the accent — it is the reason the figure exists. Never four circles: four sets cannot be drawn with circles without lying about one of the regions. |
| **network** | Undirected edges, no arrowheads. Degree is visible, so do not let an incidental node sit at the centre — the reader will read centrality as importance whether you meant it or not. |
| **cluster** | Network plus a `mf-ghost` hull behind each group and a label on the hull. The hulls are the argument; the nodes are evidence. |
| **scatter** | Both axes labelled with units at both ends. Position is measured here, not chosen — if you are placing points by feel, you want a **quadrant**. |
| **treemap** | Area is proportional to the value. Nested rectangles, two levels at most; the third level is unreadable at any canvas this skill ships. |

---

## Family: row — one line, stated big

### Equation row — the punchline form

The end-card workhorse. Three parts on one baseline:

```
left term   (mf-display, text-anchor=end,  x = 196)
arrow       (drawn path + head, accent, y = baseline - 16)
right term  (mf-display, x = 272)
sublabel    (mf-lede, x = 272, y = baseline + 32)
hairline    (mf-rule, full width, y = baseline + 64)
```

Two or three rows stacked. The arrow is **drawn**, never a typed `→` — a real
path can be animated and matches the figure's other arrows.

---

### The rest of the row family

| Type | Delta from equation |
| --- | --- |
| **stat-row** | Three or four numbers with a caption each. The number is `mf-display`, the caption `mf-tag`. Read every number off the real artefact — an invented figure in this form is the most damaging kind, because the form is what makes it look authoritative. |
| **kpi** | A stat row with direction: an arrow and a delta beside each number. Direction needs a baseline, so name the comparison period or drop the arrow. |

---

## Adding a type

1. Decide which family's geometry it already is. Nearly always one of the
   seven — and check the test above before writing a solver: needing a
   different *look* is not the same as the family version being wrong.
2. Add the row to `FAMILY` in `scripts/layout.py`, plus a `TYPE_DEFAULTS` entry
   if it needs a hub, a taper, axes or a rail.
3. Add a row to the table for its family here, saying only what differs and
   **what the reader is meant to conclude**. That last part is the type; the
   geometry is shared.

If it needs genuinely new geometry, it is an eighth family — write the layout
function and say in this file why the existing seven could not carry it.
