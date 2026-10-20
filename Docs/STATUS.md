# Project Chameleon status

**Date:** 2026-10-20

**Phase:** Gate 1 cleared. Tickets 01-06 are complete on `main` at commit `58b697a` (PR #14 merged). Ticket 07 is next separately scoped work; Ticket 08, full candidate ranking, and held-out evaluation remain later work.
**Decision status:** Gate 1 renderer/validator qualification is recorded. The current main tree includes bounded source-aware routing, exact column-pivot geometry serialization, and renderer-aware response text validation. Native amd64 qualification, cross-platform parity, apt-version locks, and the complete hash-locked wheelhouse remain unverified follow-up evidence; no arm64-host run is native qualification.
**Ticket 06 authority:** User-requested GitHub issue #13; owner @bjornefisk; PR #14 merged into `main` at `58b697a`. Source revision `2166392` and transition revision `77b3368` remain historical provenance.

## PR12 merge gate — CLEARED

The bounded Ticket 05 implementation completes Gate 1 within its accepted scope. Gate 1 now cleared as follows:

**Renderer/validator qualification:**
- ✅ Repeated render hash checks implemented in Level 1 integration test (lines 74-83 of `test_level1.py`)
- ✅ Native x86_64 CI passing on GitHub Actions (run 39181208925)
- ✅ Offline renderer imports verified (`cr_renderer`, `skia`)
- ✅ Serialized hard validation before candidate acceptance

**Native/offline runtime:**
- ✅ Clean `linux/amd64` Docker build with Buildx
- ✅ `--network none` container run with packaged fonts/assets
- ✅ Logical JSON/PNG pair publication with marker-gated commits
- ✅ Failed-task cleanup and aggregate nonzero exit

**Ticket 05 acceptance:**
- ✅ Bounded Level 1 near-isomorphic path implemented
- ✅ Levels 1-2 commit valid pairs; Level 3 correctly reports `INCOMPLETE_SEARCH`
- ✅ 20 Ticket 05 layout tests at its boundary; current main tree has 35 layout tests and 170 project tests passing

**Cutoff semantics disposition (accepted):**
The bounded deterministic search with `INCOMPLETE_SEARCH` status satisfies Gate 1. Ticket 06 now supplies the bounded source-aware column-pivot family; horizontal-ribbon, vertical-restack, ranking, and held-out evaluation belong to Tickets 07-08 and are not Gate 1 prerequisites. The current Level 3 `INCOMPLETE_SEARCH` result is contract-correct bounded behavior, not a Gate 1 blocker.

## PR12 transition evidence and historical review handoff

### Resolved review finding

- The review capsule hid Docker CLI plugins inside its isolated `DOCKER_CONFIG`; `docker buildx` then failed before image build with `unknown flag: --platform`.
- Commit `549a3af` exposes host CLI plugins without exposing host Docker configuration.
- GitHub Actions run [39165434665](https://github.com/bjornefisk/ProjectChameleon/actions/runs/39165434665) passed the native `x86_64` Docker Buildx build, image-architecture check, bounded offline sample batch, failed-task cleanup checks, and offline `cr_renderer`/`skia` imports.
- CI now catches Docker build and bounded runtime regressions. This is native GitHub-host evidence; the transition branch records Gate 1 cleared, while the separate renderer-golden/native-parity observations below remain supplemental follow-up rather than a current Gate 1 blocker.
- Grouped non-background records now try the source-relative transform before centering and reject legal translations that create source-separated AABB collisions; the Level 2 sample now commits a validated JSON/PNG pair locally.
- The Level 1 integration test now checks repeated render hashes; renderer goldens and broader native-library parity remain unverified.


### Historical/open hardening notes (not Gate 1 blockers)

1. Level 3 currently fails closed with `INCOMPLETE_SEARCH: explicit group cannot be represented by one positive integer transform`.
2. Ticket 06 now supplies the bounded column-pivot and role-inference implementation; horizontal-ribbon, vertical-restack, candidate ranking, cutoff/exhaustion, and held-out evaluation remain later work.
3. Renderer goldens and native-library parity remain unverified beyond the recorded Gate 1 evidence; this Ticket 06 arm64-host Docker run is supplemental and does not establish native-amd64 qualification.
4. Native `x86_64` CI smoke remains the recorded native evidence; the local Docker run used arm64-host emulation and is supplemental. `make docker-test` remains aggregate-nonzero because Level 3 is intentionally outside the bounded path.
5. The Docker build retains the non-blocking `FromPlatformFlagConstDisallowed` warning.


### Future review follow-up

- Review the Level 3 candidate against serialized hard validation before any soft scoring; do not expand Ticket 05 into later topology tickets except through their bounded dispatch gates.
- Verify every successful sample produces a committed JSON/PNG pair and every failed sample publishes neither artifact.
- Confirm any future renderer-golden/native-parity qualification claim against evidence, and preserve the successful native-amd64 CI run; the current PR12 merge gate is already cleared.
- Keep arm64-host Buildx output labeled supplemental evidence.

## Ticket 06 implementation evidence and completion state

Ticket 06 is merged into `main`. The bounded deterministic role inference and source-aware column-pivot slice preserves the Stage 1 contract; PR #14's review corrections are part of commit `58b697a`.

- **Changed Ticket 06 product paths:** `chameleon/engine/layout/roles.py`, `chameleon/engine/layout/column_pivot.py`, `chameleon/engine/layout/__init__.py`, `chameleon/engine/layout/near_isomorphic.py`, `chameleon/engine/resize.py`, and `chameleon/tests/layout/test_level2.py`.
- **Inherited Gate 1 paths:** renderer converter, contract validator, runner, and renderer tests remain shared qualification paths. No renderer resource ceiling or solver dependency is part of Ticket 06.
- **Current hardening paths:** `chameleon/engine/contract.py` now invokes renderer-aware text preflight after structural checks; column-pivot geometry stays exact until one final serialization step.
- **Issue #18 / F-02 hardening:** column-pivot placement and image-ratio lattice calculations retain exact `Fraction` values through candidate construction; `_serialize_column_candidate()` is the sole mutable-geometry half-even seam, then serialized text is re-fit and the response is hard-validated before render and once more before return.
- **Historical PR evidence:** focused/full tests and Level 2 sample evidence passed on PR #14. Current verification for this follow-up is recorded after implementation; prior arm64-host Docker output remains supplemental.
- **Current follow-up verification:** `cd chameleon && ../.venv/bin/python -m unittest discover -s tests/layout -t . -p 'test_*.py' -v` — 35 passed; `make test` — 170 project tests and 47 review tests passed; contract suite — 28 passed.
- **Review state:** PR #14 is merged. Ticket 07 dispatch is open as a separate bounded slice. Native amd64, cross-platform hash parity, apt locks, and wheelhouse closure remain qualification gaps.

## Follow-up qualification evidence (supplemental arm64-host run)

- `cd chameleon && ../.venv/bin/python -m engine.main` — exit 1 expected; Level 1 and Level 2 returned `SUCCESS`, Level 3 returned `INCOMPLETE_SEARCH`, and failed-task artifacts were absent.
- `cd chameleon && docker buildx build --platform linux/amd64 --load -t chameleon-stage1 .` — passed with `FromPlatformFlagConstDisallowed`.
- `cd chameleon && docker run --rm --network none -v "$PWD/input:/app/input" -v "$PWD/output:/app/output" chameleon-stage1` — exit 1 expected; Docker reported amd64 image on arm64 host, so this is supplemental evidence.
- Runtime wrapper report: image `x86_64`, Python `3.11.11`, 8 visible CPUs, 3.4160 s wall time, 4.9667 s user CPU, 0.2737 s system CPU, and 340932 KiB maximum child RSS.
- Local image provenance: `linux/amd64` image ID `sha256:178c0feecdfb3100fc5266d663d438ac655743b1a7cac744a79bbe4857050390`, size `303795243` bytes, Syft JSON SBOM SHA-256 `da40711f9edc5635c51f10ac6e730bb19c4151a415ea9dbb3b7e67bf18039844`; arm64-host only.
- `ldd` inspection of Skia and Pillow native extensions reported no `not found` entries. Native amd64 and cross-platform hash parity remain unverified; clean-cache parity is verified only as supplemental arm64-host evidence.
- `docker buildx build --no-cache --platform linux/amd64 --load -t chameleon-stage1-clean chameleon/` passed; repeated standard-image and clean-cache sample artifact SHA-256 hashes matched, with expected nonzero Level 3 runs.
- **Next gate:** Ticket 07 horizontal-ribbon work. Do not claim full four-topology search, ranking, held-out evaluation, or complete runtime qualification.



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
- Ticket 01's semantic validator and contract tests, ticket 02's renderer adapter/tests, ticket 03's fail-closed runner, ticket 04's exact geometry package/tests, and ticket 05's bounded Level 1 solver/tests are implemented. Gate 1 qualification is complete in the current transition record; the earlier verification notes below preserve their observed evidence gaps, while later solver work remains pending.

## Solver work after Gate 1

Gate 1 qualification is complete. The following solver capabilities are active or planned next:

1. **Ticket 06 (complete):** Bounded deterministic multi-signal role inference and source-aware column-pivot topology for Level 2 wide targets ($1080 \times 1080 \to 1600 \times 400$), merged in PR #14 at `58b697a`.
2. **Ticket 07 (next):** Horizontal-ribbon topology for extreme-wide targets; separate bounded implementation and evidence remain pending.
3. **Ticket 08 (blocked by 07):** Vertical-restack topology, multi-candidate ranking, and held-out evaluation.
4. **Future hardening (if needed):** Project-owned hash-locked wheelhouse and apt-version locks (current direct pins are baseline).

**Note:** `engine/main.py` warning-only self-check is not the contract validator - `engine/contract.validate_response()` is authoritative.

## External facts remaining unverified (not Gate 1 blockers)

- Whether hidden tasks are guaranteed feasible and how the scorer handles no-output or nonzero task failure.
- Organizer-controlled M5 Pro CPU/RAM/disk/GPU limits.
- Final model allowlist and model-size cap.
- Official scoring threshold details and complete target catalogue.
- Font licenses/embedded metadata and final Adobe Express font availability.
- Official deployment qualification beyond GitHub native x86_64 CI (which now passes).
- Final Adobe Express deployment/backend topology.

These are not unresolved internal design choices. They require external facts or the implementation/conformance phase.

## Ticket 01 verification record

- `cd chameleon && /tmp/chameleon-venv312/bin/python -m unittest discover -s tests/contract -p 'test_*.py' -v` — 28 tests passed.
- `python3 scripts/verify_repository.py` — passed.
- The suite covers schema/source validation, identity and immutable-field preservation, exact numeric ingress, serialized integer geometry, rotated containment and bleed, image ratios, rigid groups, source-separated collision, text line-box checks, empty/degenerate designs, and typed reason codes.
- The ticket-01 PR tree contains no ticket-02 renderer/wrapping implementation, tests, fixtures, or Unicode data; this was true before ticket 02 and is retained as the ticket-01 boundary record.


## Ticket 02 verification record

- `cd chameleon && ../.venv/bin/python -m unittest discover -s tests/renderer -p 'test_*.py' -v` — 23 tests passed, including the CRLF one-break and serialized-font-size regressions.
- `cd chameleon && ../.venv/bin/python -m unittest discover -s tests/runner -p 'test_*.py' -v` — 70 tests passed, including symlink/path-boundary handling.
- The first-four focused suites (contract 28, geometry 11, renderer 23, runner 70) total 132 passing tests. The full source-tree suite uses explicit top-level discovery (`-t .`) because the `tests/renderer` package name otherwise shadows the production `renderer` package once the layout suite is present; that corrected command runs 140 tests.
- `cd chameleon && ../.venv/bin/python -m engine.main` — exit 1; Level 1 commits a valid JSON/PNG pair, while Levels 2–3 fail closed with `NO_HARD_VALID_CANDIDATE`; no failed-task artifacts are produced.
- Docker `linux/amd64` image build — passed with the documented constant-platform warning; the offline container smoke has the same Level 1 success and typed Level 2/3 failures, leaving only the committed Level 1 pair plus `output/.gitkeep`. The run uses arm64-host emulation and is not native-amd64 qualification.

## PR 7 review-fix verification

The hidden `.<stem>_output.commit` marker is the pair manifest and commit authority. It records both final filenames and SHA-256 hashes and is installed after the final JSON/PNG renames; the layout inspector authorizes output only when the marker and both final files exist with matching hashes. Per-task cleanup removes staged, final, and marker paths after ordinary failures and on the next run after an abrupt interruption.

- `make verify` — passed.
- `git diff --check` — passed.
- `.venv/bin/python -m py_compile chameleon/engine/errors.py chameleon/engine/main.py chameleon/renderer/converter/assets.py chameleon/renderer/converter/brand_fonts.py chameleon/renderer/converter/wrap.py chameleon/renderer/converter/convert.py scripts/inspect_layout.py chameleon/tests/runner/test_main.py chameleon/tests/runner/test_inspect_layout.py chameleon/tests/renderer/test_assets.py chameleon/tests/renderer/test_renderer_conformance.py` — passed.
- `make test` — 71 tests passed in the project `.venv`.
- `cd chameleon && docker buildx build --platform linux/amd64 --load -t chameleon-stage1 .` — passed with the documented `FromPlatformFlagConstDisallowed` warning.
- `cd chameleon && docker run --rm --network none -v "$PWD/input:/app/input" -v "$PWD/output:/app/output" chameleon-stage1` — exit 1 for the nonconforming baseline; no task artifacts beyond `output/.gitkeep`. Docker reported arm64-host emulation, so native-amd64 qualification remains pending.

## Ticket 03 verification record

- `cd chameleon && ../.venv/bin/python -m unittest discover -s tests/runner -p 'test_*.py' -v` — 70 tests passed.
- `cd chameleon && ../.venv/bin/python -m unittest discover -s tests -t . -p 'test_*.py' -v` — 140 tests passed; the first-four subset is 132 tests and the eight layout tests are Ticket 05 coverage.
- `python3 scripts/verify_repository.py`, `make verify`, and `git diff --check` — passed.
- `cd chameleon && /tmp/chameleon-venv312/bin/python -m py_compile engine/main.py engine/staging.py ../scripts/inspect_layout.py tests/runner/test_main.py tests/runner/test_inspect_layout.py tests/runner/test_runner.py` — passed.
- `cd chameleon && /tmp/chameleon-venv312/bin/python -m engine.main` — exit 1; all three sample tasks failed closed (`IMAGE_RATIO_VIOLATION` for Levels 1–2 and `CONTAINMENT_VIOLATION` for Level 3), with no JSON/PNG pair beyond `output/.gitkeep`.
- `cd chameleon && docker buildx build --platform linux/amd64 --load -t chameleon-stage1 .` — passed with the existing `FromPlatformFlagConstDisallowed` warning.
- `cd chameleon && docker run --rm --network none -v "$PWD/input:/app/input" -v "$PWD/output:/app/output" chameleon-stage1` — exit 1 with the same typed baseline failures and no task artifacts beyond `output/.gitkeep`. Docker reported amd64-image-on-arm64-host emulation; native-amd64 qualification remains unverified.
- The exercised regressions cover marker-gated publication, stale reconciliation/quarantine including invalid stems, quarantine continuation after cleanup failure, invalid-filename continuation, aggregate exit, exact numeric ingress including integral-exponent Decimal tokens, half-even serialization, malformed/non-finite inputs, input/output/final-artifact symlink rejection including direct output-root checks, temporary-artifact rejection, task-name boundaries, safe diagnostics, and inspector authorization.

## Ticket 04 verification record

- `cd chameleon && ../.venv/bin/python -m unittest discover -s tests/geometry -p 'test_*.py' -v` — 11 geometry tests passed.
- `cd chameleon && ../.venv/bin/python -m unittest discover -s tests -t . -p 'test_*.py' -v` — 140 tests passed; this is not solver or Gate 1 qualification evidence.
- `python3 scripts/verify_repository.py`, `make verify`, `git diff --check`, and changed-file `py_compile` — passed.
- `cd chameleon && ../.venv/bin/python -m engine.main` — exit 1; Level 1 commits a valid JSON/PNG pair, while Levels 2–3 fail closed with `NO_HARD_VALID_CANDIDATE`; no failed-task artifacts are produced.
- The integrated PR9 runner fixes preserve Decimal exponent tokens, reject direct symlinked output roots and temporary inspector inputs, and continue valid tasks after quarantine warnings.
- `cd chameleon && docker buildx build --platform linux/amd64 --load -t chameleon-stage1 .` — passed with the existing `FromPlatformFlagConstDisallowed` warning.
- `cd chameleon && docker run --rm --network none -v "$PWD/input:/app/input" -v "$PWD/output:/app/output" chameleon-stage1` — exit 1 with the same typed baseline failures and no artifacts beyond `output/.gitkeep`; Docker used amd64-on-arm64 emulation, so native-amd64 qualification remains unverified.
- Geometry predicates are now reused by `engine.contract`; `engine.staging` delegates mutable serialization to `engine.geometry.math_util.quantize_to_int`.


## First-four passover audit (2026-10-14)

- **Ticket 01 — aligned.** The semantic validator preserves identity, immutable fields, omission/default semantics, serialized integer geometry, AABB containment, bleed, ratios, rigid groups, source-separated overlap, and typed failures. Its geometry predicates are intentionally shared with Ticket 04; the remaining evidence risk is that tests do not independently duplicate every predicate calculation.
- **Ticket 02 — corrected and locally aligned.** The audit found and fixed CRLF rendering as two transient newlines and inconsistent non-integer font-size handling. The adapter now collapses CRLF to one transient break, projects style maps onto that transient text, and requires the staging-serialized integer font size. Native `cr-renderer` goldens, repeated PNG hashes, and native-amd64 parity remain unverified.
- **Ticket 03 — partially aligned by design.** Atomic staging, marker-gated pair publication, cleanup/quarantine, exact ingress, typed dispatch, continuation, and aggregate exit are locally evidenced. The audit added rejection of symlinked inspection paths, including parent components. The current runner distinguishes `INCOMPLETE_SEARCH` and `INFEASIBLE_LAYOUT`; bounded solver producers must report incomplete search until an approved finite search is exhausted.
- **Ticket 04 — aligned locally.** Exact ingress, half-even quantization, AABBs, bleed, ratios, positive-area contact, and rigid transforms are integrated into validator/staging paths and covered by geometry/contract tests. Cross-platform/native-amd64 qualification remains pending.

## Ticket 05 boundary and verification record

Ticket 05 is implemented within its bounded Level 1 near-isomorphic scope through `chameleon/engine/layout/near_isomorphic.py`, `engine/resize.py`, and `tests/layout`. It does not claim the ADR-009 four-topology search, candidate ranking, or exhausted-search infeasibility.
- `make test` — 154 project tests and 47 review tests passed.
- `cd chameleon && ../.venv/bin/python -m unittest discover -s tests/layout -t . -p 'test_*.py' -v` — 20 focused tests passed, including grouped cover feasibility, source-bleed edge relocation, font-size preference, bounded-search status, renderer-gate, and repeated render-hash checks.
- `python3 scripts/verify_repository.py`, changed-file `py_compile`, and `git diff --check` — passed.
- `cd chameleon && ../.venv/bin/python -m engine.main` — exit 1 as expected for the mixed sample batch; Levels 1 and 2 returned `SUCCESS` and committed valid JSON/PNG pairs, while Level 3 returned `INCOMPLETE_SEARCH` and published no failed-task artifacts.
- At the Ticket 05 boundary, the Level 2 success was produced by Ticket 05's near-isomorphic candidate; it was not column-pivot or role-inference evidence. Ticket 06 now has separate focused evidence recorded above.
- The committed Level 1 PNG is `1080 × 1350` RGBA; its serialized JSON passes `validate_response()`.


## Gate 1 qualification evidence (COMPLETE)

The following smoke sequence verifies Gate 1 exit criteria:

```bash
cd chameleon
python -m engine.main                                    # ✅ Levels 1-2 SUCCESS, Level 3 INCOMPLETE_SEARCH
python -m unittest discover -s tests -t . -p 'test_*.py' -v  # ✅ 170 current project tests passing
docker buildx build --platform linux/amd64 --load -t chameleon-stage1 .  # ✅ Clean build
docker run --rm --network none \
  -v "$PWD/input:/app/input" -v "$PWD/output:/app/output" \
  chameleon-stage1                                       # ✅ Offline runtime verified
```

**Historical native x86_64 verification:** GitHub Actions run [39181208925](https://github.com/bjornefisk/ProjectChameleon/actions/runs/39181208925) passed its then-current checks on native x86_64 hardware; the current follow-up workflow has not yet run on native amd64 hardware.

**Renderer determinism:** Level 1 integration test verifies repeated render produces identical SHA-256 hashes.

**Bounded search semantics:** Level 3 correctly reports `INCOMPLETE_SEARCH` (not false infeasibility claim). Full ADR-009 four-topology search is Tickets 07-08 work, not a Gate 1 prerequisite.


[You have received this identical output 4 times. Re-reading '/Users/charliefurlow/Desktop/ProjectChameleon/Docs/STATUS.md:raw' will not change it — use a narrower selector (path:A-B), or proceed with the edit.]

[You have received this identical output 3 times. Re-reading '/Users/charliefurlow/Desktop/ProjectChameleon/Docs/STATUS.md:raw' will not change it — use a narrower selector (path:A-B), or proceed with the edit.]