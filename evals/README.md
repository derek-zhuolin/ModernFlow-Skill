# Evals

Three end-to-end scenarios for testing changes to this skill. They exist
because the skill was built from observed failures, not from imagined ones —
each expected behaviour below is something that actually went wrong first.

## How to run

1. **Baseline.** Give the `query` to a Claude instance with this skill
   *disabled*. Record what it does.
2. **With the skill.** Same query, skill enabled, fresh context.
3. **Compare** against `expected_behavior`. Every line is pass/fail.

Run on every model you intend to use. A skill that is sufficient for Opus can
be under-specified for Haiku.

## The gaps these were written against

Observed without the skill, repeatedly:

| Gap | Shows up as |
| --- | --- |
| No visual system | Every diagram invents its own palette and type |
| Video assumed | A request for a picture turns into a video pipeline |
| Contrast unchecked | Pale labels ship at ~2:1 |
| `<link>` for fonts | Silent fallback to system fonts |
| Fixed-gap edges | Arcs float away from their nodes on non-circular layouts |
| Estimated narration timing | Picture and voice drift by 15–30% |
| Placeholder content | Skeleton bars and invented numbers survive to the render |

## Adding a scenario

Add a real task that failed, not a hypothetical. Record the baseline before
writing any instruction to fix it.
