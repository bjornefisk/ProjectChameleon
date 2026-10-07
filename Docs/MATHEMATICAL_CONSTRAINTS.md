# Mathematical constraints

> **Authority Notice:** This document formalizes the geometric and optimization model. The binding Stage 1 behavioral contract is ratified in [PROJECT_CONTRACT.md](PROJECT_CONTRACT.md) and Accepted [ADRs](DECISIONS/). In any conflict, the contract and ADRs govern.

This document separates disqualifying structural failures from soft layout preferences. A hard constraint invalidates a candidate. A soft term ranks candidates that already satisfy the hard constraints.

## 1. Formal model

The retargeting step is an autonomous mapping:

$$
f: (\mathcal{D}_{\text{src}}, \mathcal{C}_{\text{tgt}})
\longrightarrow \mathcal{D}_{\text{tgt}}
$$

The source document is:

$$
\mathcal{D}_{\text{src}} = (\mathcal{C}_{\text{src}}, \mathcal{E}_{\text{src}})
$$

where:

$$
\mathcal{C}_{\text{src}} = (W_{\text{src}}, H_{\text{src}})
\qquad
\mathcal{C}_{\text{tgt}} = (W_{\text{tgt}}, H_{\text{tgt}})
$$

Each element retains its source identity:

$$
e_i =
(\operatorname{id}_i, x_i, y_i, w_i, h_i, \theta_i, z_i, \tau_i, \mathcal{A}_i)
$$

The type-specific attributes $\mathcal{A}_i$ include asset identifiers, text content, font properties, style runs, opacity, fit, and color.

The output must satisfy:

$$
\{\operatorname{id}(e_i^{\text{tgt}})\}
=
\{\operatorname{id}(e_i^{\text{src}})\}
\qquad
|\mathcal{E}_{\text{tgt}}|
=
|\mathcal{E}_{\text{src}}|
$$

Element order and every fixed attribute remain unchanged. Only the permitted geometry fields and, for text, `font_size` may change.

## 2. Canvas containment with rotation

Containment uses the rotated axis-aligned bounding box, not the unrotated width and height. For a rectangle with local width $w_i$, height $h_i$, angle $\theta_i$, and center $(c_{x,i}, c_{y,i})$:

$$
a_i =
|w_i \cos\theta_i| + |h_i \sin\theta_i|
$$

$$
b_i =
|w_i \sin\theta_i| + |h_i \cos\theta_i|
$$

Its rotated bounds are:

$$
[c_{x,i} - a_i/2,\ c_{x,i} + a_i/2]
\times
[c_{y,i} - b_i/2,\ c_{y,i} + b_i/2]
$$

Every non-background element must satisfy:

$$
x_{\min,i}^{\text{tgt}} \ge 0,\quad
y_{\min,i}^{\text{tgt}} \ge 0
$$

$$
x_{\max,i}^{\text{tgt}} \le W_{\text{tgt}},\quad
y_{\max,i}^{\text{tgt}} \le H_{\text{tgt}}
$$

*(Exception: contract-defined source-bleed decoration — an ungrouped translucent shape already clipped by the source canvas must preserve clipping on the same side set and intersect the target).*
The engine rounds output coordinates and dimensions deliberately, then recomputes these bounds. A candidate that passes before rounding but fails after rounding is invalid.

Zero-size source elements and line shapes must not cause division by zero. They remain in the output and are handled as degenerate geometry. The engine must not create a zero-size or hidden element to shed content.

## 3. Image ratio invariance

For every non-background image whose source dimensions are positive:

$$
\frac{w_i^{\text{tgt}}}{h_i^{\text{tgt}}}
=
\frac{w_i^{\text{src}}}{h_i^{\text{src}}}
$$

Equivalently:

$$
w_i^{\text{tgt}} h_i^{\text{src}}
-
h_i^{\text{tgt}} w_i^{\text{src}}
= 0
$$

This remains true when the renderer's image fit value is `fill`. Fit changes renderer treatment, not the source ratio requirement for foreground geometry.

Background elements may cover the target canvas through the renderer's `fit=cover` behavior. That permits cropping by the renderer. It does not permit editing, synthesizing, or replacing the source pixels.

## 4. Source-aware overlap

The solver must not force every pair of elements apart. Define:

- $\mathcal{O}_{\text{src}}$: source pairs that overlap intentionally, including grouped labels and backplates, layered art, and decorative translucent shapes;
- $\mathcal{P}_{\text{new}}$: source pairs that did not overlap and are not exempt background relationships; and
- $\mathcal{O}_{\text{busy}}$: image regions where text would become unreadable without a source-supported treatment.

For each pair in $\mathcal{P}_{\text{new}}$, at least one separation condition must hold:

$$
x_i^{\text{tgt}} + w_i^{\text{tgt}} \le x_j^{\text{tgt}}
$$

$$
x_j^{\text{tgt}} + w_j^{\text{tgt}} \le x_i^{\text{tgt}}
$$

$$
y_i^{\text{tgt}} + h_i^{\text{tgt}} \le y_j^{\text{tgt}}
$$

$$
y_j^{\text{tgt}} + h_j^{\text{tgt}} \le y_i^{\text{tgt}}
$$

The separation check uses rotated bounds. Pairs in $\mathcal{P}_{\text{new}}$ collide when their rotated bounding boxes have positive-area intersection; boundary contact (touching edges or corners) is permitted. Pairs in $\mathcal{O}_{\text{src}}$ must keep their source relationship, including rigid group movement or preserved relative offsets. They are excluded from unintended-overlap scoring only when that relationship remains intact. A newly placed text element must not occupy a busy image region unless the source design provides a readable overlay or equivalent treatment.
## 5. Typography and fixed text attributes

Text content, font family, weight, style, color, style runs, line height, letter spacing, and opacity remain unchanged. Only font size and geometry may change.

The renderer follows explicit line information. It does not perform greedy or optimal width-based wrapping. The engine must measure each rendered line using the supplied font and the renderer's line-height and letter-spacing semantics. Text bounds must represent the actual rendered glyph extents, not spare area used to conceal overflow.

The source hierarchy is a soft constraint:

$$
\operatorname{rank}(s_{\text{headline}})
\ge
\operatorname{rank}(s_{\text{subhead}})
\ge
\operatorname{rank}(s_{\text{body}})
$$

The engine preserves source ratios where the target allows it. It does not impose a universal ratio. A readable floor is a preference near $10$ px unless the source is smaller. If a candidate cannot keep text readable without violating a hard rule, the candidate is rejected rather than hidden or rewritten.

## 6. Reading order and rigid units

Explicit `group_id` values define rigid units. For ungrouped elements, containment and proximity provide layout hints only, not fallback rigid units. Internal offsets and relative scale are preserved within each rigid unit.
The inferred reading order is a soft relationship, not a license to separate a group. When the target requires a topology change, the candidate should preserve the source sequence and hierarchy where it can do so without causing a hard failure.

## 7. Contrast and legibility (soft ranking term)

Contrast is an internal soft ranking objective, not a disqualifying hard gate. For each text element, evaluate contrast against the actual rendered background pixels beneath its glyph bounds, with a target preference of:

$$
\operatorname{ContrastRatio}
\left(
e_i,\ \mathcal{B}_{\text{rendered}}(e_i)
\right)
\ge 4.5
$$

The contrast check accounts for the target position, the background crop, opacity, and any source-supported overlay. A lower contrast score reduces candidate ranking, but it does not invalidate an otherwise hard-valid geometry candidate.
## 8. Missing assets and pixel integrity

An unavailable asset reference does not authorize a new file, placeholder artwork, hidden element, opacity-zero element, or zero-size geometry. The output keeps the original element id and asset reference. The renderer or caller handles the missing file without changing the design record.

The engine may reposition, resize, and reflow existing elements. It must not regenerate, redraw, inpaint, seam-carve, outpaint, or replace raster content. These operations are disqualifying even when the final geometry fits the target canvas.