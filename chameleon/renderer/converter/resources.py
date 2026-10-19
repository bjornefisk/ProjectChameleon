"""Deterministic resource checks before renderer and Pillow allocations."""

from __future__ import annotations

from fractions import Fraction
from math import isfinite
from typing import Any, Mapping

try:
    from chameleon.engine.errors import InfeasibleLayoutError, InfeasibleReasonCode
except ModuleNotFoundError:  # pragma: no cover - direct engine import fallback
    from engine.errors import InfeasibleLayoutError, InfeasibleReasonCode


MAX_ELEMENTS = 1024
MAX_TEXT_CODEPOINTS = 1_000_000
MAX_CANVAS_DIMENSION = 32_768
MAX_ELEMENT_DIMENSION = 32_768
MAX_INTERMEDIATE_DIMENSION = 16_384
MAX_INTERMEDIATE_PIXELS = 16 * 1024 * 1024
MAX_TOTAL_PIXELS = 64 * 1024 * 1024


def _rounded_dimension(value: Any) -> int:
    if isinstance(value, bool):
        raise ValueError("boolean is not a dimension")
    if isinstance(value, float) and not isfinite(value):
        raise ValueError("non-finite dimension")
    fraction = Fraction(str(value))
    if fraction <= 0:
        return 1
    return max(1, (fraction.numerator + fraction.denominator - 1) // fraction.denominator)


def _resource_failure(resource: str, value: int, limit: int, **details: Any) -> None:
    raise InfeasibleLayoutError(
        InfeasibleReasonCode.INCOMPLETE_SEARCH,
        "render resource budget exceeded before allocation",
        {
            "search_kind": "render_resources",
            "search_exhausted": False,
            "resource": resource,
            "value": value,
            "limit": limit,
            **details,
        },
    )


def validate_image_dimensions(width: Any, height: Any, *, resource: str = "image") -> tuple[int, int]:
    """Validate one image allocation and return safe integer dimensions."""
    rounded_width = _rounded_dimension(width)
    rounded_height = _rounded_dimension(height)
    if rounded_width > MAX_INTERMEDIATE_DIMENSION:
        _resource_failure(f"{resource}_width", rounded_width, MAX_INTERMEDIATE_DIMENSION)
    if rounded_height > MAX_INTERMEDIATE_DIMENSION:
        _resource_failure(f"{resource}_height", rounded_height, MAX_INTERMEDIATE_DIMENSION)
    pixels = rounded_width * rounded_height
    if pixels > MAX_INTERMEDIATE_PIXELS:
        _resource_failure(f"{resource}_pixels", pixels, MAX_INTERMEDIATE_PIXELS)
    return rounded_width, rounded_height


def validate_design_resources(design: Mapping[str, Any]) -> None:
    """Reject oversized render inputs before Pillow, Skia, or renderer work."""
    canvas = design["canvas"]
    canvas_width = _rounded_dimension(canvas["width"])
    canvas_height = _rounded_dimension(canvas["height"])
    if canvas_width > MAX_CANVAS_DIMENSION:
        _resource_failure("canvas_width", canvas_width, MAX_CANVAS_DIMENSION)
    if canvas_height > MAX_CANVAS_DIMENSION:
        _resource_failure("canvas_height", canvas_height, MAX_CANVAS_DIMENSION)
    total_pixels = canvas_width * canvas_height
    if total_pixels > MAX_TOTAL_PIXELS:
        _resource_failure("canvas_pixels", total_pixels, MAX_TOTAL_PIXELS)

    elements = design.get("elements", ())
    if len(elements) > MAX_ELEMENTS:
        _resource_failure("element_count", len(elements), MAX_ELEMENTS)
    text_codepoints = 0
    for index, element in enumerate(elements):
        raw_width = _rounded_dimension(element.get("width", 1))
        raw_height = _rounded_dimension(element.get("height", 1))
        if raw_width > MAX_ELEMENT_DIMENSION:
            _resource_failure(f"element_{index}_width", raw_width, MAX_ELEMENT_DIMENSION)
        if raw_height > MAX_ELEMENT_DIMENSION:
            _resource_failure(f"element_{index}_height", raw_height, MAX_ELEMENT_DIMENSION)
        width, height = validate_image_dimensions(
            raw_width,
            raw_height,
            resource=f"element_{index}",
        )
        total_pixels += width * height
        if total_pixels > MAX_TOTAL_PIXELS:
            _resource_failure("aggregate_pixels", total_pixels, MAX_TOTAL_PIXELS, index=index)
        if element.get("type") == "text":
            text_codepoints += len(str(element.get("content", "")))
            if text_codepoints > MAX_TEXT_CODEPOINTS:
                _resource_failure("text_codepoints", text_codepoints, MAX_TEXT_CODEPOINTS, index=index)


__all__ = [
    "MAX_ELEMENTS",
    "MAX_TEXT_CODEPOINTS",
    "MAX_CANVAS_DIMENSION",
    "MAX_ELEMENT_DIMENSION",
    "MAX_INTERMEDIATE_DIMENSION",
    "MAX_INTERMEDIATE_PIXELS",
    "MAX_TOTAL_PIXELS",
    "validate_design_resources",
    "validate_image_dimensions",
]
