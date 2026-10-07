# Computational typographic reflow and structural grouping

> **Authority Notice:** This document is architectural guidance. The binding Stage 1 behavioral contract is ratified in [PROJECT_CONTRACT.md](PROJECT_CONTRACT.md) and Accepted [ADRs](DECISIONS/). In any conflict, the contract and ADRs govern.

Text is a measured layout element, not a bitmap to stretch. Its rendered bounds depend on the supplied font, font size, line representation, line height, letter spacing, and style runs.

## Why uniform text scaling fails

Uniform scaling changes the relationship between text and the rest of the composition. It can make a headline unreadable on a short banner, or leave a text box larger than the glyphs it actually renders. The target geometry must be solved with the real font metrics and then checked through the renderer.

## Renderer semantics

The public `cr-renderer` implementation renders the explicit `lineMap` entries. It does not measure the element width and insert greedy or optimal line breaks. A missing line map becomes one line covering the text, and `wordBreak` is accepted by the schema but is not used by the render path.

For each rendered line:

- the vertical origin advances by `line_index * font_size * line_height`;
- glyph advances come from the loaded typeface;
- `letter_spacing * glyph_index` is added to each glyph position, so the total width includes letter spacing between glyphs;
- left, center, and right alignment offset the rendered blobs within the element width; and
- the renderer logs when the rendered width exceeds the element width rather than clipping or wrapping it.

The renderer uses the explicit font, weight, style, color, and style maps. The reflow engine must keep those source values fixed. It may change font size and permitted geometry fields. The public design schema does not expose a line-map field; line maps are generated deterministically by the project renderer adapter from unchanged text content (ADR-002, ADR-008).

The renderer draws images by mapping the complete source rectangle into the destination rectangle. That is fill behavior, not a named contain or cover implementation in the public renderer. A wrapper may add a cover path for backgrounds, but the layout engine must not assume that a foreground image will be corrected by the renderer. Its output geometry must retain the source aspect ratio.

Rotation is applied after translating to the element's position and uses the local element center as the rotation center. Text and image bounds therefore need rotated axis-aligned checks after every geometry change.

## Elastic text geometry

When explicit lines are available, the required text height is:

$$
h_i(s_i) =
N_{\text{lines},i} \cdot s_i \cdot \lambda_i
$$

where $N_{\text{lines},i}$ comes from the line representation supplied to the renderer, $\lambda_i$ is the source line-height value, and $s_i$ is the candidate font size. The rendered width must be measured from the actual glyph advances and letter spacing for every line. It is not safe to estimate the box from character count.

If the output contract permits line geometry to change, the engine must preserve the full source string and every style run, then measure the resulting line representation again. A text box that is intentionally larger than its glyph bounds is not a valid way to hide overflow.

## Font-size optimization

Each text element has a constrained sizing problem. For a candidate slot, search for the largest font size that keeps every rendered line inside the slot:

$$
s_i^* = \arg\max_{s_i} s_i
\quad \text{subject to} \quad
w_i(s_i) \le W_{\text{slot}}, \quad
h_i(s_i) \le H_{\text{slot}}
$$

The search can use a bracketed or binary strategy when the measured result is monotonic over the tested range. It must stop at a readable floor, roughly $10$ px unless the source size is already smaller, and must reject a candidate when the floor cannot satisfy the slot.

## Preserve typographic hierarchy

The source design supplies the hierarchy. The engine should preserve the ordering and relative scale of headline, subhead, body, and CTA text after resizing:

$$
\operatorname{rank}(s_{\text{headline}})
\ge
\operatorname{rank}(s_{\text{subhead}})
\ge
\operatorname{rank}(s_{\text{body}})
$$

The source ratios are the starting point, not a universal relation such as $1.4$ or $1.96$. A narrow target may require a different absolute scale, but it should not invert the source hierarchy merely to fill a slot.

## Structural grouping

Design primitives often form rigid units. If the children are optimized independently, a CTA label can separate from its backplate or a badge caption can drift from its icon.

Grouping precedence is:

1. Use explicit `group_id` as the primary source of truth. Every element in the same group moves with the same uniform group transform (ADR-007).
2. For ungrouped elements, geometric containment and proximity are layout hints only, not fallback rigid units.
3. Do not infer a group from overlap alone. Preserve an intentional source overlap as an allowed relationship even when elements remain separate records.
The macro-layout solver places each rigid unit. Child geometry is then derived from the source internal offsets and scale. For a centered label inside a shape:

$$
x_{\text{text}} =
x_{\text{shape}} +
\frac{w_{\text{shape}} - w_{\text{text}}}{2}
$$

$$
y_{\text{text}} =
y_{\text{shape}} +
\frac{h_{\text{shape}} - h_{\text{text}}}{2}
$$

The formulas are a default for a centered source relationship, not a reason to override an explicit alignment or group transform.
