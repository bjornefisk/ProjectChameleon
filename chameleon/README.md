# CHAMELEON — Stage 1 engine

This repository contains the bounded, deterministic Stage 1 retargeting engine.
It includes exact-ingress task loading, source-preserving topology search,
renderer-aware hard validation, fixed-point ranking, atomic output publication,
and offline Docker packaging. The public function is
`resize(source, target_canvas) -> target_design`; the batch envelope and
task-level artifact handling belong to the orchestrator.
The behavioral source of truth is `../Docs/PROJECT_CONTRACT.md`; Accepted ADRs
and the pinned dependency evidence under `../Docs/` resolve implementation
ambiguities.

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
  resize.py        <- implement your approach here
  main.py           <- orchestrator (batch envelope -> resize() -> artifacts; conformance work may require updates)
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

The current engine tries four bounded topology families — near-isomorphic,
column pivot, horizontal ribbon, and vertical restack — with at most three
source-derived variants per family. Candidates are serialized once, validated
against the structural and renderer contracts, and ranked only after hard
validation. A finite cutoff or incomplete topology attempt returns the typed
`INCOMPLETE_SEARCH` result rather than claiming infeasibility; an exhausted
finite work set may fail closed as `INFEASIBLE_LAYOUT`.

## What the self-check does (and doesn't do)

`main.py` runs the contract validator, renderer preflight, and artifact gate
before committing a pair. It verifies source identity and immutable fields,
finite integer mutable values, rotated bounds, ratios, groups, source
separation, renderer-aware text limits/glyph bounds, PNG dimensions/opacity,
missing-asset warning provenance, and adapter-backed pixel provenance. These
hard checks are separate from soft quality scores. A failed task publishes no
JSON/PNG pair and the aggregate process returns nonzero.

The hidden `.<stem>_output.commit` marker is written last with both artifact hashes; only marked pairs are committed results.

## The renderer

`main.py` calls `renderer/converter/convert.py`'s `render_design_to_png()`
(the integrated converter, wrapping the pinned `cr-renderer` revision)
to produce each task's PNG — already wired in, no setup needed. It reads
fonts/assets from `brand_kit/` and writes a real rendered preview, not a
placeholder. If the renderer import fails, that task reports
`RUNTIME_IO_FAILURE` and publishes no JSON/PNG pair. Install the pinned
dependencies from `requirements.txt` before running the engine.

Before either a solver candidate is accepted or a task pair is published, the
engine runs `engine.artifact.validate_artifact()` on the decoded PNG and the
serialized design. It verifies renderer-sized dimensions, an opaque canvas,
rendered bounds, pinned-renderer pixels, source-pixel provenance for exact
draws, and the deterministic missing-asset warning. A readable but
semantically wrong PNG is rejected and no JSON/PNG pair is committed. Contrast
and readability remain separate soft-quality concerns.

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

## Source of truth

- `../Docs/PROJECT_CONTRACT.md` — ratified Stage 1 behavior and traceability
- `../Docs/DECISIONS/` — accepted rationale and rejected alternatives
- `../Docs/STATUS.md` — current implementation gaps and external blockers
- `chameleon_design_schema_v0.9.json` — ratified structural wire schema
- `RULES.md` / `FAQ.md` — organizer-facing clarifications aligned to the contract
