# Issue 23 / F-07 evidence record

This record expands the normative regression evidence on the integrated Ticket 07/08 review tree. It does not change the Stage 1 wire schema, renderer dependency, or runtime policy; the focused issue #29 fix only corrects variant candidate serialization.

## Authority and scope

`PROJECT_CONTRACT.md` and Accepted ADR-001 through ADR-009 remain authoritative. The tests use the `chameleon-contract`, `chameleon-testing`, and `chameleon-review` skills:

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
| Topology and candidate variants | `chameleon/tests/layout/test_issue23_search_evidence.py` exercises source-derived variants, stable topology enumeration across representative targets, bounded candidate counts, and real hard-valid search admission. | Covers the bounded implementation present on this review tree; it does not widen the Ticket 07/08 candidate space. |
| Variant translation serialization | `chameleon/tests/layout/test_search_ranking.py::test_variant_translations_round_complete_coordinate_once` proves dominant-media and dominant-copy translations are applied exactly before one half-even serialization and then hard-validated. | Focused local evidence; native-amd64 parity and the broader held-out qualification remain unverified. |
| Ranking | The search evidence keeps hard-validation assertions separate from fixed-point quality/tie-break assertions; existing `test_search_ranking.py` remains the direct ranker regression suite. | Soft quality is never used to rescue a hard-invalid response. |
| Persisted artifact hashes | `chameleon/tests/fixtures/renderer_artifact_hashes.json` records document, packaged-asset, font-tree, pinned-renderer, PNG hash, dimensions, and warning provenance. `test_issue23_artifact_corpus.py` recomputes every value. | Hashes are tied to the checked-in local corpus and dependency revision, not an external scorer. |
| Renderer edge cases | `chameleon/tests/renderer/test_issue23_artifact_corpus.py` covers `contain`, `cover`, and `fill`, rotated geometry, negative letter spacing, right alignment, missing-asset diagnostics, and real PNG output. | Pixel behavior is qualified only for the pinned local adapter/runtime used by the test. |
| Runtime qualification | `Docs/IMPLEMENTATION/tickets/08-qualification-evidence.md` records local engine/Docker observations, JSON/PNG hashes, image size, host RSS, runtime, and the hard/soft distinction. | The arm64-host Docker run is supplemental; native-amd64 runtime, container RSS, clean-cache parity, and organizer-controlled limits remain unverified. |
| Held-out evaluation | `chameleon/tests/layout/test_heldout_evaluation.py` and [`08-heldout-evaluation.md`](08-heldout-evaluation.md) exercise a five-case authored corpus, repeated search/PNG signatures, hard-validation metrics, selected topology distribution, and runtime/RSS observations. | Local held-out-style evidence only; it is not an organizer-held-out benchmark or native-amd64 qualification. |

## Hard validation versus soft quality

Hard evidence consists of serialized `validate_response()` results, renderer conversion failures/warnings, expected PNG dimensions, source/asset/font provenance, and repeated byte hashes. Soft evidence consists of `QualityScore` values and deterministic rank ordering among candidates that already passed hard validation. No test treats a non-empty PNG, a copied response, or a proxy score as proof of contract validity.

## Current integration verification pointer

The current Issue #16 integration tree has run the focused suites, full 207-test suite, repository checks, held-out-style evaluator, and required local smoke sequence. Exact current results and unverified Docker/native boundaries are recorded in [`../../STATUS.md`](../../STATUS.md); the historical command records below remain provenance, not current counts.

## Disposition

This closes the reachable F-07 rounding/search/renderer evidence gaps on the current review tree and adds local held-out-style search evidence. It does not close official/native-amd64 qualification criteria or the public Level 3 sample-pass gap. Those require new evidence and must not be represented as completed by this change.

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
