# 05: Safe Geometry Baseline and Level 1 Near-Isomorphic Solver

**What to build:**  
The first end-to-end working layout solver in `chameleon/engine/resize.py` that replaces the naive uniform-stretch baseline with an isotropic near-isomorphic solver. It cleanly solves Level 1 ($1080 \times 1080 \to 1080 \times 1350$) by classifying full-canvas backgrounds to apply `fit="cover"` cropping, scaling foreground product art and logos isotropically to integer lattice dimensions, scaling text font sizes within bounds, and preserving source topology without distorting images or clipping text.

**Blocked by:**  
- `02: Renderer Text Wrapping and Style-Run Conformance`
- `03: Atomic Batch Staging and Fail-Closed Runner`
- `04: Exact Rational Geometry, Bounds, and Group Transforms`
**Status:**  
implemented with local Level 1 solver, resize-time semantic validation, and warmup render evidence; bounded failures report `INCOMPLETE_SEARCH`; full Gate 1 qualification, later topology families, ranking, and exhausted-search infeasibility remain pending
**Merge status:**
Blocked until Gate 1 exit evidence and native-amd64 qualification are accepted. This bounded implementation remains phase-gated review work and does not advance the project frontier.
The current tree contains a narrow deterministic near-isomorphic candidate path, not the complete ADR-009 four-topology search/ranking implementation. Ticket 05 is complete within its Level 1 scope without changing the public schema, renderer contract, dependency baseline, or runner publication protocol.

**Merge gate:**
The merge gate requires Gate 1 exit evidence and renderer goldens/native-library parity. Commit `0f3d9ab` adds an independent adapter-to-pinned-renderer golden seam, and refreshed native `x86_64` CI run [39183646457](https://github.com/bjornefisk/ProjectChameleon/actions/runs/39183646457) passes it. Cross-runtime/native-library parity, broader renderer goldens, and full native qualification remain unverified; local Buildx evidence is amd64 emulation on the arm64 workstation.

**Observed evidence:**
- `cd chameleon && ../.venv/bin/python -m unittest discover -s tests/layout -t . -p 'test_*.py' -v` — 20 layout tests passed, including the grouped source-separation regression, bounded-search status, renderer-gate, and repeated render-hash checks.
- `make test` — 154 project tests and 47 review tests passed.
- `make verify` — repository governance and implementation wiring passed.
- `make run` — Levels 1 and 2 committed validated JSON/PNG pairs; Level 3 failed closed with `INCOMPLETE_SEARCH: explicit group cannot be represented by one positive integer transform`.
- `make docker-build` — passed with the existing `FromPlatformFlagConstDisallowed` warning; the loaded image reports `linux/amd64` on the arm64 host.
- `make docker-test` — exited nonzero after the offline container run; Levels 1 and 2 succeeded, Level 3 failed closed with `INCOMPLETE_SEARCH`, and failed-task artifacts were not published.
- `./.venv/bin/python scripts/review_pr.py --pr 12 --repo bjornefisk/ProjectChameleon --run-checks --docker --timeout 600` — capsule `pr-12-c394c649674e4796bb540b1d4d4088c2` passed diff-check, verify, tests, and Docker build; its expected aggregate `run`/`docker-test` failures are the Level 3 `INCOMPLETE_SEARCH` with no failed-task artifacts, while Levels 1 and 2 succeeded.
- GitHub Actions run [39165434665](https://github.com/bjornefisk/ProjectChameleon/actions/runs/39165434665) — native `x86_64` CI passed Docker Buildx, image architecture, bounded offline runtime, failed-task cleanup, and offline renderer imports.
- The Level 1 PNG was `1080 × 1350` RGBA and the JSON passed `validate_response()`.
- The new adapter-to-pinned-renderer golden test passed locally and in refreshed native CI, including renderer commit provenance.

- [x] Implement `chameleon/engine/layout/near_isomorphic.py` to generate safe near-isomorphic layouts for moderate aspect-ratio changes.
- [x] Implement background detection: identify full-canvas images with `fit="cover"` and resize them to match the target canvas while preserving cover semantics.
- [x] Scale every non-background foreground image isotropically to an exact positive integer ratio-lattice dimension derived from its source record. Resolve assets dynamically from the task's `asset_id`; never hardcode sample filenames.
- [x] Measure text elements using the renderer font manager and choose the largest measured size that fits, preferring the readable size near $10\text{px}$ unless the source is smaller. Enforce the schema minimum `font_size >= 1`, keep actual glyph bounds inside the text geometry, and reject overflow rather than hiding or rewriting text.
- [x] Quantize all output coordinates and font sizes using `round-half-even` to finite integers once.
- [x] Wire `resize()` in `chameleon/engine/resize.py` to invoke the near-isomorphic solver and pass output through `validate_response()`.
- [x] Verify that `chameleon_sample_level1_warmup.json` passes full semantic validation and renders a clean preview PNG without distorted artwork.
- [x] Add integration tests in `chameleon/tests/layout/test_level1.py`.
