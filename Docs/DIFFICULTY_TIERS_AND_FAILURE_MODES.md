# Empirical challenge difficulty tiers and failure modes

Project Chameleon evaluates the same retargeting task across three difficulty tiers. Each tier stresses a different part of the pipeline, from nearby aspect-ratio changes to dense layouts with missing assets and very little usable height.

## Level 1: Warm-up

Level 1 uses small compositions with:

- $n \le 5$ elements;
- shallow layer depth; and
- a moderate aspect-ratio change.

A representative transition is an Instagram square from $1080 \times 1080$ to a portrait post of $1080 \times 1350$.

The main failure mode is naive uniform stretching. It distorts product art, changes the source image ratio, or leaves unnecessary padding. A safe candidate keeps the source topology when it fits, scales foreground images isotropically, and distributes new margin from the target dimensions.

The candidate still needs to preserve exact element identity, source grouping, intentional overlaps, text attributes, and rotated containment. Near-isomorphic routing is a preference, not permission to ignore those checks.

## Level 2: Core

Level 2 is the main composition benchmark. It uses:

- approximately 10 to 15 elements;
- complex stacking hierarchies;
- semi-transparent decorative vectors;
- grouped button assemblies; and
- a substantial aspect-ratio change.

A representative transition is a square canvas of $1080 \times 1080$ to an extended landscape banner of $1600 \times 400$.

Keeping a vertical stack can push content outside the target. Moving children independently can separate a button label from its shape. Moving text over a busy image can reduce contrast even when every rectangle is inside the canvas.

The router should generate a column pivot and other plausible candidates. Column widths come from target proportions, source group extents, measured text, and image ratios. They do not come from a fixed percentage or a named pixel slot. Source-intended overlaps remain allowed, while pairs that were separate in the source must not collide after reflow.

## Level 3: Advanced

Level 3 introduces:

- dense element graphs with $n \ge 15$;
- extreme aspect-ratio changes;
- adversarial copy lengths;
- rotated elements, line shapes, or zero-size source elements; and
- deliberately unavailable asset references.

A representative transition is a tall portrait asset of $1080 \times 1350$ to a narrow web leaderboard of $728 \times 90$.

The target may not have enough height for the source stack. A horizontal ribbon can work for a wide target, while a vertical re-stack is needed when the target is tall and the source is wide. Both must derive positions from source order, group extents, content measurement, and the target canvas rather than fixed logo, text, image, or CTA slots.

The renderer uses explicit text line information instead of automatic width-based wrapping. Long copy therefore requires measured line geometry and font-size search. Missing files must not crash the pipeline or lead to a new asset. The original element record remains in the output.

## Cross-tier failure modes

The harness should include cases that are not present in the three sample tasks:

- no background, tied or missing z-index values, and several large candidates;
- a single element, an empty element list, zero-size input geometry, and line shapes;
- rotated images and text near every canvas edge;
- long text with style runs, nonzero letter spacing, and nondefault line height;
- source-intended overlap between text and a button, translucent decoration, or layered art;
- separate elements that must remain separated after routing; and
- foreground images whose `fit` value is `fill`, with the source ratio still preserved.

Every case is checked with the same identity, fixed-property, rotated-bound, image-ratio, overlap, text-bound, and pixel-integrity rules.

## Difficulty comparison

| Difficulty level | Composition complexity | Geometric stress profile | Prevalent failure modes | Algorithmic mitigation strategy |
| --- | --- | --- | --- | --- |
| Level 1: Warm-up | Few elements, $n \le 5$; shallow hierarchy | Nearby change from $1080 \times 1080$ to $1080 \times 1350$ | Distorted product art, unnecessary padding, weak margin distribution | Isotropic image scaling, source-topology preservation, and proportional margin allocation |
| Level 2: Core | Moderate element count; grouped buttons and translucent layers | Square to wide banner, represented by $1080 \times 1080$ to $1600 \times 400$ | Boundary collisions, broken groups, weak contrast over imagery | Source-aware grouping, column candidates, measured text sizing, and contrast validation |
| Level 3: Advanced | Dense graph, adversarial text, rotation, and missing assets | Extreme wide or tall catalogue formats, represented by $1080 \times 1350$ to $728 \times 90$ | Overflow after rotation or rounding, unreadable text, divide-by-zero errors, missing-asset crashes | Multiple archetypes, explicit renderer-matched text measurement, defensive geometry, and render validation |

These tiers describe stress profiles, not hard-coded layout templates. The same checks apply to hidden catalogue sizes and unseen source designs.
