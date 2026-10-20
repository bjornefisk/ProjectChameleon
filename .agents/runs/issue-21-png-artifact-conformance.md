# Issue #21 — PNG artifact conformance run record

- **Run ID:** `run-issue21-png-artifact-conformance-20261020`
- **Branch:** `feat/issue-21-png-artifact-conformance`
**Base:** `ffb6cc3` (`origin/main` at current verification)
- **Status:** Implementation complete; PR #51 carries the implementation; verification evidence is recorded below.
- **Issue:** [#21](https://github.com/bjornefisk/ProjectChameleon/issues/21)

## Goal

Reject readable but semantically wrong PNGs at both candidate-render and task-publication boundaries. Preserve the serialized design and source identity; do not repair, replace, or generate output pixels. Keep contrast/readability outside hard validity.

## Authority used

- `Docs/PROJECT_CONTRACT.md` §§6–8 and §11
- Accepted ADR-001 through ADR-009
- `chameleon/chameleon_design_schema_v0.9.json`
- `Docs/DEPENDENCY_EVIDENCE.md`, pinned `cr-renderer` commit `a17e1fb9a732959dd6c21ae168d5ee09d74bd64f`
- `Docs/FINAL_ARCHITECTURE.md`, `Docs/STATUS.md`
- `skills/chameleon-contract/SKILL.md`, `skills/chameleon-testing/SKILL.md`, `skills/chameleon-review/SKILL.md`
- GitHub issue #21 body and owner comment; merged PR #47 was treated as evidence-only.

## Changed files

### Production

- `chameleon/engine/artifact.py` — new semantic PNG gate.
  - Mirrors the pinned renderer's 2048 render-size rule.
  - Requires a fully opaque decoded canvas.
  - Enforces exact missing-asset warning provenance.
  - Replays fully opaque, integral, unrotated, one-to-one image/shape pixels from adapter rasters.
  - Bounds-checks adapter-derived paint regions, including transparent image holes and renderer-edge handling.
  - Compares any non-exact layer with a second render from the pinned adapter, preventing arbitrary text, rotated, blended, resampled, or antialiased replacement pixels.
  - Raises typed `RUNTIME_IO_FAILURE` without mutating the image.
- `chameleon/engine/staging.py` — passes serialized design and renderer warnings into semantic validation before marker publication.
- `chameleon/engine/layout/near_isomorphic.py` — validates candidate PNGs before candidate return; column-pivot reuses the same helper.
- `chameleon/renderer/converter/assets.py` and `convert.py` — shared deterministic missing-asset warning helper; rendered behavior unchanged.

### Evidence/tests

- `chameleon/tests/artifact/support.py`
- `chameleon/tests/artifact/test_artifact.py`
- `chameleon/tests/artifact/test_publication.py`
- `chameleon/tests/fixtures/artifact/README.md`
- `chameleon/tests/fixtures/artifact/{composite,missing_asset,large_canvas,bleed_overlap,low_contrast_text}.json`
- `chameleon/tests/runner/test_main.py`, `test_runner.py` — renderer doubles now write conformant renders instead of transparent 1×1 placeholders; intentionally invalid PNG tests remain invalid.

### Documentation/process

- `.agents/tasks/issue-21-png-artifact-conformance.md`
- `Docs/PROJECT_CONTRACT.md` §11 traceability row
- `Docs/FINAL_ARCHITECTURE.md` PNG artifact-conformance subsection
- `Docs/STATUS.md` Issue #21 evidence section
- `chameleon/README.md` renderer/publication description
- This run record.

## Verification evidence

All commands below were run in the Issue-21 worktree with `/Users/charliefurlow/Desktop/ProjectChameleon/.venv/bin/python` unless noted.

| Check | Command/result |
| --- | --- |
| Focused artifact suite | `cd chameleon && /Users/charliefurlow/Desktop/ProjectChameleon/.venv/bin/python -m unittest discover -s tests/artifact -t . -p 'test_*.py' -v` — **17 passed**. |
| Renderer suite | `cd chameleon && /Users/charliefurlow/Desktop/ProjectChameleon/.venv/bin/python -m unittest discover -s tests/renderer -t . -p 'test_*.py' -v` — **39 passed**. |
| Layout/candidate suite | `cd chameleon && /Users/charliefurlow/Desktop/ProjectChameleon/.venv/bin/python -m unittest discover -s tests/layout -t . -p 'test_*.py' -v` — **73 passed**. |
| Runner/publication suite | `cd chameleon && /Users/charliefurlow/Desktop/ProjectChameleon/.venv/bin/python -m unittest discover -s tests/runner -t . -p 'test_*.py' -v` — **78 passed** after the full publication suite was rechecked. |
| Full source-tree suite | `cd chameleon && /Users/charliefurlow/Desktop/ProjectChameleon/.venv/bin/python -m unittest discover -s tests -t . -p 'test_*.py'` — **248 passed**. |
| Repository governance | `python3 scripts/verify_repository.py` — passed; `make verify` — passed. |
| Changed-file syntax | `/Users/charliefurlow/Desktop/ProjectChameleon/.venv/bin/python -m py_compile` over all changed Python files — passed. |
| Whitespace | `git diff --check` — passed. |
| Engine smoke | `cd chameleon && /Users/charliefurlow/Desktop/ProjectChameleon/.venv/bin/python -m engine.main` — exit **1 expected**. Level 1 and Level 2 produced `SUCCESS` committed pairs; Level 3 produced `INCOMPLETE_SEARCH`; failed task had no pair. Generated smoke artifacts were removed afterward. |
| Docker/buildx | `docker buildx build --platform linux/amd64 --load -t chameleon-stage1-issue21 .` — passed with the existing `FromPlatformFlagConstDisallowed` warning. `docker run --rm --network none -v "$PWD/input:/app/input" -v "$PWD/output:/app/output" chameleon-stage1-issue21` — exit **1 expected** under amd64-on-arm64 emulation: Level 1 and Level 2 published pairs; Level 3 returned `INCOMPLETE_SEARCH`; generated artifacts were removed afterward. |

### Acceptance-specific behavior proven

- Readable opaque white PNG for an opaque shape is rejected as `shape_pixels` at publication and candidate seams.
- Readable opaque white PNG for a text design is rejected as `render_pixels` at publication.
- Real adapter output publishes successfully with a commit marker.
- Wrong dimensions, any transparent canvas pixel, unexpected/missing asset warnings, stray exterior ink, transparent image-hole ink, exact image/shape mutations, exact shifts, non-exact text/rotation/transparency/downscale mutations, and source-pixel changes fail closed.
- Real conformance fixtures cover composite layering, missing assets, large-canvas scaling, intentional bleed/overlap, low contrast, zero-area no-op records, RGB decoding, public Level 1/2 outputs, and candidate/publication integration.
- Low contrast remains hard-valid; no contrast score is used by `validate_artifact()`.

## Independent review and dispositions

- **ArtifactAudit (scout):** confirmed candidate/publication seam wiring and the shared candidate gate; native-amd64 qualification remains a separate evidence boundary.
- **ArtifactTests (reviewer):** identified that readable-invalid regressions needed explicit fixture-path and decode assertions; added publication, candidate, and direct-validation tests using a valid white PNG derived from `shape.json`.
- **ArtifactSecurity (security reviewer):** identified header-dimension validation ordering and custom-asset font provenance risks. `staging.validate_png()` now rejects wrong dimensions before PNG verification/loading; `_reference_image()` checks dimensions before copying and uses the renderer's sibling font directory when present, with the packaged font fallback retained for isolated asset roots. No resource ceiling was invented; that remains outside this issue and requires contract/ADR authority.

## Not run / boundaries

- Native `linux/amd64` hardware qualification: the local Docker image/run used amd64-on-arm64 emulation; no native-host claim is made.
- Mutation testing: not run; no mutation tool is configured in the repository.
- Resource-limit hardening: intentionally not implemented; outside Issue #21 and requires a future contract/ADR decision.
- PR #51 carries the implementation and its `Verify and test` check passed; GitHub remains the source of truth for merge and issue state.
