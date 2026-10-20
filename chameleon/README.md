# CHAMELEON — Stage 1 engine

This repository contains the bounded Stage 1 engine: contract validation,
renderer-gated layout candidates, deterministic ranking, and fail-closed
JSON/PNG publication. The public function is
`resize(source, target_canvas) -> target_design`; batch envelopes and
task-level artifact handling belong to the orchestrator. The behavioral source
of truth is `../Docs/PROJECT_CONTRACT.md`; Accepted ADRs and pinned dependency
evidence under `../Docs/` resolve ambiguities.

```
input:  a batch task envelope (source design + target canvas)
              |
              v
        orchestrator -> resize(source, target_canvas)
              |
              v
output: <task>_output.json  (design-shaped success output)
        <task>_output.png   (rendered success preview)

Both the JSON and the PNG are what get evaluated — see `RULES.md`.

## Repo layout

```
engine/
  resize.py        <- public resize(source, target_canvas) seam
  main.py           <- batch orchestrator and typed failure reporting
renderer/           <- integrated converter wrapping pinned cr-renderer
brand_kit/
  assets/           <- image files referenced by asset_id in the sample designs
  fonts/            <- font files matching the schema's font_family values
input/               <- drop task JSON files here for local testing (3 samples included)
output/              <- results land here
chameleon_design_schema_v0.9.json   <- full field-by-field spec for the design format
Dockerfile
RULES.md
```

## Quick start (no Docker needed for iterating on `resize()`)

Stage 1 targets Python 3.11 on `linux/amd64`; the local commands below are for development only.

```bash
pip install -r requirements.txt
python -m engine.main
```

This processes every `*.json` file in `input/` (the 3 sample designs are
already there — one per difficulty level). Successful tasks write an
`_output.json` and `_output.png` pair plus a hidden hash commit manifest
(`.<task>_output.commit`) into `output/`. The manifest is the pair-publication
gate: final files without a matching marker are uncommitted and consumers
must reject them. From the repository root, `make inspect` enforces this gate.

The bounded implementation is renderer-aware and evaluates a finite candidate
set before deterministic ranking. Unsupported or exhausted searches use the
typed failure protocol; source records are not rewritten and no compatibility
modules are required.

## What the self-check does (and doesn't do)

`main.py` runs a quick structural check after every task — same element
`id`s as the source, required fields present, nothing off-canvas. **This
is not the official scorer or the contract validator.** It exists to catch
obvious mistakes before you waste a submission on them. See `RULES.md` and
`../Docs/PROJECT_CONTRACT.md` for what's actually checked and graded.

The accepted failure protocol is defined by `../Docs/PROJECT_CONTRACT.md`:
failed tasks publish neither artifact, while successful JSON and PNG are
staged in a private task directory and exposed with a matching hidden commit
manifest; the aggregate process status is nonzero if any task fails. Do not
consume raw `_output.json` files while the runner is still executing. A
warning or written artifact is not conformance evidence until the contract
validator and publication gate accept it.
Read the warning; decide whether it identifies a real problem or, like the
Level 2 sample's intentionally corner-bleeding decorative circle, an expected
fixture case.

The hidden `.<stem>_output.commit` marker is written last with both artifact hashes; only marked pairs are committed results.

## The renderer

`main.py` calls `renderer/converter/convert.py`'s `render_design_to_png()`
(the integrated converter, wrapping the pinned `cr-renderer` revision)
to produce each task's PNG — already wired in, no setup needed. It reads
fonts/assets from `brand_kit/` and writes a real rendered preview, not a
placeholder. If the renderer import fails, that task reports
`RUNTIME_IO_FAILURE` and publishes no JSON/PNG pair. Install the pinned
dependencies from `requirements.txt` before running the engine.

## Docker (how you'll actually be run)

```bash
docker build --platform linux/amd64 -t my-chameleon-engine .
docker run --rm --network none \
  -v $(pwd)/input:/app/input \
  -v $(pwd)/output:/app/output \
  my-chameleon-engine
```

`--network none` and Python 3.11 on `linux/amd64` match the Stage 1 runtime
target: everything the engine needs must be installed at **build** time (add
it to `requirements.txt`), not fetched at run time. The initial search strategy
does not use a model; a future model would require a separate accepted
decision and immutable offline artifacts.

## Current qualification boundary

The bounded implementation covers the validated renderer and staged runner
paths, but it is not a complete qualification claim. Public Level 3 remains
typed `INCOMPLETE_SEARCH` when the bounded search cannot produce a hard-valid
candidate. Native-amd64 qualification, renderer/native parity, held-out
evaluation, and performance qualification remain open; an arm64-host
emulation run must not be presented as native-amd64 evidence.

## Source of truth

- `../Docs/PROJECT_CONTRACT.md` — ratified Stage 1 behavior and traceability
- `../Docs/DECISIONS/` — accepted rationale and rejected alternatives
- `../Docs/STATUS.md` — current implementation gaps and external blockers
- `chameleon_design_schema_v0.9.json` — ratified structural wire schema
- `RULES.md` / `FAQ.md` — organizer-facing clarifications aligned to the contract
