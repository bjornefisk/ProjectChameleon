# 05: Safe Geometry Baseline and Level 1 Near-Isomorphic Solver

**What to build:**  
The first end-to-end working layout solver in `chameleon/engine/resize.py` that replaces the naive uniform-stretch baseline with an isotropic near-isomorphic solver. It cleanly solves Level 1 ($1080 \times 1080 \to 1080 \times 1350$) by classifying full-canvas backgrounds to apply `fit="cover"` cropping, scaling foreground product art and logos isotropically to integer lattice dimensions, scaling text font sizes within bounds, and preserving source topology without distorting images or clipping text.

**Blocked by:**  
- `02: Renderer Text Wrapping and Style-Run Conformance`
- `03: Atomic Batch Staging and Fail-Closed Runner`
**Status:**  
implemented with local Level 1 solver, resize-time semantic validation, and warmup render evidence; full Gate 1 qualification, later topology families, ranking, and cutoff semantics remain pending

The current tree contains a narrow deterministic near-isomorphic candidate path, not the complete ADR-009 four-topology search/ranking implementation. Ticket 05 is complete within its Level 1 scope without changing the public schema, renderer contract, dependency baseline, or runner publication protocol.

**Observed evidence:**
- `cd chameleon && ../.venv/bin/python -m unittest discover -s tests/layout -t . -p 'test_*.py' -v` — 9 focused tests passed.
- `make test` — 139 tests passed in the current source tree.
- `cd chameleon && ../.venv/bin/python -m engine.main` — Level 1 committed a JSON/PNG pair; Level 2 and Level 3 failed closed with `NO_HARD_VALID_CANDIDATE`, leaving no failed-task artifacts.
- The Level 1 PNG is `1080 × 1350` RGBA and the JSON passes `validate_response()`.

- [x] Implement `chameleon/engine/layout/near_isomorphic.py` to generate safe near-isomorphic layouts for moderate aspect-ratio changes.
- [x] Implement background detection: identify full-canvas images with `fit="cover"` and resize them to match the target canvas while preserving cover semantics.
- [x] Scale every non-background foreground image isotropically to an exact positive integer ratio-lattice dimension derived from its source record. Resolve assets dynamically from the task's `asset_id`; never hardcode sample filenames.
- [x] Measure text elements using the renderer font manager and choose the largest measured size that fits, preferring the readable size near $10\text{px}$ unless the source is smaller. Enforce the schema minimum `font_size >= 1`, keep actual glyph bounds inside the text geometry, and reject overflow rather than hiding or rewriting text.
- [x] Quantize all output coordinates and font sizes using `round-half-even` to finite integers once.
- [x] Wire `resize()` in `chameleon/engine/resize.py` to invoke the near-isomorphic solver and pass output through `validate_response()`.
- [x] Verify that `chameleon_sample_level1_warmup.json` passes full semantic validation and renders a clean preview PNG without distorted artwork.
- [x] Add integration tests in `chameleon/tests/layout/test_level1.py`.
