# Task brief

```text
run_id: run-issue21-png-artifact-conformance-20261020
task_id: task-issue21-png-artifact-conformance
request/source: User-authorized implementation of GitHub issue #21 (audit finding F-05) under umbrella issue #16
owner/role: implementer, with independent reviewer, false-accept hunter, and false-reject hunter subagents
workflow/gate: Implement -> Verify -> Review; PR and merge only after the evidence below exists
created/updated: 2026-10-20
status: implementation complete; PR #51 open; merge pending

Goal / observable outcome:
A readable PNG that is not a conformant render of its design is never published and never accepted as a candidate render. The renderer seam checks expected dimensions, an opaque canvas, the missing-asset warning policy, rendered bounds, and source-pixel provenance. Fully opaque, integral, unrotated, one-to-one image/shape draws are replayed from adapter rasters; non-exact layers are compared with a second render from the pinned adapter after bounds validation. No output pixel is generated, repaired, or replaced. Soft contrast scoring stays out of hard validity.

Relevant authority and ADR sections:
Docs/PROJECT_CONTRACT.md section 6 (renderer contract; images, shapes, and missing assets), section 7 (rotated envelope), section 8 (hard constraints 7 and 8; fail-closed statuses). ADR-002, ADR-003 (hard constraints, fail closed), ADR-006 (typed failures, pair publication, RUNTIME_IO_FAILURE), ADR-008 (renderer and text edge semantics), ADR-009 (renderer-in-loop hard validation). Docs/FINAL_ARCHITECTURE.md sections 3, 6, and 8. Docs/DEPENDENCY_EVIDENCE.md for the pinned cr-renderer commit a17e1fb9a732959dd6c21ae168d5ee09d74bd64f. No ADR, schema, API, dependency, or contract wording is changed; the new behavior implements existing requirements.

Owned files/resources:
chameleon/engine/artifact.py (new); chameleon/engine/staging.py (validate_png and publish_task wiring only); chameleon/engine/layout/near_isomorphic.py (_render_candidate gate only); chameleon/renderer/converter/assets.py and convert.py (behavior-preserving shared definitions: missing_asset_warning, paint_order, render_geometry, element_raster); chameleon/tests/artifact/** and chameleon/tests/fixtures/artifact/** (new); chameleon/tests/runner/test_main.py and test_runner.py (renderer test doubles must now be conformant renders); Docs/PROJECT_CONTRACT.md (section 11 traceability row only); Docs/FINAL_ARCHITECTURE.md; Docs/DEPENDENCY_EVIDENCE.md; Docs/STATUS.md; chameleon/README.md; this brief; .agents/runs/issue-21-png-artifact-conformance.md.
Not owned: solver and search modules, schema, requirements, Dockerfile, CI, and all open sibling PRs (#15, #26, #34-#37, #40, #42-#46, #48).

Acceptance criteria:
1. Artifact-level checks run at the renderer seam for both publication (publish_task) and candidate rendering (near-isomorphic and column-pivot share one gate).
2. Dimensions use the pinned renderer's own scale rule including the 2048 px render limit; an opaque canvas is required; a placeholder is accepted only when the exact missing-asset warning for that element and asset was reported.
3. Rendered bounds: no pixel differs from the canvas background outside the area an element can paint (rotated envelope plus a one-pixel antialiasing margin for non-exact draws, none for exact copies); any tolerated edge pixel must also match the pinned renderer's reference output.
4. Source-pixel preservation: every opaque raster pixel of a one-to-one image or shape copy that no later element can paint over equals the render exactly. Transparent raster pixels leave the canvas untouched. Rotated, translucent, partially transparent, downscaled, and text output is compared with the pinned renderer's reference render, not accepted through a blanket tolerance.
5. Regression fixtures and tests for readable but semantically invalid artifacts, plus conformant renders (fixtures, public samples, rotated, translucent, zero-area, bleed, large canvas) that must never be rejected.
6. A rejected artifact fails the task closed as RUNTIME_IO_FAILURE with no JSON/PNG pair and no staging leftovers.

Never generate, repair, or replace output pixels; never authorize arbitrary exterior ink; keep Stage 1 offline and dependency-free (Pillow plus the already-pinned renderer); keep contrast and other soft scoring out of hard validity; preserve existing fail-closed publication behavior.

Out of scope:
Solver, ranking, search, topology, schema, API, dependency, Docker, CI, and runtime-resource changes; validation of PNG container metadata beyond staging readability; any open sibling PR.

Inputs and prior evidence:
Issue #21 body and the owner's audit comment (PR #47 is evidence-only and leaves this requirement open). Pinned cr_renderer renderer.py (canvas cleared to opaque white, nearest-sampled drawImageRect, rotate about the rectangle centre, text ignores element opacity). Local probes of the pinned renderer recorded in the run record.

Risk/data classification:
Contract/hard-validation risk: a false accept publishes a wrong artifact; a false reject fails a good task. Repository fixtures only; no secrets or personal data.

Required capabilities:
repo.read, repo.search, repo.edit, repo.write, git.inspect, local test execution, GitHub issue/PR access through gh, and subagent dispatch for independent review.

Dependencies/blockers/owners:
Local Docker daemon unavailable, so native-amd64 Docker evidence is pending; no code blocker. Main (origin/main 58b697a) is the base. Stacked PRs on the Ticket 08 branch do not touch these paths.

Verification plan and exact commands:
cd chameleon && ../.venv/bin/python -m unittest discover -s tests -t . -p 'test_*.py'; make verify; cd chameleon && ../.venv/bin/python -m engine.main (exit 1 is expected because the Level 3 sample reports INCOMPLETE_SEARCH); docker buildx build --platform linux/amd64 --load -t chameleon-stage1 chameleon/ and the offline docker run --network none sequence from AGENTS.md where Docker is available. Independent gates: spec reviewer, standards reviewer, false-accept hunter, false-reject hunter. Mutation check of the new tests against the validator.

Rollback/migration:
Revert the focused PR. Prior fail-closed publication behavior and the syntax-only validate_png(path) call remain valid; validate_png gains only optional keyword arguments.

Handoff target:
Repository maintainer and contract owner for review; the run record lists evidence and unrun checks.
```

## Completion contract

The owner updates this brief when scope or acceptance changes through change control. This brief is complete only when the run record lists the executed commands, results, review dispositions, and unrun checks.
