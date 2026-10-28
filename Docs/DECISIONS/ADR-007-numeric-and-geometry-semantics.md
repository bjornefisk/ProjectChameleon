# ADR-007: Define numeric and geometry semantics

## Status

Accepted — implemented in the parser, serializer, validator, geometry, and search paths. Cross-platform precision, organizer scoring, and release qualification remain separate evidence questions.

## Date

2026-10-06

## Context

The ratified Stage 1 contract requires finite integer serialization, deliberate post-serialization validation, exact foreground image box-ratio preservation, rotated-AABB containment, rigid groups, and source-aware overlap handling. This ADR records the exact arithmetic representation, tie rounding rule, group transform parameterization, background tie-break, and boundary-contact convention that now govern those checks.

A binary floating-point ratio comparison can reject a mathematically valid image ratio or accept an invalid one near a tie. Repeated rounding can produce a candidate that passes an intermediate check but fails after serialization. Polygon-level separating-axis collision is more exact than the Stage 1 contract requires, but would introduce a second collision predicate when the contract defines hard geometry using rotated axis-aligned envelopes.

### Authority classification

- **Ratified current contract:** `Docs/PROJECT_CONTRACT.md` §§4–7, ADR-002, and ADR-003. These require the v0.9 wire schema, immutable source fields, integer serialized mutable geometry, post-rounding validation, rotated AABB containment, foreground image ratio invariance, rigid groups, source-bleed limits, and fail-closed hard validation.
- **Accepted internal contract decision:** exact rational ingress, one half-even serialization quantization, the common group transform, positive-area AABB collision, deterministic background/bleed tie rules, and the arithmetic procedures below are ratified defaults used by the current implementation. Evidence is recorded in `Docs/STATUS.md` and the implementation tickets.
- **Externally unverified organizer fact:** no organizer clarification is currently needed to define the local arithmetic, but the official target catalogue and scoring thresholds remain external facts. They must not be inferred from the sample set when qualification is planned.

## Decision

### 1. Parse contract numbers exactly at ingress

For every finite JSON number used in contract calculations, preserve its lexical decimal/exponent value as an exact rational (`Fraction`-equivalent) or an exact decimal that is converted to a rational for comparisons. Do not route ratio feasibility, equality, containment margins, or group relationships through binary floating-point arithmetic.

The Python standard-library references for the selected representation and explicit decimal rounding are [fractions](https://docs.python.org/3/library/fractions.html) and [decimal](https://docs.python.org/3/library/decimal.html). These are implementation references, not a change to the wire schema.

The following values remain source values and are not normalized into the response merely because a parser can represent them:

- source `x`, `y`, `width`, `height`, `rotation`, and text metrics;
- omitted fields and effective defaults; and
- every immutable field listed by the ratified contract.

The response still emits only the fields and integer mutable values allowed by the contract.

### 2. Quantize once, with round-half-even, then validate again

Use one centrally defined round-half-even quantization step for mutable output geometry and mutable text `font_size`. The quantizer receives the unrounded candidate, rounds ties to the nearest even integer, and emits finite integers. No intermediate geometry, ratio, group, or AABB value is repeatedly rounded for convenience.

After serialization:

1. Re-read the serialized integers as the candidate's authoritative values.
2. Recompute rotated AABBs from those values and the immutable rotation.
3. Recompute foreground image ratios from those values using exact cross-products.
4. Recompute group relationships and source-separated overlap predicates.
5. Re-run the full hard validator, including actual rendered text bounds.

A candidate that passes only before this final serialization is invalid. A positive-area image ratio is represented by reduced positive integers `p/q`; a valid serialized foreground box must use integer multiples `(k*p, k*q)` for a positive integer `k`, subject to all other hard constraints. If the target has no such hard-valid geometry, the candidate is rejected rather than repaired by ratio drift.

The standard-library `math` trigonometric path MAY be used for the rotated-envelope calculation after exact source parsing, provided the runtime and conversion are pinned. Trigonometric values must not be rounded between sine/cosine evaluation and the envelope comparison. Ratio feasibility itself remains entirely exact and never depends on a binary float. If cross-platform bit-identical trigonometric results become an organizer requirement, that is a separate unresolved specification rather than an assumption in this ADR.

### 3. Use the ratified rotated-AABB predicate

For a rectangle center `(cx, cy)`, width `w`, height `h`, and fixed degree rotation `theta`, use the contract's envelope:

```text
a = |w cos(theta)| + |h sin(theta)|
b = |w sin(theta)| + |h cos(theta)|
AABB = [cx-a/2, cx+a/2] x [cy-b/2, cy+b/2]
```

Containment is inclusive at the target boundary. The full-canvas `fit=cover` background and the narrow source-bleed decoration are the only exceptions already named by the contract. The implementation must not add a general off-canvas exemption.

The [Geometric Tools separating-axes reference](https://www.geometrictools.com/Documentation/MethodOfSeparatingAxes.pdf) is useful evidence for a more exact rotated-polygon predicate, but polygon SAT is not selected for Stage 1: the ratified hard predicate is the rotated AABB, and adding SAT would create an incompatible second definition of containment and collision.

### 4. Define group movement as one uniform transform

For each non-null `group_id`, represent the group's candidate movement by one scalar scale `s > 0` and one translation vector `t`, applied to every child in the same group:

```text
child_center' = s * child_center + t
child_width'  = s * child_width
child_height' = s * child_height
```

The transform may be parameterized around a chosen group anchor by folding that anchor into `t`, but each child must receive the same resulting `s` and `t`. No child-specific scale, translation, or post-hoc drift is allowed. Rotation and all immutable child fields remain unchanged.

Text `font_size` may change only as the permitted mutable text metric inside the transformed child box. It may not move a sibling, alter the group's transform, or create independent child geometry. If integer quantization prevents all children from satisfying the shared relationship and the hard rules, reject that group candidate; do not repair one child independently.

Ungrouped overlap, proximity, or containment does not create a group. Explicit `group_id` remains primary, as required by the contract and existing architecture guidance.

### 5. Use deterministic background selection

Classify backgrounds only by the ratified rule: an image with `fit="cover"` whose source rotated envelope covers the entire source canvas. If multiple images qualify, choose in this order:

1. lowest effective `z_index` (missing means the contract's effective default `0`);
2. largest source rotated-envelope area relative to the source canvas; and
3. source array order.

This tie-break selects among already qualifying backgrounds; it does not grant background treatment to an otherwise ineligible image. The source-envelope-area comparison is a deterministic role signal, not a new scoring rule.

### 6. Preserve the source-bleed side set

For the contract-defined ungrouped translucent source-bleed shape, derive the set of clipped canvas sides from its source rotated AABB (`left`, `top`, `right`, and/or `bottom`). A candidate must:

- retain clipping on the same side set;
- still intersect the target canvas; and
- never move the decoration completely outside the target.

It must not gain a new exemption merely because another geometry transform would be convenient. A candidate that cannot satisfy these conditions is hard-invalid.

### 7. Define collision as positive-area AABB overlap

For active positive-area records, two rotated AABBs collide only when their intersection has positive area. Edge or point contact is allowed. Source-overlapping pairs remain eligible to overlap; pairs that were separate in the source must remain zero-area-intersection pairs in every hard-valid candidate, subject to the contract's infeasibility rule. This predicate is applied before soft aesthetic scoring.

The same convention is used after integer serialization. Degenerate source records remain records, but a zero-area record does not create a positive-area collision by itself.

## Alternatives Considered

### Binary floating point for all arithmetic

Rejected. It makes exact ratio and equality decisions depend on representational error and can disagree near integer or boundary ties.

### Round at every layout step

Rejected. It makes the result order-dependent and can allow a pre-serialization candidate to pass while the serialized output violates a ratio, group, or containment rule.

### Round-half-up or language-default rounding

Rejected. Language defaults vary and commonly treat ties differently. A documented half-even rule is deterministic and matches the explicit-rounding requirement without adding a new wire field.

### Polygon SAT for all collisions and containment

Rejected for Stage 1. The contract is AABB-based; SAT would increase cost and produce a predicate that is not the ratified hard rule. The cited SAT reference remains research evidence, not a selected dependency or behavior.

### Independent child adjustment inside a group

Rejected. It violates rigid `group_id` semantics and can make a visually plausible candidate structurally invalid.

### First qualifying background or highest `z_index`

Rejected as insufficiently deterministic across ties and inconsistent with the usual behind-content ordering. The selected tie-break is explicit and stable.

### Boundary contact counts as collision

Rejected. Positive-area overlap is the simpler convention for the contract's AABB rule and permits legitimate touching layouts without inventing clearance requirements.

## Consequences

- Ratio feasibility and serialization become reproducible and auditable without changing the v0.9 schema.
- Candidates near a boundary may be rejected after final integer serialization; this is intentional rather than a reason to weaken the hard validator.
- Group placement is simple to reason about, but some target shapes may be infeasible when a single scale cannot fit all children.
- The AABB predicate can be conservative for rotated rectangles. That conservatism is compatible with Stage 1 and avoids a second geometry contract.
- Background classification and source-bleed handling are deterministic without changing source records or renderer pixels.
- A pinned runtime remains relevant for trigonometric evaluation and renderer measurements; exact organizer hardware facts are not invented here.
- The parser, serializer, validator, and geometry paths use the ratified arithmetic without changing the v0.9 schema.

## Affected files/schema fields

The implementation touches the numeric parser, candidate serializer, semantic validator, and geometry/role-inference code. Relevant existing schema fields are `x`, `y`, `width`, `height`, `rotation`, `opacity`, `z_index`, `group_id`, `fit`, and text `font_size`; no field is added, removed, or retyped by this decision.

The current implementation and qualification evidence use this decision's rules. Native platform, cross-platform parity, organizer scoring, and release qualification remain separate evidence questions.

## Required validation/evidence

Before implementation can claim conformance, the evidence must include at least:

- decimal and exponent-form JSON numbers compared exactly, including ratios that are close to a binary floating-point tie;
- positive foreground image ratios checked by integer cross-products after serialization, including `fit="fill"` and `fit="cover"` foreground images;
- half-even tie cases for positive and negative geometry and text sizes, with no intermediate-rounding divergence;
- candidates that pass before rounding but fail after rounding, proving that the post-serialization validator rejects them;
- rotated AABB containment at zero, right-angle, non-right-angle, and negative-coordinate positions, with inclusive boundary contact;
- explicit group cases proving one common scale/translation and rejecting independent child drift;
- multiple qualifying backgrounds proving the `z_index`, source-envelope-area, then source-order tie-break;
- source-bleed cases preserving each clipped-side combination and rejecting disappearance or a newly clipped side;
- source-overlap, source-separated, edge-touching, point-touching, and degenerate-record collision cases;
- repeated runs in the pinned `linux/amd64` runtime yielding the same serialized integers and validation reasons; and
- a conformance record showing that the implementation uses the ratified AABB predicate rather than an unapproved polygon SAT path.

The external arithmetic references used for this decision are [Python `Fraction`](https://docs.python.org/3/library/fractions.html), [Python `Decimal`](https://docs.python.org/3/library/decimal.html), [Geometric Tools' separating-axis reference](https://www.geometrictools.com/Documentation/MethodOfSeparatingAxes.pdf), [MDN `matrix()`](https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/Values/transform-function/matrix), and [MDN `transform-origin`](https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/Properties/transform-origin). They document general numeric/transform behavior; the ratified project contract remains the authority for Stage 1 semantics.

Geometry and validator evidence is recorded in the implementation tickets, `Docs/STATUS.md`, and the repository test suites. This ADR defines the required evidence and does not replace those records.
