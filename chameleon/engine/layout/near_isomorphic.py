"""Level 1 safe, near-isomorphic geometry generation.

The solver deliberately generates one finite candidate. It does not rank
alternatives: if the candidate cannot satisfy the hard geometry invariants it
fails closed with ``NO_HARD_VALID_CANDIDATE``.
"""

from __future__ import annotations

from collections.abc import Mapping
from fractions import Fraction
from math import gcd
from pathlib import Path
from typing import Any, NoReturn

from ..contract import validate_source, validate_target_canvas
from ..errors import InfeasibleLayoutError, InfeasibleReasonCode
from ..geometry.bounds import (
    clipped_sides,
    intersects_canvas,
    is_contained_in_canvas,
    positive_aabb_intersection,
    rotated_aabb,
    source_bleed_sides,
)
from ..geometry.groups import derive_common_transform
from ..geometry.math_util import quantize_to_int, to_fraction
from ..geometry.ratios import reduced_ratio
try:
    from chameleon.renderer.converter.brand_fonts import load_brand_font_manager
    from chameleon.renderer.converter.convert import convert_chameleon_to_crello
    from chameleon.renderer.converter.wrap import TextLayoutError
except ModuleNotFoundError:
    from renderer.converter.brand_fonts import load_brand_font_manager
    from renderer.converter.convert import convert_chameleon_to_crello
    from renderer.converter.wrap import TextLayoutError


_GEOMETRY_FIELDS = ("x", "y", "width", "height")


def _fail(message: str, **details: Any) -> NoReturn:
    raise InfeasibleLayoutError(
        InfeasibleReasonCode.NO_HARD_VALID_CANDIDATE,
        message,
        details,
    )


def _lcm(left: int, right: int) -> int:
    return abs(left * right) // gcd(left, right) if left and right else max(abs(left), abs(right))


def _smallest_integral_scale(values: list[Fraction]) -> Fraction:
    """Return the smallest positive scale making all values integral.

    Fractions are reduced before this calculation. For ``n/d``, a scale's
    numerator must contain ``d`` and its reduced denominator must divide ``n``;
    ``lcm(denominators) / gcd(numerators)`` is therefore a convenient exact
    generator for all admissible scales.
    """

    nonzero = [value for value in values if value]
    if not nonzero:
        return Fraction(1)
    denominator_lcm = 1
    numerator_gcd = 0
    for value in nonzero:
        numerator_gcd = gcd(numerator_gcd, abs(value.numerator))
        denominator_lcm = _lcm(denominator_lcm, value.denominator)
    if numerator_gcd == 0:
        return Fraction(1)
    return Fraction(denominator_lcm, numerator_gcd)


def _background_index(source: Mapping[str, Any], source_aabbs: list[Any]) -> int | None:
    candidates: list[tuple[int, Fraction, int]] = []
    canvas = source["canvas"]
    for index, (element, aabb) in enumerate(zip(source["elements"], source_aabbs)):
        if element["type"] != "image" or element.get("fit", "contain") != "cover":
            continue
        if not (
            aabb[0] <= 0
            and aabb[1] <= 0
            and aabb[2] >= to_fraction(canvas["width"])
            and aabb[3] >= to_fraction(canvas["height"])
        ):
            continue
        area = max(Fraction(0), aabb[2] - aabb[0]) * max(
            Fraction(0), aabb[3] - aabb[1]
        )
        candidates.append((int(element.get("z_index", 0)), -area, index))
    return min(candidates)[2] if candidates else None


def _global_transform(source: Mapping[str, Any], target: Mapping[str, Any]) -> tuple[Fraction, Fraction, Fraction]:
    source_width = to_fraction(source["canvas"]["width"])
    source_height = to_fraction(source["canvas"]["height"])
    target_width = to_fraction(target["width"])
    target_height = to_fraction(target["height"])
    scale = min(target_width / source_width, target_height / source_height)
    return scale, (target_width - source_width * scale) / 2, (target_height - source_height * scale) / 2


def _transformed_box(element: Mapping[str, Any], scale: Fraction, tx: Fraction, ty: Fraction) -> tuple[Fraction, Fraction, Fraction, Fraction]:
    width = to_fraction(element["width"]) * scale
    height = to_fraction(element["height"]) * scale
    center_x = (to_fraction(element["x"]) + to_fraction(element["width"]) / 2) * scale + tx
    center_y = (to_fraction(element["y"]) + to_fraction(element["height"]) / 2) * scale + ty
    return center_x - width / 2, center_y - height / 2, width, height


def _position_candidates(x: Fraction, y: Fraction) -> list[tuple[int, int]]:
    center_x = quantize_to_int(x)
    center_y = quantize_to_int(y)
    candidates: list[tuple[int, int]] = []
    for radius in range(3):
        for dx, dy in ((0, 0), (-radius, 0), (radius, 0), (0, -radius), (0, radius)):
            item = (center_x + dx, center_y + dy)
            if item not in candidates:
                candidates.append(item)
    return candidates


def _safe_geometry(
    element: Mapping[str, Any],
    x: int,
    y: int,
    width: int,
    height: int,
    target: Mapping[str, Any],
    expected_bleed: frozenset[str] | None,
) -> bool:
    if width < 0 or height < 0:
        return False
    if to_fraction(element["width"]) > 0 and to_fraction(element["height"]) > 0 and (width <= 0 or height <= 0):
        return False
    candidate = dict(element)
    candidate.update({"x": x, "y": y, "width": width, "height": height})
    aabb = rotated_aabb(candidate)
    if expected_bleed is not None:
        return (
            clipped_sides(aabb, target) == expected_bleed
            and intersects_canvas(aabb, target)
        )
    return is_contained_in_canvas(aabb, target)


def _choose_ratio_dimensions(
    element: Mapping[str, Any],
    raw_width: Fraction,
    raw_height: Fraction,
    raw_x: Fraction,
    raw_y: Fraction,
    target: Mapping[str, Any],
    expected_bleed: frozenset[str] | None,
) -> tuple[int, int, int, int] | None:
    ratio = reduced_ratio(element["width"], element["height"])
    if ratio is None:
        width = quantize_to_int(raw_width)
        height = quantize_to_int(raw_height)
        for x, y in _position_candidates(raw_x, raw_y):
            if _safe_geometry(element, x, y, width, height, target, expected_bleed):
                return x, y, width, height
        return None

    p, q = ratio
    preferred = raw_width / p
    floor_multiplier = preferred.numerator // preferred.denominator
    # Nearest lattice point is preferred, then progressively smaller positive
    # points are considered when the rounded point cannot fit a rotated AABB.
    multipliers: list[int] = []
    for multiplier in (floor_multiplier, floor_multiplier + 1):
        if multiplier >= 1 and multiplier not in multipliers:
            multipliers.append(multiplier)
    for multiplier in range(max(1, floor_multiplier - 1), 0, -1):
        if multiplier not in multipliers:
            multipliers.append(multiplier)
    for multiplier in multipliers:
        width, height = multiplier * p, multiplier * q
        for x, y in _position_candidates(raw_x + (raw_width - width) / 2, raw_y + (raw_height - height) / 2):
            if _safe_geometry(element, x, y, width, height, target, expected_bleed):
                return x, y, width, height
    return None


def _group_candidate(
    elements: list[Mapping[str, Any]],
    scale: Fraction,
    target: Mapping[str, Any],
    *,
    cover_element_id: Any | None = None,
) -> tuple[dict[str, tuple[int, int, int, int]], Fraction] | None:
    first = elements[0]
    first_x = to_fraction(first["x"])
    first_y = to_fraction(first["y"])
    values = []
    for element in elements:
        values.extend(
            [
                to_fraction(element["width"]),
                to_fraction(element["height"]),
                to_fraction(element["x"]) - first_x,
                to_fraction(element["y"]) - first_y,
            ]
        )
    unit = _smallest_integral_scale(values)
    minimum_scale = scale
    cover_element = next(
        (element for element in elements if element["id"] == cover_element_id),
        None,
    )
    source_aabbs = [rotated_aabb(element) for element in elements]
    if cover_element is not None:
        cover_aabb = rotated_aabb(cover_element)
        cover_width = cover_aabb[2] - cover_aabb[0]
        cover_height = cover_aabb[3] - cover_aabb[1]
        minimum_scale = max(
            minimum_scale,
            to_fraction(target["width"]) / cover_width,
            to_fraction(target["height"]) / cover_height,
        )
    scale_ratio = minimum_scale / unit
    minimum_multiplier = scale_ratio.numerator // scale_ratio.denominator
    if scale_ratio.numerator % scale_ratio.denominator:
        minimum_multiplier += 1
    if minimum_multiplier < 1:
        minimum_multiplier = 1
    group_scale = unit * minimum_multiplier

    def _translation_for_axis(axis: int, first_coordinate: Fraction, target_size: Fraction) -> Fraction | None:
        source_min = min(aabb[axis] for aabb in source_aabbs)
        source_max = max(aabb[axis + 2] for aabb in source_aabbs)
        source_center = (source_min + source_max) / 2
        lower: Fraction | None = None
        upper: Fraction | None = None
        for element, aabb in zip(elements, source_aabbs):
            if element["id"] == cover_element_id:
                element_lower = target_size - group_scale * aabb[axis + 2]
                element_upper = -group_scale * aabb[axis]
            else:
                element_lower = -group_scale * aabb[axis]
                element_upper = target_size - group_scale * aabb[axis + 2]
            lower = element_lower if lower is None else max(lower, element_lower)
            upper = element_upper if upper is None else min(upper, element_upper)
        assert lower is not None and upper is not None
        anchor_lower = lower + group_scale * first_coordinate
        anchor_upper = upper + group_scale * first_coordinate
        if anchor_lower > anchor_upper:
            return None
        minimum_anchor = -((-anchor_lower.numerator) // anchor_lower.denominator)
        maximum_anchor = anchor_upper.numerator // anchor_upper.denominator
        if minimum_anchor > maximum_anchor:
            return None
        desired_anchor = (
            target_size / 2
            - group_scale * source_center
            + group_scale * first_coordinate
        )
        anchor = min(maximum_anchor, max(minimum_anchor, quantize_to_int(desired_anchor)))
        return anchor - group_scale * first_coordinate

    tx = _translation_for_axis(0, first_x, to_fraction(target["width"]))
    ty = _translation_for_axis(1, first_y, to_fraction(target["height"]))
    if tx is None or ty is None:
        return None

    result: dict[str, tuple[int, int, int, int]] = {}
    for element in elements:
        width = quantize_to_int(to_fraction(element["width"]) * group_scale)
        height = quantize_to_int(to_fraction(element["height"]) * group_scale)
        x = quantize_to_int(to_fraction(element["x"]) * group_scale + tx)
        y = quantize_to_int(to_fraction(element["y"]) * group_scale + ty)
        candidate = dict(element)
        candidate.update({"x": x, "y": y, "width": width, "height": height})
        aabb = rotated_aabb(candidate)
        if element["id"] == cover_element_id:
            target_width = to_fraction(target["width"])
            target_height = to_fraction(target["height"])
            if not (
                aabb[0] <= 0
                and aabb[1] <= 0
                and aabb[2] >= target_width
                and aabb[3] >= target_height
            ):
                return None
        elif not _safe_geometry(element, x, y, width, height, target, None):
            return None
        result[element["id"]] = (x, y, width, height)
    return result, group_scale


def _text_fits(element: Mapping[str, Any], font_size: int, font_manager, target: Mapping[str, Any]) -> bool:
    candidate = dict(element)
    candidate["font_size"] = font_size
    try:
        # Passing the candidate through the production converter is important:
        # it exercises effective style runs, Unicode wrapping, line-height,
        # letter spacing, and positioned glyph bounds together.
        convert_chameleon_to_crello(
            {"canvas": dict(target), "elements": [candidate]}, font_manager
        )
    except TextLayoutError:
        return False
    return True


def _validate_candidate(
    source: Mapping[str, Any],
    response: Mapping[str, Any],
    background_index: int | None,
    source_aabbs: list[Any],
) -> bool:
    target = response["canvas"]
    response_elements = response["elements"]
    response_aabbs = [rotated_aabb(element) for element in response_elements]
    for index, (source_element, element, aabb) in enumerate(
        zip(source["elements"], response_elements, response_aabbs)
    ):
        if any(type(element[field]) is not int for field in _GEOMETRY_FIELDS):
            return False
        if element["width"] < 0 or element["height"] < 0:
            return False
        if source_element["width"] > 0 and source_element["height"] > 0 and (
            element["width"] <= 0 or element["height"] <= 0
        ):
            return False
        if index == background_index:
            if not intersects_canvas(aabb, target):
                return False
            continue
        expected_bleed = source_bleed_sides(source_element, source_aabbs[index], source["canvas"])
        if expected_bleed is None:
            if not is_contained_in_canvas(aabb, target):
                return False
        elif clipped_sides(aabb, target) != expected_bleed or not intersects_canvas(aabb, target):
            return False
        if source_element["type"] == "image" and index != background_index:
            source_ratio = reduced_ratio(source_element["width"], source_element["height"])
            if source_ratio is not None and (
                element["width"] * source_ratio[1] != element["height"] * source_ratio[0]
            ):
                return False
        if source_element["type"] == "text":
            if type(element["font_size"]) is not int or element["font_size"] < 1:
                return False
            line_count = element["content"].count("\n") + 1
            max_lines = element.get("max_lines")
            if max_lines is not None and line_count > max_lines:
                return False
            if to_fraction(element["font_size"]) * to_fraction(element.get("line_height", Fraction(6, 5))) * line_count > element["height"]:
                return False

    groups: dict[Any, list[int]] = {}
    for index, element in enumerate(source["elements"]):
        if element.get("group_id") is not None:
            groups.setdefault(element["group_id"], []).append(index)
    for indices in groups.values():
        try:
            derive_common_transform(
                [source["elements"][index] for index in indices],
                [response_elements[index] for index in indices],
            )
        except (KeyError, TypeError, ValueError):
            return False

    for left in range(len(response_elements)):
        if response_elements[left]["width"] <= 0 or response_elements[left]["height"] <= 0:
            continue
        for right in range(left + 1, len(response_elements)):
            if response_elements[right]["width"] <= 0 or response_elements[right]["height"] <= 0:
                continue
            if not positive_aabb_intersection(source_aabbs[left], source_aabbs[right]) and positive_aabb_intersection(response_aabbs[left], response_aabbs[right]):
                return False
    return True


def solve_near_isomorphic(
    source: Mapping[str, Any],
    target_canvas: Mapping[str, Any],
    *,
    font_manager=None,
    fonts_dir: str | None = None,
) -> dict[str, Any]:
    """Return one hard-safe, centered near-isomorphic candidate.

    Source mappings are shallow-copied at every preserved level; no source
    object or nested element mapping is mutated. Missing font faces and other
    runtime renderer failures intentionally propagate to the caller.
    """

    validate_source(source)
    validate_target_canvas(target_canvas)
    source_elements = list(source["elements"])
    source_aabbs = [rotated_aabb(element) for element in source_elements]
    background_index = _background_index(source, source_aabbs)
    scale, tx, ty = _global_transform(source, target_canvas)
    response_elements = [dict(element) for element in source_elements]
    group_indices: dict[Any, list[int]] = {}
    for index, element in enumerate(source_elements):
        if element.get("group_id") is not None:
            group_indices.setdefault(element["group_id"], []).append(index)

    transformed: dict[int, tuple[int, int, int, int]] = {}
    handled_groups: set[Any] = set()
    for group_id, indices in group_indices.items():
        cover_element_id = (
            source_elements[background_index]["id"]
            if background_index in indices
            else None
        )
        group = _group_candidate(
            [source_elements[index] for index in indices],
            scale,
            target_canvas,
            cover_element_id=cover_element_id,
        )
        if group is None:
            _fail("explicit group cannot be represented by one positive integer transform", group_id=group_id)
        geometries, _group_scale = group
        for index in indices:
            transformed[index] = geometries[source_elements[index]["id"]]
        handled_groups.add(group_id)

    target_width = to_fraction(target_canvas["width"])
    target_height = to_fraction(target_canvas["height"])
    for index, element in enumerate(source_elements):
        if index == background_index:
            if element.get("group_id") is None:
                transformed[index] = (0, 0, int(target_width), int(target_height))
                continue
            if index not in transformed:
                _fail("grouped background has no rigid candidate", element_id=element["id"])
            grouped_background = dict(element)
            grouped_background.update(dict(zip(_GEOMETRY_FIELDS, transformed[index])))
            background_aabb = rotated_aabb(grouped_background)
            if not (
                background_aabb[0] <= 0
                and background_aabb[1] <= 0
                and background_aabb[2] >= target_width
                and background_aabb[3] >= target_height
            ):
                _fail(
                    "rigid grouped background does not cover the target canvas",
                    element_id=element["id"],
                )
            continue
        if element.get("group_id") in handled_groups:
            continue
        raw_x, raw_y, raw_width, raw_height = _transformed_box(element, scale, tx, ty)
        expected_bleed = source_bleed_sides(element, source_aabbs[index], source["canvas"])
        geometry = _choose_ratio_dimensions(
            element,
            raw_width,
            raw_height,
            raw_x,
            raw_y,
            target_canvas,
            expected_bleed,
        )
        if geometry is None:
            _fail("foreground geometry cannot be represented as safe integer bounds", element_id=element["id"])
        transformed[index] = geometry

    for index, geometry in transformed.items():
        response_elements[index].update(dict(zip(_GEOMETRY_FIELDS, geometry)))

    text_indices = [index for index, element in enumerate(source_elements) if element["type"] == "text"]
    if text_indices:
        if font_manager is None:
            resolved_fonts_dir = fonts_dir or str(Path(__file__).resolve().parents[2] / "brand_kit" / "fonts")
            font_manager = load_brand_font_manager(resolved_fonts_dir)
        for index in text_indices:
            element = source_elements[index]
            preferred = max(1, quantize_to_int(to_fraction(element["font_size"]) * scale))
            selected = None
            for size in range(preferred, 0, -1):
                if _text_fits(response_elements[index], size, font_manager, target_canvas):
                    selected = size
                    break
            if selected is None:
                _fail("no integer text size fits the renderer bounds", element_id=element["id"])
            response_elements[index]["font_size"] = selected

    response = {
        "canvas": {"width": int(target_width), "height": int(target_height)},
        "elements": response_elements,
    }
    if not _validate_candidate(source, response, background_index, source_aabbs):
        _fail("candidate failed hard geometry, topology, ratio, or group validation")
    return response


__all__ = ["solve_near_isomorphic"]
