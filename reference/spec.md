# The spec — meaning in, geometry out

## Contents

- Why a spec instead of hand-placed SVG
- Decomposing text into scenes
- Schema
- Camera
- Rate
- The gates
- Editing without rebuilding

`scripts/layout.py` reads a JSON spec and writes the page. Nothing in a spec is
a coordinate.

---

## Why a spec instead of hand-placed SVG

Hand-placing works exactly once. The moment a label grows by two characters,
the box around it is too small, the edge that ended at that box now ends in
white space, and the figure is wrong in a way that still renders. Nobody
notices until the render, and by then the fix is another round of nudging.

A spec removes the class of failure rather than the instance:

- **Box sizes come from labels.** Chinese is full-width, latin is not, so the
  same character count is two different widths. `layout.py` measures.
- **Edge endpoints come from the boxes.** Change a label, the box changes, the
  edge follows.
- **Beats come from the node order and the rate.** Re-order the argument and
  the timing re-derives instead of drifting.
- **Camera targets are node ids.** Move a node and the camera still points at
  it, because it never pointed at a coordinate.

The cost is that you have to say what the figure *means* before you can draw
it. That is not overhead; it is the step that decides whether the diagram is
right, and doing it in JSON makes it reviewable.

---

## Decomposing text into scenes

This is the part a script cannot do. Work in this order — it is the order that
keeps you from picking a diagram type because it looks good.

**1 · Cut the text at its turns, not at its paragraphs.** A turn is where the
argument changes shape: a claim becomes a mechanism, a mechanism becomes a
consequence, a general rule meets a case. Each turn is one scene. Paragraph
breaks are a writing convenience and cut in the wrong places about half the
time.

**2 · For each scene, name the shape of the subject in one sentence.** "Four
things that hand off in order and then start again." "Two approaches the reader
has to hold at once." "One parent with five children." Say it out loud before
choosing anything.

**3 · Read the type off that sentence** using the discriminator table in
`reference/diagram-types.md`. If the sentence does not fit a type, the sentence
is still vague — go back to it. Do not pick the nearest type and hope.

**4 · Pull the nodes out of the noun phrases and the edges out of the verbs.**
Labels are the subject's own words wherever possible. Renaming a step to
something tidier is how a diagram stops describing the thing it is about.

**5 · Pick the accent: the one node the scene exists to deliver.** If two
candidates survive, the scene is two scenes.

**6 · Point the camera at whatever the narration dwells on.** Usually the
accent; sometimes a node with detail the wide shot cannot carry.

**7 · Check the budget before writing any JSON.** Over nine nodes means the
scene is doing two jobs. Split it into an overview and a detail — and note that
the detail scene is where the camera earns its keep, because the overview can
stay wide and the detail can arrive already pushed in.

Only now write the spec. Steps 1–7 take longer than the JSON does.

---

## Schema

```jsonc
{
  "title":   "browser tab title",
  "canvas":  "landscape" | "portrait" | "square",
  "profile": "soft-gradient" | "editorial-paper",
  "rate":    1.3,                    // narration rate; see below
  "scenes": [ { … } ]
}
```

A scene:

```jsonc
{
  "id":       "s1",                  // camera and --scene refer to this
  "type":     "flow",                // any of the 41; family follows
  "eyebrow":  "SECTION 01 · TOPIC",
  "title":    "the headline",        // or ["line one", "line two"]
  "num":      "01",
  "tag":      "SECTION NAME",
  "brand":    "PROJECT",
  "tagline":  "or tagline",
  "watermark":"FLOW",                // optional, sits behind the figure
  "enter":    "rise",                // headline entrance; auto-varied per scene
  "seam":     "squeeze",             // exit transition; auto-varied per seam
  "alt":      "what the figure says, for a screen reader",

  "nodes": [
    { "id": "a", "label": "文稿", "sub": "raw text", "kind": "start" },
    { "id": "b", "label": "能画成图吗？", "kind": "decision" },
    { "id": "x", "label": "退回文字", "kind": "exit", "lane": -1, "from": "b" },
    { "id": "d", "label": "解出版面", "kind": "step" }
  ],
  "edges": [
    { "from": "a", "to": "b" },
    { "from": "b", "to": "x", "label": "NO" },
    { "from": "b", "to": "d", "label": "YES" },
    { "from": "d", "to": "e", "kind": "accent" }
  ],
  "accent": "d",
  "camera": "auto"
}
```

**node.kind** picks the shape, and shape carries type — recolouring never does:

| kind | Shape | Means |
| --- | --- | --- |
| `start`, `end`, `terminal` | stadium | entry and exit points |
| `step`, `thing`, `node` | rectangle | a step, a thing |
| `decision`, `branch` | diamond | a decision — every edge out of it needs a label |
| `hub`, `store`, `state` | dark filled box | shared state |
| `exit`, `ghost`, `dead`, `external` | ghost box | inert, dead end, someone else's system |

**node extras**, by family and type:

| Field | Used by | Means |
| --- | --- | --- |
| `sub` | everything | the small-caps line under the label |
| `lane`, `from` | chain | a side lane hanging off a spine node |
| `lane`, `col` | swimlane | which owner, which stage |
| `level`, `parent` | tree | explicit rank and parenthood; otherwise read off the edges |
| `pos: [x, y]` 0–1 | grid with axes, field | position IS the claim, so you supply it |
| `span` | bento | how many grid columns this cell takes |
| `start`, `end` | gantt | real numbers; bar length is duration |
| `score` 0–1 | radar | the vertex's distance from the centre |
| `value` | treemap | area is proportional to this |
| `fields: [...]` | er | the entity's columns |
| `cells: [...]` | table, spec-rows | one row's values, left to right |
| `group` | cluster | which hull this point belongs inside |
| `r` | venn | circle radius, if the default overlap is wrong |

**scene extras**: `axes: {"x": [lo, hi], "y": [lo, hi]}` names the axes for
quadrant, matrix and scatter — without them position is unreadable.
`ticks: [{"at": 3, "label": "周四"}]` puts dated gridlines on a gantt.
`cols` sets the grid width; `colw: [1, 1.2, 1.4]` sets relative column widths
for a table. A table's first row is its header unless `header: false`.

**edge.kind** is `solid` (default), `accent`, `dashed`, or `spoke`. Dashed and
spoke edges fade in rather than draw — the draw animation works by taking over
`stroke-dasharray`, which is where the dash pattern lives, so one erases the
other.

---

## Variation

Eight scenes built the same way look like eight of the same scene. The pieces
that vary are the headline entrance and the seam transition, and varying them
**by index** — entrance = `ENTRANCES[i % 4]` — is worse than not varying at
all: index 0 is always the same gesture, so every deck ever built has one
rhythm and a reader who has seen two of them has seen all of them.

They vary by a **seeded permutation** instead. `seed` at the top of the spec
(defaulting to the title) drives a CRC — a die that always rolls the same way
for the same spec. So a re-render is the same film, which matters because a
different cut would silently desync narration that was timed to the last one,
while two different specs are two different films.

The dice are constrained, not free:

- **no seam repeats the one before it**, and no headline repeats the last
- **distinct kinds ≥ ⌈seams / 2⌉**, which adjacent-difference alone does not
  give you — `A B A B` satisfies "never the same twice running" and uses two
  kinds forever
- past about a dozen seams that rule saturates against the vocabulary itself.
  Six transitions ship; a longer set repeats a kind, and the repeats are spread
  rather than adjacent

Set `enter` or `seam` on a scene to pin one; the planner leaves pinned values
alone and varies around them.

---

## Camera

```jsonc
"camera": "auto"
"camera": [{ "focus": "c", "zoom": 1.7, "dwell": 1.8 }]
"camera": [{ "focus": "c", "zoom": 1.9, "at": 3.4, "release": 5.8 }]
```

`focus` is a node id, never a coordinate. `at` and `release` default to the
focus node's own beat plus `dwell`, and are scaled by `rate` like every other
time.

**`auto` is the default** — a scene with no `camera` key gets one. It picks a
shape from the same seeded die:

| Mode | Shape |
| --- | --- |
| `punch` | push to the accent at 1.7×, dwell, pull |
| `survey` | go and read one node early at 1.55×, come back, then land on the accent |
| `drift` | one slow 1.32× push held long, for a figure that wants dwelling on rather than pointing at |
| `none` | no move |

It refuses on figures with **fewer than four nodes**, whatever the die says.
There is nothing to go and read on a three-node figure, and a camera move with
no referent is idle motion in better clothes. Write `"camera": "none"` to
refuse it yourself.

Moves must not overlap. `layout.py` refuses an overlapping pair rather than
rendering a frame that never comes back to centre; see the camera section of
`reference/motion-grammar.md` for why.

---

## Rate

`"rate": 1.3` compresses every gap in the beat table by 1.3 and leaves element
durations alone, floored at 300ms. Narration at 1.3× against a picture at 1.0×
drifts about a third of a second per scene, and it accumulates.

Set it once at the top of the spec, or override per render with `--rate`.

---

## The gates

`layout.py` exits non-zero, before writing anything, on:

- an unknown type
- duplicate node ids, or an edge pointing at a node that does not exist
- more than 9 nodes or 12 edges in one scene
- more than one accent
- an unlabelled edge out of a decision
- overlapping camera moves

All of these render fine and are wrong, which is the definition of something
that belongs in a gate rather than in a style note.

---

## Editing without rebuilding

The published page carries a frame seek. Append `?t=` to the URL and it freezes
there:

```
figure.built.html?t=4.4
```

In the console, `mfSeek(3.2)` moves it. `build.py --png --at 4.4` uses the same
mechanism, which is why a still is reproducible on any Chrome build rather than
depending on how fast the machine reached four seconds.

To change the figure, edit the spec and re-run — layout, edge endpoints, beats
and camera all re-solve together. Editing the generated HTML gets you one
correct frame and a file that is wrong the next time anything changes.
