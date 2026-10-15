"""Rotated axis-aligned envelopes and contract boundary predicates."""

from __future__ import annotations

import math
from collections.abc import Mapping
from fractions import Fraction
from typing import Any, NamedTuple

from .math_util import to_fraction


class AABB(NamedTuple):
    """Tuple-compatible ``(min_x, min_y, max_x, max_y)`` envelope."""

    min_x: Fraction
    min_y: Fraction
    max_x: Fraction
    max_y: Fraction


Canvas = Mapping[str, Any] | tuple[Any, Any] | list[Any]


def _canvas_size(canvas_or_width: Canvas | Any, height: Any | None = None) -> tuple[Fraction, Fraction]:
    if height is not None:
        return to_fraction(canvas_or_width), to_fraction(height)
    if isinstance(canvas_or_width, Mapping):
        return to_fraction(canvas_or_width["width"]), to_fraction(canvas_or_width["height"])
    if isinstance(canvas_or_width, (tuple, list)) and len(canvas_or_width) == 2:
        return to_fraction(canvas_or_width[0]), to_fraction(canvas_or_width[1])
    raise TypeError("canvas must provide width and height")


def element_center(element: Mapping[str, Any]) -> tuple[Fraction, Fraction]:
    """Return an element's exact center from its ``x/y/width/height`` fields."""

    return (
        to_fraction(element["x"]) + to_fraction(element["width"]) / 2,
        to_fraction(element["y"]) + to_fraction(element["height"]) / 2,
    )


def _sin_cos_degrees(value: Any) -> tuple[float, float]:
    degrees = to_fraction(value)
    if degrees.denominator == 1 and degrees.numerator % 90 == 0:
        # Exact right-angle values avoid platform trig noise and preserve the
        # validator's pinned special cases, including negative rotations.
        quarter_turn = (degrees.numerator // 90) % 4
        return ((0.0, 1.0), (1.0, 0.0), (0.0, -1.0), (-1.0, 0.0))[quarter_turn]
    radians = math.radians(float(degrees))
    sine, cosine = math.sin(radians), math.cos(radians)
    if not (math.isfinite(sine) and math.isfinite(cosine)):
        raise ValueError("rotation is outside the runtime trigonometric range")
    return sine, cosine


def rotated_aabb(
    element_or_x: Mapping[str, Any] | Any,
    y: Any | None = None,
    width: Any | None = None,
    height: Any | None = None,
    rotation: Any = 0,
) -> AABB:
    """Compute the contract rotated AABB for a mapping or scalar rectangle.

    Mapping form is ``rotated_aabb(element)``.  Scalar form is
    ``rotated_aabb(x, y, width, height, rotation=0)``.  Trigonometric values
    for non-right angles are pinned to the runtime's ``math`` implementation
    and converted immediately to exact fractions; ratio decisions do not use
    this approximation path.
    """

    if isinstance(element_or_x, Mapping):
        if y is not None or width is not None or height is not None:
            raise TypeError("mapping form does not accept scalar rectangle arguments")
        element = element_or_x
        x_value = element["x"]
        y_value = element["y"]
        width_value = element["width"]
        height_value = element["height"]
        rotation_value = element.get("rotation", 0)
    else:
        if y is None or width is None or height is None:
            raise TypeError("scalar form requires x, y, width, and height")
        x_value, y_value, width_value, height_value, rotation_value = (
            element_or_x,
            y,
            width,
            height,
            rotation,
        )

    x = to_fraction(x_value)
    y_coordinate = to_fraction(y_value)
    box_width = to_fraction(width_value)
    box_height = to_fraction(height_value)
    center_x = x + box_width / 2
    center_y = y_coordinate + box_height / 2
    sine, cosine = _sin_cos_degrees(rotation_value)
    sine_fraction = Fraction.from_float(sine)
    cosine_fraction = Fraction.from_float(cosine)
    extent_x = abs(box_width * cosine_fraction) + abs(box_height * sine_fraction)
    extent_y = abs(box_width * sine_fraction) + abs(box_height * cosine_fraction)
    return AABB(
        center_x - extent_x / 2,
        center_y - extent_y / 2,
        center_x + extent_x / 2,
        center_y + extent_y / 2,
    )


def is_contained_in_canvas(
    aabb: AABB | tuple[Any, Any, Any, Any],
    canvas_or_width: Canvas | Any,
    height: Any | None = None,
) -> bool:
    """Return whether an envelope lies in the canvas, including its edges."""

    left, top, right, bottom = (to_fraction(value) for value in aabb)
    canvas_width, canvas_height = _canvas_size(canvas_or_width, height)
    return left >= 0 and top >= 0 and right <= canvas_width and bottom <= canvas_height


def clipped_sides(
    aabb: AABB | tuple[Any, Any, Any, Any],
    canvas_or_width: Canvas | Any,
    height: Any | None = None,
) -> frozenset[str]:
    """Return sides crossed by an envelope; touching an edge is not clipping."""

    left, top, right, bottom = (to_fraction(value) for value in aabb)
    canvas_width, canvas_height = _canvas_size(canvas_or_width, height)
    sides: set[str] = set()
    if left < 0:
        sides.add("left")
    if top < 0:
        sides.add("top")
    if right > canvas_width:
        sides.add("right")
    if bottom > canvas_height:
        sides.add("bottom")
    return frozenset(sides)


def positive_aabb_intersection(
    left: AABB | tuple[Any, Any, Any, Any],
    right: AABB | tuple[Any, Any, Any, Any],
) -> bool:
    """Return true only when two envelopes overlap with positive area."""

    left_values = tuple(to_fraction(value) for value in left)
    right_values = tuple(to_fraction(value) for value in right)
    overlap_x = min(left_values[2], right_values[2]) - max(left_values[0], right_values[0])
    overlap_y = min(left_values[3], right_values[3]) - max(left_values[1], right_values[1])
    return overlap_x > 0 and overlap_y > 0


has_positive_area_intersection = positive_aabb_intersection


def intersects_canvas(
    aabb: AABB | tuple[Any, Any, Any, Any],
    canvas_or_width: Canvas | Any,
    height: Any | None = None,
) -> bool:
    """Return true when an envelope has positive-area intersection with canvas."""

    canvas_width, canvas_height = _canvas_size(canvas_or_width, height)
    return positive_aabb_intersection(
        aabb, AABB(Fraction(0), Fraction(0), canvas_width, canvas_height)
    )


def source_bleed_sides(
    element: Mapping[str, Any],
    aabb: AABB | tuple[Any, Any, Any, Any],
    canvas: Canvas,
) -> frozenset[str] | None:
    """Classify an eligible source-bleed decoration and return its side set.

    ``None`` means that the element is not the narrow contract exception.
    Eligibility is intentionally limited to ungrouped translucent shapes with
    at least one clipped side and positive source-canvas intersection.
    """

    if element.get("type") != "shape" or element.get("group_id") is not None:
        return None
    if to_fraction(element.get("opacity", 1)) >= 1:
        return None
    sides = clipped_sides(aabb, canvas)
    if not sides or not intersects_canvas(aabb, canvas):
        return None
    return sides


def check_source_bleed(
    source_aabb: AABB | tuple[Any, Any, Any, Any],
    target_aabb: AABB | tuple[Any, Any, Any, Any],
    source_canvas: Canvas,
    target_canvas: Canvas,
) -> bool:
    """Check side-set preservation and visible target intersection.

    This four-argument form is deliberately geometry-only; callers classify
    source eligibility with :func:`source_bleed_sides` before invoking it.
    """

    source_sides = clipped_sides(source_aabb, source_canvas)
    target_sides = clipped_sides(target_aabb, target_canvas)
    return (
        bool(source_sides)
        and source_sides == target_sides
        and intersects_canvas(source_aabb, source_canvas)
        and intersects_canvas(target_aabb, target_canvas)
    )


__all__ = [
    "AABB",
    "check_source_bleed",
    "clipped_sides",
    "element_center",
    "has_positive_area_intersection",
    "intersects_canvas",
    "is_contained_in_canvas",
    "positive_aabb_intersection",
    "rotated_aabb",
    "source_bleed_sides",
]
