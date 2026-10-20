# Ticket 08 qualification evidence

This record covers the integrated PR #15 review stack, not `main`.
Measurements ran on Darwin arm64 unless stated otherwise.

Integrated revisions:

- PR #15 base: `9ca4802`
- Ticket 07 dependency: `b11d7c3`
- Evidence code revision before these documentation edits: `c254cd6`

Evidence uses three dispositions:

- **Complete:** command ran and passed.
- **Incomplete:** implementation or target remains unresolved.
- **Unverified:** required environment or corpus was unavailable.

## Complete local checks

| Check | Command | Observed result |
| --- | --- | --- |
| Focused integration | `cd chameleon && ../.venv/bin/python -m unittest tests.layout.test_level1 tests.layout.test_level2 tests.layout.test_level3 tests.layout.test_search_ranking tests.layout.test_search_status -v` | 33 tests passed. |
| Repository wiring | `make verify` | Passed: repository governance and implementation wiring are consistent. |
| Syntax smoke | `cd chameleon && ../.venv/bin/python -m py_compile engine/layout/search.py engine/layout/ranking.py engine/resize.py engine/layout/near_isomorphic.py engine/layout/column_pivot.py engine/layout/horizontal_ribbon.py engine/layout/vertical_restack.py tests/layout/test_search_ranking.py tests/layout/test_search_status.py` | Passed. |
| Full project and review suites | `make test` | 187 project tests passed; 47 review tests passed. |

The integrated search now records exhaustion only when every attempted failure carries boolean `details["search_exhausted"] is True`.
Cutoffs, missing metadata, non-boolean metadata, and serialized-validation failures remain `INCOMPLETE_SEARCH`.

## Local sample smoke

The required system command was attempted:

```bash
cd chameleon
python -m engine.main
```

Observed: exit `127`; this workstation has no `python` executable.

The project interpreter then ran:

```bash
cd chameleon
../.venv/bin/python -m engine.main
```

Observed:

- Level 1: `SUCCESS`, JSON/PNG pair, `0.98s`.
- Level 2: `SUCCESS`, JSON/PNG pair, `0.97s`.
- Level 3: typed `INCOMPLETE_SEARCH`, no JSON/PNG pair.
- Process exit: `1`, because the batch contains the typed Level 3 failure.
- The warning-only Level 2 off-canvas self-check remains non-authoritative.

Repeated render hashing passed in `test_repeated_render_hash_is_deterministic`.
Held-out evaluation was not run because no held-out corpus is present in this checkout.

## Offline Docker smoke

Build command:

```bash
cd chameleon
docker buildx build --platform linux/amd64 --load -t chameleon-stage1 .
```

Observed: build passed with `FromPlatformFlagConstDisallowed`.
Docker identified image `sha256:3af4dfc796a0c0b737cb4b396aaeb1152ef396e44cf75917b06158359cdc8a32` as `linux/amd64`.
Reported image size was `303844764` bytes.

Run command:

```bash
cd chameleon
docker run --rm --network none \
  -v "$PWD/input:/app/input" -v "$PWD/output:/app/output" \
  chameleon-stage1
```

Observed on arm64-host amd64 emulation:

- Level 1: `SUCCESS`, JSON/PNG pair, `1.46s`.
- Level 2: `SUCCESS`, JSON/PNG pair, `1.43s`.
- Level 3: typed `INCOMPLETE_SEARCH`, no JSON/PNG pair.
- Container exit: `1`, because the batch contains the typed Level 3 failure.
- Docker emitted the expected platform mismatch warning and a fontconfig warning.

These are supplemental emulation results, not native-amd64 qualification.
Current output hashes:

```text
7b93fdfd44ad8e669c00aeae3a8e96931f85a761a60e67cc31d2bb02b10853b9  output/chameleon_sample_level1_warmup_output.json
172d23ca87020478d24568a603ba6f9deaf272629b59d73608789aca9789a85c  output/chameleon_sample_level1_warmup_output.png
df2a08c7c87f66837726bb98bf9ac896739d91766da12dbd3d35233a2a2bc8ec  output/chameleon_sample_level2_core_output.json
c75148701283de9f81663489ea09e76b7b757f36d0fefe110940b15644bc867f  output/chameleon_sample_level2_core_output.png
```

## Disposition

**Complete locally:**

- Four-topology bounded candidate generation.
- Role-specific variants.
- Independent variant dispatch after base failure.
- One final variant serialization and serialized hard validation.
- Renderer-gated candidate admission.
- Fixed-point ranking and deterministic tie-breaking.
- Solver PNG reuse for source-proportional candidates.
- Ticket 07/Ticket 08 resize ownership and solver export contract.
- Local full-suite, review-suite, and offline-container smoke evidence.

**Incomplete:**

- Public Level 3 sample still returns typed `INCOMPLETE_SEARCH`.
- No hard-valid Level 3 output is claimed.
- Emulated runtime does not establish native qualification.

**Unverified:**

- Native-amd64 runtime and peak RSS.
- Held-out evaluation and repeated held-out determinism.
- Native renderer/library parity and renderer goldens.

The previous duplicate base render residual is resolved in this stack.
Topology solvers expose rendered PNG bytes through a private collector.
Search reuses those bytes for source-proportional candidates and renders derived variants after geometry changes.
Central serialized validation remains before and after rendering.
