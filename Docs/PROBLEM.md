# Problem formulation

> **Authority Notice:** This document is architectural guidance. The binding Stage 1 behavioral contract is ratified in [PROJECT_CONTRACT.md](PROJECT_CONTRACT.md) and Accepted [ADRs](DECISIONS/). In any conflict, the contract and ADRs govern.

## The problem

Project Chameleon retargets an existing graphic design from its source canvas to a target canvas with a different spatial envelope. The output must preserve the design's hierarchy, brand identity, visual balance, and typographic legibility.

The engine changes the layout of existing elements. It may reposition, resize, and reflow their geometry so they fit the target canvas. It must not treat the whole design as one image, stretch the composition, or generate replacement pixels.

For Project Chameleon, the retargeting step is an autonomous mapping:

$$
f: (\mathcal{D}_{\text{src}}, \mathcal{C}_{\text{tgt}})
\longrightarrow \mathcal{D}_{\text{tgt}}
$$

The mapping receives the source document and target canvas, then returns the target document without manual placement decisions during the solve.

## Why simple resizing is not enough

Uniform scaling changes the proportions of the composition. It can distort brand imagery, move rotated elements outside the canvas, and make text too small or too wide for the renderer's actual glyph bounds. Cropping avoids some distortion but can remove important content.

Generative computer vision methods create a different problem. Seam carving, structural inpainting, diffusion-based outpainting, and replacement imagery alter pixels. Project Chameleon does not permit that behavior. Backgrounds may use the renderer's permitted `fit=cover` crop, but the source pixels remain the source pixels. Foreground images keep their source ratios, including when their fit value is `fill`.

## What the input does not tell us

The input JSON contains spatial data, layer indices, text properties, grouping, and asset identifiers. It may not label which element is a brand logo, product showcase, primary headline, or action container.

The engine infers functional hierarchy and layout relationships from:

- element position and geometry, including rotation;
- layer order, opacity, coverage, and fit;
- text type, scale, font metrics, and content length;
- explicit `group_id` values; and
- asset characteristics and source overlap.

`group_id` is the primary source of truth for rigid units. For ungrouped elements, geometric containment and proximity are layout hints only, not fallback rigid units. Source overlap is evidence of an intended relationship, not automatic proof that two elements should be forced apart or merged into a unit.

The inferred roles guide layout decisions. They do not change the underlying assets, text content, fixed text attributes, or element identity.

## Required output behavior

In practical terms, the output must:

1. keep the same element ids, count, order, and required records;
2. keep active foreground elements inside the target canvas using rotated axis-aligned bounds after integer quantization (with the narrow exception for contract-defined source-bleed decorative shapes);
3. preserve raster image aspect ratios, including `fit=fill`, except for permitted background cover cropping;
4. preserve source-intended overlaps and avoid new collisions between pairs that were separate in the source;
5. keep text content, font family, weight, style, color, and style runs fixed;
6. keep text inside its real rendered bounds; readability and contrast are soft ranking objectives evaluated against rendered pixels; and
7. avoid zero-size, hidden, opacity-zero, or replacement elements used to remove content.

These requirements describe the problem. The companion constraints document expresses them as mathematical checks and identifies which failures are disqualifying and which are soft preferences.
