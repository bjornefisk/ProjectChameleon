# Issue 23 / F-07 evidence record

This record expands the normative regression evidence on the integrated Ticket 07/08 review tree before Issue #61. Its recorded public-sample failure is historical, not the current result; see `Docs/STATUS.md` for Issue #61 behavior and verification. It does not change the Stage 1 wire schema, renderer dependency, or runtime policy; the focused Issue #29 fix only corrects variant candidate serialization.

## Authority and scope

`PROJECT_CONTRACT.md` and Accepted ADR-001 through ADR-013 remain authoritative. The tests use the `chameleon-contract`, `chameleon-testing`, and `chameleon-review` skills:

- hard validation is exercised before soft quality assertions;
- mutable geometry/font-size behavior is checked after one half-even serialization step;
- renderer evidence uses the local adapter and pinned `cr-renderer` revision;
- tests are deterministic and offline; and
- persisted hashes are evidence, not a new response field or ranking input.

The local checked-in held-out-style evaluator is now implemented and recorded in [`08-heldout-evaluation.md`](08-heldout-evaluation.md). Broad organizer-held-out evaluation and native-amd64 qualification remain unverified; this record keeps those limitations visible rather than converting local evidence into an official qualification claim.

## Evidence matrix

| Issue 23 criterion | Evidence | Boundary |
| --- | --- | --- |
| Rounding regressions | `chameleon/tests/geometry/test_issue23_rounding.py` covers signed half-even ties and a ratio candidate that is valid before serialization but rejected after serialized integer geometry is revalidated. | Local contract-seam evidence; native-amd64 parity is not claimed. |
| Topology and candidate variants | `chameleon/tests/layout/test_issue23_search_evidence.py` exercises source-derived variants and the bounded work set: ADR-009 §3 variant omission (text-only, image-only, empty, shape-only, and full-canvas `cover` background sources omit the variants they cannot support), `source_order` as the first evidence element's array index, the twelve-candidate bound with many elements, target-independent enumeration, and a per-work-item accounting invariant at the `search()` seam (every enumerated item is an admitted candidate or a typed failure record, on wide/tall/extreme and on an unfittable target). | Covers the bounded implementation present on this tree; it does not widen the Ticket 07/08 candidate space. Which family is admitted for a target is a solver outcome, not an ADR-009 mandate, so per-family admission is asserted only on the authored held-out corpus (corpus design intent, below), never on the synthetic sources here. |
| Variant translation serialization | `chameleon/tests/layout/test_search_ranking.py::test_variant_translations_round_complete_coordinate_once` proves dominant-media and dominant-copy translations are applied exactly before one half-even serialization and then hard-validated. | Focused local evidence; native-amd64 parity and the broader held-out qualification remain unverified. |
| Ranking | The search evidence keeps hard-validation assertions separate from fixed-point quality/tie-break assertions; existing `test_search_ranking.py` remains the direct ranker regression suite. | Soft quality is never used to rescue a hard-invalid response. |
| Persisted artifact hashes | Renderer corpus: `chameleon/tests/fixtures/renderer_artifact_hashes.json` records document, packaged-asset, font-tree, pinned-renderer, PNG hash, dimensions, and warning provenance; `test_issue23_artifact_corpus.py` recomputes every value. Engine level: `chameleon/tests/fixtures/engine_artifact_hashes.json` pins the SHA-256 of the committed JSON/PNG pair published for the Level 1 and Level 2 samples; `chameleon/tests/runner/test_issue23_engine_artifact_hashes.py` runs `python -m engine.main` in fresh processes under two `PYTHONHASHSEED` values, re-validates the published JSON with `validate_response`, checks PNG size and commit-marker hashes, requires byte identity across processes, and compares against the pins. | Pins are keyed by `<system>-<machine>` (`linux-x86_64`, `linux-aarch64`, `darwin-arm64`) and bound to task, schema, asset, font, renderer-commit, and Pillow/skia versions. An unrecorded platform skips only the pin comparison. Not an external scorer. See "Platform evidence". |
| Renderer edge cases | `chameleon/tests/renderer/test_issue23_artifact_corpus.py` covers `contain`, `cover`, and `fill`, rotated geometry, negative letter spacing, right alignment, missing-asset diagnostics, and real PNG output. `chameleon/tests/renderer/test_issue23_render_behavior.py` adds behavior that hashes cannot show: pixel-level contain/cover/fill on an opaque banded asset (contract §6), ink width changing by exactly (glyphs − 1) × spacing for ±2 px letter spacing, left/center/right ink edges inside the element box, the renderer-preflight validator (`validate_renderer_response`) rejecting a word that overflows at spacing 0 but accepting it at negative spacing (and the converse for positive spacing), and 30°/−30°/45° rotation against the contract's rotated AABB plus clockwise-about-centre direction. | Pixel behavior is qualified only for the pinned local adapter/runtime used by the test; expectations adapt to the platform's own measured advances and avoid boundaries. |
| Runtime qualification | `Docs/IMPLEMENTATION/tickets/08-qualification-evidence.md` and `Docs/DEPENDENCY_EVIDENCE.md` record the native-amd64 CI run, local asset/font hashes, JSON/PNG hashes, image size, container RSS, runtime, and the hard/soft distinction. | Native-amd64 runtime, native-library, and clean-cache sample-output evidence is recorded; cross-platform hash parity, apt/wheelhouse closure, and organizer-controlled limits remain unverified. Observed arm64-host Docker timings are supplemental, not qualification. |
| Held-out evaluation | `chameleon/tests/layout/test_heldout_evaluation.py` and [`08-heldout-evaluation.md`](08-heldout-evaluation.md) evaluate the five-case authored corpus once and assert, per case: `SUCCESS`, no hard-validation errors, source unchanged, repeat stability, no cutoff, at most twelve candidates, admitted equals hard-valid, a typed rejection for every non-admitted work item, and that the case's intended family was admitted (hard-valid), not merely enumerated. Corpus level: the union of per-case admitted families is all four, admission is selective so rejections stay exercised, aggregates equal a recomputation from per-case numbers, and soft quality is reported separately as integer fixed-point components. | Local held-out-style evidence only; it is not an organizer-held-out benchmark or native-amd64 qualification. Selected topology is soft-ranked and platform dependent, so it is deliberately not asserted. |

## Hard validation versus soft quality

Hard evidence consists of serialized `validate_response()` results, renderer conversion failures/warnings, expected PNG dimensions, source/asset/font provenance, and repeated byte hashes. Soft evidence consists of `QualityScore` values and deterministic rank ordering among candidates that already passed hard validation. No test treats a non-empty PNG, a copied response, or a proxy score as proof of contract validity.

## Historical Issue 23 integration verification pointer

The Issue #16 integration record below predates Issue #61; its counts and statuses remain evidence for the revision exercised at the time only. Current Issue #61 results and native-amd64 PR CI state are recorded in [`../../STATUS.md`](../../STATUS.md).

## Hardening pass: assertions that could not fail

An audit of the first F-07 test set against the acceptance criterion "avoid tautological tests" found assertions that would pass whether or not the named behavior held. Each was replaced by a check that a plausible regression breaks:

| Earlier assertion | Why it could not fail | Replacement |
| --- | --- | --- |
| Held-out test: `REQUIRED_FAMILIES.issubset(hard["topology_coverage"])` | The evaluator reports `topology_coverage` as admitted ∪ work-set topologies, and the work set always lists all four families. | Per-case `admitted_topology_coverage` must contain the case's intended family; the union of per-case admitted families must be all four; admission must be selective; work-set coverage is asserted separately and labelled enumeration evidence. |
| Held-out test: `0.0 <= hard_valid_rate <= 1.0` | True for any ratio. | The aggregate rate and distributions must equal a recomputation from per-case counts. |
| Held-out test: `assertIn(key, report)` shape checks, no case status | Prove wiring only. | Status, validation errors, stability, cutoff, candidate bound, admitted/hard-valid equality and rejection accounting per case. |
| `test_representative_targets_observe_supported_topology_families` | Re-asserted that enumeration lists four families for any target. | Target-independent enumeration plus an admitted-xor-typed-failure accounting invariant at the `search()` seam. |
| Search byte-stability test: PNG header-prefix check and `hard_validity == 1` constant | Prove "looks like a PNG" and a constant. | PIL decode with exact target dimensions; admission proven by independent `validate_response` on every admitted candidate. |
| Variants (ADR-009 §3 "a missing source signal omits the corresponding variant") | Only a source with both media and copy was exercised. | Omission tests for text-only, image-only, empty, shape-only, and background-plus-text sources; `source_order` and the twelve-candidate bound. |
| Negative letter spacing, non-right-angle rotation, fit modes | Only a pass-through dict check, a 90° rotation (symmetric about the centre), and relative bounding boxes on an alpha-shaped asset. | `test_issue23_render_behavior.py` (see matrix). |

### Mutation checks

| Mutation | Exact production/fixture edit | Modules run | Result and failing new-test evidence |
| --- | --- | --- | --- |
| S1 | `search.py::_source_variant_indices` returns `(0, 1, 2)` unconditionally. | `tests.layout.test_issue23_search_evidence tests.layout.test_heldout_evaluation` | **KILLED** — `test_text_only_source_omits_dominant_media`, `test_foreground_image_only_source_omits_dominant_copy`, `test_empty_source_has_only_base_variants_and_returns_target_canvas`, `test_shape_only_source_has_no_media_or_copy_variants`, `test_full_canvas_cover_background_is_not_media_evidence`. |
| S2 | `_source_variant_orders` uses the last matching evidence index instead of the first. | Same search/held-out modules | **KILLED** — `test_variant_source_order_is_first_evidence_array_index`. |
| S3 | `MAX_VARIANTS_PER_FAMILY = 2`. | Same search/held-out modules | **KILLED** — target-independent enumeration, twelve-candidate, source-variant, source-order, and aggregate-limit assertions. |
| S4 | `solve_vertical_restack` immediately raises a non-exhausted `InfeasibleLayoutError`. | Same search/held-out modules | **KILLED** — tall-target work-set accounting plus `test_intended_family_is_admitted_for_each_authored_case` and `test_union_of_admitted_families_covers_all_four_topologies`. |
| S5 | Solver-failure handling skips the rejection record. | Same search/held-out modules | **KILLED** — `test_bounded_search_admits_hard_valid_candidates_and_repeats_byte_stably`, non-square/unfittable work-set accounting, and per-case rejection accounting. |
| S6 | `enumerate_candidate_specs` omits `vertical_restack` when target height is less than target width. | Same search/held-out modules | **KILLED** — `test_enumeration_is_target_independent`, source-variant/twelve-candidate tests, and work-set coverage. |
| S7 | Held-out per-case admitted coverage reports admitted ∪ work-set topologies. | Same search/held-out modules | **KILLED** — `test_admission_is_selective_so_rejected_attempts_stay_exercised`. |
| S8 | Held-out aggregate `hard_valid_rate` uses the wrong denominator. | Same search/held-out modules | **KILLED** — `test_aggregate_metrics_match_recomputation_from_per_case_numbers`. |
| S9 | Ranking emits one fixed-point quality component as a float. | Same search/held-out modules | **KILLED** — bounded-search and fixed-point/separation tests; the runtime path rejects the non-integer component. |
| R1 | Renderer swaps `contain` and `cover` fit handling. | `tests.renderer.test_issue23_render_behavior` | **KILLED** — `test_contain_letterboxes_isotropically_at_pixel_level`, `test_cover_center_crops_isotropically_at_pixel_level`. |
| R2 | Renderer forces `letter_spacing` to zero. | Same renderer module | **KILLED** — ink-width and negative/positive letter-spacing validator tests. |
| R3 | Renderer negates the rotation angle. | Same renderer module | **KILLED** — both subtests of `test_rotation_direction_is_clockwise`. |
| R4 | Renderer maps right-aligned text to center alignment. | Same renderer module | **KILLED** — `test_text_alignment_is_honored_inside_element_width`. |
| R5 | Validator-side width measurement ignores letter spacing. | Same renderer module | **KILLED** — negative-spacing acceptance and positive-spacing overflow assertions. |
| E1 | `near_isomorphic._preferred_font_size` returns one size below the preferred value. | `tests.runner.test_issue23_engine_artifact_hashes` | **KILLED** — `test_artifact_hashes_match_the_persisted_pins_for_this_platform`. |
| E2 | Commit marker includes a process-dependent field. | Same engine module | **KILLED** — `test_published_bytes_are_identical_across_processes_and_hash_seeds` and output-set assertion. |
| E3 | Runner writes `stray.tmp` after publishing. | Same engine module | **KILLED** — `test_runner_succeeds_in_every_process_and_publishes_only_committed_pairs`. |
| E4 | `quantize_to_int` uses floor instead of half-even. | Engine module; search and renderer modules were also smoke-run | **KILLED by engine artifact pins** — `test_artifact_hashes_match_the_persisted_pins_for_this_platform`; search/renderer behavior remained green because those suites do not exercise this runner artifact path. |
| F1 | One current-platform Level 1 JSON hash digit is flipped. | `tests.runner.test_issue23_engine_artifact_hashes` | **KILLED** — `test_artifact_hashes_match_the_persisted_pins_for_this_platform`. |
| F2 | One byte is appended to `solstice_bottle.png`. | Same engine module | **KILLED** — `test_persisted_pins_bind_current_task_schema_asset_font_and_dependency_inputs`. |
| F3 | Delete the persisted `linux-x86_64` platform entry. | Not run in the interrupted scratch mutation pass | **Not run; no result claimed.** |

The mutation pass used a pristine export for every applied mutation. The
mutated checkout, pristine export, and logs were scratch-only; the review
worktree was unchanged by the pass. F3 is explicitly left as a verification
gap rather than represented as killed.

## Platform evidence (observed)

Labels: OBSERVED = a command was run in this change and its output captured; INFERRED = reasoned, not directly observed.

### Level 1 and Level 2 engine artifacts (`python -m engine.main`)

SHA-256 prefixes; full values are in `chameleon/tests/fixtures/engine_artifact_hashes.json`.

| Platform key | L1 JSON | L1 PNG | L2 JSON | L2 PNG | Observed on |
| --- | --- | --- | --- | --- | --- |
| `linux-x86_64` | `237a8a9eeeea` | `71e0be9ea2ae` | `3e26ef9e95df` | `bf24e6712552` | Native amd64 GitHub Actions container run [39461763417](https://github.com/bjornefisk/ProjectChameleon/actions/runs/39461763417) (`main@8097c09`, step "Record native sample artifact hashes") and a local `linux/amd64` Docker run emulated on Apple Silicon; byte-identical. |
| `linux-aarch64` | `237a8a9eeeea` | `58d49a6e5191` | `3e26ef9e95df` | `ef0d29f6bdb3` | Local native `linux/arm64` container built from the pinned Dockerfile with only the platform flag changed; two runs byte-identical. |
| `darwin-arm64` | `237a8a9eeeea` | `e04df5d20fb9` | `9618cc72bfde` | `bc5af21d9c57` | Local `.venv` with the pinned dependency versions; repeated runs and different `PYTHONHASHSEED` values byte-identical. |

Findings:

1. **OBSERVED — layout JSON follows the operating system's text metrics, not the CPU.** Linux x86_64 and aarch64 produce the same JSON; macOS differs in Level 2 only by `headline.font_size` 39 vs 40 and `subhead.font_size` 18 vs 19. The rejection that sets the macOS limit is vertical: converting the headline at 40 px raises `TextOverflowError: positioned glyph bounds exceed text element` with the glyph bottom at 52.24 px against a 52 px box, while the Linux hinted metrics place the bottom inside the box (41 px is rejected at 53.25). The subhead behaves the same way against its 26 px box. Skia glyph advances also differ (`Chase the Light`, Solstice Serif Bold: 299.04 at 40 px on macOS, integer-valued 302.0 on Linux). The font backend (fractional versus hinted metrics) is the INFERRED underlying cause; it was not isolated further.
2. **OBSERVED — PNG bytes depend on the operating system and the CPU architecture.** Three distinct PNG hashes exist for each sample, one per platform key above.
3. **OBSERVED — hard feasibility of borderline targets differs by operating system.** For the issue 23 search source, `search()` rejects 40×12 and 400×12 targets on macOS but admits `horizontal_ribbon` on Linux aarch64 (40×12 was also admitted on emulated Linux x86_64); 1×1 through 10×10 are rejected on macOS and Linux aarch64. Selection among admitted candidates is also soft-ranked on rendered pixels: the `vertical-restack-studio` held-out case selects `near_isomorphic` on macOS and `vertical_restack` on Linux aarch64, while hard admission (3, 6, 9, 6, 3 candidates, identical families) matched on both. Tests therefore avoid borderline targets and do not assert the selected topology.
4. **OBSERVED — a persisted renderer pin was wrong for native Linux/aarch64.** In `renderer_artifact_hashes.json`, `right_negative_spacing` mapped `aarch64` (the Linux spelling of arm64) to the macOS hash `5a058be8…`. On native Linux aarch64 the test failed with `'5a058be8…' != 'a0125103…'`, which is the x86_64 value. The `aarch64` pin now holds the Linux value; the other five corpus cases are identical on all three platforms. The existing test passes on macOS arm64 and native Linux aarch64 after the correction (it keys on `platform.machine()`: `arm64` is macOS, `aarch64` is Linux).
5. **OBSERVED — emulated and native amd64 agree.** The local emulated `linux/amd64` Docker output equals the native amd64 CI container output for all four sample files.

Observed per-task wall times for the samples (not qualification; the project's `<2.0s` target in `PROJECT_CONTRACT.md` is still unqualified, and `chameleon/RULES.md` states there is no hard stage-one time limit):

| Environment | Level 1 | Level 2 |
| --- | --- | --- |
| Native amd64 GitHub Actions container (run 39461763417) | 3.33 s | 5.24 s |
| Local `linux/amd64` Docker under Apple Silicon emulation (this change) | 22.50 s | 32.91 s |
| Local native `linux/arm64` container | 1.80 s | 2.75 s |
| Local macOS arm64 `.venv` | 1.60 s | 2.46 s |

Not verified: Windows, macOS x86_64, other Linux distributions or font-library builds, dependency versions other than the pinned ones, clean-cache runs, container RSS, and the organizer's scoring environment. The pins make no claim outside the recorded environments.

## Open questions found while hardening (not changed here)

1. **`INFEASIBLE_LAYOUT` is not reachable from the real solvers in any input observed.** ADR-009 §6 reports `INFEASIBLE_LAYOUT` when the finite work set is exhausted with no hard-valid result. `search()` only does so when every family attempt reports exhaustion; for targets from 1×1 to 10×10 and for the public Level 3 sample, every observed no-candidate outcome has `finite_work_exhausted=False` and ends as `INCOMPLETE_SEARCH`. The exhausted path is covered only with injected solvers in `test_search_ranking.py`. This is conservative and consistent with ADR-006's refusal to claim infeasibility without proof; whether a degenerate target should be provably infeasible is a policy decision outside this issue.
2. **Resolved by issue #20:** `validate_response()` now invokes the pinned renderer's text preflight at the authoritative hard-validation seam. It measures effective style faces and letter spacing, applies Unicode-safe wrapping and line-map/empty-line semantics, enforces max-lines and height, and rejects positioned glyph overflow. `validate_renderer_response()` remains the publication-time full-document gate. The focused contract regression suite calls `validate_response()` directly; no renderer-only wrapper is treated as proof of this seam.

## Disposition

At the time of this Issue 23/F-07 evidence run, it closed the local rounding/search/renderer evidence gaps and the F-04 validator gap, but did not establish official/native-amd64 qualification or a public Level 3 pair. The then-current `STATUS.md` recorded those limitations; Issue #61 later revised the local public-sample result under ADR-010 through ADR-012. Current results remain in `Docs/STATUS.md`.

## Historical Issue 23 verification (pre-Issue #61)

| Command | Observed result |
| --- | --- |
| `git diff --check` | Passed. |
| `make verify` | Passed. |
| `cd chameleon && /Users/charliefurlow/Desktop/ProjectChameleon/.venv/bin/python -m py_compile tests/layout/test_issue23_search_evidence.py tests/layout/test_heldout_evaluation.py tests/renderer/test_issue23_render_behavior.py tests/runner/test_issue23_engine_artifact_hashes.py` | Passed. |
| `cd chameleon && /Users/charliefurlow/Desktop/ProjectChameleon/.venv/bin/python -m unittest tests.geometry.test_issue23_rounding tests.layout.test_search_ranking tests.layout.test_issue23_search_evidence tests.layout.test_heldout_evaluation tests.renderer.test_issue23_artifact_corpus tests.renderer.test_issue23_render_behavior tests.runner.test_issue23_engine_artifact_hashes -v` | 53 tests passed in 16.607 s. |
| `make test VENV_DIR=/Users/charliefurlow/Desktop/ProjectChameleon/.venv` | 240 project tests passed in 341.812 s; 47 review-capsule tests passed in 34.923 s. |
| `cd chameleon && python -m engine.main` | Exit 1: system interpreter lacks `jsonschema`; no contract evidence inferred. |
| `cd chameleon && /Users/charliefurlow/Desktop/ProjectChameleon/.venv/bin/python -m engine.main` | Exit 1 as expected: Level 1/2 `SUCCESS` with pairs; Level 3 `INCOMPLETE_SEARCH` with no pair. |
| `cd chameleon && /Users/charliefurlow/Desktop/ProjectChameleon/.venv/bin/python ../scripts/evaluate_heldout_search.py --corpus tests/fixtures/heldout_search_cases.json --repeats 2 --output /tmp/issue23-heldout-search.json` | Five cases, 27/60 hard-valid candidates, all repeated response/PNG signatures stable; captured report hash `68d7e611ef85047998cbf9105a6b71c60084390608a982d4ffe51744589faa47`. |
| `cd chameleon && docker buildx build --platform linux/amd64 --load -t chameleon-stage1 .` | Passed with the existing `FromPlatformFlagConstDisallowed` warning. |
| `cd chameleon && docker run --rm --network none -v "$PWD/input:/app/input" -v "$PWD/output:/app/output" chameleon-stage1` | Exit 1 as expected under arm64-host amd64 emulation: Level 1 `SUCCESS` in 112.40 s, Level 2 `SUCCESS` in 167.03 s, Level 3 `INCOMPLETE_SEARCH`; no Level 3 pair. |

The Docker run is supplemental emulated-amd64 evidence, not native-amd64
qualification. The hard-validation, artifact, and soft-quality boundaries
remain those stated above.

## Historical Issue #29 focused verification

- `cd chameleon && ../.venv/bin/python -m unittest tests.layout.test_search_ranking tests.geometry.test_issue23_rounding -v` — 9 tests passed, including both exact variant-translation axes.
- `cd chameleon && ../.venv/bin/python -m unittest discover -s tests -t . -p 'test_*.py' -v` — 191 tests passed.
- `python3 scripts/verify_repository.py` — passed.
- `make verify` — passed.
- `cd chameleon && ../.venv/bin/python -m py_compile engine/layout/search.py tests/layout/test_search_ranking.py` — passed.
- `cd chameleon && ../.venv/bin/python -m engine.main` — exit 1 as expected for the mixed sample batch: Levels 1–2 `SUCCESS` with pairs; Level 3 `INCOMPLETE_SEARCH` with no pair.
- `cd chameleon && python -m engine.main` — exit 1 because the system interpreter lacks `jsonschema`; the project environment result above is the exercised engine evidence.
- `cd chameleon && docker buildx build --platform linux/amd64 --load -t chameleon-stage1 .` — attempted but blocked before build because the Docker daemon was unavailable; no Docker run was performed.

The focused tests exercise hard serialized integer validation and the dominant-media/dominant-copy half-even regression. Docker/native-amd64 evidence remains unverified in this environment.

## Historical observed integration commands

| Command | Result |
| --- | --- |
| `cd chameleon && ../.venv/bin/python -m unittest tests.geometry.test_issue23_rounding tests.layout.test_issue23_search_evidence tests.renderer.test_issue23_artifact_corpus -v` | 10 tests passed. |
| `make test` | 190 project tests and 47 review-capsule tests passed. |
| `python3 scripts/verify_repository.py` | Passed. |
| `make verify` | Passed. |
| `../.venv/bin/python -m py_compile chameleon/tests/geometry/test_issue23_rounding.py chameleon/tests/layout/test_issue23_search_evidence.py chameleon/tests/renderer/test_issue23_artifact_corpus.py` | Passed. |
| `cd chameleon && python -m engine.main` | Not runnable in the system interpreter: `jsonschema` is not installed. |
| `cd chameleon && ../.venv/bin/python -m engine.main` | Exit 1 as expected for the mixed sample batch: Levels 1–2 `SUCCESS` with pairs; Level 3 `INCOMPLETE_SEARCH` with no pair. |
| `cd chameleon && docker buildx build --platform linux/amd64 --load -t chameleon-stage1 .` | Passed with the existing `FromPlatformFlagConstDisallowed` warning. |
| `cd chameleon && docker run --rm --network none -v "$PWD/input:/app/input" -v "$PWD/output:/app/output" chameleon-stage1` | Exit 1 under arm64-host amd64 emulation: Level 1 `SUCCESS` in 6.12s, Level 2 `SUCCESS` in 9.56s, Level 3 `INCOMPLETE_SEARCH`; no Level 3 pair. |

The Docker run is supplemental evidence only. Native-amd64 runtime, container RSS, clean-cache reproducibility, and cross-platform hash parity remain unverified. The existing successful local artifact hashes and image/runtime observations remain in [`08-qualification-evidence.md`](08-qualification-evidence.md); hard validation is not inferred from the warning-only self-check or from soft ranking scores.
