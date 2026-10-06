# Hermetic container architecture and offline execution

Stage 1 must run without network access:

```text
docker run --rm --network none ...
```

The submission image targets `linux/amd64`. The build host may be different, but the image must contain every dependency needed by the runtime.

## Offline requirements

The engine:

- cannot call remote web services;
- cannot query third-party APIs at runtime;
- cannot download packages, model checkpoints, fonts, or assets while processing a task; and
- must receive runtime dependencies, brand fonts, and brand assets from the image. Mounted input and output paths carry task data and results only.

Brand fonts and supplied assets are inputs to the layout process and are baked into the image at build time. A missing asset reference must remain in the output record. The engine must not download it, add a replacement file, hide the element, or synthesize pixels.

The renderer may produce the scored PNG from the source elements. That is layout rendering, not permission to regenerate, redraw, inpaint, seam-carve, outpaint, or replace image content.

## Model and solver choices

A large multimodal model is not required for role inference or coordinate placement. It adds image, memory, and startup dependencies that are difficult to justify in an offline container. If an optional model is used, its weights and runtime must be baked into the image and its use must remain deterministic for the same input.

The core path can use local font measurement, image metadata, a role inference pass, CP-SAT or structured candidate search, and render validation. Kiwi is optional for cleanup after topology is fixed.

## Runtime safeguards

The container path must verify:

- exact element ids and count;
- fixed text and visual properties;
- rotated bounds after integer rounding;
- foreground image ratios, including `fit=fill`;
- source-aware overlap rules;
- text bounds from the actual renderer behavior;
- missing assets without replacement content; and
- identical behavior when network access is disabled.

Quality takes priority over an unverified latency target. Candidate generation may render several layouts, but it must reject hard failures before ranking them.

## Architecture comparison

| Architectural attribute | Remote or generative runtime | Hermetic deterministic engine |
| --- | --- | --- |
| Network access | Required or difficult to prove absent | Disabled with `--network none` |
| Runtime dependencies | May be fetched or resolved dynamically | Baked into the `linux/amd64` image |
| Pixel behavior | May synthesize or alter image content | Reuses the supplied assets |
| Geometry behavior | Can drift outside constraints | Checks identity, ratios, rotated bounds, and overlap |
| Candidate choice | Often opaque | Explicit archetypes, hard validation, and soft ranking |

The container is complete when a clean build produces an image that runs with no network and returns the same structural contract for mounted inputs.
