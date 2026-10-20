# Issue #21 — PNG artifact conformance run record

- **Run ID:** `run-issue21-png-artifact-conformance-20261020`
- **Branch:** `feat/issue-21-png-artifact-conformance`
- **Base:** `58b697a` (`origin/main` at implementation start)
- **Status:** Implementation complete locally; PR creation/merge remains pending.
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
| Focused artifact suite | `cd chameleon && ../.venv/bin/python -m unittest discover -s tests/artifact -t . -p 'test_*.py' -v` — **34 passed**. |
| Renderer suite | `cd chameleon && ../.venv/bin/python -m unittest discover -s tests/renderer -t . -p 'test_*.py' -v` — **24 passed**. |
| Layout/candidate suite | `cd chameleon && ../.venv/bin/python -m unittest discover -s tests/layout -t . -p 'test_*.py' -v` — **35 passed**. |
| Runner/publication suite | `cd chameleon && ../.venv/bin/python -m unittest discover -s tests/runner -t . -p 'test_*.py' -v` — **72 passed**. |
| Full source-tree suite | `cd chameleon && ../.venv/bin/python -m unittest discover -s tests -t . -p 'test_*.py' -v` — **204 passed**. |
| Repository governance | `python3 scripts/verify_repository.py` — passed; `make verify` — passed. |
| Changed-file syntax | `../.venv/bin/python -m py_compile` over all changed Python files — passed. |
| Whitespace | `git diff --check` — passed. |
| Engine smoke | `cd chameleon && ../.venv/bin/python -m engine.main` — exit **1 expected**. Level 1 and Level 2 produced `SUCCESS` committed pairs; Level 3 produced `INCOMPLETE_SEARCH`; failed task had no pair. Generated smoke artifacts were removed afterward. |
| Docker/buildx | Attempted `docker buildx build --platform linux/amd64 --load -t chameleon-stage1-issue21 .`; could not start because the local daemon was unavailable: `Cannot connect to the Docker daemon at unix:///Users/charliefurlow/.docker/run/docker.sock`. Offline Docker run was not attempted. |

### Acceptance-specific behavior proven

- Readable opaque white PNG for an opaque shape is rejected as `shape_pixels` at publication and candidate seams.
- Readable opaque white PNG for a text design is rejected as `render_pixels` at publication.
- Real adapter output publishes successfully with a commit marker.
- Wrong dimensions, any transparent canvas pixel, unexpected/missing asset warnings, stray exterior ink, transparent image-hole ink, exact image/shape mutations, exact shifts, non-exact text/rotation/transparency/downscale mutations, and source-pixel changes fail closed.
- Real conformance fixtures cover composite layering, missing assets, large-canvas scaling, intentional bleed/overlap, low contrast, zero-area no-op records, RGB decoding, public Level 1/2 outputs, and candidate/publication integration.
- Low contrast remains hard-valid; no contrast score is used by `validate_artifact()`.

## Independent review and dispositions

- **Contract reviewer (`ArtifactContractReview`):** confirmed seam wiring and acceptance coverage. Reported a possible zero-area mismatch because local rasters clamp to one pixel; direct pinned-renderer probes showed zero-area destination draws produce no ink. Added `test_zero_area_records_follow_renderer_noop_semantics`.
- **Security reviewer (`ArtifactSecurityReview`):** identified arbitrary one-pixel exterior ink acceptance for non-exact layers. Fixed by retaining the renderer-edge allowance only for pixels/color matching a pinned reference render; added a regression requiring exterior mutations to fail. Also identified a pre-existing unbounded decoded-image/resource risk. No arbitrary resource policy was added: project instructions keep resource limits unverified and require contract/ADR authority for such a change.
- **Coverage scout (`ArtifactCoverageScout`):** mapped publication, near-isomorphic, and column-pivot reuse; identified missing docs/run evidence, now added. Confirmed no separate ranking/topology seam exists on this branch.

## Not run / blockers

- Native `linux/amd64` Docker build and offline container smoke: blocked by unavailable local Docker daemon; no native qualification claim.
- Mutation testing: not run; no mutation tool is configured in the repository.
- Resource-limit hardening: intentionally not run/implemented; outside Issue #21 and requires a future contract/ADR decision.
- GitHub PR creation, CI, partner review, merge, and issue closure: pending after maintainer review.
