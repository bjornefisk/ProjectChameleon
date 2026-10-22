# Ticket 08 qualification evidence

This is an earlier Ticket 08 evidence record, not qualification evidence for the Issue #61 branch. The native-amd64 run below is for commit `7f39a3e`, which predates Issue #61; branch-specific native-amd64 CI is pending. Local Darwin arm64 observations are identified separately.
The issue #23/F-07 normative evidence expansion is recorded separately in [`08-issue-23-evidence.md`](08-issue-23-evidence.md).

## Historical F-06 native-amd64 qualification for commit `7f39a3e`

The prior authoritative native qualification observation is GitHub Actions run [39481028806](https://github.com/bjornefisk/ProjectChameleon/actions/runs/39481028806), job `118829322922`, for commit `7f39a3e`. It built and loaded the pinned `linux/amd64` image, generated a non-empty SPDX SBOM with pinned Syft `v1.42.3`, loaded the packaged local assets and seven Solstice TTF files under `--network none`, and passed offline `cr_renderer`/Skia imports plus native `ldd` closure checks.

The runtime report measured `13.690699821` seconds wall time, `13.256694` user and `0.51691` system CPU seconds, `307076 KiB` maximum RSS, peak `3` Linux threads from procfs, and `2` available CPUs on Python `3.11.11`/`x86_64`. Level 1 and Level 2 returned `SUCCESS` with committed JSON/PNG pairs; Level 3 returned the contract-correct `INCOMPLETE_SEARCH` without a pair, so the aggregate process return code was the expected nonzero `1`. The loaded image was `sha256:6c555cecec045651bcadc3d5f28215ff9a5b9dd9257e367e3fe5e26975642d4b` and `886388964` bytes; the SBOM SHA-256 was `944833771af7e92d0bae7da85fe4924c54175ac1e2027c9dd3407b75acb9a0fc`.

Repeated native and clean-cache runs passed regular-file/symlink checks and matched the committed Level 1/2 artifact hashes recorded in [`../../DEPENDENCY_EVIDENCE.md`](../../DEPENDENCY_EVIDENCE.md). This establishes native-amd64 CI evidence for the pinned environment, not organizer-controlled resource limits or cross-platform hash parity. Apt package versions, a hash-locked wheelhouse, font licensing/metadata, organizer limits, and official scoring remain explicitly unverified.

## Historical Ticket 08 implementation checks
The measurements below are the earlier local Ticket 08 record. Current Issue #16 verification supersedes its counts for the integrated tree and is recorded in [`../../STATUS.md`](../../STATUS.md); no native-amd64 or official held-out qualification is inferred.
| Check | Command | Observed result |
| --- | --- | --- |
| Focused integration | `cd chameleon && ../.venv/bin/python -m unittest tests.layout.test_level1 tests.layout.test_level2 tests.layout.test_search_ranking -v` | 22 tests, all passed. |
| Repository wiring | `make verify` | Passed: repository governance and implementation wiring are consistent. |
| Syntax smoke | `cd chameleon && ../.venv/bin/python -m py_compile engine/layout/candidate.py engine/layout/search.py engine/layout/ranking.py engine/layout/near_isomorphic.py engine/layout/column_pivot.py engine/layout/horizontal_ribbon.py engine/layout/vertical_restack.py engine/layout/__init__.py engine/resize.py tests/layout/test_search_ranking.py tests/layout/test_near_isomorphic.py tests/layout/test_level2.py tests/layout/test_level3.py` | Passed. |
| Full suite | `make test` | 180 project tests and 47 review-capsule tests, all passed. |
| PR review capsule | `.venv/bin/python -m unittest scripts.test_review_pr -v` | 47 tests, all passed. |

## Local public samples

Command: `cd chameleon && ../.venv/bin/python -m engine.main`

- The repository's exact `python -m engine.main` command was also attempted first and failed before application startup because the system interpreter lacks `jsonschema`. The project `.venv` command above is the successful local run.
- `chameleon_sample_level1_warmup.json`: `SUCCESS`; JSON/PNG pair published; `0.45s` in the post-integration batch run.
- `chameleon_sample_level2_core.json`: `SUCCESS`; JSON/PNG pair published; `0.70s` in the post-integration batch run; the existing non-authoritative self-check reported the known off-canvas `deco_circle_1` source-bleed warning.
- The public run therefore is not a 100% pass and is not reported as one.

A separate in-process measurement around `resize()` reported:

| Sample | Status | Runtime | Process peak RSS |
| --- | --- | ---: | ---: |
| Level 1 warmup | `SUCCESS` | 0.918s | 212.5 MiB |
| Level 2 core | `SUCCESS` | 0.622s | 286.3 MiB |
| Level 3 advanced | `INCOMPLETE_SEARCH` | 0.414s | 287.3 MiB |

The RSS measurement uses macOS `ru_maxrss` bytes converted to MiB. It is host-process evidence, not native-amd64 container evidence.

The successful local artifact hashes from the batch run were:

```text
237a8a9eeeeae02ab954bf820fc0294b2501890097c390b3bb6c0c148d2744ba  output/chameleon_sample_level1_warmup_output.json
df2a08c7c87f66837726bb98bf9ac896739d91766da12dbd3d35233a2a2bc8ec  output/chameleon_sample_level2_core_output.json
71e0be9ea2ae55ab860100fed77ce870e1f531da8f74df05adb67414cf27cea0  output/chameleon_sample_level1_warmup_output.png
c75148701283de9f81663489ea09e76b7b757f36d0fefe110940b15644bc867f  output/chameleon_sample_level2_core_output.png
```

## Contract fixtures

The source-only fixtures were exercised with their own canvas as the target; `infeasible_target.json` and `image_ratio.json` supplied explicit task envelopes.

| Fixture | Observed status |
| --- | --- |
| `empty_design.json` | `SUCCESS` |
| `image_ratio.json` | `SUCCESS` |
| `infeasible_target.json` | typed `INCOMPLETE_SEARCH`; no output artifact |
| `minimal_design.json` | `SUCCESS` |
| `offcanvas_decoration.json` | `SUCCESS` |
| `style_run_boundary.json` | typed `INCOMPLETE_SEARCH`; no output artifact |

## Historical offline Docker smoke

Command:

```bash
docker buildx build --platform linux/amd64 --load -t chameleon-stage1 .
```

Observed: build passed. Buildx emitted the existing `FromPlatformFlagConstDisallowed` warning for the pinned `FROM --platform=linux/amd64` line. The loaded image reports `amd64/linux`, image ID `sha256:f6b7ad0326b6791b57ca0d4327f912df270dec0cb57d9f5daae8b5df43ff248a`, and Docker's reported image size is `303848897` bytes (about 290 MiB), below the 8 GB ceiling.

Command:

```bash
docker run --rm --network none \
  -v "$PWD/input:/app/input" -v "$PWD/output:/app/output" \
  chameleon-stage1
```

Observed on this arm64 workstation under Docker amd64 emulation:

- `chameleon_sample_level1_warmup.json`: `SUCCESS`, JSON/PNG pair, `6.03s`.
- `chameleon_sample_level2_core.json`: `SUCCESS`, JSON/PNG pair, `9.47s`.
- `chameleon_sample_level3_advanced.json`: typed `INCOMPLETE_SEARCH`, no pair.
- The container exited `1` because the batch includes the typed Level 3 failure.
- Docker reported the expected `linux/amd64` versus host `linux/arm64/v8` emulation warning, plus a fontconfig warning from the base image.

The post-integration emulated container runtimes still exceed the `<2.0s` target. This remains an explicit qualification blocker: native-amd64 runtime and peak-memory qualification are **unverified** on this arm64 host, and the arm64-host emulation measurements do not complete the ratified latency target. The local host RSS measurements above remain below the 500 MiB target, but they are not a substitute for container memory measurement.

## Issue #32 resolution

The shared topology hand-off now returns a `RenderedCandidate` containing the serialized response and the verified PNG bytes. The centralized search gate still calls `validate_response()` before admission and again at the render boundary:

- each topology/variant work item invokes its solver independently from source data;
- the source-proportional variant reuses its own solver PNG;
- every translated or emphasis-derived variant is rendered once by centralized search after independent generation;
- the selected candidate's stored PNG remains available to ranking; and
- the batch staging path still renders the selected serialized response for the final published artifact pair, which is a separate publication boundary.

`tests.layout.test_search_ranking.SearchRankingTests.test_each_variant_invokes_solver_and_derived_variants_render_once` proves independent variant dispatch and one centralized render for each derived variant. The `<2.0s` runtime target remains blocked by the explicit qualification exception above, not marked complete.
