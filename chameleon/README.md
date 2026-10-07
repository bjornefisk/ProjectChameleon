# CHAMELEON — starter repo

This is the scaffolding for the Stage 1 engine. It includes starter input
loading, output writing, rendering, and Docker packaging. The public function
is `resize(source, target_canvas) -> target_design`; the batch envelope and
task-level artifact handling belong to the orchestrator. `engine/resize.py` is
the starter baseline entry point, but conformance work MAY touch the
orchestrator and renderer adapter as required by the contract.
The behavioral source of truth is `../Docs/PROJECT_CONTRACT.md`; Accepted ADRs and the pinned dependency evidence under `../Docs/` resolve ambiguities that this starter README does not.

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
`_output.json` and `_output.png` pair into `output/`; see the contract for
typed failure statuses and failed-task artifact behavior.

The included baseline is a **uniform stretch** — deliberately the wrong
approach (see the main brief: "a naive program stretches the picture; a
good one moves the furniture"). It's there so the pipeline runs on day
one. Run it once, look at `output/*_output.png`, and you'll see exactly
why it's not good enough — that's the point. Replace the body of
`resize()` in `engine/resize.py`, not just its constants.

## What the self-check does (and doesn't do)

`main.py` runs a quick structural check after every task — same element
`id`s as the source, required fields present, nothing off-canvas. **This
is not the official scorer or the contract validator.** It exists to catch
obvious mistakes before you waste a submission on them. See `RULES.md` and
`../Docs/PROJECT_CONTRACT.md` for what's actually checked and graded.

The accepted failure protocol is defined by `../Docs/PROJECT_CONTRACT.md`:
failed tasks publish neither artifact, while successful JSON and PNG are
staged and committed as one logical pair; the aggregate process status is
nonzero if any task fails. The starter baseline may not yet implement every
accepted rule, so a warning or written artifact is not conformance evidence.
Read the warning; decide whether it identifies a real problem or, like the
Level 2 sample's intentionally corner-bleeding decorative circle, an expected
fixture case.

## The renderer

`main.py` calls `renderer/converter/convert.py`'s `render_design_to_png()`
(the integrated converter, wrapping the pinned `cr-renderer` revision)
to produce each task's PNG — already wired in, no setup needed. It reads
fonts/assets from `brand_kit/` and writes a real rendered preview, not a
placeholder. If you ever see plain labeled boxes instead of real text and
images in `output/*.png`, that means the import in `main.py` failed (e.g.
`cr-renderer` didn't install — check `requirements.txt` installed cleanly)
and it silently fell back to the box-and-label placeholder; don't judge
your layout quality by that fallback.

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
