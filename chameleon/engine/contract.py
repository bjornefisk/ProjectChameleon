"""Independent semantic oracle for the ratified Stage 1 design contract.

The validator intentionally lives outside the layout and rendering paths.  A
candidate generator may propose geometry, but only this module decides whether
serialized output preserves the source contract.
"""

from __future__ import annotations

import json
import math
from collections.abc import Mapping, Sequence
from decimal import Decimal
from fractions import Fraction
from numbers import Number
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from .errors import InfeasibleLayoutError, InfeasibleReasonCode

_SCHEMA_PATH = Path(__file__).resolve().parents[1] / "chameleon_design_schema_v0.9.json"
with _SCHEMA_PATH.open(encoding="utf-8") as _schema_file:
    _SCHEMA = json.load(_schema_file)

_DESIGN_VALIDATOR = Draft202012Validator(_SCHEMA)
_CANVAS_VALIDATOR = Draft202012Validator(_SCHEMA["$defs"]["canvas"])

_GEOMETRY_FIELDS = ("x", "y", "width", "height")

# AABB tuple: min_x, min_y, max_x, max_y. Coordinate arithmetic stays exact.
# Pinned math.sin/cos coefficients use exact fractions of their float results.
AABB = tuple[Fraction, Fraction, Fraction, Fraction]


def validate_source(source: Mapping[str, Any]) -> None:
    """Validate a source ``DesignDocument`` before candidate generation.

    The function returns ``None`` on success and raises
    :class:`InfeasibleLayoutError` with ``INVALID_SOURCE`` on structural or
    semantic source failures.  It never applies defaults or mutates ``source``.
    Callers must parse JSON decimal tokens with ``parse_float=Decimal``.
    Binary-float source values are rejected because their original tokens are lost.
    """

    if not isinstance(source, Mapping):
        _fail(
            InfeasibleReasonCode.INVALID_SOURCE,
            "source must be a design object",
            {"path": []},
        )

    _validate_schema(source, _DESIGN_VALIDATOR, InfeasibleReasonCode.INVALID_SOURCE, "source")
    _validate_finite_numbers(source, InfeasibleReasonCode.INVALID_SOURCE, "source")

    elements = source["elements"]
    seen_ids: set[str] = set()
    for index, element in enumerate(elements):
        element_id = element["id"]
        if element_id in seen_ids:
            _fail(
                InfeasibleReasonCode.INVALID_SOURCE,
                f"source element id is not unique: {element_id!r}",
                {"index": index, "id": element_id},
            )
        seen_ids.add(element_id)

        if element["type"] == "text":
            _validate_source_style_runs(element, index)



def validate_target_canvas(target_canvas: Mapping[str, Any]) -> None:
    """Validate a task target canvas before candidate generation."""

    _validate_target_canvas(target_canvas)


def validate_response(
    source: Mapping[str, Any],
    target_canvas: Mapping[str, Any],
    response: Mapping[str, Any],
) -> None:
    """Validate a serialized candidate against ``source`` and ``target_canvas``.

    All mutable geometry is checked from the response's serialized integer
    values.  The source is validated first, then the response is checked in a
    deterministic order so callers receive one stable reason code for the
    first hard failure.
    """

    validate_source(source)
    validate_target_canvas(target_canvas)

    if not isinstance(response, Mapping):
        _fail(
            InfeasibleReasonCode.MALFORMED_INPUT,
            "response must be a design object",
            {"path": []},
        )

    # Identity is a semantic contract rule, not merely a schema property.  Do
    # this lightweight comparison before full response validation so a
    # well-formed identity mutation receives IMMUTABLE_FIELD_CHANGED even when
    # the new type omits fields required by its new schema branch.
    source_elements = source["elements"]
    candidate_elements = response.get("elements")
    if isinstance(candidate_elements, list):
        if len(candidate_elements) != len(source_elements):
            _fail(
                InfeasibleReasonCode.IMMUTABLE_FIELD_CHANGED,
                "response element count differs from source",
                {"expected": len(source_elements), "actual": len(candidate_elements)},
            )
        for index, (source_element, candidate_element) in enumerate(
            zip(source_elements, candidate_elements)
        ):
            if not isinstance(candidate_element, Mapping):
                continue
            if "id" in candidate_element and candidate_element["id"] != source_element["id"]:
                _fail(
                    InfeasibleReasonCode.IMMUTABLE_FIELD_CHANGED,
                    "response element ids or array order differ from source",
                    {
                        "index": index,
                        "expected_id": source_element["id"],
                        "actual_id": candidate_element["id"],
                    },
                )
            if "type" in candidate_element and candidate_element["type"] != source_element["type"]:
                _fail(
                    InfeasibleReasonCode.IMMUTABLE_FIELD_CHANGED,
                    "response element type differs from source",
                    {
                        "index": index,
                        "id": source_element["id"],
                        "expected_type": source_element["type"],
                        "actual_type": candidate_element["type"],
                    },
                )
            if (
                candidate_element.get("id") == source_element["id"]
                and candidate_element.get("type") == source_element["type"]
            ):
                source_immutable = _immutable_projection(source_element)
                candidate_immutable = _immutable_projection(candidate_element)
                for key, expected_value in source_immutable.items():
                    if key not in candidate_immutable or not _strict_equal(
                        expected_value, candidate_immutable[key]
                    ):
                        _fail(
                            InfeasibleReasonCode.IMMUTABLE_FIELD_CHANGED,
                            "response changed or omitted an immutable element field",
                            {"index": index, "id": source_element["id"], "field": key},
                        )


    _validate_schema(response, _DESIGN_VALIDATOR, InfeasibleReasonCode.MALFORMED_INPUT, "response")
    _validate_finite_numbers(response, InfeasibleReasonCode.MALFORMED_INPUT, "response")

    expected_canvas = _schema_view(target_canvas)
    if not _strict_equal(response["canvas"], expected_canvas):
        _fail(
            InfeasibleReasonCode.MALFORMED_INPUT,
            "response canvas must equal target_canvas exactly",
            {"expected": expected_canvas, "actual": response["canvas"]},
        )

    source_elements = source["elements"]
    response_elements = response["elements"]
    if len(response_elements) != len(source_elements):
        _fail(
            InfeasibleReasonCode.IMMUTABLE_FIELD_CHANGED,
            "response element count differs from source",
            {"expected": len(source_elements), "actual": len(response_elements)},
        )

    for index, (source_element, response_element) in enumerate(
        zip(source_elements, response_elements)
    ):
        if response_element["id"] != source_element["id"]:
            _fail(
                InfeasibleReasonCode.IMMUTABLE_FIELD_CHANGED,
                "response element ids or array order differ from source",
                {
                    "index": index,
                    "expected_id": source_element["id"],
                    "actual_id": response_element["id"],
                },
            )
        if response_element["type"] != source_element["type"]:
            _fail(
                InfeasibleReasonCode.IMMUTABLE_FIELD_CHANGED,
                "response element type differs from source",
                {
                    "index": index,
                    "id": source_element["id"],
                    "expected_type": source_element["type"],
                    "actual_type": response_element["type"],
                },
            )

    _validate_serialized_geometry(source_elements, response_elements)

    for index, (source_element, response_element) in enumerate(
        zip(source_elements, response_elements)
    ):
        if not _strict_equal(
            _immutable_projection(source_element), _immutable_projection(response_element)
        ):
            _fail(
                InfeasibleReasonCode.IMMUTABLE_FIELD_CHANGED,
                "response changed an immutable element field",
                {"index": index, "id": source_element["id"]},
            )

    try:
        source_aabbs = [_rotated_aabb(element) for element in source_elements]
    except (TypeError, ValueError, OverflowError) as error:
        _fail(
            InfeasibleReasonCode.INVALID_SOURCE,
            "source geometry cannot be evaluated by the contract AABB predicate",
            {"error": str(error)},
        )
    try:
        response_aabbs = [_rotated_aabb(element) for element in response_elements]
    except (TypeError, ValueError, OverflowError) as error:
        _fail(
            InfeasibleReasonCode.MALFORMED_INPUT,
            "response geometry cannot be evaluated by the contract AABB predicate",
            {"error": str(error)},
        )
    background_index = _background_index(source, source_aabbs)
    bleed_sides = {
        index: _source_bleed_sides(source_element, source_aabb, source["canvas"])
        for index, (source_element, source_aabb) in enumerate(zip(source_elements, source_aabbs))
    }

    for index, (source_element, response_element, response_aabb) in enumerate(
        zip(source_elements, response_elements, response_aabbs)
    ):
        if index == background_index:
            # The cover exemption lifts the containment bound, not visibility:
            # a background with no overlap with the target is a hidden record
            # (PROJECT_CONTRACT section 8, hard rule 3).
            if not _positive_intersection_with_canvas(response_aabb, response["canvas"]):
                _fail(
                    InfeasibleReasonCode.CONTAINMENT_VIOLATION,
                    "background must keep positive-area overlap with the target canvas",
                    {"index": index, "id": response_element["id"], "aabb": response_aabb},
                )
            continue

        expected_bleed = bleed_sides[index]
        if expected_bleed is not None:
            actual_bleed = _clipped_sides(response_aabb, response["canvas"])
            if actual_bleed != expected_bleed or not _positive_intersection_with_canvas(
                response_aabb, response["canvas"]
            ):
                _fail(
                    InfeasibleReasonCode.CONTAINMENT_VIOLATION,
                    "source-bleed decoration changed its clipped side set or disappeared",
                    {
                        "index": index,
                        "id": response_element["id"],
                        "expected_sides": sorted(expected_bleed),
                        "actual_sides": sorted(actual_bleed),
                    },
                )
            continue

        if not _contained_in_canvas(response_aabb, response["canvas"]):
            _fail(
                InfeasibleReasonCode.CONTAINMENT_VIOLATION,
                "rotated element bounds are outside the target canvas",
                {"index": index, "id": response_element["id"], "aabb": response_aabb},
            )

    _validate_image_ratios(source_elements, response_elements, background_index)
    _validate_groups(source_elements, response_elements)
    _validate_source_separation(
        source_elements, response_elements, source_aabbs, response_aabbs
    )
    _validate_text_overflow(response_elements)


def _schema_view(value: Any) -> Any:
    """Return ``value`` with zero-fraction Decimals as ints.

    JSON Schema treats ``1.0`` as an integer. ``jsonschema`` checks Decimal
    values by type, so integral Decimal tokens must be converted before the
    integer check. Fractional values are returned unchanged and still fail.
    """

    if isinstance(value, Decimal) and value.is_finite() and value == value.to_integral_value():
        return int(value)
    if isinstance(value, Mapping):
        return {key: _schema_view(child) for key, child in value.items()}
    if isinstance(value, list):
        return [_schema_view(child) for child in value]
    return value


def _validate_schema(
    value: Any,
    validator: Draft202012Validator,
    reason_code: InfeasibleReasonCode,
    label: str,
) -> None:
    errors = sorted(
        validator.iter_errors(_schema_view(value)),
        key=lambda error: tuple(str(part) for part in error.path),
    )
    if not errors:
        return
    error = errors[0]
    path = list(error.absolute_path)
    _fail(
        reason_code,
        f"{label} does not match the ratified design schema: {error.message}",
        {"path": path, "schema_path": list(error.absolute_schema_path)},
    )


def _validate_target_canvas(target_canvas: Any) -> None:
    if not isinstance(target_canvas, Mapping):
        _fail(
            InfeasibleReasonCode.INVALID_TARGET,
            "target_canvas must be a canvas object",
            {"path": []},
        )

    errors = sorted(
        _CANVAS_VALIDATOR.iter_errors(_schema_view(target_canvas)),
        key=lambda error: tuple(str(part) for part in error.path),
    )
    if errors:
        error = errors[0]
        _fail(
            InfeasibleReasonCode.INVALID_TARGET,
            f"target_canvas does not match the canvas schema: {error.message}",
            {"path": list(error.absolute_path)},
        )

    canonical_canvas = _schema_view(target_canvas)
    if (
        type(canonical_canvas["width"]) is not int
        or type(canonical_canvas["height"]) is not int
        or canonical_canvas["width"] <= 0
        or canonical_canvas["height"] <= 0
    ):
        _fail(
            InfeasibleReasonCode.INVALID_TARGET,
            "target canvas dimensions must be positive serialized integers",
            {"target_canvas": target_canvas},
        )


def _validate_finite_numbers(
    value: Any, reason_code: InfeasibleReasonCode, label: str, path: tuple[Any, ...] = ()
) -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            _validate_finite_numbers(child, reason_code, label, path + (key,))
        return
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for index, child in enumerate(value):
            _validate_finite_numbers(child, reason_code, label, path + (index,))
        return
    if not _is_numeric(value):
        return
    if not _is_finite_number(value):
        _fail(
            reason_code,
            f"{label} contains a non-finite number",
            {"path": list(path), "value": repr(value)},
        )
    if reason_code is InfeasibleReasonCode.INVALID_SOURCE and isinstance(value, float):
        _fail(
            reason_code,
            "source contains a binary float; parse JSON decimal tokens as Decimal",
            {"path": list(path), "value": repr(value)},
        )


def _validate_source_style_runs(element: Mapping[str, Any], index: int) -> None:
    content = element["content"]
    for run_index, run in enumerate(element.get("style_runs") or []):
        start = run["start"]
        end = run["end"]
        if start > end or end > len(content):
            _fail(
                InfeasibleReasonCode.INVALID_SOURCE,
                "text style_run range is outside the source content",
                {
                    "element_index": index,
                    "run_index": run_index,
                    "start": start,
                    "end": end,
                    "content_length": len(content),
                },
            )


def _validate_serialized_geometry(
    source_elements: Sequence[Mapping[str, Any]],
    response_elements: Sequence[Mapping[str, Any]],
) -> None:
    for index, (source_element, response_element) in enumerate(
        zip(source_elements, response_elements)
    ):
        for field in _GEOMETRY_FIELDS:
            value = response_element[field]
            if type(value) is not int:
                _fail(
                    InfeasibleReasonCode.MALFORMED_INPUT,
                    f"serialized response {field} must be a finite integer",
                    {"index": index, "id": response_element["id"], "field": field, "value": repr(value)},
                )
        if response_element["width"] < 0 or response_element["height"] < 0:
            _fail(
                InfeasibleReasonCode.MALFORMED_INPUT,
                "serialized response width and height must be non-negative",
                {"index": index, "id": response_element["id"]},
            )

        if "font_size" in response_element and type(response_element["font_size"]) is not int:
            _fail(
                InfeasibleReasonCode.MALFORMED_INPUT,
                "serialized response font_size must be a finite integer",
                {"index": index, "id": response_element["id"]},
            )
        if response_element["type"] == "text" and response_element["font_size"] < 1:
            _fail(
                InfeasibleReasonCode.MALFORMED_INPUT,
                "serialized text font_size must be at least one",
                {"index": index, "id": response_element["id"]},
            )

        source_is_positive = (
            _as_fraction(source_element["width"]) > 0
            and _as_fraction(source_element["height"]) > 0
        )
        response_is_positive = response_element["width"] > 0 and response_element["height"] > 0
        if source_is_positive and not response_is_positive:
            _fail(
                InfeasibleReasonCode.MALFORMED_INPUT,
                "a positive-area source element cannot be reduced to zero area",
                {"index": index, "id": response_element["id"]},
            )


def _immutable_projection(element: Mapping[str, Any]) -> dict[str, Any]:
    projection: dict[str, Any] = {}
    for key, value in element.items():
        if key in _GEOMETRY_FIELDS:
            continue
        if key == "font_size" and element["type"] == "text":
            continue
        projection[key] = value
    return projection


def _validate_image_ratios(
    source_elements: Sequence[Mapping[str, Any]],
    response_elements: Sequence[Mapping[str, Any]],
    background_index: int | None,
) -> None:
    for index, (source_element, response_element) in enumerate(
        zip(source_elements, response_elements)
    ):
        if source_element["type"] != "image" or index == background_index:
            continue
        source_width = _as_fraction(source_element["width"])
        source_height = _as_fraction(source_element["height"])
        if source_width <= 0 or source_height <= 0:
            continue
        if response_element["width"] * source_height != response_element["height"] * source_width:
            _fail(
                InfeasibleReasonCode.IMAGE_RATIO_VIOLATION,
                "foreground image dimensions do not preserve the source ratio",
                {
                    "index": index,
                    "id": response_element["id"],
                    "source_width": source_element["width"],
                    "source_height": source_element["height"],
                    "response_width": response_element["width"],
                    "response_height": response_element["height"],
                },
            )


def _validate_groups(
    source_elements: Sequence[Mapping[str, Any]],
    response_elements: Sequence[Mapping[str, Any]],
) -> None:
    groups: dict[Any, list[int]] = {}
    for index, element in enumerate(source_elements):
        group_id = element.get("group_id")
        if group_id is not None:
            groups.setdefault(group_id, []).append(index)

    for group_id, indices in groups.items():
        scale: Fraction | None = None
        translation: tuple[Fraction, Fraction] | None = None
        for index in indices:
            source_element = source_elements[index]
            response_element = response_elements[index]

            source_width = _as_fraction(source_element["width"])
            source_height = _as_fraction(source_element["height"])
            response_width = Fraction(response_element["width"])
            response_height = Fraction(response_element["height"])

            if source_width == 0:
                if response_width != 0:
                    _group_fail(group_id, index, "zero source width changed inside a rigid group")
            else:
                candidate_scale = response_width / source_width
                scale = _merge_group_scale(scale, candidate_scale, group_id, index)

            if source_height == 0:
                if response_height != 0:
                    _group_fail(group_id, index, "zero source height changed inside a rigid group")
            else:
                candidate_scale = response_height / source_height
                scale = _merge_group_scale(scale, candidate_scale, group_id, index)

        if scale is None:
            source_anchor_center = _element_center(source_elements[indices[0]])
            response_anchor_center = _element_center(response_elements[indices[0]])
            for index in indices[1:]:
                source_center = _element_center(source_elements[index])
                response_center = _element_center(response_elements[index])
                for axis in (0, 1):
                    source_delta = source_center[axis] - source_anchor_center[axis]
                    response_delta = response_center[axis] - response_anchor_center[axis]
                    if source_delta == 0:
                        if response_delta != 0:
                            _group_fail(
                                group_id,
                                index,
                                "group children do not share one scale",
                            )
                    else:
                        scale = _merge_group_scale(
                            scale,
                            response_delta / source_delta,
                            group_id,
                            index,
                        )
            if scale is None:
                scale = Fraction(1)
        if scale <= 0:
            _group_fail(group_id, indices[0], "rigid group scale must be positive")

        for index in indices:
            source_element = source_elements[index]
            response_element = response_elements[index]
            source_center = _element_center(source_element)
            response_center = _element_center(response_element)
            candidate_translation = (
                response_center[0] - scale * source_center[0],
                response_center[1] - scale * source_center[1],
            )
            if translation is None:
                translation = candidate_translation
            elif candidate_translation != translation:
                _group_fail(group_id, index, "group children do not share one translation")


def _merge_group_scale(
    current: Fraction | None,
    candidate: Fraction,
    group_id: Any,
    index: int,
) -> Fraction:
    if candidate <= 0:
        _group_fail(group_id, index, "rigid group scale must be positive")
    if current is None:
        return candidate
    if candidate != current:
        _group_fail(group_id, index, "group children do not share one scale")
    return current


def _group_fail(group_id: Any, index: int, message: str) -> None:
    _fail(
        InfeasibleReasonCode.GROUP_VIOLATION,
        message,
        {"group_id": group_id, "index": index},
    )


def _validate_source_separation(
    source_elements: Sequence[Mapping[str, Any]],
    response_elements: Sequence[Mapping[str, Any]],
    source_aabbs: Sequence[AABB],
    response_aabbs: Sequence[AABB],
) -> None:
    for left in range(len(source_elements)):
        if not _positive_element(response_elements[left]):
            continue
        for right in range(left + 1, len(source_elements)):
            if not _positive_element(response_elements[right]):
                continue
            if _positive_aabb_intersection(source_aabbs[left], source_aabbs[right]):
                continue
            if not _positive_aabb_intersection(response_aabbs[left], response_aabbs[right]):
                continue
            _fail(
                InfeasibleReasonCode.SOURCE_SEPARATION_VIOLATION,
                "source-separated elements collide with positive-area AABB overlap",
                {
                    "left_id": response_elements[left]["id"],
                    "right_id": response_elements[right]["id"],
                },
            )


def _validate_text_overflow(response_elements: Sequence[Mapping[str, Any]]) -> None:
    for index, element in enumerate(response_elements):
        if element["type"] != "text":
            continue

        content = element["content"]
        visual_lines = content.count("\n") + 1
        max_lines = element.get("max_lines")
        if max_lines is not None and visual_lines > max_lines:
            _fail(
                InfeasibleReasonCode.TEXT_OVERFLOW,
                "text has more forced visual lines than max_lines permits",
                {
                    "index": index,
                    "id": element["id"],
                    "visual_lines": visual_lines,
                    "max_lines": max_lines,
                },
            )

        line_height = _as_fraction(element.get("line_height", Decimal("1.2")))
        required_height = Fraction(element["font_size"]) * line_height * visual_lines
        if required_height > element["height"]:
            _fail(
                InfeasibleReasonCode.TEXT_OVERFLOW,
                "text line boxes exceed the serialized element height",
                {
                    "index": index,
                    "id": element["id"],
                    "visual_lines": visual_lines,
                    "required_height": str(required_height),
                    "height": element["height"],
                },
            )


def _background_index(source: Mapping[str, Any], source_aabbs: Sequence[AABB]) -> int | None:
    candidates: list[tuple[int, Fraction, int]] = []
    source_canvas = source["canvas"]
    for index, (element, aabb) in enumerate(zip(source["elements"], source_aabbs)):
        if element["type"] != "image" or element.get("fit", "contain") != "cover":
            continue
        if not _contained_canvas_in_aabb(aabb, source_canvas):
            continue
        area = max(Fraction(0), aabb[2] - aabb[0]) * max(
            Fraction(0), aabb[3] - aabb[1]
        )
        candidates.append((int(element.get("z_index", 0)), -area, index))
    if not candidates:
        return None
    return min(candidates)[2]


def _source_bleed_sides(
    element: Mapping[str, Any], aabb: AABB, canvas: Mapping[str, int]
) -> frozenset[str] | None:
    if element["type"] != "shape":
        return None
    if element.get("group_id") is not None:
        return None
    if _as_fraction(element.get("opacity", 1)) >= 1:
        return None
    sides = _clipped_sides(aabb, canvas)
    if not sides or not _positive_intersection_with_canvas(aabb, canvas):
        return None
    return frozenset(sides)


def _clipped_sides(aabb: AABB, canvas: Mapping[str, int]) -> frozenset[str]:
    sides: set[str] = set()
    if aabb[0] < 0:
        sides.add("left")
    if aabb[1] < 0:
        sides.add("top")
    if aabb[2] > canvas["width"]:
        sides.add("right")
    if aabb[3] > canvas["height"]:
        sides.add("bottom")
    return frozenset(sides)


def _positive_intersection_with_canvas(aabb: AABB, canvas: Mapping[str, int]) -> bool:
    canvas_aabb = (
        Fraction(0),
        Fraction(0),
        Fraction(canvas["width"]),
        Fraction(canvas["height"]),
    )
    return _positive_aabb_intersection(aabb, canvas_aabb)


def _contained_in_canvas(aabb: AABB, canvas: Mapping[str, int]) -> bool:
    return (
        aabb[0] >= 0
        and aabb[1] >= 0
        and aabb[2] <= canvas["width"]
        and aabb[3] <= canvas["height"]
    )


def _contained_canvas_in_aabb(aabb: AABB, canvas: Mapping[str, int]) -> bool:
    return (
        aabb[0] <= 0
        and aabb[1] <= 0
        and aabb[2] >= canvas["width"]
        and aabb[3] >= canvas["height"]
    )


def _rotated_aabb(element: Mapping[str, Any]) -> AABB:
    x = _as_fraction(element["x"])
    y = _as_fraction(element["y"])
    width = _as_fraction(element["width"])
    height = _as_fraction(element["height"])
    center_x = x + width / 2
    center_y = y + height / 2
    sine, cosine = _sin_cos_degrees(element.get("rotation", 0))
    sine = Fraction.from_float(sine)
    cosine = Fraction.from_float(cosine)
    extent_x = abs(width * cosine) + abs(height * sine)
    extent_y = abs(width * sine) + abs(height * cosine)
    return (
        center_x - extent_x / 2,
        center_y - extent_y / 2,
        center_x + extent_x / 2,
        center_y + extent_y / 2,
    )


def _sin_cos_degrees(value: Any) -> tuple[float, float]:
    degrees = _as_fraction(value)
    if degrees.denominator == 1 and degrees % 90 == 0:
        quarter_turn = (degrees.numerator // 90) % 4
        return ((0.0, 1.0), (1.0, 0.0), (0.0, -1.0), (-1.0, 0.0))[quarter_turn]
    radians = math.radians(_as_float(value))
    return math.sin(radians), math.cos(radians)


def _element_center(element: Mapping[str, Any]) -> tuple[Fraction, Fraction]:
    return (
        _as_fraction(element["x"]) + _as_fraction(element["width"]) / 2,
        _as_fraction(element["y"]) + _as_fraction(element["height"]) / 2,
    )


def _positive_element(element: Mapping[str, Any]) -> bool:
    return _as_fraction(element["width"]) > 0 and _as_fraction(element["height"]) > 0


def _positive_aabb_intersection(left: AABB, right: AABB) -> bool:
    overlap_x = min(left[2], right[2]) - max(left[0], right[0])
    overlap_y = min(left[3], right[3]) - max(left[1], right[1])
    return overlap_x > 0 and overlap_y > 0


def _is_numeric(value: Any) -> bool:
    return isinstance(value, (int, float, Decimal, Fraction, Number)) and not isinstance(value, bool)


def _is_finite_number(value: Any) -> bool:
    if isinstance(value, Decimal):
        return value.is_finite()
    if isinstance(value, float):
        return math.isfinite(value)
    return True


def _as_fraction(value: Any) -> Fraction:
    if isinstance(value, bool):
        raise TypeError("boolean is not a contract number")
    if isinstance(value, Fraction):
        return value
    if isinstance(value, Decimal):
        return Fraction(value)
    if isinstance(value, int):
        return Fraction(value, 1)
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("non-finite contract number")
        return Fraction(str(value))
    if isinstance(value, Number):
        return Fraction(str(value))
    raise TypeError(f"not a contract number: {value!r}")


def _as_float(value: Any) -> float:
    result = float(_as_fraction(value))
    if not math.isfinite(result):
        raise ValueError("contract number is outside the runtime float range")
    return result


def _strict_equal(left: Any, right: Any) -> bool:
    if type(left) is not type(right):
        return False
    if isinstance(left, Mapping):
        if set(left) != set(right):
            return False
        return all(_strict_equal(left[key], right[key]) for key in left)
    if isinstance(left, list):
        return len(left) == len(right) and all(
            _strict_equal(left_item, right_item)
            for left_item, right_item in zip(left, right)
        )
    if isinstance(left, Decimal):
        return left.as_tuple() == right.as_tuple()
    if isinstance(left, float):
        return left.hex() == right.hex()
    return left == right


def _fail(
    reason_code: InfeasibleReasonCode,
    message: str,
    details: Mapping[str, Any] | None = None,
) -> None:
    raise InfeasibleLayoutError(reason_code, message, details)


__all__ = ["validate_response", "validate_source", "validate_target_canvas"]
