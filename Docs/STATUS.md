# Project Chameleon status

**Date:** 2026-10-21

**Phase:** Gate 1 is cleared. Tickets 01-08 are implemented within their accepted bounded scopes. Issue #61's PDF-grounded fix now produces the public 1080×1350 → 728×90 sample as one hard-valid JSON/PNG pair in repeated local runs. The issue branch is awaiting independent maintainer review and native-amd64 CI; no official organizer score, cross-platform parity, or release qualification is claimed.
**Decision status:** The current issue branch preserves bounded four-topology search, at most twelve source-derived candidates, renderer-gated hard validation, fixed-point ranking, deterministic output, and typed fail-closed behavior. Accepted ADR-010 through ADR-012 reconcile only quantized common group transforms, the absence of a numeric readability floor, and the renderer-measured transient glyph inset against the source challenge PDF. Local success does not establish organizer qualification; prior native-amd64 evidence applies to an earlier revision.
**Ticket 06 authority:** User-requested GitHub issue #13; owner @bjornefisk; partner reviewer @gabegaines24. Implementation branch `feat/ticket-06-column-pivot-level2`, merged PR #14, now included in the current issue branch's `main` base `c5b1159`.

## Issue #61 public Level 3 acceptance

The public fixture now returns `SUCCESS` and publishes exactly one JSON/PNG pair. The integration regression invokes the real `engine.main.main()` twice in isolated input/output directories, validates the serialized response through the hard contract, verifies PNG decoding and 728×90 dimensions, asserts all 17 source records/IDs and integer mutable fields are preserved, and checks both artifact hashes are identical across runs. A separate runner regression retains genuine `INCOMPLETE_SEARCH`, a nonzero exit, and no artifact pair.

Accepted ADR-010 through ADR-012 are based on the original challenge PDF §§2.3, 2.5, and 7.2, supplied by the issue owner. They preserve same-design content and rendered elements while replacing project-authored constraints not present in the PDF: rigid groups are checked against one reconstructed transform after canonical half-even quantization; readability has no universal numeric font-size floor; and actual glyphs receive only a minimal transient vertical inset inside unchanged declared text bounds. Renderer bounds and qualitative legibility remain mandatory. No official score or organizer acceptance is inferred.

- Public-path test: `cd chameleon && /Users/charliefurlow/Desktop/ProjectChameleon/.venv/bin/python -m unittest discover -s tests/layout -p 'test_level3.py' -v` — 10 passed, including repeated runner publication and the grouped-text refinement cutoff.
- Full repository `make test PYTHON=/Users/charliefurlow/Desktop/ProjectChameleon/.venv/bin/python` — 275 repository tests, 47 PR-review script tests, and 3 runtime-qualification script tests passed (325 total). A preliminary run exposed missing successful-search rejection diagnostics; those were restored, and the final full run passed.
- `make verify` and `make preflight` — passed.
- Full engine smoke — actual `engine.main.main()` ran all three checked-in samples against isolated temporary output; exit 0, all three statuses `SUCCESS`, and all expected JSON/PNG/commit-marker files were published.
- Docker smoke — `docker buildx build --platform linux/amd64 --load -t chameleon-issue61 .` passed with the repository's `FromPlatformFlagConstDisallowed` warning. The offline container run produced all three sample pairs with `SUCCESS`; it ran as linux/amd64 on a Darwin arm64 host and is supplemental emulation, not native-amd64 evidence.
- Direct renderer observation: `/tmp/issue61-public-final.png`, 728×90, 38,159 bytes, SHA-256 `5761d119b7011b7ce2e7a2ca2ac8b72753fb710ca6e27acea549f5bd02e72572`. All 17 source records are retained. The missing `solstice_holiday_badge_2025.png` remains a warning-only placeholder and the source asset ID remains unchanged.
- Qualitative visual evidence, separate from hard validity: at native pixel scale, the banner's text remains visible; headline, subhead, and legal copy are compact at 8px, with the legal copy the smallest. This is local inspection only, not organizer legibility/scoring evidence.
- Bounded work: font probes are capped at 74; grouped-text scale refinement is capped at 74 iterations per invocation and reports aggregate invocation/iteration counts. Hitting the refinement cutoff propagates `INCOMPLETE_SEARCH` with `search_exhausted=false`, never infeasibility.
- PR state: implementation is not merged. Maintainer review and this branch's native-amd64 CI remain pending; keep issue #61 open until acceptance is complete.

## Issue #16 F-01..F-09 disposition matrix

This matrix is an audit index, not a new contract or qualification claim. `PROJECT_CONTRACT.md` and Accepted ADRs remain authoritative. Local evidence does not establish organizer-controlled qualification.

| Finding | Disposition | Exact evidence / boundary |
| --- | --- | --- |
| **F-01** four-topology search/ranking | **Implemented bounded slice; broad qualification deferred.** | `chameleon/engine/layout/search.py`, `ranking.py`, `candidate.py`, `near_isomorphic.py`, `column_pivot.py`, `horizontal_ribbon.py`, `vertical_restack.py`, and `resize.py`; `chameleon/tests/layout/test_issue23_search_evidence.py`, `test_search_ranking.py`, `test_heldout_evaluation.py`. At most 12 source-derived candidates are enumerated and hard-validated before ranking. The checked-in evaluator is not organizer-held-out qualification; broader held-out evaluation remains deferred. |
| **F-02** intermediate column-pivot rounding | **Fixed and locally evidenced.** | `chameleon/engine/layout/column_pivot.py` retains exact geometry through construction and applies one final half-even candidate serialization; staging reserializes only already-integral published values; `chameleon/tests/geometry/test_issue23_rounding.py`, `chameleon/tests/layout/test_level2.py`, and `chameleon/tests/layout/test_search_ranking.py` cover the boundary. Native-amd64 parity remains unverified. |
| **F-03** exhaustion-aware failure mapping | **Fixed for bounded producers and runner; public Level 3 now succeeds locally.** | `chameleon/engine/layout/{near_isomorphic,column_pivot,horizontal_ribbon,vertical_restack,search}.py`, `chameleon/engine/resize.py`, `chameleon/engine/main.py`; tests cover typed cutoff, real incomplete-search no-publication, and the public hard-valid pair. `INCOMPLETE_SEARCH` is retained for cutoff/incomplete attempts; `INFEASIBLE_LAYOUT` requires exhausted finite search. |
| **F-04** renderer-aware text validation | **Implemented at the authoritative hard-validation seam; platform qualification boundary remains.** | `chameleon/engine/contract.py::validate_response()` invokes the pinned converter text preflight with effective face/style-run metrics, Unicode-safe wrapping and forced-line accounting, spacing/alignment, max-lines/height, unbreakable-segment, and positioned-glyph checks. `chameleon/tests/contract/test_renderer_contract.py` calls the authoritative seam directly; layout callers pass their renderer context. Native renderer-golden/platform parity and final-font qualification remain unverified. |
| **F-05** PNG/artifact conformance | **Implemented local hard gate; external qualification absent.** | `chameleon/engine/artifact.py`, `chameleon/engine/staging.py`, `chameleon/tests/artifact/`, `chameleon/tests/runner/`, `chameleon/tests/fixtures/artifact/`, and renderer hash fixtures cover dimensions, opacity, bounds, exact image/shape source-pixel replay, pinned-adapter reference equality, missing-asset warning provenance, and fail-closed publication. Hash/provenance and expected dimensions are local pinned-runtime evidence; soft scores, warnings, or non-empty PNGs never substitute for hard validity. |
| **F-06** runtime/resource/reproducibility qualification | **Native-amd64 evidence recorded; full organizer qualification remains open.** | `Docs/DEPENDENCY_EVIDENCE.md` and `Docs/IMPLEMENTATION/tickets/08-qualification-evidence.md` record GitHub Actions run `39481028806` on commit `7f39a3e`: pinned `linux/amd64` image, non-empty SPDX SBOM, packaged local asset/font hashes, `13.690699821s` wall time, `307076 KiB` container maximum RSS, `3` peak threads, expected Level 1/2 success plus Level 3 `INCOMPLETE_SEARCH`, native imports/`ldd` closure, and matching repeated/clean-cache sample-output hashes. Cross-platform hash parity, apt/wheelhouse closure, organizer-controlled limits, and official scoring remain unverified.
| **F-07** normative search/renderer test evidence | **Local bounded evidence recorded; official evaluation deferred.** | `Docs/IMPLEMENTATION/tickets/08-issue-23-evidence.md`, `Docs/IMPLEMENTATION/tickets/08-heldout-evaluation.md`, `scripts/evaluate_heldout_search.py`, `chameleon/tests/artifact/`, `chameleon/tests/layout/`, `tests/renderer/`, `tests/geometry/`, and `tests/fixtures/renderer_artifact_hashes.json`. The evidence covers rounding, variants, ranking, renderer edges, artifact provenance, hashes, and a seven-case locally authored held-out-style corpus (six `SUCCESS`, one `INCOMPLETE_SEARCH`, with stable repeated response/PNG signatures); organizer-held-out scoring remains unverified. |
| **F-08** stale status/roadmap/dependencies | **Reconciled by this documentation update.** | This matrix, the current status/roadmap/architecture sections, Ticket 07/08 status lines, and qualification evidence distinguish implemented bounded work from pending or unverified gates. |
| **F-09** stale traceability/ADR/README claims | **Reconciled by this documentation update.** | Contract traceability, ADR-002, ADR-008, `Docs/IMPLEMENTATION/SPEC.md`, `Docs/IMPLEMENTATION/README.md`, and `chameleon/README.md` identify historical pre-implementation wording and current local evidence without changing normative authority. |

The public Level 3 sample now returns a hard-valid pair with stable repeated local signatures. The separate extreme-ratio regression remains typed `INCOMPLETE_SEARCH`, exits nonzero, and publishes no artifacts. These local results are not proof of organizer-held-out acceptance, official scoring, or native-amd64 parity for the issue branch; no merge or release is claimed here.

## Issue #20 F-04 authoritative validator verification

Issue #20 closes the gap between structural contract validation and renderer-aware text semantics. `validate_response()` now hard-validates every serialized text element through the pinned local converter and packaged font manager. `validate_renderer_response()` remains the publication-time full-document gate for assets and renderer conversion.

The focused contract regressions cover width wrapping and unbreakable segments, Unicode mandatory breaks and forced empty lines, effective style-run face metrics, letter spacing, center alignment, positioned italic glyph bounds, and missing-font runtime failure. Existing contract/geometry fixtures were adjusted only where the newly authoritative actual-glyph-bound rule exposed an invalid narrow box.

## Issue #16 historical verification record (pre-Issue #61)

The following evidence was produced on the Issue #16 integration tree before the Issue #61 changes; it remains historical evidence and is not the current branch verification:

- `cd chameleon && ../.venv/bin/python -m unittest discover -s tests -t . -p 'test_*.py' -v` — **268 tests ran; 265 passed** on local Darwin arm64. Three persisted artifact/pin checks fail because installed `skia-python` is `144.0.post2` while the fixture pins `132.0b11`; the same failures reproduce on `origin/main`. GitHub CI run `39610104556` passed for the current evaluator/test changes.
- Focused suites after the Issue #20 change: contract **34**, layout **75**, renderer **39**, and runner **78** tests passed.
- `python3 scripts/verify_repository.py` and `make verify` — **passed**; corrected changed-file `py_compile` and `git diff --check` — **passed**.
- `cd chameleon && python -m engine.main` — not runnable because the system interpreter lacks `jsonschema`.
- `cd chameleon && ../.venv/bin/python -m engine.main` — exit **1 expected**; Level 1 and Level 2 published valid pairs, Level 3 returned typed `INCOMPLETE_SEARCH` with no pair. Generated smoke artifacts were cleaned afterward.
- `cd chameleon && docker buildx build --platform linux/amd64 --load -t chameleon-stage1 .` — **passed** with Docker's constant-platform warning.
- `cd chameleon && docker run --rm --network none -v "$PWD/input:/app/input" -v "$PWD/output:/app/output" chameleon-stage1` — exit **1 expected** under the arm64 host's amd64 emulation; Level 1 and Level 2 published valid pairs, Level 3 returned typed `INCOMPLETE_SEARCH`, and generated smoke artifacts were cleaned. This is not native-amd64 qualification.
- Pinned `chameleon-main-edge-v2` `linux/amd64` source-mounted suite — **254 tests passed**. Arm64-host emulation remains supplemental.

The earlier sections below preserve historical ticket and transition records. Their counts, branch names, and environment results are not current Issue #16 verification evidence.

## Issue #21 artifact-conformance implementation

Issue #21 adds hard semantic PNG validation at both trust boundaries. `engine.artifact.validate_artifact()` checks the pinned `max_size=2048` dimensions, fully opaque canvas, exact missing-asset warnings, adapter-derived paint bounds, one-to-one opaque raster replay, and full pixel equality with a second pinned-adapter render for non-exact layers. The gate returns `RUNTIME_IO_FAILURE`; staging cleans the private pair before publication. Contrast remains outside hard validity.

- **Changed production paths:** `chameleon/engine/artifact.py` and `chameleon/engine/staging.py`; candidate validation is reused by near-isomorphic and column-pivot paths.
- **Changed evidence paths:** artifact fixtures/tests under `chameleon/tests/fixtures/artifact/` and `chameleon/tests/artifact/`; readable-invalid renderer doubles and publication regressions remain under `tests/runner`.
- **Focused artifact evidence:** `cd chameleon && /Users/charliefurlow/Desktop/ProjectChameleon/.venv/bin/python -m unittest discover -s tests/artifact -t . -p 'test_*.py' -v` — 17 passed.
- **Related focused evidence:** renderer 39 passed; layout 73 passed; runner 78 passed.
- **Full local evidence:** `cd chameleon && /Users/charliefurlow/Desktop/ProjectChameleon/.venv/bin/python -m unittest discover -s tests -t . -p 'test_*.py'` — 248 passed.
- **Repository evidence:** `python3 scripts/verify_repository.py`, `make verify`, changed-file `py_compile`, and `git diff --check` passed.
- **Engine smoke:** `cd chameleon && /Users/charliefurlow/Desktop/ProjectChameleon/.venv/bin/python -m engine.main` — exit 1 expected; Level 1 and Level 2 committed valid pairs, Level 3 returned `INCOMPLETE_SEARCH` with no pair. Generated smoke artifacts were removed afterward.
- **Docker evidence:** Buildx succeeded with the documented constant-platform warning; the offline run is supplemental amd64-on-arm64 evidence, not native-amd64 qualification.
- **Independent review:** subagent audit confirmed seam reuse; test review added explicit decoded readable-invalid fixtures at validation, publication, and candidate seams; security review drove header-dimension ordering and font-directory fallback hardening. Resource limits remain outside scope.

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
- ✅ 20 layout tests, 154 total tests passing

**Cutoff semantics disposition (accepted):**
The bounded deterministic search with `INCOMPLETE_SEARCH` status satisfied Gate 1 at the historical Ticket 05 boundary. The current tree additionally contains bounded column-pivot, horizontal-ribbon, vertical-restack, candidate-variant, ranking, and exhaustion-aware paths; the public Level 3 result remains contract-correct fail-closed and is not a Gate 1 blocker.

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
2. Ticket 06 supplies bounded column-pivot and role-inference behavior; Ticket 07 supplies horizontal-ribbon and vertical-restack families; Ticket 08 supplies bounded candidate enumeration, renderer-gated ranking, and qualification evidence. Broad held-out evaluation remains deferred.
3. Renderer goldens and native-library parity remain unverified beyond the recorded local evidence; the arm64-host Docker run is supplemental and does not establish native-amd64 qualification.
4. Native `x86_64` CI smoke remains historical native evidence; current local Docker observations use arm64-host emulation and are supplemental. The mixed public batch remains aggregate-nonzero because Level 3 is intentionally fail-closed.
5. The Docker build retains the non-blocking `FromPlatformFlagConstDisallowed` warning.


### Future review follow-up

- Review the current bounded search and every candidate against serialized hard validation before soft scoring; preserve the topology and cutoff gates.
- Verify every successful sample produces a committed JSON/PNG pair and every failed sample publishes neither artifact.
- Confirm any future renderer-golden/native-parity or held-out qualification claim against new evidence; keep arm64-host Buildx output labeled supplemental.

## Ticket 06 implementation evidence — complete

Ticket 06 implementation evidence is complete and PR #14 is merged into `main`. The refreshed-PR corrections removed the unauthorized relationship/resource cap and stale evidence claims; the relationship view, readable-floor font search, resource-guard removal, and documentation corrections passed local verification before merge. No native-amd64 qualification is claimed from the local arm64-host Docker run.

- **Changed Ticket 06 product paths:** `chameleon/engine/layout/roles.py` (new lazy relationship view), `chameleon/engine/layout/column_pivot.py` (new), `chameleon/engine/layout/__init__.py`, `chameleon/engine/layout/near_isomorphic.py` (bounded renderer/font-search hardening), `chameleon/engine/resize.py`, and `chameleon/tests/layout/test_level2.py` (new/updated).
- **Inherited Gate 1 paths present in the merged tree:** renderer converter and renderer tests remain from the prior transition; the temporary `resources.py` policy and its imports/call sites were removed. No new renderer resource ceiling is part of Ticket 06.
- **Changed documentation paths:** `AGENTS.md`, `.agents/README.md`, `.agents/PROJECT_PROFILE.md`, `.agents/PRODUCTION_STANDARD.md`, `.agents/roles/implementer.md`, `.agents/workflows/02-plan.md`, `.agents/tasks/ticket-06-column-pivot-level2.md`, `.agents/runs/ticket-06-column-pivot-level2.md`, `Docs/STATUS.md`, `Docs/FINAL_ARCHITECTURE.md`, `Docs/IMPLEMENTATION/README.md`, `Docs/IMPLEMENTATION_ROADMAP.md`, `Docs/IMPLEMENTATION/tickets/06-column-pivot-and-level-2-solver.md`, and `Docs/IMPLEMENTATION/tickets/07-horizontal-ribbon-and-level-3-solver.md`.
- **Focused tests:** `cd chameleon && ../.venv/bin/python -m unittest discover -s tests/layout -t . -p 'test_*.py' -v` — 35 passed after the refreshed-PR correction pass.
- **Full tests:** `cd chameleon && ../.venv/bin/python -m unittest discover -s tests -p 'test_*.py' -v` — 170 passed.
- **Repository/syntax checks:** `python3 scripts/verify_repository.py`, `make verify`, changed-file `py_compile`, and final `git diff --check` passed.
- **Engine smoke:** `cd chameleon && ../.venv/bin/python -m engine.main` — exit 1 expected; Levels 1-2 `SUCCESS` with pairs, Level 3 `INCOMPLETE_SEARCH` with no pair; warning-only off-canvas self-check remains non-authoritative.
- **Docker supplemental smoke:** `docker buildx build --platform linux/amd64 --load -t chameleon-stage1 .` passed with `FromPlatformFlagConstDisallowed`; offline `docker run --rm --network none ... chameleon-stage1` exited 1 as expected with Levels 1-2 pairs and Level 3 `INCOMPLETE_SEARCH`. This is arm64-host supplemental evidence, not native-amd64 qualification.
- **Review:** Independent correctness/security review found and resolved the contract-visible relationship/resource-cap and stale-path/status findings. Pre-existing exact-ingress/style-run and unbounded schema/render resource risks remain outside this bounded fix. Partner review and merge disposition are complete.
- **Next review:** Resolve the Ticket 07 public Level 3 sample acceptance gap through bounded implementation review or an accepted contract/fixture decision. Ticket 08 implementation and local evidence are present; its native-amd64, clean-cache, resource, and held-out qualification boundaries remain open.



## Ticket 07 implementation evidence — active review

Ticket 07 product work is implemented on `feat/ticket-07-horizontal-ribbon-level3`, but the Level 3 fixture acceptance remains open. The implementation is intentionally contract-first: it keeps exact group transforms, rotated AABB checks, source-separated placement, image-ratio lattices, renderer-gated integer font search, missing-asset records, and typed fail-closed behavior. It does not claim a hard-valid output for the adversarial `1080 x 1350 -> 728 x 90` sample.

- **Changed product paths:** `chameleon/engine/layout/horizontal_ribbon.py`, `chameleon/engine/layout/vertical_restack.py`, `chameleon/engine/layout/__init__.py`, `chameleon/engine/resize.py`, and `chameleon/tests/layout/test_level3.py`.
- **Focused evidence:** `cd chameleon && ../.venv/bin/python -m unittest tests.layout.test_level3 -v` — 4 passed. Feasible synthetic horizontal and vertical candidates validate; repeated synthetic rendering produces identical PNG hashes; the public Level 3 fixture fails closed after the bounded ribbon candidates are exhausted.
- **Level 2 regression:** `cd chameleon && ../.venv/bin/python -m unittest tests.layout.test_level2 -v` — 15 passed.
- **Full evidence:** `cd chameleon && ../.venv/bin/python -m unittest discover -s tests -p 'test_*.py' -v` — 174 passed.
- **Repository checks:** `python3 scripts/verify_repository.py`, `make verify`, and changed-file `py_compile` passed; `git diff --check` passed for tracked edits.
- **Engine smoke:** required system `python -m engine.main` could not start because that interpreter lacks `jsonschema`; the project environment `../.venv/bin/python -m engine.main` ran Levels 1-2 successfully and Level 3 as typed `INCOMPLETE_SEARCH` with no pair.
- **Docker supplemental smoke:** `docker buildx build --platform linux/amd64 --load -t chameleon-stage1 .` passed with the existing `FromPlatformFlagConstDisallowed` warning. Offline `docker run --rm --network none ... chameleon-stage1` ran under arm64-host amd64 emulation, produced Level 1-2 pairs, and returned the expected nonzero status for the Level 3 typed failure. This is supplemental, not native-amd64 qualification.
- **Observed public Level 3 result:** typed `INCOMPLETE_SEARCH`; no design/PNG pair. The horizontal family exhausts its finite geometry/order variants at renderer-gated text placement; column-pivot and near-isomorphic remain bounded fallbacks and also fail on the fixture's rigid groups. This is evidence of an unresolved acceptance gap, not proof that the fixture is contract-infeasible.
- **Known review risk:** the ticket requires a valid $728 x 90$ sample output, but the current hard-valid search has not produced one. Do not mark Ticket 07 complete, claim sample-pass evidence, or promote this arm64-host work to native-amd64 qualification until the gap is resolved or superseded by an accepted contract decision.
- **Next review question:** independently enumerate the legal integer group/image lattices and renderer-valid text boxes for the fixture before changing hard constraints. A solver change MUST remain bounded and MUST NOT shed records, rewrite copy/font attributes, substitute fonts, or relax overlap/containment rules.

## Ground truth now recorded

- `Docs/PROJECT_CONTRACT.md` is the Stage 1 behavioral authority.
- ADR-001 establishes source precedence.
- ADR-002 ratifies the v0.9 design wire shape and pins the project renderer contract.
- ADR-003 separates hard constraints from soft objectives and chooses fail-closed infeasibility handling.
- ADR-004 fixes the initial offline `linux/amd64` runtime target and dependency baseline.
- ADR-005 separates autonomous Stage 1 from finale-only Adobe Express interactions.
- ADR-006 ratifies typed failure statuses, logical JSON/PNG pair publication, and conservative cutoff semantics without adding a failure wire envelope.
- ADR-007 ratifies exact numeric ingress, one round-half-even serialization, rigid group transforms, contract AABBs, and positive-area overlap; quantized group reconstruction is narrowly superseded by ADR-010.
- ADR-008 ratifies Unicode-safe line generation, code-point `[start,end)` style ranges, effective span metrics, overflow rejection, and in-box rectangle/ellipse strokes; transient glyph-origin inset is narrowly extended by ADR-012.
- ADR-009 ratifies bounded deterministic four-topology search, renderer-in-loop hard validation, fixed-point ranking, and no initial model/OR-Tools dependency.
- ADR-010 defines the PDF-grounded quantized common-group transform.
- ADR-011 makes readability a renderer-validated soft objective without a universal numeric font-size floor.
- ADR-012 requires the minimal renderer-measured transient glyph inset inside unchanged declared text bounds.
- `Docs/DEPENDENCY_EVIDENCE.md` records official-source verification, detected versions, pins, risks, and conformance tests.
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
| Infeasible target & fallback | Bounded spatial compression and readability preference maximize feasibility on extreme canvases; typed `InfeasibleLayoutError` and `INCOMPLETE_SEARCH` distinguish exhausted from unfinished work; no misleading JSON/PNG | ADR-003, ADR-006, ADR-011, contract §8 |
| Failure protocol | `SUCCESS`, `MALFORMED_INPUT`, `INFEASIBLE_LAYOUT`, `INCOMPLETE_SEARCH`, and `RUNTIME_IO_FAILURE`; no failed-task artifacts; JSON/PNG committed as a logical pair; nonzero aggregate if any task fails; cutoff is never proof of infeasibility | ADR-006, contract §8 |
| Numeric/geometry | Exact rational ingress; one round-half-even serialization; reduced image-ratio lattice; group transform reconstructed after canonical quantization; rotated AABB hard predicate; boundary contact allowed; deterministic background and same-side bleed rules | ADR-007, ADR-010, contract §§5, 7 |
| Typography/renderer | UAX #29 clusters intersected with UAX #14 opportunities; latest-fitting greedy breaks; code-point `[start,end)` runs; effective span metrics; explicit/empty-line accounting; overflow rejection; in-box strokes; minimal transient glyph inset; no public line map | ADR-008, ADR-012, contract §6 |
| Readability | No universal numeric minimum font size; renderer-valid glyph bounds and qualitative legibility remain required; size remains a soft preference | ADR-011, contract §§6, 9 |
| Initial search | Deterministic multi-signal inference; four topology families; at most three source-derived variants per family; renderer-in-loop hard validation; fixed-point ranking; no model/OR-Tools dependency | ADR-009, contract §9 |
| Runtime & hardware | Pinned Python 3.11 `linux/amd64`, runtime `--network none`, CPU-only execution, dynamic asset/font loading, no current model/OR-Tools requirement | ADR-004, ADR-009 |
| Stage split & finale | Stage 1 is autonomous offline engine; pinning, shedding, copy/font changes, and reduced previews are finale-only; finale add-on communicates with engine via local HTTP service | ADR-005, contract §10 |

## Ratified source-of-truth artifacts

These are contract artifacts, not solver or renderer implementation:

- `chameleon/requirements.txt` pins the initial external compatibility baseline.
- `chameleon/Dockerfile` records the intended Python 3.11.11 Bookworm amd64 image and offline environment defaults.
- `chameleon/chameleon_design_schema_v0.9.json` is no longer provisional, accepts empty designs, and records structural ranges/defaults.
- Contract fixtures live under `chameleon/tests/fixtures/contract/`.
- The Level 2 public sample's style range is corrected to valid end-exclusive `[6, 15)` semantics; this is fixture/source-data correction, not solver implementation.
- Ticket 01's semantic validator and contract tests, ticket 02's renderer adapter/tests, ticket 03's fail-closed runner, ticket 04's exact geometry package/tests, and ticket 05's bounded Level 1 solver/tests are implemented. Gate 1 qualification is complete in the historical transition record; Ticket 06 is merged; Issue #61 resolves the public Level 3 local sample acceptance gap under ADR-010 through ADR-012. Issue-branch review/native-amd64 CI and organizer-held-out evaluation remain pending.

## Solver work after Gate 1

The current bounded capabilities are active:

1. **Ticket 06:** Complete and merged in PR #14; the bounded role-inference and column-pivot evidence is recorded above.
2. **Ticket 07:** Horizontal-ribbon and vertical-restack candidates now produce the public Level 3 sample as a hard-valid pair locally. The original project-authored numeric text floor and post-rounding exact group relationship were reconciled against the source PDF through Accepted ADR-010 through ADR-012.
3. **Ticket 08:** Four-family candidate search, source-derived variants, renderer-gated fixed-point ranking, artifact provenance, and local held-out-style evaluation are implemented; official/native qualification is pending.
4. **Future hardening (if needed):** A project-owned hash-locked wheelhouse and apt-version locks require separate evidence and change control.

**Note:** `engine/main.py` warning-only self-check is not the contract validator - `engine/contract.validate_response()` is authoritative.

## External facts remaining unverified (not Gate 1 blockers)

- Whether hidden tasks are guaranteed feasible and how the scorer handles no-output or nonzero task failure.
- Organizer-controlled M5 Pro CPU/RAM/disk/GPU limits.
- Final model allowlist and model-size cap.
- Official scoring threshold details and complete target catalogue.
- Font licenses/embedded metadata and final Adobe Express font availability.
- Native-amd64 CI for this issue branch, cross-platform parity, and release readiness. Earlier native-amd64 evidence pertains to a prior revision and does not verify this fix.
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


## Historical Gate 1 qualification evidence (transition record)

The following smoke sequence is preserved from the earlier Gate 1 transition and is not current Issue #16 qualification evidence. The current run and environment boundaries are recorded in the Issue #16 verification record above.
```bash
cd chameleon
python -m engine.main                                    # ✅ Levels 1-2 SUCCESS, Level 3 INCOMPLETE_SEARCH
python -m unittest discover -s tests -p 'test_*.py' -v  # ✅ 154 tests passing
docker buildx build --platform linux/amd64 --load -t chameleon-stage1 .  # ✅ Clean build
docker run --rm --network none \
  -v "$PWD/input:/app/input" -v "$PWD/output:/app/output" \
  chameleon-stage1                                       # ✅ Offline runtime verified
```

**Native x86_64 verification:** GitHub Actions run [39181208925](https://github.com/bjornefisk/ProjectChameleon/actions/runs/39181208925) passed all checks on native x86_64 hardware.

**Renderer determinism:** Level 1 integration test verifies repeated render produces identical SHA-256 hashes.

**Bounded search semantics:** Level 3 correctly reports `INCOMPLETE_SEARCH` (not false infeasibility claim). Full ADR-009 four-topology search is Tickets 06-08 work, not a Gate 1 prerequisite.


[You have received this identical output 4 times. Re-reading '/Users/charliefurlow/Desktop/ProjectChameleon/Docs/STATUS.md:raw' will not change it — use a narrower selector (path:A-B), or proceed with the edit.]

[You have received this identical output 3 times. Re-reading '/Users/charliefurlow/Desktop/ProjectChameleon/Docs/STATUS.md:raw' will not change it — use a narrower selector (path:A-B), or proceed with the edit.]