# ADR-008: Define typography and renderer edge semantics

## Status

Accepted — normative contract decision. The bounded implementation and local evidence are recorded in `Docs/STATUS.md`; this ADR does not claim native-amd64, final-font, or organizer-controlled qualification.

## Date

2026-10-06

## Context

The ratified contract already fixes the public text content, font family/weight/style, color, alignment, line height, letter spacing, style-run data, and allowed mutable `font_size`. It also requires explicit-newline preservation, deterministic adapter-owned wrapping, end-exclusive external style ranges, actual glyph-bound validation, `max_lines` and height enforcement, and rejection rather than truncation or rewriting. The pinned `cr-renderer` revision consumes an explicit internal line map; it does not supply the project's width-based wrapping policy.

The current adapter gaps listed here describe the pre-implementation baseline. They are evidence for this decision, not permission to weaken the ratified rules; the bounded adapter now implements the listed wrapping, measurement, overflow, and stroke behavior, with qualification boundaries recorded separately.

### Authority classification

- **Ratified current contract:** `Docs/PROJECT_CONTRACT.md` §§4–6, ADR-002, and ADR-003. These preserve text and style data, use external `[start, end)` ranges, require measured renderer semantics and actual glyph bounds, and reject overflow without mutation.
- **Accepted internal contract decision:** Unicode cluster/line-break policy, greedy line generation, overlapping-run resolution, line-count/height rejection, span-local measurement, and adapter shape-stroke policy below are ratified defaults. The current bounded adapter implements these behaviors locally; native renderer/font/platform qualification remains unverified.
- **Externally unverified organizer fact:** final fonts/assets/licensing and native `amd64` qualification remain organizer or release facts. They determine which font bytes may be packaged and whether a submission can qualify, but they do not authorize substitution or metric invention.

## Decision

### 1. Generate lines from Unicode-safe boundaries

Use Unicode extended grapheme clusters as atomic units, following [Unicode Standard Annex #29](https://www.unicode.org/reports/tr29/). Generate line-break opportunities from [Unicode Standard Annex #14](https://www.unicode.org/reports/tr14/), then intersect those opportunities with extended-grapheme-cluster boundaries. A line break must never split an extended grapheme cluster.

Use a deterministic latest-fitting greedy algorithm:

1. Preserve every explicit newline as a forced break.
2. For the current line, measure the candidate span using the effective face and spacing for each style span.
3. If the candidate fits, continue.
4. If it does not fit, break at the latest permitted opportunity that fits and continue from the following cluster.
5. If no permitted break exists before an unbreakable segment and that segment cannot fit the element width, reject the candidate.

Do not hyphenate, rewrite, reorder, delete, or silently truncate content. A transient renderer line map MAY represent a breakable source space as a line boundary as allowed by the contract, but the external JSON `content` remains byte-for-byte/code-point-for-code-point unchanged.

Every visual line counts, including forced empty lines. For example, a forced newline creates a break even when one or both adjacent lines contain no glyphs. A trailing forced newline therefore contributes its final empty visual line to `max_lines` and height checks.

### 2. Keep style ranges external, code-point indexed, and deterministic

Interpret every external style range as a Python/Unicode code-point `[start, end)` range into the unchanged `content` string. Require:

```text
0 <= start <= end <= len(content)
```

An empty range is valid but has no effect. For overlapping runs, resolve properties independently: the later input run wins for each property it supplies, while properties it does not supply inherit the earlier effective value or the base text value. This preserves input order as the deterministic tie-break and avoids inventing a style-run normalization field.

Line wrapping remains cluster-safe even when a style boundary falls inside an extended grapheme cluster. The boundary can affect effective span metrics without becoming a line-break opportunity. The adapter converts the external ranges to the pinned upstream renderer's inclusive internal representation only at the transient line-map boundary; it never exposes inclusive ranges in the public schema.

### 3. Measure the effective renderer spans, not a base-face approximation

Measure each line using:

- the exact packaged face selected by the base `font_family`, `font_weight`, and `font_style`;
- the effective face for each style span;
- the serialized integer `font_size` candidate;
- the element's `letter_spacing`, using the pinned renderer's glyph-placement semantics; and
- the transient line map that will actually be supplied to the renderer.

Validate the actual positioned glyph bounds, not only nominal advance width or spare rectangle area. Alignment remains the immutable source `text_align` behavior inside the element width. The upstream source evidence for line maps, glyph advances, alignment, and spacing is the pinned [cr-renderer commit](https://github.com/CyberAgentAILab/cr-renderer/commit/a17e1fb9a732959dd6c21ae168d5ee09d74bd64f), including its [schema](https://raw.githubusercontent.com/CyberAgentAILab/cr-renderer/a17e1fb9a732959dd6c21ae168d5ee09d74bd64f/src/cr_renderer/schema.py), [text utilities](https://raw.githubusercontent.com/CyberAgentAILab/cr-renderer/a17e1fb9a732959dd6c21ae168d5ee09d74bd64f/src/cr_renderer/text_utils.py), and [renderer](https://raw.githubusercontent.com/CyberAgentAILab/cr-renderer/a17e1fb9a732959dd6c21ae168d5ee09d74bd64f/src/cr_renderer/renderer.py).

A rendered candidate is not hard-valid merely because its line advances fit. The actual glyph envelope, including negative bearings, italic overhang, and the selected style face, must be within the declared text geometry under the contract's rotation and containment rules.

### 4. Reject line-count and line-box overflow

When `max_lines` is non-null, reject any candidate whose visual-line count exceeds it. Never truncate to meet the cap. For every candidate, reject if the line-box stack implied by the integer `font_size` and `line_height` cannot fit the element height, or if actual positioned glyph bounds exceed the element geometry. Preserve the source `line_height` and `letter_spacing`; changing `font_size` is the only permitted text-style adjustment.

The check must include forced empty lines and must occur after final integer serialization. A candidate that fits only at a pre-serialization font size or geometry is invalid. An unbreakable segment that cannot fit the available width is a hard failure, not an invitation to rewrite content, substitute a font, or hide the record.

### 5. Rasterize declared rectangle and ellipse strokes inside the box

The adapter policy MUST rasterize rectangle and ellipse strokes inside the declared element box when `stroke_color` and positive `stroke_width` are present, while preserving all source fields exactly. Stroke rasterization is adapter behavior because the pinned upstream renderer has no native shape primitive. It must not expand the public geometry, alter `stroke_width`, or create pixels outside the declared shape bounds.

This is a renderer-conformance decision, not a claim about upstream native shape support. The local adapter rasterizes rectangle/ellipse strokes inside the declared box and covers them with local tests; platform/golden qualification remains separate. The contract's line-shape behavior and all immutable shape fields remain unchanged.

### 6. Keep typography deterministic and local

The adapter owns line-map generation and must use only packaged, explicitly loaded font bytes in the offline Stage 1 image. It must not download a font, silently substitute a family, or use a finale/Adobe Express font metric in the Stage 1 path. If a declared face cannot be loaded, the task follows the typed runtime/failure protocol rather than changing the source font attributes.

No public line-map field is added. The external JSON remains the ratified design document, while line maps and transient break representations remain internal renderer inputs.

## Alternatives Considered

### Treat each code point as an independently breakable character

Rejected. It can split combining marks, emoji sequences, regional indicators, and other extended grapheme clusters. UAX #29 provides a maintained boundary rule for atomic user-perceived units.

### Use arbitrary spaces or code points as break opportunities

Rejected. UAX #14 is the authoritative general line-breaking reference, and intersecting it with cluster boundaries avoids unsafe breaks while retaining deterministic behavior.

### Apply style ranges inclusively at both ends

Rejected. The schema and ADR-002 define public `[start, end)` ranges. Inclusive conversion is permitted only inside the pinned upstream line-map adapter.

### Measure only the base face and global spacing

Rejected. A styled span can have different advances, bearings, and glyph bounds. Omitting its metrics can accept a rendered overflow or reject a valid candidate unpredictably.

### Truncate, hyphenate, rewrite, or shrink content to fit

Rejected. Stage 1 preserves source text and immutable style fields. Hyphenation or rewriting also changes the deterministic renderer input and is outside the ratified contract.

### Ignore `max_lines` or rely on clipping

Rejected. The contract requires enforcement and failure rather than silent clipping or truncation.

### Treat rectangle/ellipse stroke fields as metadata forever

Rejected as the long-term conformance default. The fields are ratified source data and this decision makes their declared visual semantics explicit, while acknowledging that implementation and evidence are still pending.

### Add a public line-map field

Rejected for this decision. The current wire schema does not expose one, and ADR-002 assigns deterministic line-map generation to the adapter.

## Consequences

- Line breaking is Unicode-safe, deterministic, and compatible with unchanged JSON content.
- The same text can fail at a larger or differently styled `font_size` even when a rough character-count heuristic would pass; this is intentional renderer-in-loop validation.
- Empty and forced lines consume line-count and height budget, making `max_lines` and height behavior explicit rather than renderer-dependent.
- Style-run boundary, spacing, face-selection, and glyph-bearing cases are conformance obligations. The current bounded adapter has local evidence for them; official/native qualification remains a separate gate.
- Missing or unlicensed final fonts remain an external qualification issue; Stage 1 must not hide that issue by substituting a different font.
- Stroke rasterization is implemented by the adapter and covered by local evidence; it does not change the schema or the source record set. Any platform/golden discrepancy remains a qualification issue.
- This ADR does not authorize unrelated code, schema, dependency, font, or runtime changes. Its implementation evidence is tracked separately so documentation-only ratification is not confused with platform qualification.

## Affected files/schema fields

The implemented bounded work touches the text wrapping/line-map adapter, font loading and glyph measurement path, semantic validator, and shape rasterization adapter. Relevant existing fields are `content`, `font_family`, `font_size`, `font_weight`, `font_style`, `color`, `text_align`, `line_height`, `letter_spacing`, `max_lines`, `style_runs`, `shape_type`, `stroke_color`, `stroke_width`, and geometry/rotation fields.

No public line-map field or new style-run field is added. The project continues to use the pinned `cr-renderer` revision and the ratified v0.9 wire schema. The current bounded implementation and local evidence do not establish native-amd64, clean-cache, final-font, or organizer-controlled qualification.

## Required validation/evidence

Before implementation can claim conformance, the evidence must include at least:

- UAX #29 extended-grapheme cases for combining marks, emoji ZWJ sequences, regional indicators, and other cluster boundaries;
- UAX #14 opportunities intersected with cluster boundaries, including punctuation, spaces, scripts with different break behavior, and an unbreakable segment;
- explicit newlines, leading/trailing newlines, consecutive empty lines, and visual-line counts against `max_lines`;
- style ranges at `[0, 0)`, `[0, 1)`, the final code-point boundary, overlapping properties, omitted properties, and a range whose endpoint falls inside an extended grapheme cluster;
- effective base/style-run face metrics, positive and negative letter spacing, all alignments, nondefault line height, italic overhang, negative bearings, and integer font-size serialization;
- renderer-in-loop glyph bounds proving that nominal advances alone cannot pass a hard-validity check;
- width overflow, line-box-height overflow, `max_lines` overflow, and unbreakable-word failure all reject without content or style mutation;
- rectangle, rounded-rectangle, ellipse, and line shape cases proving declared stroke fields are preserved and required rectangle/ellipse stroke rasterization stays inside the declared box;
- missing-font and missing-asset paths preserve source identity and use the typed failure/placeholder behavior already authorized by the contract, without silent font substitution;
- repeated renders in the pinned offline `linux/amd64` image produce the same line maps, glyph bounds, status, and PNG bytes; and
- a source record tying measured behavior to the pinned `cr-renderer` revision and packaged font hashes.

The external references used for this decision are [Unicode UAX #14](https://www.unicode.org/reports/tr14/), [Unicode UAX #29](https://www.unicode.org/reports/tr29/), and the pinned [cr-renderer commit](https://github.com/CyberAgentAILab/cr-renderer/commit/a17e1fb9a732959dd6c21ae168d5ee09d74bd64f) and source files linked above. The project contract and pinned dependency evidence remain authoritative over generic upstream behavior.

The current tree provides local tests and renderer/artifact evidence for the bounded behavior described here; see `Docs/STATUS.md` and `Docs/DEPENDENCY_EVIDENCE.md`. Native-amd64, final-font, and cross-platform hash qualification remain unverified.

### Organizer clarification required

- Final fonts/assets/licensing and native amd64 qualification.
