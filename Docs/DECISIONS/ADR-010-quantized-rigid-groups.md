# ADR-010: Preserve rigid groups through integer serialization

## Status

Accepted — implemented in PR #65, merged at `6dbbc0a3eaba3090997ad9731a4026677dc6978c`. Partner review was waived by the repository owner; no partner approval is recorded. Native and official qualification boundaries remain separate evidence questions.

## Date / owner / reviewers

- Date: 2026-10-21
- Owner: @bjornefisk (issue owner/project authority)
- Reviewers: independent reviewer role (ADR proposal review, APPROVE, 2026-10-21); partner review on implementation PR #65 was waived by repository owner @bjornefisk before merge; no partner approval is recorded.

## Context / authority

The original challenge PDF (§§2.3, 2.5, 3.1, 7.2) requires the same design structure/elements, updated positions and sizes, no unwanted collisions, readable text, and intact brand. It does not prescribe an exact common group transform after serialization. The project contract §§5, 7, and 8 and ADR-007 §4 add one shared group scale/translation and one half-even integer serialization. ADR-007 §4 currently tells the validator to reject any group whose children no longer satisfy an exact rational transform after serialization.

The public Level 3 issue is blocked because small shared transforms produce integer geometry by independently quantizing fields; a strict exact-ratio check then rejects the serialized result even when every field came from one common pre-serialization transform. Allowing independent per-child drift or an unbounded numeric tolerance would weaken the group invariant. The original PDF is the controlling organizer source for visual semantics; the exact post-serialization equality is project-authored.

## Decision

Keep the common positive scale and translation exact in candidate geometry. For source element `e` with top-left `(x, y)` and size `(w, h)`, one group transform `(s, tx, ty)` produces:

```text
x* = s*x + tx
y* = s*y + ty
w* = s*w
h* = s*h
```

Only the mutable geometry fields `x`, `y`, `width`, and `height` participate in this transform; `font_size` is separate. Using the original exact source values and the canonical half-even `quantize_to_int`, the serialized group is valid iff one exact rational `s > 0`, `tx`, and `ty` reproduce every response geometry field:
```text
response.x      == quantize_to_int(s * source.x + tx)
response.y      == quantize_to_int(s * source.y + ty)
response.width  == quantize_to_int(s * source.width)
response.height == quantize_to_int(s * source.height)
```
The validator evaluates all children against the same transform, original source rationals, and canonical quantizer. This is not an independent ±0.5 tolerance per child. Zero source dimensions remain zero. Rotation and all immutable fields remain unchanged.

All hard checks continue to run on the serialized response: finite integer geometry, rotated AABB containment, exact image ratios, source-separated non-overlap, actual glyph bounds, and missing-asset preservation. A candidate that cannot be reconstructed from one transform is rejected. `derive_common_transform` may remain exact for unquantized candidate geometry; the serialized contract validator uses the quantized reconstruction predicate.

## Options considered

1. Retain exact common-transform equality on serialized integers. Rejected: it discards valid results created by the required single quantization step and keeps the Level 3 area failure even when one shared transform exists.
2. Allow each child to deviate within a numeric tolerance. Rejected: it permits incompatible scales/translations and makes the tolerance, rather than source grouping, authoritative.
3. Require exact reconstruction through the common half-even serializer. Selected: preserves one shared transform and leaves every downstream hard check unchanged.

## Consequences / tradeoffs

- Group invariance is defined before serialization; after serialization, any rounding difference is accepted only if one exact transform reproduces the entire group.
- Child geometry cannot be adjusted independently to improve packing. The maximum field-rounding deviation is a consequence of the existing quantizer, not a new tolerance.
- Existing exact-transform fixtures must distinguish raw rational candidates from serialized candidates.
- The prior issue-61 area certificate based on integer-exact group scales no longer proves infeasibility; it must be corrected and the public sample re-evaluated.

## Security / dependency / data impact

No dependency, schema, runtime, network, asset, source-data, or public API change. The validator uses exact rational arithmetic already required by ADR-007.

## Migration / rollback

No wire migration. Candidate generators continue to apply one common transform before the existing single half-even serialization. Roll back this decision and implementation if a candidate can pass without a single shared transform, if exact image ratios/bounds/overlap regress, or if group children drift independently. Keep the previous typed fail-closed behavior until a fully hard-valid candidate passes.

## Affected files / callers / docs

`Docs/PROJECT_CONTRACT.md` §§5, 7, 8; ADR-007 §4; `chameleon/engine/geometry/groups.py`; `chameleon/engine/contract.py`; group and contract tests; `chameleon/engine/layout/horizontal_ribbon.py`; `Docs/STATUS.md`; Ticket 07; issue #61.

## Verification

Add positive cases proving quantized scale/translation reconstruction for even and odd dimensions, half-even ties, rotated groups, and small scales; add negative cases for child-specific drift, incompatible scales/translations, changed rotation, and output dimensions/positions outside the quantizer's reconstruction. Run the public Level 3 hard validator and preserve a separate incomplete-search/no-artifact case.

## Supersedes

Supersedes ADR-007 §4's exact post-serialization group equality only. The common-transform formulas, exact ingress, one half-even serialization, and all other ADR-007 decisions remain in force.

## Open external facts

No organizer group-transform rule exists in the supplied PDF. Official score thresholds and the hidden target catalogue remain unverified and are not inferred from this decision.
