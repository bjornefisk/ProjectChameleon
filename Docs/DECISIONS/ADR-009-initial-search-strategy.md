# ADR-009: Select the initial deterministic search strategy

## Status

Accepted — pre-implementation contract decision. This ADR ratifies the initial deterministic Stage 1 search strategy for future implementation. It is documentation-only: acceptance does not claim that search, renderer validation, dependencies, model artifacts, or runtime behavior is implemented or qualified, and it does not authorize code changes by itself.

## Date

2026-10-06

## Context

The ratified Stage 1 contract defines what a hard-valid output must preserve but intentionally does not require a particular layout algorithm. Existing architecture notes describe both structured archetype search and possible CP-SAT/model paths. ADR-004 explicitly keeps OR-Tools and model runtimes out of the current dependency baseline.

Stage 1 must preserve source identity, fixed properties, image ratios, groups, intentional overlap, text, and renderer semantics before optimizing visual preferences. A solver that scores a proxy before rendering can select a structurally invalid or unreadable result. Conversely, a large model or unconstrained optimizer would add offline packaging, determinism, and resource questions before the repository has evidence that it improves hidden-case coverage.

The existing architecture identifies four useful regimes—near-isomorphic, column pivot, horizontal ribbon, and vertical re-stack—and recommends renderer-in-loop validation. This ADR turns those research recommendations into a bounded initial search default without making them current implementation behavior.

### Authority classification

- **Ratified current contract:** `Docs/PROJECT_CONTRACT.md` §§5–9, ADR-002, ADR-003, and ADR-004. These fix mutable fields, hard validation, renderer authority, fail-closed behavior, offline `linux/amd64` execution, and the absence of a current model/OR-Tools dependency.
- **Accepted internal contract decision:** deterministic multi-signal role inference, four topology families, at most three source-derived variants per family, renderer-in-loop hard validation, fixed-point ranking, and the future solver gate below are ratified defaults for future implementation. They remain unimplemented until the relevant work is completed and evidenced.
- **Externally unverified organizer fact:** hidden-task feasibility, scorer handling of failed tasks, official score thresholds and target catalogue, exact M5 Pro resources/model limits, final fonts/assets/licensing, native `amd64` qualification, and Adobe Express deployment details remain outside the repository's authority.

## Decision

### 1. Start with bounded structured search

The initial algorithm MUST be a deterministic structured candidate search, not a model or CP-SAT dependency. It must:

1. parse and semantically validate the input;
2. infer roles, groups, source-overlap relationships, backgrounds, bleed decorations, and measured content requirements from contract data;
3. generate a bounded set of topology/slot candidates;
4. serialize each candidate using the ratified numeric rules in ADR-007;
5. render each candidate through the pinned adapter and apply the hard validator, including the ratified typography rules in ADR-008; and
6. rank only candidates that pass every hard check.

No soft proxy score may rescue a hard-invalid candidate. No candidate may shed, hide, replace, or rewrite a source record in order to improve its score.

### 1b. Performance and resource budget targets

- **Zero model weight footprint (0 MB):** The engine operates as a 100% deterministic symbolic solver without neural weights, eliminating model loading time and GPU dependencies.
- **Execution speed:** The solver targets < 2.0 seconds per design on CPU (under Rosetta 2 x86 emulation on Apple Silicon), well inside any evaluation timeout.
- **Memory footprint:** Resident memory for the solver pipeline stays under 500 MB RAM, leaving headroom under the 8 GB container ceiling.
- **Reproducibility:** Two runs on the exact same input task JSON produce identical serialized output coordinates and identical rendered preview PNG bytes.
### 2. Use deterministic multi-signal role and relationship inference

Role inference must be inspectable and stable for identical input. Use a fixed ordered set of source signals:

- explicit `group_id` (primary rigid-unit signal);
- image `fit`, source rotated-envelope coverage, and aspect ratio;
- effective `z_index`, with the contract default for an omitted value;
- opacity and the narrow contract-defined source-bleed predicate;
- element type and shape/image/text properties;
- text geometry, font-size ranking, and measured content requirements;
- position, proximity, relative size, and source order; and
- already-overlapping versus source-separated pairs.

The background decision and source-bleed rule come from the contract and ADR-007; the inference pass must not introduce a threshold-based exemption. Source overlap records intent but does not create an ungrouped rigid group. Ties resolve by the fixed signal order and then source array order. No random seed, network request, learned model, or mutable global state participates in this phase.

### 3. Generate four topology families and at most three variants each

Generate candidates from these four topology families, in the listed stable order:

1. **near-isomorphic** — preserve the source relationships when the target shape permits them, distributing change through proportional margins, isotropic foreground-image scaling, and measured text reflow;
2. **column pivot** — pivot major source groups into columns for wider targets when the original stack cannot fit, deriving slots from target proportions, source extents, and measured text;
3. **horizontal ribbon** — arrange source groups along the primary horizontal axis for very wide/short targets, preserving source sequence and grouping;
4. **vertical re-stack** — re-stack groups along the vertical axis for tall targets when the source is too horizontally dense, preserving hierarchy, reading order, and permitted overlaps.

For each family, produce at most three source-derived slot/emphasis variants:

- a source-proportional variant when source proportions and relationships provide a stable baseline;
- a dominant-media/hero variant only when source evidence identifies a media emphasis; and
- a dominant-copy variant only when source evidence identifies a text emphasis.

The exact names are implementation labels, not wire fields. A missing source signal omits the corresponding variant rather than inventing a hero, logo, or call-to-action role. The total initial candidate count is therefore at most twelve before any deterministic renderer/validator rejection. Slot dimensions come from target proportions, source group extents, image-ratio constraints, and measured text—not fixed universal pixel reservations or invented font-size ratios.

### 4. Make rendered hard validation the candidate gate

Every generated candidate must pass the following sequence:

1. apply the common group and image-ratio rules;
2. quantize mutable values once according to ADR-007;
3. recompute serialized geometry, AABBs, ratios, group relationships, and source-separated overlap;
4. render through the pinned project adapter and `cr-renderer` commit;
5. validate identity/order/immutable fields, containment and bleed, foreground ratios, group and overlap policy, missing assets, actual glyph bounds, and any other contract hard rule; and
6. admit the candidate to ranking only if all checks pass.

Rendering is not a final screenshot after ranking. It is part of hard validation because fit preprocessing, rotation, style-face metrics, letter spacing, line maps, and glyph bounds are contract-relevant behavior.

### 5. Rank with fixed-point scores and stable tie-breaks

For admitted candidates, convert each soft metric to a documented fixed-point integer before comparison. The quality tuple SHOULD cover the contract's preferences in this stable order:

1. readable font size and rendered contrast;
2. source hierarchy and emphasis preservation;
3. shared alignment and even spacing;
4. visual balance and usable whitespace; and
5. preservation of source-intended ungrouped overlap relationships.

The implementation must record the component values used for the selected candidate. Rank with this lexicographic key:

```text
(hard_validity,
 quality_tuple,
 topology_order,
 candidate_index,
 source_order)
```

`hard_validity` is equal for the admitted set but remains explicit in diagnostics. Quality components compare in descending preference; topology order, candidate index, and source order compare ascending. If an aggregate score is used, it must itself be fixed-point and the component tuple remains the deterministic tie-break. No randomness is permitted.

### 6. Make cutoff semantics explicit

The initial search has a deterministic candidate/work budget. A candidate found before an optimization cutoff MUST be returned as the best hard-valid candidate found so far, using the ranking above. If no candidate has passed hard validation before the cutoff, report `INCOMPLETE_SEARCH`, not proven infeasibility, as set by ADR-006. If the finite candidate/work set is fully exhausted with no hard-valid result, report `INFEASIBLE_LAYOUT` through the contract's typed fail-closed path.

A wall-clock interruption, renderer timeout, or resource limit cannot be silently converted into a proof that the target has no valid layout. The cutoff, candidate order, work-unit definition, and status reason must be recorded for reproducibility.

### 7. Defer CP-SAT and models behind measured evidence

Do not add OR-Tools, model code, model weights, network fetches, or a new runtime dependency in the initial strategy. Consider CP-SAT only after a held-out benchmark demonstrates a material hard-valid coverage gain that the bounded structured search cannot provide while preserving the offline resource budget.

If CP-SAT is later selected, it requires a separate accepted dependency/runtime ADR and must use one worker, a fixed seed, a deterministic work limit, and explicit handling of `OPTIMAL`, `FEASIBLE`, `UNKNOWN`, and `INFEASIBLE`. The official [CP-SAT solver guide](https://developers.google.com/optimization/cp/cp_solver) and [CP-SAT task/status guidance](https://developers.google.com/optimization/cp/cp_tasks) are references for those statuses and limits; they do not authorize adding CP-SAT to Stage 1 now.

A model is subject to the same gate and must additionally prove local immutable artifacts, deterministic inference, resource fit, and held-out benefit. Model selection cannot relax any hard contract rule.

### 8. Evaluate on held-out evidence, not public samples alone

Before broadening the algorithm, maintain a held-out evaluation set that is not used to tune candidate weights. Record at least:

- hard-valid rate and each hard-failure reason code;
- rendered quality components and selected-candidate distribution;
- repeated-run determinism of JSON, status, score, and PNG bytes;
- runtime and peak memory in the pinned offline image;
- candidate count, cutoff status, and resource failures; and
- coverage by source/target aspect ratio, topology family, text length, grouping, background, bleed, missing asset, and renderer edge case.

Public examples remain conformance fixtures, not the full target catalogue. A future organizer catalogue or threshold must be recorded as external evidence rather than guessed from those examples.

## Alternatives Considered

### Add CP-SAT immediately

Rejected for the initial path. ADR-004 excludes OR-Tools from the current dependency baseline, and no held-out evidence yet shows that its complexity improves coverage enough to justify a new dependency and resource decision.

### Start with a neural or generative model

Rejected. There is no ratified local model artifact, allowlist, size budget, or deterministic inference contract. A model-first path would add offline packaging and reproducibility risk before hard structural validation is reliable.

### Use random topology or seed-based exploration

Rejected. Randomness makes hidden-case failures difficult to reproduce and offers no evidence-backed benefit for the small bounded candidate set.

### Generate an unbounded set of archetypes and slots

Rejected as the default. An unbounded search makes cutoff status ambiguous, complicates deterministic evidence, and encourages tuning to public samples. The initial twelve-candidate ceiling is transparent and can be revised only with measured evidence.

### Rank by proxy geometry before rendering

Rejected. Text glyph bounds, style faces, letter spacing, fit preprocessing, rotation, missing assets, and contrast depend on the pinned render path. Renderer-in-loop hard validation must precede soft ranking.

### Tune only on the three shipped samples

Rejected. It risks overfitting to public fixtures and cannot establish hidden-case generalization, runtime, or failure semantics.

## Consequences

- The first implementation path is small, inspectable, dependency-light, and reproducible.
- The four families cover the documented wide, tall, near-isomorphic, and extreme-ratio regimes without forcing one aspect-ratio threshold or fixed pixel template.
- At most twelve initial candidates limits coverage and may leave some difficult targets incomplete; the failure protocol makes that limitation visible rather than mislabeling it as infeasibility.
- Rendering every candidate increases work, but it makes the PNG path the same authority used for hard text and image behavior.
- CP-SAT/model improvements remain possible, but they require held-out evidence, a new accepted dependency decision, and explicit deterministic status/resource handling.
- Hardware limits, score thresholds, catalogue breadth, and final assets remain external blockers for claims about official qualification.
- No code, schema, fixture, Docker, dependency, model, or runtime change is claimed or authorized by this documentation-only ratification.

## Affected files/schema fields

When implemented, the affected work would touch the future role-inference/router, candidate generator, renderer-in-loop validator, ranker, and evaluation harness. It would read the existing `x`, `y`, `width`, `height`, `rotation`, `opacity`, `z_index`, `group_id`, `fit`, text, asset, and shape fields but would add no wire fields and change no immutable source data.

The current requirements, container, renderer pin, and offline boundary remain governed by ADR-004 and the project contract. Any later CP-SAT or model adoption requires a separate accepted dependency/runtime decision. This documentation-only ratification changes project documentation only; implementation and qualification remain pending.

## Required validation/evidence

Before implementation can claim conformance, the evidence must include at least:

- deterministic role inference for missing/tied `z_index`, multiple qualifying backgrounds, source bleed, explicit groups, ungrouped containment, source-intended overlap, and source-separated pairs;
- candidate enumeration proving stable topology order, source-derived variant selection, and a maximum of twelve initial family/variant candidates;
- near-isomorphic, column-pivot, horizontal-ribbon, and vertical-re-stack cases across wide, tall, square, and extreme target ratios;
- renderer-in-loop rejection of identity, fixed-field, ratio, AABB, group, overlap, missing-asset, glyph-bound, line-count, and height failures before scoring;
- fixed-point score records and stable tie-breaks across repeated runs, including candidates with equal quality tuples;
- deterministic cutoff tests proving a found hard-valid candidate can be selected while no pre-cutoff candidate is reported as incomplete rather than infeasible;
- exhausted-search tests proving a complete no-candidate set uses the typed fail-closed infeasibility path;
- held-out metrics for hard-valid rate, reason codes, rendered quality, determinism, runtime, memory, candidate count, and resource/cutoff status; and
- if CP-SAT or a model is proposed later, a separate evidence record proving material held-out coverage gain, offline artifact closure, one-worker/fixed-seed behavior, deterministic work limits, explicit solver statuses, and resource compliance.

The external search references used for this decision are the [CP-SAT solver guide](https://developers.google.com/optimization/cp/cp_solver) and [CP-SAT tasks/status guidance](https://developers.google.com/optimization/cp/cp_tasks). The existing project architecture and dependency evidence remain subordinate to the ratified contract and Accepted ADRs.

No such tests, builds, benchmarks, dependency changes, model runs, or runtime changes were run or made for this documentation-only ratification; acceptance does not imply qualification.

### Organizer clarification required

- Are hidden tasks guaranteed feasible? How does the scorer handle no-output/nonzero task failure?
- Exact M5 Pro CPU/RAM/disk/GPU and model allowlist/size.
- Official score thresholds and full target catalogue.
- Final fonts/assets/licensing and native amd64 qualification.
- Adobe Express deployment/backend details.
