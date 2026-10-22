# Implementation roadmap and review report

**Status:** Execution plan; `PROJECT_CONTRACT.md` and Accepted ADRs remain authoritative. Gate 1 is cleared, Tickets 01–08 have bounded implementation/evidence, and Issue #61 now produces a hard-valid public Level 3 JSON/PNG pair in local integration tests using ADR-010 through ADR-012. The issue-linked PR's maintainer review and native-amd64 CI remain pending; held-out evaluation, cross-platform parity, full packaging closure, and organizer-controlled qualification remain unverified.

## Issue #16 reconciliation

The current implementation is not the pre-implementation plan described by several historical paragraphs below. F-01/F-02/F-03/F-04/F-07 have bounded local evidence at their authoritative seams; F-05 has local renderer/artifact seam evidence but not complete platform qualification; F-06 has native-amd64 CI observations, while cross-platform parity, full packaging closure, and broad held-out evaluation remain open. See the audit matrix and exact paths in [`STATUS.md`](STATUS.md). No warning-only check, soft score, arm64 emulation, or missing artifact is contract or qualification evidence.

Decision ratification is complete, including the PDF-grounded Issue #61 changes in ADR-010 through ADR-012. The public Level 3 sample-pass behavior is now implemented and locally evidenced; do not claim issue completion until its PR is reviewed/merged, or claim official scoring, broad held-out evaluation, cross-platform parity, or complete organizer runtime qualification without corresponding evidence.

### Gate 0 — Contract and evidence (complete; documentation only)

- Read `PROJECT_CONTRACT.md`, ADR-001 through ADR-012, the pinned schema, and `DEPENDENCY_EVIDENCE.md`.
- Record the accepted failure, numeric/geometry, typography, and initial-search decisions without adding wire fields or weakening hard constraints.
- Keep every unresolved external fact visible: hidden-task feasibility and missing-output scoring, scorer thresholds, target catalogue, M5 Pro resources, model limits, final fonts/assets/licensing, native amd64 qualification, and Adobe deployment.
- Treat the three shipped samples plus the contract fixtures as regression inputs, not as the whole hidden-test universe.
- Gate 0 acceptance records decisions only; it is not implementation or qualification evidence.

### Gate 1 — Renderer and validator qualification (COMPLETE)

- Build the pinned `linux/amd64` environment and prove local fonts/assets work with `--network none`.
- Establish the semantic validator around identity/order/fixed fields, finite integer geometry, rotated AABB, exact foreground image ratio, group/overlap policy, text bounds, and missing-asset preservation.
- Preserve numeric JSON tokens at ingress before any binary-float conversion; use exact integer/decimal parse hooks, reject non-finite constants, and test decimal and exponent cases through the runner/geometry seam.
- Close the adapter gaps already recorded in `STATUS.md`: end-exclusive style runs, style-aware/letter-spaced measurement, `max_lines`/height, and renderer goldens.
- Add synthetic fixtures for empty/no-background/single/degenerate/rotated/long-copy/missing-asset/foreground-`fill` cases.
- Conformance work may touch the task orchestrator and renderer adapter as well as validator-facing paths; it must preserve the public wire schema and Stage 1 mutability boundary.
- Acceptance: no candidate reaches soft scoring before hard validation; repeated renders are deterministic. **Gate 1 acceptance achieved** - see `STATUS.md` for verification evidence.

### Gate 2 — Safe geometry baseline (COMPLETE)

- Preserve IDs, array order, types, fixed fields, source groups, and missing asset records.
- Classify only the contract-defined full-canvas background and source-bleed decoration exemptions.
- Place groups as rigid units; scale foreground images isotropically; round once; recompute rotated bounds and ratios after rounding.
- Apply one round-half-even serialization step and validate serialized integers, reduced image-ratio lattice, rotated AABB containment, positive-area overlap, deterministic background tie-break, and same-side source bleed.
- Acceptance: Level 1 plus geometry fixtures pass structural validation. The baseline must never hide or drop an element. **Gate 2 acceptance achieved** - Ticket 05 Level 1 solver complete with 20 layout tests passing.

### Gate 3 — Source-aware routing (Ticket 06 complete; Ticket 07 public sample implementation ready for review)

- Infer roles from multiple signals without fixed z-index/coverage thresholds.
- Derive slots from target proportions, source group extents, measured text, and image ratios. Never reserve fixed logo/hero/CTA pixels.
- Acceptance: Ticket 06 implementation, focused/full tests, and Level 2 sample evidence are recorded and merged. The Issue #61 implementation now produces the hard-valid Level 3 sample pair locally with source identities, groups, image ratios, overlap, and renderer checks intact; PR review and native-amd64 CI evidence for this change remain pending.

### Gate 4 — Typography and candidate generation

- Measure the supplied font bytes with the same Skia/cr-renderer revision used for the PNG.
- Generate Unicode-safe line maps from UAX #29 clusters and UAX #14 opportunities using latest-fitting greedy breaks; preserve explicit and empty lines, code-point `[start,end)` style runs, and no-rewrite behavior.
- Search the largest feasible font size per candidate while preserving content, style runs, line height, spacing, and source hierarchy.
- Reject actual glyph overflow and unreadable candidates; do not solve typography by truncation, copy edits, font substitution, or oversized concealment boxes.
- Reject `max_lines`, line-box-height, actual glyph-bound, and unbreakable-segment overflow; rasterize declared rectangle/ellipse strokes inside their boxes without changing source fields.
- Acceptance: style-run boundary, long-copy, line-height, spacing, and contrast fixtures match rendered bounds.

### Gate 5 — Candidate ranking and solver choice

- Start with the accepted bounded structured search: at most three source-derived variants per each of four topology families, renderer-in-loop hard validation, and fixed-point ranking. Ticket 06 MUST remain deterministic and MUST NOT add CP-SAT, OR-Tools, models, or model weights/runtime; any later solver-dependency proposal requires separate authority and change control.
- Represent only source-separated pairs in no-overlap constraints. Keep intentional overlaps and rigid groups out of universal separation constraints.
- Rank only hard-valid candidates using alignment, even spacing, hierarchy, balance, whitespace, readability, and source relationship preservation. A cutoff with no hard-valid candidate is `INCOMPLETE_SEARCH`, never proven infeasibility.
- Acceptance: the current bounded tree records hard-validation reports and reproducible fixed-point candidate scores in `Docs/STATUS.md` and the held-out-style evaluator. Native-amd64 F-06 evidence is recorded for its prior revision; issue-branch native-amd64 CI, official/native cross-platform, and organizer-held-out qualification remain pending.

### Gate 6 — Offline submission qualification

- Build the pinned amd64 image from a clean cache, run with `--network none`, and record package/source hashes, native-library imports, render hashes, and failure behavior.
- Exercise all three sample levels, the fixture matrix, and catalogue-sized synthetic targets. Test on native amd64 and Apple Silicon Buildx output.
- Use the accepted failure statuses and pair-publication rule: stage JSON and PNG together, publish neither on failure, continue independent tasks where possible, and return a nonzero aggregate status if any task fails or does not commit both artifacts.
- Confirm `INFEASIBLE_LAYOUT` and `INCOMPLETE_SEARCH` tasks fail closed with the documented reason rather than emitting dishonest JSON/PNG or a failure envelope.
- Acceptance: a clean rebuild reproduces the same contract artifacts and no runtime download occurs.

### Gate 7 — Finale product layer

- Keep the Stage 1 engine stable. Build the Adobe Express add-on only after the engine has hard-valid outputs and a stable serialized contract.
- Add candidate carousel, pinning, copy/font experiments, and reduced previews only as explicit user-controlled finale objects.
- Validate that any item labeled Stage 1 still passes the same validator; never route reduced or rewritten previews through the Stage 1 output path.

## Score-maximizing strategy

The reliable path to a strong submission is not a large model or a one-sample demo:

1. Eliminate disqualifying structural failures first; a beautiful invalid PNG cannot recover its JSON score.
2. Preserve the source's hierarchy and relationships with boring deterministic rules before optimizing aesthetics.
3. Use renderer-in-the-loop validation so glyph overflow, fit preprocessing, rotation, and missing assets are judged as rendered, not estimated.
4. Keep multiple topology candidates alive for extreme ratios; do not commit from aspect ratio alone.
5. Build adversarial fixtures that target every documented failure mode and never hand-tune to the three public samples.
6. Prefer a smaller deterministic dependency footprint over an unverified model. Keep Ticket 06 role inference deterministic; do not add learned models or model weights/runtime to the Stage 1 engine.
7. Demonstrate the same engine path in the finale; product controls must not fork the Stage 1 truth.

The design review establishes the intended deterministic Stage 1 engine contract. Implementation must return the source element set unchanged, preserve intentional relationships, and adapt geometry to the target canvas without generating pixels or rewriting content. This paragraph's former statement that no implementation was claimed predates Issue #61; the public Level 3 pair is now locally evidenced in `STATUS.md`, while official qualification remains unverified.

The original design review identified five corrections; all are resolved or superseded in the current documents above. The list is retained as historical rationale, not as an outstanding checklist:

- `group_id` is the primary grouping signal. Geometric containment is a fallback for ungrouped elements.
- Source overlaps are evidence of intent. The solver separates only pairs that did not overlap in the source, while keeping text off busy image regions.
- The layout router needs four regimes: near-isomorphic, column pivot, horizontal ribbon, and vertical re-stack for wide-to-tall targets.
- Slot dimensions and text hierarchy come from source proportions, measured content, and target dimensions. Fixed pixel slots and invented font-size ratios are not valid.
- Stage 1 cannot shed elements, rewrite copy, change fixed font attributes, or synthesize image content. These remain outside the automated path.

The pinned `cr-renderer` source also changes the typography assumptions in the earlier proposal. It renders explicit `lineMap` entries and does not insert width-based line breaks. `lineHeight` multiplies the font size for each line's vertical offset, `letterSpacing` is added between glyph positions, images are drawn by stretching the full source rectangle into the destination rectangle, and rotation is applied around the element's local center. The relevant immutable sources are [schema.py](https://raw.githubusercontent.com/CyberAgentAILab/cr-renderer/a17e1fb9a732959dd6c21ae168d5ee09d74bd64f/src/cr_renderer/schema.py), [text_utils.py](https://raw.githubusercontent.com/CyberAgentAILab/cr-renderer/a17e1fb9a732959dd6c21ae168d5ee09d74bd64f/src/cr_renderer/text_utils.py), and [renderer.py](https://raw.githubusercontent.com/CyberAgentAILab/cr-renderer/a17e1fb9a732959dd6c21ae168d5ee09d74bd64f/src/cr_renderer/renderer.py).

The following review notes are retained for rationale and are subordinate to the ratified contract above. The repository now includes schema, dependency, fixture, contract, renderer, validator, runner, geometry, and bounded Level 1 implementation work; full architecture implementation and qualification remain unclaimed.

## Historical review notes (non-normative)

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

- Use the bounded structured search as the Stage 1 primary path, with intentional source overlaps represented as allowed relationships. CP-SAT is deferred; Kiwi is not a current dependency. Either requires measured benefit, explicit deterministic behavior, and an accepted dependency decision before implementation.
- Include alignment and even-spacing terms in the objective.
- Render every candidate, reject hard-constraint failures, and select the highest-scoring valid result.
- Exercise the engine with synthetic designs and catalogue sizes such as Instagram Post, Instagram Story, YouTube Thumbnail, Leaderboard, Poster, and Facebook cover.
- Build for `linux/amd64` and run the container with `--network none` only after the offline path is complete.

## Historical review findings (resolved or superseded)

| Document | Original review finding |
| --- | --- |
| [Neuro-symbolic architecture](NEURO_SYMBOLIC_ARCHITECTURE.md) | Replace fixed role thresholds, containment-first grouping, three-regime routing, universal non-overlap, and mandatory Kiwi with source-aware rules. |
| [Typographic reflow and grouping](TYPOGRAPHIC_REFLOW_AND_GROUPING.md) | Document explicit renderer line maps, measured metrics, source hierarchy preservation, and `group_id` precedence. |
| [Mathematical constraints](MATHEMATICAL_CONSTRAINTS.md) | Add identity, fixed-property, rotated-bound, rounding, missing-asset, and source-overlap checks. |
| [Objective metrics](OBJECTIVE_EVALUATION_METRICS.md) | Treat Val, Ove, Ali, Bal, Occ, and Rea as internal proxies, not the judging rubric, and make overlap and contrast source-aware. |
| [Difficulty tiers](DIFFICULTY_TIERS_AND_FAILURE_MODES.md) | Remove fixed pixel slots and include vertical re-stack and adversarial edge cases. |
| [Computational layout solvers](COMPUTATIONAL_LAYOUT_SOLVERS.md) | Keep bounded structured search primary; keep CP-SAT and Kiwi deferred unless measured evidence and an accepted dependency decision justify them; score alignment and spacing. |
| [Hermetic runtime](HERMETIC_RUNTIME_ARCHITECTURE.md) | State the `linux/amd64` build target and separate offline requirements from unverified performance targets. |
| [Interactive finale](ADOBE_EXPRESS_INTERACTIVE_ADDON.md) | Keep shedding and copy revision explicitly outside Stage 1, with no zero-size or hidden-element workaround. |

The following phase matrix names implementation workstreams after Gate 1; these phases are not product stages and do not override current gate blockers.

## Phase matrix

| Phase | Main deliverable | Required evidence |
| --- | --- | --- |
| 1. Safe geometry baseline | Identity-preserving isotropic layout and missing-asset handling | Rotated bounds, integer rounding, image ratios, and source groups remain valid |
| 2. Role and archetype routing | Four layout regimes selected from source and target geometry | Wide, tall, square, and extreme-ratio synthetic cases |
| 3. Typography and candidates | Renderer-matched text sizing plus several valid layout candidates | Long copy, style runs, letter spacing, line height, and contrast checks |
| 4. Solver and validation | Hard-check rejection, soft-score ranking, and offline packaging | Catalogue-size harness, rendered PNG review, and Docker `--network none` run |
