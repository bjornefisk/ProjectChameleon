# 02: Renderer Text Wrapping and Style-Run Conformance

**What to build:**  
Renderer adapter fixes that bring text measurement, wrapping, and shape rasterization into 100% compliance with the ratified contract (ADR-002, ADR-008). Text wrapping must measure using effective style-run font faces and letter spacing without breaking extended grapheme clusters; external style-run indices must use $[start, end)$ code-point indexing; line counts must be enforced against `max_lines` and element box height; and shape strokes must rasterize inside the bounding box.

**Blocked by:**  
None (can start immediately).

**Status:**  
implemented with local renderer-conformance evidence

- [x] Update `chameleon/renderer/converter/wrap.py` to use Unicode UAX #29 extended grapheme clusters as atomic units intersected with UAX #14 line-break opportunities, including Indic_Conjunct_Break and emoji tag sequences. A break must never split an extended grapheme cluster.
- [x] Measure text widths per span using the effective typeface (accounting for bold/italic overrides in `style_runs`) and span-local `letter_spacing`, matching Skia and upstream `cr-renderer` rendering behavior.
- [x] Update greedy wrapping in `wrap.py` to preserve character indices exactly, turning breakable spaces into `\n` in place while retaining non-space UAX #14 breaks in the adapter-owned line map. Raise a deterministic error if an unbreakable word exceeds the slot width.
- [x] Enforce visual line count against `max_lines` and check total line-box height (`lines * font_size * line_height <= height`). Explicit newlines, CRLF, Unicode mandatory separators, and forced empty lines count as visual lines.
- [x] Update `chameleon/renderer/converter/convert.py` to interpret external `style_runs` as $[start, end)$ 0-based code-point intervals, converting them to inclusive ranges only when building upstream `TextMapItem` records.
- [x] Implement overlapping style run resolution: for overlapping spans, the later input run wins per property specified.
- [x] Update `chameleon/renderer/converter/shapes.py` to rasterize declared `stroke_color` and `stroke_width` for rectangles and ellipses completely inside the declared bounding box without expanding outside; every positive width remains at least one pixel.
- [x] Add unit tests under `chameleon/tests/renderer/test_renderer_conformance.py` covering multi-color style boundaries, letter-spaced wrapping, explicit and mandatory Unicode newlines, non-space line maps, Indic/emoji graphemes, max_lines rejection, actual italic glyph bounds, and in-box stroke rasterization.
