# Project Chameleon pre-implementation decision register

## Status

Accepted pre-implementation documentation package. ADR-006 through ADR-009 are accepted contract decisions for Stage 1; they do not claim implementation, conformance qualification, or runtime verification, and they do not authorize code changes by themselves.

## Date

2026-10-06

## Scope and authority

This package records accepted operational decisions and remaining external questions for Stage 1 only:

- `Docs/PROJECT_CONTRACT.md` and Accepted ADR-001 through ADR-009 are the ratified authority.
- The ratified `chameleon/chameleon_design_schema_v0.9.json`, pinned renderer evidence, and Accepted ADRs are not silently overridden by starter code, fixtures, or lower-precedence guidance.
- A conflict with the contract requires an explicit superseding ADR or contract update before implementation. Acceptance of this package records decisions but does not change runtime behavior.
- No code, schema, fixture, Docker, requirements, engine, renderer, validator, solver, model, or runtime behavior changes are authorized by this register; implementation and qualification remain pending.

The package distinguishes three kinds of statement:

| Label | Meaning |
| --- | --- |
| **Ratified current contract** | Binding behavior already established by the project contract or an Accepted ADR. All later implementation must preserve it. |
| **Accepted internal contract decision** | A deterministic, maintainable default ratified for later implementation. It is a contract decision, not evidence that the behavior is implemented or qualified. |
| **Externally unverified organizer fact** | A fact controlled by the organizer or deployment environment and not established by this repository. It must remain open rather than being guessed. |

## Ratified baseline that these accepted decisions must preserve

| Ratified source | Current contract boundary |
| --- | --- |
| `PROJECT_CONTRACT.md` and ADR-001 | The authority hierarchy is explicit; starter code, samples, and lower-precedence guidance cannot silently override the contract. |
| ADR-002 and the v0.9 schema | Stage 1 returns a design-only document; source IDs/order/types and immutable fields remain fixed; only target canvas dimensions, element geometry, and text `font_size` may change; external style ranges are `[start, end)`. |
| ADR-003 | Hard constraints are checked after deliberate integer serialization; rotated AABB containment, foreground image ratios, groups, identity, text bounds, and source-bleed rules are mandatory; no hard-valid candidate means fail closed with no misleading design/PNG. |
| ADR-004 and ADR-009 | The current artifact is offline `linux/amd64`; no model or OR-Tools dependency is used initially, and any later adoption needs a separate decision; organizer resource/model limits remain TBD. |
| ADR-005 | Stage 1 remains autonomous and identity-preserving; finale interaction, copy edits, font substitution, shedding, and reduced previews are not Stage 1 behavior. |

## Decision matrix

The status of every new ADR is **Accepted**. “Blocking” below means acceptance settles the contract before the corresponding implementation work can claim a settled behavior; it does not claim that work is implemented or qualified.

| ADR | Decision area | Register classification | Implementation gate | Ratified decision recorded | External blocker |
| --- | --- | --- | --- | --- | --- |
| [ADR-006](DECISIONS/ADR-006-failure-protocol-and-search-status.md) | Failure protocol, incomplete versus infeasible search, artifact publication, batch exit | **Accepted; blocking decision** for a conforming runner/orchestrator | Implement only after the contract and evidence path are available | Stable typed internal statuses; no unsatisfiable success envelope; stage and commit JSON/PNG as one logical pair; zero only when every task commits | `Are hidden tasks guaranteed feasible? How does the scorer handle no-output/nonzero task failure?` |
| [ADR-007](DECISIONS/ADR-007-numeric-and-geometry-semantics.md) | Exact numeric ingress, rounding, transforms, AABB, background, bleed, overlap | **Accepted; blocking decision** for validator/geometry/search work | Implement only with post-serialization conformance evidence | Exact rational ingress; one round-half-even serialization; post-serialization validation; common group transform; positive-area AABB collision; deterministic background and bleed rules | Official catalogue and score facts remain external, but no organizer answer is needed for the local arithmetic default |
| [ADR-008](DECISIONS/ADR-008-typography-and-renderer-edge-semantics.md) | Unicode line generation, style-run boundaries, metrics, overflow, shape strokes | **Accepted; blocking decision** for renderer/typography conformance | Implement only with renderer and font evidence | UAX #29 clusters plus UAX #14 opportunities; latest-fitting greedy breaks; effective span metrics; reject overflow; preserve content; rasterize declared rectangle/ellipse strokes inside the box; no public line-map field | `Final fonts/assets/licensing and native amd64 qualification.` |
| [ADR-009](DECISIONS/ADR-009-initial-search-strategy.md) | Initial candidate generation, ranking, cutoff, and future solver gate | **Accepted; recommended initial strategy; blocking for search implementation** | Implement only with held-out evaluation and deterministic evidence | Deterministic role inference; four topology families; at most three source-derived variants each; renderer-in-loop hard validation; fixed-point ranking; no model/CP-SAT now | Hidden feasibility/scoring, hardware/model limits, score thresholds, and catalogue breadth remain unverified |

### Blocking decisions

The failure, numeric/geometry, and typography decisions are accepted blocking decisions for their named hard-behavior workstreams. ADR-009 is accepted as the initial deterministic strategy and is binding when search implementation starts. Acceptance settles the contract choice; implementation, verification, and qualification remain pending.

### Ratified decisions

The accepted, deterministic defaults are:

1. **Failure & Feasibility:** Typed internal status distinctions, fail closed for genuinely invalid/unsolvable geometry, atomic task-level JSON/PNG commit boundary, and proactive spatial compression (font floors, isotropic art scaling, horizontal ribboning) to maximize feasibility on extreme canvases (ADR-006).
2. **Numeric & Geometry:** Exact rational comparisons, one final half-even quantization, contract AABBs, rigid group transforms, and positive-area overlap (ADR-007).
3. **Typography:** Unicode-safe cluster boundaries, renderer-matched span metrics, explicit line/height rejection, and no text rewrite (ADR-008).
4. **Search & Runtime:** Bounded four-topology structured search with 0 MB neural model weights, < 2.0s CPU latency target, < 500 MB solver RAM, strictly CPU-only execution under <= 8 cores and <= 8 GB RAM in Docker on Apple Silicon under Rosetta 2, followed by renderer-in-loop validation and fixed-point ranking (ADR-004, ADR-009).
5. **Finale Integration:** Lightweight local HTTP service (FastAPI/Flask) or WebAssembly module connecting the Stage 1 engine to the Adobe Express add-on iframe (ADR-005).
These are accepted internal contract decisions, not claims that implementation, verification, or qualification is complete.

These decisions preserve the schema and existing hard constraints while settling internal behavior for later implementation.

## Organizer clarification questions and external blockers

The following questions are intentionally copied exactly from the decision research. They are **externally unverified organizer facts**, not questions that local code or ADRs may answer:

- Are hidden tasks guaranteed feasible? How does the scorer handle no-output/nonzero task failure?
- Exact M5 Pro CPU/RAM/disk/GPU and model allowlist/size.
- Official score thresholds and full target catalogue.
- Final fonts/assets/licensing and native amd64 qualification.
- Adobe Express deployment/backend details.

Their impact is different by workstream:

| External question | Why it remains a blocker |
| --- | --- |
| Hidden feasibility and no-output/nonzero scoring | Determines how an externally scored batch treats `INFEASIBLE_LAYOUT`, `INCOMPLETE_SEARCH`, and missing task artifacts. It does not justify returning a best-effort design locally. |
| M5 Pro resources and model allowlist/size | Blocks claims about official runtime capacity and any future model path; it does not authorize inventing a budget. |
| Score thresholds and full catalogue | Blocks claims of score qualification and representative coverage; public fixtures remain conformance inputs, not the full target set. |
| Fonts/assets/licensing and native amd64 qualification | Blocks release-grade metric/licensing and platform evidence; Stage 1 cannot silently substitute unverified fonts or assets. |
| Adobe Express deployment/backend | Blocks finale deployment planning only; it is not a Stage 1 engine dependency under ADR-005. |

## Evidence basis

The accepted defaults are grounded in the following primary or authoritative references; the URLs are evidence for general behavior, not replacements for the ratified project contract:

- [POSIX utility conventions](https://pubs.opengroup.org/onlinepubs/9699919799/utilities/V3_chap01.html) for the ordinary zero/nonzero process-status convention.
- [JSON Schema Draft 2020-12 validation](https://json-schema.org/draft/2020-12/json-schema-validation) for the distinction between structural validation and process status.
- Python [`Fraction`](https://docs.python.org/3/library/fractions.html) and [`Decimal`](https://docs.python.org/3/library/decimal.html) references for exact rational ingress and explicit rounding modes.
- [Geometric Tools' separating-axes reference](https://www.geometrictools.com/Documentation/MethodOfSeparatingAxes.pdf), [MDN `matrix()`](https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/Values/transform-function/matrix), and [MDN `transform-origin`](https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/Properties/transform-origin) as geometry/transform evidence; Stage 1 still uses the contract's rotated AABB predicate.
- [Unicode UAX #14](https://www.unicode.org/reports/tr14/) and [UAX #29](https://www.unicode.org/reports/tr29/) for the accepted line-break and grapheme-cluster semantics.
- The pinned [`cr-renderer` commit](https://github.com/CyberAgentAILab/cr-renderer/commit/a17e1fb9a732959dd6c21ae168d5ee09d74bd64f) and its [schema](https://raw.githubusercontent.com/CyberAgentAILab/cr-renderer/a17e1fb9a732959dd6c21ae168d5ee09d74bd64f/src/cr_renderer/schema.py), [text utilities](https://raw.githubusercontent.com/CyberAgentAILab/cr-renderer/a17e1fb9a732959dd6c21ae168d5ee09d74bd64f/src/cr_renderer/text_utils.py), and [renderer](https://raw.githubusercontent.com/CyberAgentAILab/cr-renderer/a17e1fb9a732959dd6c21ae168d5ee09d74bd64f/src/cr_renderer/renderer.py), as recorded in `Docs/DEPENDENCY_EVIDENCE.md`.
- [OR-Tools CP-SAT solver guidance](https://developers.google.com/optimization/cp/cp_solver) and [CP-SAT tasks/status guidance](https://developers.google.com/optimization/cp/cp_tasks) for a possible future solver only. ADR-004 remains the current authority against adding CP-SAT now.

## Remaining ambiguity not silently resolved

Even after these decisions are ratified, the following implementation/evidence details must be made explicit rather than guessed:

- The concrete filesystem primitive for the logical JSON/PNG pair commit must be qualified on the target runtime; ADR-006 specifies the observable all-or-nothing behavior, not a platform-specific syscall.
- The pinned runtime's trigonometric precision and any requirement for cross-platform bit-identical AABB values need conformance evidence; ADR-007 deliberately keeps ratio feasibility exact and does not invent an organizer precision requirement.
- Fixed-point score scales/weights and the exact work-unit budget inside each bounded topology candidate need an evidence-backed implementation record; they cannot override hard validation or become an unbounded search by implication.
- Packaged font bytes, asset inventory, licensing, and native `amd64` behavior remain unresolved until the external clarification above is answered and evidence is collected.
- Official task failure scoring, thresholds, catalogue coverage, hardware limits, model policy, and finale deployment remain external facts even though the local decisions are ratified.

## Acceptance and implementation boundary

ADR-006, ADR-007, ADR-008, and ADR-009 are accepted pre-implementation decisions:

- these files are documentation-only contract records; they do not claim implementation or qualification;
- they preserve and extend `PROJECT_CONTRACT.md` and ADR-001 through ADR-005; together with those prior decisions they form the accepted ADR-001 through ADR-009 package without adding wire fields or weakening hard constraints;
- no code/schema/fixture/Docker/requirements/engine/renderer/validator/solver/model/runtime behavior changes on the strength of this register; and
- an implementation that encounters a conflict must stop and request a superseding accepted ADR or contract update rather than silently choosing a different behavior.

## Files created by this package

- `Docs/DECISION_REGISTER.md`
- `Docs/DECISIONS/ADR-006-failure-protocol-and-search-status.md`
- `Docs/DECISIONS/ADR-007-numeric-and-geometry-semantics.md`
- `Docs/DECISIONS/ADR-008-typography-and-renderer-edge-semantics.md`
- `Docs/DECISIONS/ADR-009-initial-search-strategy.md`

No implementation files were changed for this documentation-only package. No tests, builds, linters, formatters, or network commands were run.
