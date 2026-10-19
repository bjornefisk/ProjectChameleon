# Ticket 08 qualification evidence

This record belongs to Ticket 08 and is intentionally separate from the parallel Ticket 07 implementation. Measurements were taken on the local Darwin arm64 workstation unless stated otherwise.

## Implementation checks

| Check | Command | Observed result |
| --- | --- | --- |
| Focused integration | `cd chameleon && ../.venv/bin/python -m unittest tests.layout.test_level1 tests.layout.test_level2 tests.layout.test_search_ranking -v` | 20 tests, all passed. |
| Repository wiring | `make verify` | Passed: repository governance and implementation wiring are consistent. |
| Syntax smoke | `cd chameleon && ../.venv/bin/python -m py_compile engine/layout/search.py engine/layout/ranking.py engine/resize.py tests/layout/test_search_ranking.py` | Passed. |
| Full suite | `make test` | 178 tests; 4 errors, all in the uncommitted parallel Ticket 07 `tests.layout.test_level3` cases. No Ticket 08 focused test failed. The command stopped before its second `scripts.test_review_pr` unittest target. |
| PR review capsule | `.venv/bin/python -m unittest scripts.test_review_pr -v` | 47 tests, all passed. |

## Local public samples

Command: `cd chameleon && ../.venv/bin/python -m engine.main`

- The repository's exact `python -m engine.main` command was also attempted first and failed before application startup because the system interpreter lacks `jsonschema`. The project `.venv` command above is the successful local run.
- `chameleon_sample_level1_warmup.json`: `SUCCESS`; JSON/PNG pair published; `0.58s` in the batch run.
- `chameleon_sample_level2_core.json`: `SUCCESS`; JSON/PNG pair published; `0.95s` in the batch run; the existing non-authoritative self-check reported the known off-canvas `deco_circle_1` source-bleed warning.
- `chameleon_sample_level3_advanced.json`: typed `INCOMPLETE_SEARCH`; no JSON/PNG pair published; process exit was nonzero.
- The public run therefore is not a 100% pass and is not reported as one.

A separate in-process measurement around `resize()` reported:

| Sample | Status | Runtime | Process peak RSS |
| --- | --- | ---: | ---: |
| Level 1 warmup | `SUCCESS` | 1.077s | 223.6 MiB |
| Level 2 core | `SUCCESS` | 0.850s | 295.9 MiB |
| Level 3 advanced | `INCOMPLETE_SEARCH` | 0.147s | 296.3 MiB |

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

## Offline Docker smoke

Command:

```bash
docker buildx build --platform linux/amd64 --load -t chameleon-stage1 .
```

Observed: build passed. Buildx emitted the existing `FromPlatformFlagConstDisallowed` warning for the pinned `FROM --platform=linux/amd64` line. The loaded image reports `amd64/linux`, image ID `sha256:b97ebd731dfeb4532a74ec3d794c0d3b41ccecc97340f5eafeb3aaf1f5a29ce4`, and Docker's reported image size is `303846425` bytes (about 290 MiB), below the 8 GB ceiling.

Command:

```bash
docker run --rm --network none \
  -v "$PWD/input:/app/input" -v "$PWD/output:/app/output" \
  chameleon-stage1
```

Observed on this arm64 workstation under Docker amd64 emulation:

- `chameleon_sample_level1_warmup.json`: `SUCCESS`, JSON/PNG pair, `20.36s`.
- `chameleon_sample_level2_core.json`: `SUCCESS`, JSON/PNG pair, `32.93s`.
- `chameleon_sample_level3_advanced.json`: typed `INCOMPLETE_SEARCH`, no pair.
- The container exited `1` because the batch includes the typed Level 3 failure.
- Docker reported the expected `linux/amd64` versus host `linux/arm64/v8` emulation warning, plus a fontconfig warning from the base image.

The emulated container runtimes exceed the `<2.0s` target. Native-amd64 runtime and peak-memory qualification remain **unverified** on this arm64 host; these measurements must not be promoted to native-amd64 evidence. The local host RSS measurements above remain below the 500 MiB target, but they are not a substitute for container memory measurement.

## Integration residual

The existing topology solver APIs render their source-proportional response internally for text/layout validation and discard those PNG bytes. Ticket 08 renders each admitted response again at the centralized search gate so derived variants are gated and the actual PNG is available for scoring. Removing that duplicate base render requires changing the shared topology solver return contract, including the parallel Ticket 07-owned solvers; this PR leaves that ownership boundary intact. The duplicated base render is a documented performance risk, not a bypassed hard-validation step.
