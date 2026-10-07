# 05: Safe Geometry Baseline and Level 1 Near-Isomorphic Solver

**What to build:**  
The first end-to-end working layout solver in `chameleon/engine/resize.py` that replaces the naive uniform-stretch baseline with an isotropic near-isomorphic solver. It cleanly solves Level 1 ($1080 \times 1080 \to 1080 \times 1350$) by classifying full-canvas backgrounds to apply `fit="cover"` cropping, scaling foreground product art and logos isotropically to integer lattice dimensions, scaling text font sizes within bounds, and preserving source topology without distorting images or clipping text.

**Blocked by:**  
- `02: Renderer Text Wrapping and Style-Run Conformance`
- `03: Atomic Batch Staging and Fail-Closed Runner`
- `04: Exact Rational Geometry, Bounds, and Group Transforms`

**Status:**  
ready-for-agent

- [ ] Implement `chameleon/engine/layout/near_isomorphic.py` to generate safe near-isomorphic layouts for moderate aspect-ratio changes.
- [ ] Implement background detection: identify full-canvas images with `fit="cover"` and resize them to match the target canvas while preserving cover semantics.
- [ ] Scale every non-background foreground image isotropically to an exact positive integer ratio-lattice dimension derived from its source record. Resolve assets dynamically from the task's `asset_id`; never hardcode sample filenames.
- [ ] Measure text elements using the renderer font manager and choose the largest measured size that fits, preferring the readable size near $10\text{px}$ unless the source is smaller. Enforce the schema minimum `font_size >= 1`, keep actual glyph bounds inside the text geometry, and reject overflow rather than hiding or rewriting text.
- [ ] Quantize all output coordinates and font sizes using `round-half-even` to finite integers once.
- [ ] Wire `resize()` in `chameleon/engine/resize.py` to invoke the near-isomorphic solver and pass output through `validate_response()`.
- [ ] Verify that `chameleon_sample_level1_warmup.json` passes full semantic validation and renders a clean preview PNG without distorted artwork.
- [ ] Add integration tests in `chameleon/tests/layout/test_level1.py`.
