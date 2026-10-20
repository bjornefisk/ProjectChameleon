# ADR-002: Pin the Stage 1 schema and renderer contract

## Status

Accepted

## Date

2026-10-06

## Context

`chameleon_design_schema_v0.9.json` is the only schema but calls itself provisional. It permits empty-coordinate ambiguity, does not enforce semantic identity or ratios, and describes `max_lines` behavior that the adapter does not implement. The upstream renderer consumes an internal explicit line map, while the project adapter performs its own wrapping. The dependency currently follows a moving Git branch. These are the pre-ratification/pre-implementation conditions; current bounded implementation and evidence are recorded in `Docs/STATUS.md`.

## Decision

1. Ratify `chameleon/chameleon_design_schema_v0.9.json` as the Stage 1 structural schema. Keep the v0.9 identifier for compatibility, remove its provisional status, allow an empty `elements` array, and tighten only structural rules that are part of this contract. Future incompatible wire changes require a new schema identifier.
2. Define the Stage 1 API as `resize(source, target_canvas) -> {canvas, elements}`. Batch metadata remains outside the design document.
3. Permit only target canvas dimensions, element `x/y/width/height`, and text `font_size` to change. Serialize mutable geometry and font size as finite integers; freeze rotation and every other source field.
4. Use the local `renderer/converter` as the project adapter and pin its upstream renderer to commit `a17e1fb9a732959dd6c21ae168d5ee09d74bd64f`. The adapter's effective defaults, stable z-order sorting, image preprocessing, shape rasterization, missing-asset warning, and `max_size=2048` behavior are documented in the project contract.
5. Keep external style-run indices end-exclusive. The adapter must convert them to the upstream renderer's inclusive internal line-map ranges. Wrapping is adapter behavior; upstream `cr-renderer` itself does not width-wrap.
6. Renderer conformance includes measured glyph widths, style-run face changes, letter spacing, line height, max-lines, height, actual glyph bounds, explicit newlines, and deterministic unbreakable-word failure. It never changes JSON text content.

The adapter's former inclusive style-run loop, spacing omission, style-width omission, and ignored `max_lines`/height are historical conformance gaps. The current adapter implements the ratified bounded behavior; renderer-golden, final-font, and platform qualification evidence remains separate and incomplete.

## Alternatives considered

### Create a new v1.0 schema immediately

Rejected for this ratification pass. It would create a second wire identifier before consumers have a migration need. v0.9 is versioned and can be ratified compatibly; an incompatible change will use v1.0.

### Treat upstream `cr-renderer` alone as the contract

Rejected. The project adapter supplies font bytes, fit preprocessing, shape rasterization, and task-schema conversion that upstream does not provide.

### Adopt the current adapter as-is

Rejected. Its behavior conflicts with the schema's end-exclusive ranges and the required typography measurements.

### Add a public line-map field now

Rejected. The current task schema does not expose one. The adapter owns deterministic line-map generation until a separate wire-schema ADR adds an explicit field.

## Consequences

- Renderer behavior is reproducible only when the VCS revision and compatibility pins stay fixed.
- The response can preserve source JSON while the adapter uses transient newline and line-map data.
- The current bounded adapter and validator have local renderer/text evidence; native-amd64, final-font, and cross-platform qualification remain unverified.
- Rectangle/ellipse stroke behavior is implemented in the local adapter and covered by local renderer tests; any remaining platform/golden discrepancy requires new evidence rather than a contract change.

## Implementation evidence (non-normative)

The decisions above remain authoritative. The current tree implements the bounded adapter behavior through `renderer/converter/{wrap,convert,shapes}.py`, `engine/contract.py`, and the renderer/artifact publication seams. Local conformance tests cover style ranges, effective face metrics, letter spacing, forced lines, line limits, glyph bounds, strokes, and missing assets. These observations do not establish native-amd64 or organizer-controlled qualification; see `Docs/STATUS.md`.

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
