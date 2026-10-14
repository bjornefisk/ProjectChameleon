# Project Chameleon status

**Date:** 2026-10-14

**Phase:** Tickets 01, 02, 03, and 04 implementation complete; Gate 1 qualification remains pending.
**Decision status:** Ticket 01 semantic validation, ticket 02 renderer conformance, ticket 03 runner behavior, and ticket 04 exact geometry have local evidence. Deterministic cutoff/search semantics, solver, and full runtime qualification remain pending.

## Ground truth now recorded

- `Docs/PROJECT_CONTRACT.md` is the Stage 1 behavioral authority.
- ADR-001 establishes source precedence.
- ADR-002 ratifies the v0.9 design wire shape and pins the project renderer contract.
- ADR-003 separates hard constraints from soft objectives and chooses fail-closed infeasibility handling.
- ADR-004 fixes the initial offline `linux/amd64` runtime target and dependency baseline.
- ADR-005 separates autonomous Stage 1 from finale-only Adobe Express interactions.
- `Docs/DEPENDENCY_EVIDENCE.md` records official-source verification, detected versions, pins, risks, and conformance tests.
- ADR-006 ratifies typed failure statuses, logical JSON/PNG pair publication, and conservative cutoff semantics without adding a failure wire envelope.
- ADR-007 ratifies exact numeric ingress, one round-half-even serialization, rigid group transforms, contract AABBs, and positive-area overlap.
- ADR-008 ratifies Unicode-safe line generation, code-point `[start,end)` style ranges, effective span metrics, overflow rejection, and in-box rectangle/ellipse strokes.
- ADR-009 ratifies bounded deterministic four-topology search, renderer-in-loop hard validation, fixed-point ranking, and no initial model/OR-Tools dependency.
- `Docs/FINAL_ARCHITECTURE.md` consolidates the ratified Stage 1 architecture and finale boundary for implementation; it is subordinate to the contract and Accepted ADRs.

## Resolved contract decisions

| Area | Ratified decision | Evidence |
| --- | --- | --- |
| Authority | Contract/Accepted ADRs > schema > pinned renderer > challenge/rules > fixtures > other proposals > starter code | ADR-001, contract §2 |
| API | `resize(source, target_canvas)` returns a flat design; batch metadata is outside it | ADR-002, contract §3 |
| Mutable fields | Target canvas; element `x/y/width/height`; text `font_size`; all serialized as finite integers | ADR-002, contract §5 |
| Fixed fields | Identity/order/type/rotation/z-order/group/material/text/style/fit/shape fields remain unchanged | ADR-002, contract §5 |
| Text | Adapter-owned deterministic line maps; upstream renderer is explicit-line only; `[start,end)` style runs | ADR-002, contract §6 |
| Images | Exact source box ratio for foreground images, including `fit=fill`; full-canvas `fit=cover` is background-only exception | ADR-003, contract §7 |
| Decoration bleed | Only an already-clipped, translucent, ungrouped shape may keep same-side bleed | ADR-003, contract §7 |
| Empty designs | Valid; output is target canvas plus empty list | ADR-003, schema |
| Infeasible target & fallback | Graceful spatial compression (font floors, isotropic scaling, ribboning) maximizes feasibility on extreme canvases; typed `InfeasibleLayoutError` reserved for mathematically impossible geometry; no misleading JSON/PNG | ADR-003, ADR-006, contract §8 |
| Failure protocol | `SUCCESS`, `MALFORMED_INPUT`, `INFEASIBLE_LAYOUT`, `INCOMPLETE_SEARCH`, and `RUNTIME_IO_FAILURE`; no failed-task artifacts; JSON/PNG committed as a logical pair; nonzero aggregate if any task fails; cutoff is never proof of infeasibility | ADR-006, contract §8 |
| Numeric/geometry | Exact rational ingress; one round-half-even serialization; reduced image-ratio lattice; uniform explicit-group scale plus translation; rotated AABB hard predicate; boundary contact allowed; deterministic background and same-side bleed rules | ADR-007, contract §§5, 7 |
| Typography/renderer | UAX #29 clusters intersected with UAX #14 opportunities; latest-fitting greedy breaks; code-point `[start,end)` runs; effective span metrics; explicit/empty-line accounting; overflow rejection; in-box strokes; no public line map | ADR-008, contract §6 |
| Initial search | Deterministic multi-signal inference; four topology families; at most three source-derived variants per family; renderer-in-loop hard validation; fixed-point ranking; 0 MB neural model footprint; < 2.0s latency target | ADR-009, contract §9 |
| Runtime & hardware | Pinned Python 3.11 `linux/amd64`, runtime `--network none`, CPU-only execution (<= 8 cores, <= 8 GB RAM, Rosetta 2 emulation compatible), dynamic asset/font loading, no current model/OR-Tools requirement | ADR-004, ADR-009 |
| Stage split & finale | Stage 1 is autonomous offline engine; pinning, shedding, copy/font changes, and reduced previews are finale-only; finale add-on communicates with engine via local HTTP service | ADR-005, contract §10 |
## Ratified source-of-truth artifacts

These are contract artifacts, not solver or renderer implementation:

- `chameleon/requirements.txt` pins the initial external compatibility baseline.
- `chameleon/Dockerfile` records the intended Python 3.11.11 Bookworm amd64 image and offline environment defaults.
- `chameleon/chameleon_design_schema_v0.9.json` is no longer provisional, accepts empty designs, and records structural ranges/defaults.
- Contract fixtures live under `chameleon/tests/fixtures/contract/`.
- The Level 2 public sample's style range is corrected to valid end-exclusive `[6, 15)` semantics; this is fixture/source-data correction, not solver implementation.
- Ticket 01's semantic validator and contract tests, ticket 02's renderer adapter/tests, ticket 03's fail-closed runner, and ticket 04's exact geometry package/tests are implemented; the renderer adapter, runner, solver, and full Gate 1 qualification remain pending only where the verification records below identify evidence gaps.

## Known implementation gaps before the solver

These are intentionally visible; none is silently promoted to contract behavior:

1. `engine/resize.py` is the documented uniform-stretch baseline and violates image-ratio, group, overlap, rotation, and typography rules.
2. `engine/main.py` has a warning-only self-check that checks unrotated rectangles and ID sets; it is not the contract validator.
3. Renderer goldens and native-amd64 qualification remain; ticket 02 closes style-run end handling, Unicode-safe wrapping, letter-spacing/style-width measurement, mandatory/non-space line-map handling, positioned glyph-bound rejection, explicit line/max-lines/height enforcement, and rectangle/ellipse stroke rasterization.
4. The runner's typed-status, private staging, marker-gated pair publication, stale-path quarantine, aggregate exit, exact target validation, exact numeric ingress, and half-even serialization paths are implemented and focused-tested; deterministic cutoff semantics and full runtime qualification remain pending.
5. The deterministic role-inference, four-topology candidate search, renderer-in-loop ranking, and held-out evaluation path have not been implemented.
6. The Docker build has no project-owned hash-locked wheelhouse or apt-version lock; the direct compatibility pins are an initial baseline.

## External blockers that remain explicitly unverified

- Whether hidden tasks are guaranteed feasible and how the scorer handles no-output or nonzero task failure.
- Organizer-controlled M5 Pro CPU/RAM/disk/GPU limits.
- Final model allowlist and model-size cap.
- Official scoring threshold details and complete target catalogue.
- Font licenses/embedded metadata and final Adobe Express font availability.
- Clean native-amd64 build, PNG determinism, native-library closure, and Apple Silicon Buildx parity.
- Final Adobe Express deployment/backend topology.

These are not unresolved internal design choices. They require external facts or the implementation/conformance phase.

## Ticket 01 verification record

- `cd chameleon && /tmp/chameleon-venv312/bin/python -m unittest discover -s tests/contract -p 'test_*.py' -v` — 28 tests passed.
- `python3 scripts/verify_repository.py` — passed.
- The suite covers schema/source validation, identity and immutable-field preservation, exact numeric ingress, serialized integer geometry, rotated containment and bleed, image ratios, rigid groups, source-separated collision, text line-box checks, empty/degenerate designs, and typed reason codes.
- The ticket-01 PR tree contains no ticket-02 renderer/wrapping implementation, tests, fixtures, or Unicode data; this was true before ticket 02 and is retained as the ticket-01 boundary record.


## Ticket 02 verification record

- `cd chameleon && ../.venv/bin/python -m unittest discover -s tests/renderer -p 'test_*.py' -v` — 22 tests passed, including the regional-indicator flag-pair wrapping regression, exact-font, and asset-containment regressions.
- `cd chameleon && ../.venv/bin/python -m unittest discover -s tests/runner -p 'test_*.py' -v` — 21 tests passed, including accepted status mapping, setup-failure handling, warning propagation, interruption cleanup, and commit-marker filtering.
- `cd chameleon && ../.venv/bin/python -m unittest discover -s tests -p 'test_*.py' -v` — 71 tests passed.
- `cd chameleon && ../.venv/bin/python -m engine.main` — exit 1 as required for the nonconforming baseline; all three sample tasks logged `MALFORMED_INPUT (MALFORMED_INPUT): serialized response x must be a finite integer`, and no task artifacts were produced beyond `output/.gitkeep`.
- Docker `linux/amd64` image build — passed with the documented constant-platform warning; offline container smoke exited 1 for the same nonconforming baseline and left only `output/.gitkeep`. The run used arm64-host emulation and is not native-amd64 qualification.

## PR 7 review-fix verification

The hidden `.<stem>_output.commit` marker is the pair manifest and commit authority. It records both final filenames and SHA-256 hashes and is installed after the final JSON/PNG renames; the layout inspector authorizes output only when the marker and both final files exist with matching hashes. Per-task cleanup removes staged, final, and marker paths after ordinary failures and on the next run after an abrupt interruption.

- `make verify` — passed.
- `git diff --check` — passed.
- `.venv/bin/python -m py_compile chameleon/engine/errors.py chameleon/engine/main.py chameleon/renderer/converter/assets.py chameleon/renderer/converter/brand_fonts.py chameleon/renderer/converter/wrap.py chameleon/renderer/converter/convert.py scripts/inspect_layout.py chameleon/tests/runner/test_main.py chameleon/tests/runner/test_inspect_layout.py chameleon/tests/renderer/test_assets.py chameleon/tests/renderer/test_renderer_conformance.py` — passed.
- `make test` — 71 tests passed in the project `.venv`.
- `cd chameleon && docker buildx build --platform linux/amd64 --load -t chameleon-stage1 .` — passed with the documented `FromPlatformFlagConstDisallowed` warning.
- `cd chameleon && docker run --rm --network none -v "$PWD/input:/app/input" -v "$PWD/output:/app/output" chameleon-stage1` — exit 1 for the nonconforming baseline; no task artifacts beyond `output/.gitkeep`. Docker reported arm64-host emulation, so native-amd64 qualification remains pending.

## Ticket 03 verification record

- `cd chameleon && ../.venv/bin/python -m unittest discover -s tests/runner -p 'test_*.py' -v` — 63 tests passed.
- `cd chameleon && ../.venv/bin/python -m unittest discover -s tests -p 'test_*.py' -v` — 113 tests passed.
- `python3 scripts/verify_repository.py`, `make verify`, and `git diff --check` — passed.
- `cd chameleon && ../.venv/bin/python -m py_compile engine/main.py engine/staging.py ../scripts/inspect_layout.py tests/runner/test_main.py tests/runner/test_runner.py tests/runner/test_inspect_layout.py` — passed.
- `cd chameleon && ../.venv/bin/python -m engine.main` — exit 1; all three sample tasks failed closed (`IMAGE_RATIO_VIOLATION` for Levels 1–2 and `CONTAINMENT_VIOLATION` for Level 3), with no JSON/PNG pair beyond `output/.gitkeep`.
- `cd chameleon && docker buildx build --platform linux/amd64 --load -t chameleon-stage1 .` — passed with the existing `FromPlatformFlagConstDisallowed` warning.
- `cd chameleon && docker run --rm --network none -v "$PWD/input:/app/input" -v "$PWD/output:/app/output" chameleon-stage1` — exit 1 with the same typed baseline failures and no task artifacts beyond `output/.gitkeep`. Docker reported amd64-image-on-arm64-host emulation; native-amd64 qualification remains unverified.
- The exercised regressions cover marker-gated publication, stale reconciliation/quarantine including invalid stems, invalid-filename continuation, aggregate exit, exact numeric ingress and half-even serialization, malformed/non-finite inputs, input/output/final-artifact symlink rejection, task-name boundaries, safe diagnostics, and inspector authorization.

## Ticket 04 verification record

- `cd chameleon && ../.venv/bin/python -m unittest discover -s tests/geometry -p 'test_*.py' -v` — 11 geometry tests passed.
- `cd chameleon && ../.venv/bin/python -m unittest discover -s tests -p 'test_*.py' -v` — 125 tests passed, including contract, runner, and geometry coverage through the staging/validator integration.
- `python3 scripts/verify_repository.py`, `make verify`, `git diff --check`, and changed-file `py_compile` — passed.
- `cd chameleon && python -m engine.main` — the system interpreter failed before application startup because `jsonschema` is not installed; the project `.venv` equivalent was used for the observable runner smoke.
- `cd chameleon && ../.venv/bin/python -m engine.main` — exit 1 as required for the nonconforming baseline; Level 1/2 failed with `IMAGE_RATIO_VIOLATION`, Level 3 with `CONTAINMENT_VIOLATION`, and no artifacts were produced beyond `output/.gitkeep`.
- `cd chameleon && docker buildx build --platform linux/amd64 --load -t chameleon-stage1 .` — passed with the existing `FromPlatformFlagConstDisallowed` warning.
- `cd chameleon && docker run --rm --network none -v "$PWD/input:/app/input" -v "$PWD/output:/app/output" chameleon-stage1` — exit 1 with the same typed baseline failures and no artifacts beyond `output/.gitkeep`; Docker used amd64-on-arm64 emulation, so native-amd64 qualification remains unverified.
- Geometry predicates are now reused by `engine.contract`; `engine.staging` delegates mutable serialization to `engine.geometry.math_util.quantize_to_int`.


## Remaining Gate 1 qualification

The following sequence is required for later Gate 1 qualification and is not complete ticket-01 through ticket-04 evidence:

```bash
cd chameleon
python -m engine.main
python -m unittest discover -s tests -p 'test_*.py' -v
docker buildx build --platform linux/amd64 --load -t chameleon-stage1 .
docker run --rm --network none \
  -v "$PWD/input:/app/input" -v "$PWD/output:/app/output" \
  chameleon-stage1
```

The warning-only baseline self-check remains non-authoritative; accepted cutoff/search-status integration, renderer goldens/native-library parity, clean native amd64 run, and solver remain outside this PR.
