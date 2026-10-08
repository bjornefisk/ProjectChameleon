# 01: Semantic Contract Validator and Failure Reason Codes

**What to build:**  
An independent semantic contract validator and error taxonomy that acts as the oracle for the entire project. Given a source design, target canvas, and candidate response, the validator independently checks all hard rules (element count, stable IDs, array ordering, immutable field preservation, finite integer geometry, rotated AABB containment, foreground image cross-product ratios, rigid group integrity, source-separated non-collision, and missing asset preservation) and raises typed errors with exact reason codes.

**Blocked by:**  
None (can start immediately).

**Status:**  
implemented

- [x] Create `chameleon/engine/errors.py` defining `InfeasibleReasonCode` (covering `INVALID_SOURCE`, `INVALID_TARGET`, `MALFORMED_INPUT`, `IMMUTABLE_FIELD_CHANGED`, `CONTAINMENT_VIOLATION`, `IMAGE_RATIO_VIOLATION`, `GROUP_VIOLATION`, `SOURCE_SEPARATION_VIOLATION`, `TEXT_OVERFLOW`, `NO_HARD_VALID_CANDIDATE`, `INCOMPLETE_SEARCH`, `RUNTIME_IO_FAILURE`) and `InfeasibleLayoutError`.
- [x] Create `chameleon/engine/contract.py` implementing `validate_source(source)` and `validate_response(source, target_canvas, response)`.
- [x] Enforce that element IDs, count, order, and types in `response` match `source` exactly.
- [x] Enforce that all immutable fields (content, font family, style runs, asset_id, fit, shape properties, rotation, opacity, z_index, group_id) are bit-for-bit identical to the source.
- [x] Enforce that serialized output coordinates (`x`, `y`, `width`, `height`) and `font_size` are finite integers.
- [x] Enforce rotated AABB canvas containment after deliberate integer quantization, honoring the narrow source-bleed exception for ungrouped translucent shapes (ADR-003, ADR-007).
- [x] Enforce exact integer cross-product equality for all positive-area foreground images: `response.width * source.height == response.height * source.width` (including `fit="fill"`).
- [x] Enforce rigid `group_id` integrity: all elements sharing a `group_id` must maintain their relative spatial configuration without child drift.
- [x] Enforce zero positive-area collisions between element pairs that did not overlap in the source design.
- [x] Create unit tests under `chameleon/tests/contract/test_contract.py` verifying that contract fixtures pass and mutated invalid designs fail with the exact expected reason codes.
