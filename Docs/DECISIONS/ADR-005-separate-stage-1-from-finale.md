# ADR-005: Separate autonomous Stage 1 behavior from finale interaction

## Status

Accepted

## Date

2026-10-06

## Context

The challenge describes an offline, automatically scored engine first and an open-ended Adobe Express add-on finale later. Existing FAQ text incorrectly presents a viewer add-on as part of the Stage 1 submission, while the brief places candidate selection, pinning, reduced previews, copy revision, and font substitution outside the automated path.

## Decision

Stage 1 consists of the autonomous offline engine, its contract, runtime image, and run instructions. It returns every source element with fixed source content/materials and only the permitted geometry/font-size changes.

The finale is a separate Adobe Express product layer. It MAY offer candidate selection, user pinning, copy alternatives, font substitution, or a reduced composition as explicitly separate user-controlled interactions. Any candidate labeled as a Stage 1 output must still satisfy the Stage 1 contract. Reduced or copy-altered previews are never silently passed off as Stage 1 responses. Image regeneration, redrawing, replacement, inpainting, seam carving, and outpainting are prohibited in both stages.

### Finale integration architecture
For the live finale showcase at Adobe HQ, the Express add-on frontend runs as an iframe in the Express client via the `@adobe/express-add-on-sdk`. The Stage 1 engine will be exposed as a lightweight local HTTP service (e.g. FastAPI/Flask on `localhost`) or WebAssembly module that accepts the active canvas JSON and returns the resized design document, allowing the add-on to update the user's canvas in real time.
## Alternatives considered

### Require a viewer add-on in Stage 1

Rejected for the current contract. The challenge defines Stage 1 as a service that receives input and returns output; no viewer API is specified. A viewer can be developed independently without changing the scored engine contract.

### Allow shedding or copy edits in Stage 1

Rejected. Automated structural scoring cannot treat a changed design as the same element set, and the brief explicitly reserves those experiments for the finale.

### Treat finale controls as hidden engine inputs

Rejected. Manual decisions would violate autonomous Stage 1 behavior and make results non-reproducible.

## Consequences

- No Adobe SDK dependency is needed for the Stage 1 image.
- Finale architecture documents remain proposals until an add-on repository and manifest are created.
- Adobe Express API verification is recorded as external evidence, not as a Stage 1 implementation requirement.
- Product demos must label exploratory reduced/copy-altered candidates separately from contract-conforming results.

## Affected files/schema fields

- `Docs/FINAL_ARCHITECTURE.md` finale boundary
- `chameleon/FAQ.md` and `chameleon/README.md`
- `content`, `font_family`, `font_weight`, `font_style`, `color`, `style_runs`, `asset_id`, and element identity fields

## Required validation tests

- Verify Stage 1 output preserves all source IDs, content, font attributes, assets, and count.
- Verify no Stage 1 code path accepts user pinning, shedding, copy rewriting, or font substitution.
- In a future add-on, validate that altered/reduced previews are separate objects and that any displayed Stage 1 candidate passes the same validator.
