# Project Chameleon: Autonomous Layout Reflow Engine

Adobe University Hackathon 2026 | Stage 1 submission

Project Chameleon moves a structured design to a new canvas while preserving every source record, ID, order, text string, asset reference, and fixed style field. It changes the target canvas, element geometry, and text size only. It uses bounded deterministic search, not neural or generative models, model weights, CP-SAT, or OR-Tools. The engine does not create or change copy or regenerate, redraw, or replace source image assets. The renderer makes a new PNG from the existing design records.

## How it works

The engine infers roles and relationships, then searches four layout patterns:

1. Near-isomorphic: keep the source arrangement when the target shape permits.
2. Column pivot: move related groups into columns for wider canvases.
3. Horizontal ribbon: arrange groups across wide banners.
4. Vertical restack: arrange groups down tall canvases.

Each pattern has at most three source-derived variants, for no more than twelve initial candidates. For an inferred dense banner on a target narrower than 350 pixels or shorter than 300 pixels, a bounded compact-grid fallback can run inside an existing ribbon or restack attempt. It groups elements in two or three columns, or full-width rows for narrow and tall targets. It adds no fifth pattern and does not increase the twelve-candidate limit.

Candidates are serialized once, checked against the hard geometry and identity rules, and rendered through the pinned adapter. Skia and the renderer measure text and rendered bounds. Only candidates that pass these checks receive a fixed-point quality score. Scores use deterministic scaled integers and stable tie-breaks; they rank valid candidates but never rescue an invalid one.

## Rules the output must pass

- Identity: preserve every source element, ID, order, type, text, asset reference, and immutable field.
- Image proportions: preserve each positive-area foreground image's exact integer ratio. For a reduced source ratio `p:q`, valid output dimensions are `(k*p, k*q)` for positive integer `k`.
- Rigid groups: use one shared scale and translation for every group member. Round once with round-half-even, so exact ties go to the nearest even integer. Validate the final integer values against the shared transform.
- Text: preserve copy and all fixed font fields; only `font_size` may change. Check Skia-measured letter bounds, line count, and line height after serialization. Reject clipping or overflow rather than editing copy.
- Assets: keep source IDs and pixels. A missing asset may show a labeled diagnostic placeholder in the PNG and produce a warning; the placeholder never replaces the source reference.
- Publication: stage and validate JSON and PNG together. A hash manifest commits the pair. Failures publish neither artifact.

## Ranking and trade-offs

The score favors readable text, contrast, hierarchy, alignment, spacing, balance, whitespace, and source relationships. Wide-banner preferences favor a headline at least as large as the CTA and a CTA at least as large as grouped badge labels; a larger headline than CTA receives an extra preference. These are soft preferences, not hard size rules. There is no universal minimum font size, and the score does not require CTA text to be larger than supporting copy.

The search can fall back only among its bounded generated candidates. It does not promise coverage of every possible layout. The walkthrough records current-main sample timings; the measured local run is above 1.5 seconds per task and is not platform qualification evidence.

The bundled font files are Lora and Poppins stand-ins. Stage 1 preserves the source font family and other fixed font fields, may adjust `font_size`, and does not substitute a font. Final Adobe/Solstice font identity and redistribution permission remain unverified.

## Run locally

Use Python 3.11. From the repository root:

```bash
make setup
source .venv/bin/activate
cd chameleon
python -m engine.main
```

The runner reads task JSON files from `chameleon/input/`. Successful tasks write a design, rendered PNG, and hidden commit manifest in `chameleon/output/`. The process exits nonzero if any task fails.

## Run the Stage 1 container

Prepare the verified dependency wheelhouse from the repository root, then build and run the amd64 image:

```bash
make prepare-dependencies
cd chameleon
docker build --platform linux/amd64 -t chameleon-stage1 .
docker run --rm --network none --platform linux/amd64 \
  -v "$(pwd)/input:/app/input:ro" \
  -v "$(pwd)/output:/app/output" \
  chameleon-stage1
```

On Apple Silicon, `make docker-build` uses Buildx and loads the amd64 image into the local Docker image store. Emulated runs are slower than native amd64 and do not qualify the native platform.

## Further reading

- [Stage 1 contract](Docs/PROJECT_CONTRACT.md)
- [Current status and evidence](Docs/STATUS.md)
- [Submission packet](Docs/SUBMISSION_PACKET.md)
- [Presentation outline](Docs/PRESENTATION.md)
- [Final architecture](Docs/FINAL_ARCHITECTURE.md)
- [Dependency evidence](Docs/DEPENDENCY_EVIDENCE.md)