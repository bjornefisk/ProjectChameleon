# Project Chameleon implementation specification

**Status:** Bounded Stage 1 implementation present; public Level 3 remains typed `INCOMPLETE_SEARCH` where the bounded search cannot complete, and native-amd64/parity/held-out/performance qualification remains open.
**Date:** 2026-10-06
**Normative Authority:** [`../PROJECT_CONTRACT.md`](../PROJECT_CONTRACT.md) and [`../DECISIONS/`](../DECISIONS/) (ADR-001 through ADR-009)

**Consolidated architecture:** [`../FINAL_ARCHITECTURE.md`](../FINAL_ARCHITECTURE.md) summarizes the implementation boundary and remains subordinate to the contract and Accepted ADRs.
**Implementation boundary:** This specification distinguishes the implemented bounded modules from the broader target architecture. The contract and Accepted ADRs remain authoritative; module presence is not evidence of complete qualification.

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

## Target architecture

A deterministic, renderer-aware adaptive layout engine separates macro-topology selection from coordinate solving and micro-typography optimization. The bounded implementation covers the contract validator, renderer adapter, exact geometry, bounded topology dispatch, renderer-gated candidate search, fixed-point ranking, and staged publication. Broader qualification and difficult-target coverage remain open:

1. **Ingest & validate:** Parse the input task JSON using exact rational arithmetic (`fractions.Fraction` / `decimal.Decimal`) to prevent floating-point drift.
2. **Infer roles & intent:** Compute a scene graph of element roles (background, brand lockup, product hero, primary text, supporting text, button/badge containers, decorative shapes) using multi-signal geometric heuristics (coverage, layer index, fit mode, opacity, content type) without requiring semantic labels.
3. **Select topology:** Map the aspect-ratio delta $\Delta_{\text{AR}} = \log((W_{\text{tgt}}/H_{\text{tgt}}) / (W_{\text{src}}/H_{\text{src}}))$ into candidate layout families:
   - Near-isomorphic (for nearby ratios);
   - Column pivot (for square-to-landscape banners);
   - Horizontal ribbon (for ultra-wide banners like 728×90);
   - Vertical re-stack (for wide-to-tall conversions).
4. **Solve layout & typography:** Place rigid units and independent elements along computed slot bounds. Measure text using Skia against the exact brand fonts with Unicode grapheme-cluster safety (UAX #29 / UAX #14), searching for the largest measured font size that fits the slot. Prefer the readable size floor near 10px unless the source is smaller; the schema hard minimum remains `1`.
5. **Serialize & quantize:** Quantize mutable coordinates and font sizes once using `round-half-even` into finite integers.
6. **Hard validate:** Recompute rotated AABB bounds, exact integer lattice image ratios, group offsets, non-collision of source-separated pairs, and actual glyph bounds. Reject invalid candidates immediately.
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

The following paths are implemented bounded modules unless explicitly marked as a target or qualification boundary:

1. **`chameleon/engine/errors.py`:**
   - Defines `InfeasibleReasonCode`, including `INCOMPLETE_SEARCH` and `RUNTIME_IO_FAILURE`, plus `InfeasibleLayoutError` and task status values.
2. **`chameleon/engine/contract.py`:**
   - Provides `validate_source(source)`, `validate_target_canvas(target_canvas)`, and `validate_response(source, target_canvas, response)`.
   - Checks identity/order/type preservation, immutable fields, serialized integer geometry, rotated AABB containment, foreground image ratios, group integrity, and source-separated non-collision.
3. **`chameleon/renderer/converter/`:**
   - `wrap.py` implements Unicode-safe wrapping, effective style-span measurement, external `[start, end)` handling, line-count/height overflow rejection, and glyph-bound checks.
   - `convert.py` integrates the adapter and pinned renderer; `shapes.py` rasterizes declared rectangle/ellipse strokes inside the element box; `brand_fonts.py` loads exact packaged faces.
4. **`chameleon/engine/geometry/`:**
   - `math_util.py`: Converts parser-owned exact integer/decimal values to `Fraction` and provides deliberate `round-half-even` quantization.
   - `bounds.py`: Rotated axis-aligned bounding boxes, containment, and source-bleed predicates.
   - `ratios.py`: Reduced integer lattice point calculation for foreground images.
   - `groups.py`: Uniform macro-scale and translation-vector computation.
5. **`chameleon/engine/layout/`:**
   - `roles.py`: Deterministic multi-signal role and relationship inference.
   - Bounded topology behavior is split across `near_isomorphic.py`, `column_pivot.py`, `horizontal_ribbon.py`, and `vertical_restack.py`; there is no `topologies.py` compatibility module.
   - `search.py`: Bounded topology/variant enumeration, renderer/contract gating, and candidate diagnostics (at most 12 candidates).
   - `ranking.py`: Fixed-point lexicographic scoring and deterministic candidate selection.
   - There is no separate `typography.py`; bounded text sizing is implemented in the topology/renderer paths and is gated by the renderer.
6. **`chameleon/engine/resize.py`, `staging.py`, and `main.py`:**
   - `resize(source, target_canvas)` is the public flat-design seam and delegates to bounded search.
   - `main.py` decodes exact numeric JSON, validates task envelopes, handles typed failures including `RUNTIME_IO_FAILURE`, and drives independent batch tasks.
   - `staging.py` validates and publishes JSON/PNG pairs through private task staging and a hash-checked commit marker; failed tasks leave no committed pair.

### Runtime data structures and API boundary

The task envelope and design document remain JSON contract shapes, not public Python data classes. The actual internal search records are `CandidateSpec`, `Candidate`, and `SearchResult` in `chameleon/engine/layout/search.py`; they are not wire fields. The public Python API is `engine.resize.resize(source, target_canvas)`. Task-level loading and publication are runner behavior in `engine.main`/`engine.staging`; there is no `run_task()` API.

### Qualification boundary

The bounded paths are implementation evidence, not complete qualification. Public Level 3 remains typed `INCOMPLETE_SEARCH` where the bounded search does not produce a hard-valid candidate. Native-amd64 qualification, renderer/native parity, held-out evaluation, and performance qualification remain open.

---

## Testing decisions

### Test seams (Highest possible seams)
1. **Contract validation seam (`engine.contract`):**  
   Test directly against serialized JSON dictionaries. Verify that valid designs pass and mutated invalid designs (altered IDs, off-canvas coordinates, broken ratios, drifting groups) fail with the exact expected `InfeasibleReasonCode`.
2. **Renderer conversion seam (`renderer.converter`):**  
   Feed synthetic and contract element dictionaries into `convert_chameleon_to_crello` and `wrap_text`. Verify that measured line counts, style-run maps, and glyph bounds strictly match Skia rendering outputs.
3. **Solver entrypoint seam (`engine.resize`):**  
   Call `resize(source, target_canvas)` directly with level 1 and level 2 fixtures; verify returned designs pass full semantic validation and maintain ratio and grouping invariants. For bounded Level 3 cases that cannot complete, verify the typed `INCOMPLETE_SEARCH` result rather than assuming public Level 3 success.
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
