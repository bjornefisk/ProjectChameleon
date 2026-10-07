# Hermetic container architecture and offline execution

> **Authority Notice:** This document is architectural guidance. The binding Stage 1 behavioral contract is ratified in [PROJECT_CONTRACT.md](PROJECT_CONTRACT.md) and Accepted [ADRs](DECISIONS/). In any conflict, the contract and ADRs govern.

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

## Model, solver, and resource profile

Stage 1 runs CPU-only inside the `linux/amd64` Docker container under Rosetta 2 translation on the host Apple M5 Pro machine, without GPU passthrough. The engine operates with a 0 MB neural weight footprint, eliminating model download, cold start, and memory bloat. The runtime budgets for $\le$ 8 CPU threads, $\le$ 8 GB RAM, and a Docker image under 8 GB.

The primary solver is a bounded structured candidate search across four topology families. OR-Tools CP-SAT and local models are deferred and require empirical justification and an accepted ADR (ADR-004, ADR-009).
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

The container is complete when a clean build produces an image that runs with `--network none`, executes within the CPU/RAM budget, commits JSON and PNG as an atomic logical pair on success (ADR-006), and returns the same structural contract for mounted inputs.
