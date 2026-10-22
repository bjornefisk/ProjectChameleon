"""Exact geometry primitives for the Stage 1 contract."""

from .bounds import (
    AABB,
    check_source_bleed,
    clipped_sides,
    element_center as bounds_element_center,
    has_positive_area_intersection,
    intersects_canvas,
    is_contained_in_canvas,
    positive_aabb_intersection,
    rotated_aabb,
    source_bleed_sides,
)
from .groups import (
    GroupTransform,
    apply_transform,
    derive_common_transform,
    derive_quantized_common_transform,
    element_center as group_element_center,
    has_common_transform,
    has_quantized_common_transform,
)
from .math_util import as_fraction, quantize_to_int, to_fraction
from .ratios import (
    is_ratio_lattice,
    is_valid_ratio_lattice,
    lattice_dimensions,
    preserves_source_ratio,
    reduced_ratio,
    source_ratio,
)

__all__ = [
    "AABB",
    "GroupTransform",
    "apply_transform",
    "as_fraction",
    "bounds_element_center",
    "check_source_bleed",
    "clipped_sides",
    "derive_common_transform",
    "derive_quantized_common_transform",
    "group_element_center",
    "has_common_transform",
    "has_quantized_common_transform",
    "has_positive_area_intersection",
    "intersects_canvas",
    "is_contained_in_canvas",
    "is_ratio_lattice",
    "is_valid_ratio_lattice",
    "lattice_dimensions",
    "positive_aabb_intersection",
    "preserves_source_ratio",
    "quantize_to_int",
    "reduced_ratio",
    "rotated_aabb",
    "source_bleed_sides",
    "source_ratio",
    "to_fraction",
]
