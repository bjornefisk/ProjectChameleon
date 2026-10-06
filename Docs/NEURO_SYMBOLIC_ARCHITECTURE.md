# Neuro-symbolic system architecture

Project Chameleon uses a deterministic pipeline that separates role inference from coordinate resolution. The parser proposes relationships and layout archetypes from the source document. The solver places the existing elements while enforcing the hard output rules.

The pipeline does not redraw assets, rewrite text, or treat every overlap as an error. It preserves source relationships first, then uses constraints and measured rendering to choose among valid layouts.

## Pipeline overview

```text
Source document and target canvas dimensions
                      │
                      ▼
STAGE 1: Role and relationship inference
  - Normalize geometry, rotation, z-order, opacity, fit, and coverage
  - Infer background, brand, hero, text, and decorative roles
  - Use group_id for rigid units and containment only as a fallback
  - Record intentional source overlaps and busy image regions
                      │
                      ▼
STAGE 2: Layout archetype generation
  - Measure aspect-ratio change and source composition structure
  - Generate near-isomorphic, column-pivot, horizontal-ribbon,
    and vertical-re-stack candidates
  - Derive slots from canvas proportions and measured content
                      │
                      ▼
STAGE 3: Constraint placement and typography
  - Place rigid groups and independent elements on integer geometry
  - Preserve allowed source overlaps and separate new collisions
  - Measure text with the supplied fonts and renderer semantics
  - Generate candidates with different hero and copy emphasis
                      │
                      ▼
STAGE 4: Render-and-validate
  - Render each candidate through the project renderer
  - Check ids, fixed properties, rotated bounds, image ratios,
    text bounds, overlap policy, and contrast
  - Round deliberately, re-check, and emit the best valid JSON
```

## Stage 1: Role and relationship inference

The input supplies geometry, stacking data, visual properties, asset identifiers, and text attributes, but it does not label semantic roles. The engine builds a scene graph:

$$
\mathcal{G} = (\mathcal{V}, \mathcal{E}_R, \mathcal{E}_O)
$$

Nodes $\mathcal{V}$ represent source elements. Relationship edges $\mathcal{E}_R$ encode proximity, alignment, relative scale, stacking, and group membership. The separate overlap set $\mathcal{E}_O$ records pairs that already intersect in the source.

Role inference uses several signals together:

- z-index, including missing or tied values;
- opacity and fit mode;
- coverage and aspect ratio;
- font-size ranking and text geometry;
- explicit `group_id`; and
- position, proximity, and relative size.

No single z-index or coverage threshold defines the background. The same signals must work when the background is missing, tied with another element, or not the largest rectangle.

Grouping follows a strict precedence:

1. Elements with the same `group_id` form a rigid unit.
2. For ungrouped elements, geometric containment and layer proximity may identify a fallback unit.
3. Source overlap alone does not create a group. It records an overlap relationship that the target layout should preserve when it appears intentional.

The parser also marks image regions that are visually busy. Text may overlap a deliberate container or decorative layer, but it must not be placed over a busy image without a readable treatment already present in the source.

## Stage 2: Layout archetype generation

The router measures aspect-ratio change with:

$$
\Delta_{\text{AR}} =
\log\left(
\frac{W_{\text{tgt}} / H_{\text{tgt}}}
     {W_{\text{src}} / H_{\text{src}}}
\right)
$$

The value is a routing signal, not a fixed pixel template. Candidate generation covers four regimes:

### Near-isomorphic

Keep the source topology when the target shape is close enough that the existing relationships fit. Distribute the change through proportional margins, isotropic image scaling, and measured text reflow.

### Column pivot

For a wider target that cannot hold the source vertical stack, pivot major source groups into columns. Allocate width from the target proportions, source group extents, and text requirements. Do not reserve a fixed percentage or pixel width for a named role.

### Horizontal ribbon

For very wide and short targets, arrange the source groups along the primary horizontal axis. The sequence comes from source order and grouping, not a fixed logo, text, image, and CTA slot width.

### Vertical re-stack

For a tall target, re-stack groups along the vertical axis when a wide source composition leaves unusable horizontal density. Preserve source hierarchy, reading order, and intentional overlaps while deriving the gaps from measured content.

The engine may keep several archetypes alive until hard validation and soft scoring select the result. This avoids committing to a layout from aspect ratio alone.

## Stage 3: Constraint placement and typography

For small scenes, CP-SAT or a structured integer search can place the rigid units and independent elements. Its constraints must distinguish source-intended overlaps from new collisions. Alignment, even spacing, hierarchy, balance, whitespace, and readability belong in the objective. Kiwi is optional and can refine coordinates after the topology is fixed.

Typography changes only font size and geometry. Content, font family, weight, style, color, and style runs remain source values. The engine measures the supplied font files and follows the renderer's explicit line representation, line height, letter spacing, and style maps. It searches for the largest size that fits each candidate slot without imposing a universal headline-to-body ratio.

Candidate weights may favor hero scale, copy scale, or balance, but every candidate must satisfy the same hard rules. The ranking step must not rescue an invalid candidate by shrinking an element to zero, hiding it, or dropping it from the output.

## Stage 4: Render-and-validate

Before serialization, the engine renders each valid candidate and checks:

- the output has the same element ids, count, and order as the source;
- fixed text attributes and fixed visual properties are unchanged;
- every rotated axis-aligned bound stays inside the target canvas;
- deliberate integer rounding does not create an overflow;
- foreground image ratios match their source ratios, including elements whose renderer fit mode is `fill`;
- permitted background coverage uses the renderer's crop behavior without changing pixels;
- source-intended overlaps and their rigid relationships are preserved;
- pairs that did not overlap in the source do not collide in the target;
- text remains within its real rendered bounds and readable against the pixels below it; and
- missing asset references remain present without adding replacement content.

The validator rejects hard failures before soft scoring. A repair pass may adjust geometry, but it must not change identity, fixed properties, source content, or the overlap policy.
