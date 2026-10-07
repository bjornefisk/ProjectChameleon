# 04: Exact Rational Geometry, Bounds, and Group Transforms

**What to build:**  
The exact geometric calculation engine in `chameleon/engine/geometry/` that consumes parser-owned exact numeric values, eliminates floating-point drift, computes rotated axis-aligned bounding boxes (AABBs), calculates exact integer aspect ratio lattices for foreground images, implements uniform macro-transforms for rigid `group_id` units, and provides a central `round-half-even` quantizer.

**Blocked by:**  
`01: Semantic Contract Validator and Failure Reason Codes` and `03: Atomic Batch Staging and Fail-Closed Runner`

**Status:**  
ready-for-agent

- [ ] Create `chameleon/engine/geometry/math_util.py` to convert parser-owned exact integer/decimal values to `Fraction`; never reconstruct a lexical number from a binary float. Provide a centralized `quantize_to_int(value)` helper using `round-half-even` (`decimal.ROUND_HALF_EVEN`).
- [ ] Create `chameleon/engine/geometry/bounds.py` implementing the rotated AABB formula: $a = |w\cos\theta| + |h\sin\theta|$, $b = |w\sin\theta| + |h\cos\theta|$ around element center $(cx, cy)$.
- [ ] Implement `is_contained_in_canvas(aabb, canvas_width, canvas_height)` returning true if the envelope is within $[0, W] \times [0, H]$ (inclusive of canvas edges).
- [ ] Implement `check_source_bleed(source_aabb, target_aabb, source_canvas, target_canvas)` verifying that a translucent ungrouped shape preserves its exact clipped side set.
- [ ] Create `chameleon/engine/geometry/ratios.py` to calculate valid integer lattice dimensions $(k \cdot p, k \cdot q)$ for any foreground image with reduced aspect ratio $p/q$.
- [ ] Create `chameleon/engine/geometry/groups.py` to apply a single uniform scale $s > 0$ and translation vector $\mathbf{t} = (tx, ty)$ to all elements sharing a `group_id`, deriving child geometries without individual child drift.
- [ ] Create unit tests under `chameleon/tests/geometry/test_geometry.py` verifying exact rational calculations, tie-rounding behavior, rotated AABB calculations, and group transform preservation.
