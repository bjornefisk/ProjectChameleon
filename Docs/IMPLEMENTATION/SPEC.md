# Project Chameleon implementation specification

**Status:** The public Level 3 sample succeeds in local integration tests under the Issue #61 changes; PR #65 merged the implementation and Issue #61 is closed. Required native x86_64 CI run 39711973748 passed on PR head `33f6fd9`; held-out scoring, cross-platform parity, and broader qualification remain explicit in `Docs/STATUS.md`.
**Date:** 2026-10-22
**Normative Authority:** [`../PROJECT_CONTRACT.md`](../PROJECT_CONTRACT.md) and [`../DECISIONS/`](../DECISIONS/) (ADR-001 through ADR-012)

**Consolidated architecture:** [`../FINAL_ARCHITECTURE.md`](../FINAL_ARCHITECTURE.md) summarizes the implementation boundary and remains subordinate to the contract and Accepted ADRs.

---

## Problem statement

Designers spend hours manually rebuilding creative assets for dozens of canvas sizes (from tall 9:16 phone stories to ultra-wide 8:1 web banners). Existing automated resize tools in platforms like Adobe Express either uniformly stretch the composition (distorting branded products and text) or crop the canvas (lopping off vital logos, headlines, and call-to-action buttons). 

Naive programs stretch the picture; good ones move the furniture. The challenge is to build an autonomous engine that takes any source design and target canvas and resizes it so it looks intentionally designed:
- zero pixel stretching or generative hallucinations;
- all elements preserved in exact count, identity, and content;
- branded products and logos kept in true aspect ratio;
- rigid groups (like badges and buttons) kept unified;
- text reflowed at readable sizes without awkward collisions;
- extreme canvas shapes handled with deliberate architectural shifts (like horizontal ribbons);
- 100% offline, deterministic execution inside a `linux/amd64` container under tight resource limits.

---

## Solution

A deterministic, renderer-aware adaptive layout engine that separates macro-topology selection from coordinate solving and micro-typography optimization:

1. **Ingest & validate:** Parse the input task JSON using exact rational arithmetic (`fractions.Fraction` / `decimal.Decimal`) to prevent floating-point drift.
2. **Infer roles & intent:** Compute a scene graph of element roles (background, brand lockup, product hero, primary text, supporting text, button/badge containers, decorative shapes) using multi-signal geometric heuristics (coverage, layer index, fit mode, opacity, content type) without requiring semantic labels.
3. **Select topology:** Map the aspect-ratio delta $\Delta_{\text{AR}} = \log((W_{\text{tgt}}/H_{\text{tgt}}) / (W_{\text{src}}/H_{\text{src}}))$ into candidate layout families:
   - Near-isomorphic (for nearby ratios);
   - Column pivot (for square-to-landscape banners);
   - Horizontal ribbon (for ultra-wide banners like 728×90);
   - Vertical re-stack (for wide-to-tall conversions).
4. **Solve layout & typography:** Place rigid units and independent elements along computed slot bounds. Measure text using Skia against the exact brand fonts with Unicode grapheme-cluster safety (UAX #29 / UAX #14); use the deterministic bounded renderer-measured font probes. Readability is a soft preference without a universal numeric floor; actual glyph bounds and qualitative legibility remain mandatory.
5. **Serialize & quantize:** Quantize mutable coordinates and font sizes once using `round-half-even` into finite integers.
6. **Hard validate:** Recompute rotated AABB bounds, exact integer-lattice image ratios, one common group transform reconstructed after canonical quantization, source-separated non-collision, and actual glyph bounds. Reject invalid candidates immediately.
7. **Rank & commit:** Score surviving candidates using fixed-point quality metrics (readability, balance, alignment, hierarchy, whitespace). Stage and commit the winning design JSON and rendered PNG atomically as one logical pair.

---

## User stories

### Automated grading & container environment
1. **As an automated evaluation harness,** I want the engine to run fully offline with `--network none`, so that it does not attempt network downloads or call external APIs at runtime.
2. **As an automated evaluation harness,** I want the engine to execute within a `linux/amd64` container on an Apple Silicon host under Rosetta 2 translation, using $\le 8$ CPU threads and $\le 8\text{ GB}$ RAM, so that execution never crashes from resource exhaustion or unsupported GPU calls.
3. **As an automated evaluation harness,** I want the engine to output `<task>_output.json` and `<task>_output.png` atomically as a pair upon success, so that partial or corrupted runs are never scored.
4. **As an automated evaluation harness,** I want the engine to exit with status `0` only when every task in the batch produces a valid pair, so that batch test results are unambiguously verifiable.

### Contract, identity & integrity
5. **As a brand marketer,** I want every element from my original design to appear in the resized design with its exact ID, content, and layer order, so that no critical brand element is dropped or replaced.
6. **As a brand marketer,** I want foreground product photography and logos to strictly preserve their source aspect ratio, so that products are never stretched or distorted.
7. **As a brand designer,** I want grouped button components (background shape + text label) to stay locked together, so that labels never drift outside their containers.
8. **As a brand designer,** I want elements that were completely separate in the source design to remain separate without overlapping in the target design, so that visual clarity is maintained.
9. **As a brand designer,** I want elements that intentionally overlapped in the source design (like layered graphics or badges on backgrounds) to be allowed to overlap, so that intentional design layering is respected.
10. **As a compliance officer,** I want fine print, legal disclaimers, and watermark elements to be preserved in the output even when assets are missing on disk, so that legal records are never deleted.

### Adaptive geometry & extreme canvas formats
11. **As a social media manager,** I want a square $1080 \times 1080$ post to adapt into a $1600 \times 400$ wide banner by pivoting vertical stacks into side-by-side columns, so that the layout naturally utilizes the wide horizontal space.
12. **As a web publisher,** I want a tall $1080 \times 1350$ poster to adapt into an extreme $728 \times 90$ leaderboard by trying the contract-permitted compression and topology levers, so that the engine maximizes the chance of a scorable compliant design and uses the typed fail-closed result when no hard-valid candidate exists.
13. **As a visual designer,** I want full-bleed background artwork with `fit="cover"` to cover the target canvas through centered cropping, while foreground elements remain fully bounded inside the canvas.
14. **As a visual designer,** I want decorative translucent background shapes that intentionally bled off the source canvas corners to be allowed to maintain their corner bleed on the target canvas, so that decorative edge styling is preserved.

### Typography, rendering & legibility
15. **As a reader,** I want text to remain readable where feasible, with a preference near $10\text{px}$ unless the source is smaller, so that the engine does not shrink text unnecessarily. Readability is a soft objective; `font_size >= 1` is the structural minimum.
16. **As a reader,** I want text to wrap at valid Unicode word and grapheme boundaries without breaking words in half or dropping characters, so that text reads naturally.
17. **As a brand designer,** I want text with multi-color style runs (like two-tone headlines) to preserve its color and weight overrides at the exact character offsets after reflow, so that typographic styling remains intact.
18. **As an evaluator,** I want rendered text glyphs to stay strictly inside their element bounding boxes, so that text never overflows outside its container or clips canvas borders.

---

## Implementation decisions

### Module breakdown
1. **`chameleon/engine/errors.py`:**
   - Defines `InfeasibleReasonCode` enum: `INVALID_SOURCE`, `INVALID_TARGET`, `MALFORMED_INPUT`, `IMMUTABLE_FIELD_CHANGED`, `CONTAINMENT_VIOLATION`, `IMAGE_RATIO_VIOLATION`, `GROUP_VIOLATION`, `SOURCE_SEPARATION_VIOLATION`, `TEXT_OVERFLOW`, `NO_HARD_VALID_CANDIDATE`, `INCOMPLETE_SEARCH`.
   - Defines `InfeasibleLayoutError(reason_code, message, details)`.
2. **`chameleon/engine/contract.py`:**
   - Standalone semantic validator: `validate_source(source)`, `validate_response(source, target_canvas, response)`.
   - Checks IDs, count, order, types, immutable fields, integer geometry, rotated AABB containment, foreground image cross-product ratio equality, group integrity, and source-separated non-collision.
3. **`chameleon/renderer/converter/wrap.py` & `convert.py`:**
   - Updates text wrapping to measure using effective style-run font faces and span-local letter spacing.
   - Enforces visual line count against `max_lines` (including forced newlines) and element box height.
   - Implements $[start, end)$ code-point indexing for style runs and converts to upstream inclusive indices.
   - Updates `shapes.py` to rasterize declared rectangle/ellipse strokes inside the bounding box.
4. **`chameleon/engine/geometry/`:**
   - `math_util.py`: Converts parser-owned exact integer/decimal values to `Fraction`, provides deliberate `round-half-even` quantization, and never reconstructs lexical values from binary floats.
   - `bounds.py`: Rotated axis-aligned bounding box formula $a = |w\cos\theta| + |h\sin\theta|$, $b = |w\sin\theta| + |h\cos\theta|$, containment predicate, source-bleed predicate.
   - `ratios.py`: Reduced integer lattice point calculation for foreground images.
   - `groups.py`: Uniform macro-scale and translation vector computation.
5. **`chameleon/engine/layout/`:**
   - `roles.py`: deterministic multi-signal role classifier (background, logo, hero, headline, subhead, cta, badge, decoration).
   - `near_isomorphic.py`, `column_pivot.py`, `horizontal_ribbon.py`, and `vertical_restack.py`: four bounded topology generators with renderer-gated candidates.
   - `search.py`: structured macro-candidate orchestrator generating at most 12 source-derived candidates.
   - `ranking.py`: fixed-point lexicographic scorer: `(hard_validity, quality_tuple, topology_order, candidate_index, source_order)`.
6. **`chameleon/engine/artifact.py`, `staging.py` & `main.py`:**
   - Renderer-aware semantic text and PNG artifact gates run before candidate admission or pair publication.
   - JSON ingress uses exact integer/decimal parse hooks and rejects non-finite constants; output serialization emits only contract-approved JSON values.
   - Task isolation stages `<task>_output.json.tmp` and `<task>_output.png.tmp`, validates both, and commits the logical pair with a marker.
   - The runner handles typed exceptions, cleans stale artifacts, and returns exit code `0` only on total batch success.

### Key data structures
```text
TaskEnvelope       = { "source": DesignDocument, "target_canvas": Canvas }
DesignDocument     = { "canvas": Canvas, "elements": list[Element] }
Canvas             = { "width": int, "height": int }
Element            = dict (id, type, x, y, width, height, rotation, opacity, z_index, group_id, ...)
RotatedAABB        = (min_x: Fraction, min_y: Fraction, max_x: Fraction, max_y: Fraction)
SceneGraph         = { "roles": dict[str, Role], "groups": dict[str, list[str]], "source_overlaps": set[tuple] }
LayoutCandidate    = { "topology": str, "variant": str, "elements": list[Element], "report": ValidationReport }
```

---

## Testing decisions

### Test seams (Highest possible seams)
1. **Contract validation seam (`engine.contract`):**  
   Test directly against serialized JSON dictionaries. Verify that valid designs pass and mutated invalid designs (altered IDs, off-canvas coordinates, broken ratios, drifting groups) fail with the exact expected `InfeasibleReasonCode`.
2. **Renderer conversion seam (`renderer.converter`):**  
   Feed synthetic and contract element dictionaries into `convert_chameleon_to_crello` and `wrap_text`. Verify that measured line counts, style-run maps, and glyph bounds strictly match Skia rendering outputs.
3. **Solver entrypoint seam (`engine.resize`):**  
   Call `resize(source, target_canvas)` directly with level 1, 2, and 3 fixtures. Verify that returned designs pass full semantic validation and maintain ratio and grouping invariants.
4. **End-to-end batch runner seam (`engine.main`):**  
   Execute `python -m engine.main` against fixture directories. Verify exit code, file generation, atomic staging, and stale file cleanup.

### Testing rules
- Test only observable external behavior, contracts, and invariants.
- Never write tests that assert incidental internal implementation defaults.
- All test fixtures must be deterministic and runnable completely offline.

---

## Out of scope
- **Generative AI / Pixel synthesis:** Diffusion outpainting, inpainting, seam carving, or pixel regeneration are disqualified and out of scope.
- **Neural model weights:** No LLM, VLM, or neural network weights are included in the Stage 1 engine. The engine is 100% deterministic symbolic Python.
- **Stage 2 Adobe Express add-on UI:** Interactive carousel UI, spatial pinning, and copy rewriting belong to the Stage 2 finale and are out of scope for Stage 1.
- **Dynamic network fetching:** No runtime package installation, font downloading, or API querying.

---

## Further notes
- **Performance target:** Aim for total solver execution below $2.0\text{s}$ per design on CPU under Rosetta 2 x86 translation, subject to qualification evidence. The supplied challenge rules currently have no hard Stage 1 latency disqualifier.
- **Memory target:** Aim for solver resident memory below $500\text{ MB}$ within the container ceiling; record measured usage rather than treating the target as completed evidence.
