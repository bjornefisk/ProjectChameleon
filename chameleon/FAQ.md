# CHAMELEON — Frequently Asked Questions

*Adobe North America Hackathon 2026 — Pilot Edition*

---

## Input & Output

**Q1. What is the input?**

At the batch boundary, the runner receives one JSON envelope with two parts:

- **`source`** — the design you're resizing, at its original size. This is a `canvas` (width/height) plus a list of `elements`. Every element is one of three types — `text`, `image`, or `shape` — and carries a position, size, and type-specific properties (font, color, asset reference, etc.). There are no semantic labels telling you which element is "the headline" or "the logo" — you get `id`, `type`, and geometry, same as the actual engine will at evaluation time.
- **`target_canvas`** — the width and height you need to resize the source design into.

The public Stage 1 function is `resize(source, target_canvas) -> target_design`: it receives those two values separately and returns one flat design document. The batch orchestrator owns the envelope and task-level JSON/PNG artifact protocol. The engine's job is to return the same elements — same `id`s, same count, nothing added or removed — with updated position/size (and, for text, optionally font size) so the design fits `target_canvas`.

The full field-by-field spec is in the design schema (`chameleon_design_schema_v0.9.json`). Three worked examples, one per difficulty level, ship in the starter repo's **`input/`** folder:

| File | Elements | Resize |
|---|---|---|
| `chameleon_sample_level1_warmup.json` | 4 | 1080×1080 → 1080×1350 |
| `chameleon_sample_level2_core.json` | 11 | 1080×1080 → 1600×400 |
| `chameleon_sample_level3_advanced.json` | 17 | 1080×1350 → 728×90 |

Open one of these alongside the schema — it's the fastest way to see the shape of the data before writing any code against it.

**Q2. Why can't we give the JSON in Crello's format, since you're using cr-renderer to render it?**

Because Crello's format is a research dataset's internal storage layout, not something built for a hackathon spec to read:

- Coordinates are normalized `[0,1]` fractions of the canvas, not pixels.
- Categorical fields (element type, font, etc.) are stored as integer indices — you can't read them without the dataset's `features` object to decode them.
- Images are embedded, pre-rendered pixel crops baked into the data, not a reference to an asset file.
- Rotation is stored in units of π, not degrees.

That's plumbing specific to how CyberAgent happens to store the Crello dataset — it has nothing to do with the actual resize problem, and shouldn't cost you time figuring it out. Our schema keeps pixel coordinates, plain field names, and simple `asset_id` references so the *design problem* is what you're reading, not a dataset format.

cr-renderer is still doing the real rendering work under the hood — we convert our schema into Crello's format right before the render call. That conversion is on us, not something you need to touch.

---

## Rendering & local preview

**Q3. How do I render my output to see what it actually looks like?**

Use the integrated renderer already present in `renderer/converter/`. From the repository root:

```
cd chameleon
python -m engine.main
```

This processes each task in `input/`, writes `<task>_output.json` and
`<task>_output.png` through the local adapter for successful tasks, and
records a matching hidden `.<task>_output.commit` manifest. From the
repository root, `make inspect` uses that manifest to reject partial or stale
pairs; failed tasks follow the typed failure/artifact behavior in
`../Docs/PROJECT_CONTRACT.md`. The adapter reads fonts/assets from `brand_kit/`.

The upstream renderer consumes explicit internal line information, rotates around each element's local center, and maps the prepared image rectangle into the destination rectangle. The project adapter performs its own deterministic text preprocessing and `contain`/`cover`/`fill` handling. See `../Docs/PROJECT_CONTRACT.md` and `../Docs/DEPENDENCY_EVIDENCE.md` for the ratified behavior and known conformance gaps.

Missing assets remain in output record. Development renderer emits labeled placeholder and warning for missing file; placeholder is renderer diagnostic output, not asset replacement in engine response.

If renderer import fails, engine reports `RUNTIME_IO_FAILURE` and publishes no JSON/PNG pair. Install pinned dependencies before running `engine.main`.

**Q4. Where do I find the actual brand assets and fonts?**

They ship in the starter repo at:

- **`brand_kit/assets/`** — the image files referenced by `asset_id` in the sample JSONs: backgrounds, logo, product art.
- **`brand_kit/fonts/`** — the font files matching the `font_family` values used in the schema (`Solstice Serif`, `Solstice Sans`).

The integrated `renderer/converter` path resolves these folders automatically; any future engine or viewer code must use the same paths.

One deliberate exception: the Level 3 sample's `holiday_watermark` element references `solstice_holiday_badge_2025.png`, which is **not** in `brand_kit/assets/` — that's the intentional missing-asset case from Q1, not a packaging gap. Don't add it.

---

## Using the starter kit & submitting

**Q5. How do I use the starter kit, and how do I submit?**

**Using it:**

1. Install the pinned dependencies with Python 3.11 for the Stage 1 runtime: `pip install -r requirements.txt`.
2. Read `../Docs/PROJECT_CONTRACT.md` before changing `engine/resize.py`; `resize(source, target_canvas)` is the public solver function, while conformance work may also touch the task orchestrator and renderer adapter. The contract—not the baseline—defines behavior.
3. Run the starter pipeline locally: `python -m engine.main`. It processes the three sample task files and writes successful JSON/PNG pairs plus hidden commit manifests to `output/`; from the repository root, use `make inspect` rather than consuming raw JSON during execution.
4. Use the contract fixtures and the renderer conformance plan before claiming a behavior is supported. The current `resize.py` is intentionally nonconforming uniform stretch; failure behavior is defined by `../Docs/PROJECT_CONTRACT.md` and must not be inferred from starter output.
5. Qualify the actual Stage 1 image for Python 3.11 on `linux/amd64` with:
   ```
   docker buildx build --platform linux/amd64 -t my-chameleon-engine .
   docker run --rm --network none \
     -v $(pwd)/input:/app/input -v $(pwd)/output:/app/output \
     my-chameleon-engine
   ```
   `--network none` is part of the Stage 1 runtime contract.

The Stage 1 deliverable is the autonomous engine and its run instructions. An Adobe Express viewer/add-on is a separate finale concern under `Docs/DECISIONS/ADR-005-separate-stage-1-from-finale.md`.

Where to send it, and any submission form, will be announced separately ahead of the deadline — keep an eye out for that announcement. In the meantime, make sure your repo builds and runs cleanly in Docker (see step 5 above) so you're not doing that work last-minute once submission opens.