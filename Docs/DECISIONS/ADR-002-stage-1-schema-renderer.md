# ADR-002: Pin the Stage 1 schema and renderer contract

## Status

Accepted

## Date

2026-10-06

## Context

At the time of this decision, `chameleon_design_schema_v0.9.json` was the only schema but called itself provisional. It permitted empty-coordinate ambiguity, did not enforce semantic identity or ratios, and described `max_lines` behavior that the adapter did not implement. The upstream renderer consumed an internal explicit line map, while the project adapter performed its own wrapping. The dependency followed a moving Git branch.

## Decision

1. Ratify `chameleon/chameleon_design_schema_v0.9.json` as the Stage 1 structural schema. Keep the v0.9 identifier for compatibility, remove its provisional status, allow an empty `elements` array, and tighten only structural rules that are part of this contract. Future incompatible wire changes require a new schema identifier.
2. Define the Stage 1 API as `resize(source, target_canvas) -> {canvas, elements}`. Batch metadata remains outside the design document.
3. Permit only target canvas dimensions, element `x/y/width/height`, and text `font_size` to change. Serialize mutable geometry and font size as finite integers; freeze rotation and every other source field.
4. Use the local `renderer/converter` as the project adapter and pin its upstream renderer to commit `a17e1fb9a732959dd6c21ae168d5ee09d74bd64f`. The adapter's effective defaults, stable z-order sorting, image preprocessing, shape rasterization, missing-asset warning, and `max_size=2048` behavior are documented in the project contract.
5. Keep external style-run indices end-exclusive. The adapter must convert them to the upstream renderer's inclusive internal line-map ranges. Wrapping is adapter behavior; upstream `cr-renderer` itself does not width-wrap.
6. Renderer conformance includes measured glyph widths, style-run face changes, letter spacing, line height, max-lines, height, actual glyph bounds, explicit newlines, and deterministic unbreakable-word failure. It never changes JSON text content.

**Historical pre-implementation note (superseded):** at acceptance, the adapter's inclusive style-run loop, spacing omission, style-width omission, and ignored `max_lines`/height were recorded as conformance gaps. They did not redefine the contract. The bounded local adapter now implements the corresponding style-run, spacing, line-count/height, glyph-bound, and in-box-stroke behavior in `chameleon/renderer/converter/wrap.py`, `convert.py`, and `shapes.py`, with focused evidence in `chameleon/tests/renderer/test_renderer_conformance.py`; this does not claim full qualification.

## Alternatives considered

### Create a new v1.0 schema immediately

Rejected for this ratification pass. It would create a second wire identifier before consumers have a migration need. v0.9 is versioned and can be ratified compatibly; an incompatible change will use v1.0.

### Treat upstream `cr-renderer` alone as the contract

Rejected. The project adapter supplies font bytes, fit preprocessing, shape rasterization, and task-schema conversion that upstream does not provide.

### Adopt the current adapter as-is

**Historical pre-implementation alternative:** rejected at acceptance. Its then-current behavior conflicted with the schema's end-exclusive ranges and the required typography measurements.

### Add a public line-map field now

Rejected. The current task schema does not expose one. The adapter owns deterministic line-map generation until a separate wire-schema ADR adds an explicit field.

## Consequences

- Renderer behavior is reproducible only when the VCS revision and compatibility pins stay fixed.
- The response can preserve source JSON while the adapter uses transient newline and line-map data.
- Historical consequence: renderer conformance work was required before typography correctness could be claimed. The bounded implementation now supplies that local behavior, while qualification and external runtime evidence remain separate gates.
- Historical gap note superseded by the bounded in-box stroke implementation; rectangle/ellipse stroke fields remain fixed schema data and the normative decision is unchanged.

## Affected files/schema fields

- `chameleon/chameleon_design_schema_v0.9.json`
- `chameleon/requirements.txt`
- `chameleon/renderer/converter/convert.py`, `wrap.py`, `assets.py`, `shapes.py`, and `brand_fonts.py`
- `rotation`, `x`, `y`, `width`, `height`, `font_size`, `max_lines`, `style_runs`, `line_height`, `letter_spacing`, `fit`, and shape fields

## Required validation tests

- Validate all three sample `source` documents and the empty-design fixture with Draft 2020-12.
- Exercise `[start, end)` style runs at both boundaries.
- Render explicit two-line text, long words, styled runs, positive/negative letter spacing, nondefault line height, all alignments, rotation, contain/cover/fill, shapes, missing assets, and tied/missing z-index values.
- Compare rendered glyph bounds and PNG dimensions/hashes against the pinned adapter and upstream revision.
