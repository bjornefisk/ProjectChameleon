# Implementation roadmap and review report

The design review establishes a deterministic Stage 1 engine. It must return the source element set unchanged, preserve intentional relationships, and adapt geometry to the target canvas without generating pixels or rewriting content.

The current documentation needs five corrections before implementation:

- `group_id` is the primary grouping signal. Geometric containment is a fallback for ungrouped elements.
- Source overlaps are evidence of intent. The solver separates only pairs that did not overlap in the source, while keeping text off busy image regions.
- The layout router needs four regimes: near-isomorphic, column pivot, horizontal ribbon, and vertical re-stack for wide-to-tall targets.
- Slot dimensions and text hierarchy come from source proportions, measured content, and target dimensions. Fixed pixel slots and invented font-size ratios are not valid.
- Stage 1 cannot shed elements, rewrite copy, change fixed font attributes, or synthesize image content. These remain outside the automated path.

The public `cr-renderer` source also changes the typography assumptions in the earlier proposal. It renders the explicit `lineMap` entries and does not insert width-based line breaks. `lineHeight` multiplies the font size for each line's vertical offset, `letterSpacing` is added between glyph positions, images are drawn by stretching the full source rectangle into the destination rectangle, and rotation is applied around the element's local center. The relevant source is [schema.py](https://raw.githubusercontent.com/CyberAgentAILab/cr-renderer/main/src/cr_renderer/schema.py), [text_utils.py](https://raw.githubusercontent.com/CyberAgentAILab/cr-renderer/main/src/cr_renderer/text_utils.py), and [renderer.py](https://raw.githubusercontent.com/CyberAgentAILab/cr-renderer/main/src/cr_renderer/renderer.py).

This review changed documentation only. The engine, sample renderer, Docker image, and output files were not run or modified.

## Proposed build order

### Phase 1: Safe geometry baseline

- Preserve element ids, count, order, and all fixed properties.
- Scale foreground images isotropically. Apply any permitted background crop through the task's `fit=cover` wrapper path, if present, rather than editing pixels.
- Keep every source group rigid, preserve source-intended overlaps, and handle ungrouped elements without divide-by-zero assumptions.
- Compute rotated axis-aligned bounds, round deliberately, and re-check containment after rounding.
- Preserve missing-asset elements without adding replacement files or hiding their records.

### Phase 2: Role inference and archetype routing

- Infer roles from z-index, opacity, fit, coverage, font-size ranking, group membership, and geometry. Do not require a particular z-index or coverage threshold for the background.
- Use aspect-ratio change to choose near-isomorphic, column-pivot, horizontal-ribbon, or vertical-re-stack layouts.
- Derive slots from canvas proportions, source relationships, and measured element content.

### Phase 3: Typography and candidate generation

- Measure the supplied font files and reproduce the renderer's explicit line behavior, line height, letter spacing, and style runs.
- Binary-search font size for each candidate slot while changing only font size and geometry.
- Preserve the source hierarchy rather than imposing a universal ratio. Check contrast against the actual background pixels below each text box.
- Generate several valid candidates with different hero and copy weights, then rank them by alignment, spacing, balance, hierarchy, whitespace, and readability.

### Phase 4: Constraint solving and validation

- Use CP-SAT or a structured slot search for small scenes, with intentional source overlaps represented as allowed relationships. Kiwi is optional for continuous cleanup after topology is fixed.
- Include alignment and even-spacing terms in the objective.
- Render every candidate, reject hard-constraint failures, and select the highest-scoring valid result.
- Exercise the engine with synthetic designs and catalogue sizes such as Instagram Post, Instagram Story, YouTube Thumbnail, Leaderboard, Poster, and Facebook cover.
- Build for `linux/amd64` and run the container with `--network none` only after the offline path is complete.

## Review findings by document

| Document | Required correction |
| --- | --- |
| [Neuro-symbolic architecture](NEURO_SYMBOLIC_ARCHITECTURE.md) | Replace fixed role thresholds, containment-first grouping, three-regime routing, universal non-overlap, and mandatory Kiwi with source-aware rules. |
| [Typographic reflow and grouping](TYPOGRAPHIC_REFLOW_AND_GROUPING.md) | Document explicit renderer line maps, measured metrics, source hierarchy preservation, and `group_id` precedence. |
| [Mathematical constraints](MATHEMATICAL_CONSTRAINTS.md) | Add identity, fixed-property, rotated-bound, rounding, missing-asset, and source-overlap checks. |
| [Objective metrics](OBJECTIVE_EVALUATION_METRICS.md) | Treat Val, Ove, Ali, Bal, Occ, and Rea as internal proxies, not the judging rubric, and make overlap and contrast source-aware. |
| [Difficulty tiers](DIFFICULTY_TIERS_AND_FAILURE_MODES.md) | Remove fixed pixel slots and include vertical re-stack and adversarial edge cases. |
| [Computational layout solvers](COMPUTATIONAL_LAYOUT_SOLVERS.md) | Make CP-SAT sufficient for small scenes, keep Kiwi optional, and score alignment and spacing. |
| [Hermetic runtime](HERMETIC_RUNTIME_ARCHITECTURE.md) | State the `linux/amd64` build target and separate offline requirements from unverified performance targets. |
| [Interactive finale](ADOBE_EXPRESS_INTERACTIVE_ADDON.md) | Keep shedding and copy revision explicitly outside Stage 1, with no zero-size or hidden-element workaround. |

## Phase matrix

| Phase | Main deliverable | Required evidence |
| --- | --- | --- |
| 1. Safe geometry baseline | Identity-preserving isotropic layout and missing-asset handling | Rotated bounds, integer rounding, image ratios, and source groups remain valid |
| 2. Role and archetype routing | Four layout regimes selected from source and target geometry | Wide, tall, square, and extreme-ratio synthetic cases |
| 3. Typography and candidates | Renderer-matched text sizing plus several valid layout candidates | Long copy, style runs, letter spacing, line height, and contrast checks |
| 4. Solver and validation | Hard-check rejection, soft-score ranking, and offline packaging | Catalogue-size harness, rendered PNG review, and Docker `--network none` run |
