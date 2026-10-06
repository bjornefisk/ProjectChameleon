# ADR-003: Define hard constraints and infeasible-layout fallback

## Status

Accepted

## Date

2026-10-06

## Context

The design notes mix disqualifying structural rules with aesthetic preferences. They do not specify whether source-clipped decoration is allowed, whether an empty design is valid, or what `resize()` returns when a target cannot fit every required record without violating a hard rule. A best-effort output that silently drops content would look valid while breaking the challenge contract.

## Decision

### Hard constraints

A candidate is valid only when it preserves:

- request structure and exact target canvas;
- unique element IDs, count, source order, types, and all immutable fields;
- finite integer geometry, source records, asset references, and pixel-integrity rules;
- rotated AABB containment for active foreground records;
- exact source box ratio for positive-area foreground images, including `fit=fill`;
- rigid `group_id` relationships and separation of pairs that were separate in the source;
- text content/style and actual glyph bounds; and
- the prohibition on engine-generated, hidden, removed, opacity-zero, or replacement elements.

A full-canvas `fit=cover` image is the only background exemption. The Level 2 corner bleed is handled by one narrow derived exception: an ungrouped, translucent shape already clipped by the source canvas must remain clipped on the same side(s) and still intersect the target. No arbitrary source-off-canvas record receives an exemption.

Readable size, contrast, hierarchy, alignment, even spacing, balance, whitespace, and ungrouped overlap-area preservation are soft ranking objectives. They run only after hard validation; a proxy score cannot rescue a hard failure.

### Empty and degenerate input

An empty `elements` list is valid and returns the target canvas with an empty list. Source-authored zero-size records remain records. Positive-area records cannot be reduced to zero as a workaround.

### Infeasible targets

The fallback is **fail closed**. If no hard-valid candidate exists, `resize()` raises a typed `InfeasibleLayoutError` with a reason code. The batch runner writes no Stage 1 design or PNG for that task and returns a nonzero status. It must not return a misleading best-effort design, hide an element, rewrite copy, substitute a font, or violate an image ratio to force a response.

Soft objectives may be relaxed during candidate search. Hard rules may not be relaxed. Target-generation systems should avoid infeasible source/target pairs, but hidden inputs use the same deterministic failure protocol.

## Alternatives considered

### Always return a best-effort design

Rejected. It makes an invalid design indistinguishable from a valid submission and encourages silent hard-rule violations.

### Add a second JSON response variant for `unsatisfiable`

Deferred. The supplied scoring interface expects a design response. The typed exception is an internal API decision until the organizer publishes a failure envelope.

### Shed, hide, zero-size, or opacity-zero elements

Rejected. These violate identity and pixel-integrity rules and are explicitly outside Stage 1.

### Treat every source-off-canvas element as exempt

Rejected. It would let content evade containment. The exception is limited to the documented translucent source-bleed decoration predicate.

## Consequences

- The orchestrator needs an explicit failure path before the solver is implemented.
- The hidden-task generator must either guarantee feasibility or accept deterministic task failures.
- Validator tests must distinguish soft quality failure from hard invalidity.
- The intentional Level 2 decoration is no longer an unexplained warning-only case.

## Affected files/schema fields

- `chameleon/chameleon_design_schema_v0.9.json` (`elements.minItems`, geometry fields)
- `x`, `y`, `width`, `height`, `rotation`, `opacity`, `group_id`, `fit`, `font_size`
- `chameleon/engine/main.py` self-check and future failure handling
- `Docs/MATHEMATICAL_CONSTRAINTS.md`, `Docs/DIFFICULTY_TIERS_AND_FAILURE_MODES.md`

## Required validation tests

- Rotated AABB containment after integer rounding.
- Source-bleed decoration versus arbitrary off-canvas content.
- Exact foreground image cross-product ratio, including `fit=fill`.
- Empty list, zero-size source record, missing asset, no background, and no-text scenes.
- Duplicate/reordered/missing IDs, changed fixed fields, new source-separated collision, and a target that has no hard-valid candidate.
