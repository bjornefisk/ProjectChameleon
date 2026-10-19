"""Bounded, source-aware column-pivot candidate generation.

This module owns one deterministic topology family.  It derives column extents
from source proportions and role extents, applies rigid transforms to explicit
groups, serializes once, then runs the same validator and renderer seam as the
near-isomorphic solver.  It intentionally does not rank topology families.
"""

from fractions import Fraction
from pathlib import Path
from typing import Any, Mapping, NoReturn

from ..contract import validate_response, validate_source, validate_target_canvas
from ..errors import InfeasibleLayoutError, InfeasibleReasonCode
from ..geometry.bounds import intersects_canvas, is_contained_in_canvas, rotated_aabb, source_bleed_sides
from ..geometry.math_util import quantize_to_int, to_fraction
from ..geometry.ratios import reduced_ratio
from .near_isomorphic import (
    _largest_fitting_font_size,
    _render_candidate,
    _text_fits,
    _preferred_font_size,
    _smallest_integral_scale,
)
from .roles import RoleKind, RoleModel, infer_roles

_GEOMETRY_FIELDS = ("x", "y", "width", "height")


def _fail(message: str, **details: Any) -> NoReturn:
    raise InfeasibleLayoutError(
        InfeasibleReasonCode.INCOMPLETE_SEARCH,
        message,
        {"search_kind": "column_pivot", "search_exhausted": False, **details},
    )

def _ceil_fraction(value: Fraction) -> int:
    return -((-value.numerator) // value.denominator)



def is_column_pivot_suitable(source: Mapping[str, Any], target_canvas: Mapping[str, Any], roles: RoleModel | None = None) -> bool:
    """Return whether source/target proportions support a column candidate.

    Suitability compares target and source proportions and requires distinct
    media/copy evidence.  It does not expose a fixed aspect-ratio delta or an
    element-id routing rule.
    """

    model = roles or infer_roles(source)
    source_ratio = to_fraction(source["canvas"]["width"]) / to_fraction(source["canvas"]["height"])
    target_ratio = to_fraction(target_canvas["width"]) / to_fraction(target_canvas["height"])
    role_values = {assignment.role for assignment in model.assignments}
    has_media = RoleKind.HERO_MEDIA in role_values or RoleKind.LOGO in role_values
    has_copy = bool(role_values & {RoleKind.HEADLINE, RoleKind.SUPPORTING_TEXT, RoleKind.CTA, RoleKind.BADGE})
    return target_ratio > source_ratio and has_media and has_copy


def _serialize_box(raw_box: tuple[Fraction, Fraction, Fraction, Fraction]) -> tuple[int, int, int, int]:
    return tuple(quantize_to_int(value) for value in raw_box)  # type: ignore[return-value]


def _image_dimensions(element: Mapping[str, Any], desired_width: Fraction, desired_height: Fraction) -> tuple[int, int] | None:
    ratio = reduced_ratio(element["width"], element["height"])
    if ratio is None:
        return quantize_to_int(desired_width), quantize_to_int(desired_height)
    p, q = ratio
    multiplier = min(
        quantize_to_int(desired_width) // p,
        quantize_to_int(desired_height) // q,
    )
    if multiplier < 1:
        return None
    return multiplier * p, multiplier * q


def _set_box(response: list[dict[str, Any]], index: int, box: tuple[int, int, int, int]) -> None:
    response[index].update(dict(zip(_GEOMETRY_FIELDS, box)))


def _group_span(elements: list[Mapping[str, Any]]) -> tuple[Fraction, Fraction, Fraction, Fraction]:
    aabbs = [rotated_aabb(element) for element in elements]
    return (
        min(aabb[0] for aabb in aabbs),
        min(aabb[1] for aabb in aabbs),
        max(aabb[2] for aabb in aabbs),
        max(aabb[3] for aabb in aabbs),
    )


def _place_group(
    source_elements: list[Mapping[str, Any]],
    response: list[dict[str, Any]],
    indices: list[int],
    anchor_x: Fraction,
    anchor_y: Fraction,
    max_width: Fraction,
    max_height: Fraction,
) -> bool:
    group = [source_elements[index] for index in indices]
    min_x, min_y, max_x, max_y = _group_span(group)
    span_x, span_y = max_x - min_x, max_y - min_y
    values: list[Fraction] = []
    first_x, first_y = to_fraction(group[0]["x"]), to_fraction(group[0]["y"])
    for element in group:
        values.extend(
            (
                to_fraction(element["width"]),
                to_fraction(element["height"]),
                to_fraction(element["x"]) - first_x,
                to_fraction(element["y"]) - first_y,
            )
        )
    unit = _smallest_integral_scale(values)
    desired = min(
        max_width / span_x if span_x > 0 else Fraction(1),
        max_height / span_y if span_y > 0 else Fraction(1),
        Fraction(1),
    )
    multiplier = (desired / unit).numerator // (desired / unit).denominator
    if multiplier < 1:
        return False
    scale = unit * multiplier
    tx = anchor_x - min_x * scale
    ty = anchor_y - min_y * scale
    for index in indices:
        element = source_elements[index]
        box = _serialize_box(
            (
                to_fraction(element["x"]) * scale + tx,
                to_fraction(element["y"]) * scale + ty,
                to_fraction(element["width"]) * scale,
                to_fraction(element["height"]) * scale,
            )
        )
        _set_box(response, index, box)
    return True


def _safe_box(
    source_element: Mapping[str, Any],
    box: tuple[int, int, int, int],
    target: Mapping[str, Any],
    bleed: frozenset[str] | None,
) -> bool:
    x, y, width, height = box
    if width < 0 or height < 0:
        return False
    if to_fraction(source_element["width"]) > 0 and to_fraction(source_element["height"]) > 0 and (width <= 0 or height <= 0):
        return False
    candidate = dict(source_element)
    candidate.update(dict(zip(_GEOMETRY_FIELDS, box)))
    aabb = rotated_aabb(candidate)
    if bleed is None:
        return is_contained_in_canvas(aabb, target)
    return intersects_canvas(aabb, target) and frozenset(
        side for side, crossed in (("left", aabb[0] < 0), ("top", aabb[1] < 0), ("right", aabb[2] > target["width"]), ("bottom", aabb[3] > target["height"])) if crossed
    ) == bleed


def _role_indices(model: RoleModel) -> dict[RoleKind, list[int]]:
    result: dict[RoleKind, list[int]] = {}
    for assignment in model.assignments:
        result.setdefault(assignment.role, []).append(assignment.index)
    return result

def _bleed_position(size: int, canvas_size: int, sides: frozenset[str], low: str, high: str) -> int:
    """Return integer placement that crosses one side and keeps overlap positive."""

    if low in sides and high in sides:
        return -1 if size > canvas_size + 1 else canvas_size - size + 1
    overshoot = min(max(1, size // 5), size - 1)
    if low in sides:
        return -overshoot
    if high in sides:
        return canvas_size - size + overshoot
    return max(0, canvas_size - size)



def _build_column_candidate(
    source: Mapping[str, Any],
    target_canvas: Mapping[str, Any],
    model: RoleModel,
    *,
    font_manager=None,
    fonts_dir: str | None = None,
) -> dict[str, Any]:
    source_elements = list(source["elements"])
    response_elements = [dict(element) for element in source_elements]
    target_width = to_fraction(target_canvas["width"])
    target_height = to_fraction(target_canvas["height"])
    source_width = to_fraction(source["canvas"]["width"])
    source_height = to_fraction(source["canvas"]["height"])
    roles = _role_indices(model)
    transformed: set[int] = set()

    if model.background_index is not None:
        index = model.background_index
        _set_box(response_elements, index, (0, 0, int(target_width), int(target_height)))
        transformed.add(index)

    hero_index = roles.get(RoleKind.HERO_MEDIA, [None])[0]
    if hero_index is None:
        # A logo is a supported media anchor when role inference has no
        # distinct hero (for example, a grouped hero image).
        hero_index = roles.get(RoleKind.LOGO, [None])[0]
    if hero_index is None:
        _fail("column pivot requires a source media role")
    hero = source_elements[hero_index]
    media_fraction = min(Fraction(1), max(Fraction(1, 4), to_fraction(hero["width"]) / source_width))
    gutter = max(Fraction(1), target_width * Fraction(1, 40))
    left_slot = target_width * media_fraction
    right_x = left_slot + gutter
    right_width = target_width - right_x - gutter
    if right_width <= 0:
        _fail("target has no positive copy column")

    # The hero extent is target-proportional and source-derived, then snapped to
    # its exact reduced image-ratio lattice.
    hero_side = min(target_height * media_fraction, target_height * Fraction(3, 4))
    dimensions = _image_dimensions(hero, hero_side, hero_side)
    if dimensions is None:
        _fail("hero image ratio has no positive integer lattice point")
    hero_width, hero_height = dimensions
    hero_x = quantize_to_int((left_slot - hero_width) / 2)
    hero_y = quantize_to_int(target_height - hero_height - target_height * Fraction(7, 100))
    hero_box = (hero_x, hero_y, hero_width, hero_height)
    if not _safe_box(hero, hero_box, target_canvas, None):
        _fail("hero image cannot fit the media column", element_id=hero["id"])
    _set_box(response_elements, hero_index, hero_box)
    transformed.add(hero_index)

    # Place non-background images other than hero in the media column, above or
    # beside the hero according to their source-proportional extents.
    for index in roles.get(RoleKind.LOGO, []) + roles.get(RoleKind.IMAGE, []):
        if index in transformed:
            continue
        element = source_elements[index]
        desired_width = min(left_slot * to_fraction(element["width"]) / source_width, left_slot - gutter)
        desired_height = target_height * to_fraction(element["height"]) / source_height
        dimensions = _image_dimensions(element, desired_width, desired_height)
        if dimensions is None:
            _fail("image ratio has no positive integer lattice point", element_id=element["id"])
        width, height = dimensions
        x = quantize_to_int((left_slot - width) / 2)
        y = quantize_to_int(target_height * to_fraction(element["y"]) / source_height)
        if y + height > hero_y and x + width > hero_x and x < hero_x + hero_width:
            y = max(0, hero_y - height - quantize_to_int(gutter))
        box = (x, y, width, height)
        if not _safe_box(element, box, target_canvas, None):
            _fail("image cannot fit the media column", element_id=element["id"])
        _set_box(response_elements, index, box)
        transformed.add(index)

    # Explicit groups are copied as one scale/translation. Their slots are
    # derived from target dimensions and source group extents, never IDs.
    groups: dict[Any, list[int]] = {}
    for index, element in enumerate(source_elements):
        if element.get("group_id") is not None:
            groups.setdefault(element["group_id"], []).append(index)
    for group_id, indices in groups.items():
        role = model.assignments[indices[0]].role
        if role == RoleKind.BADGE:
            anchor_x = right_x
            anchor_y = target_height * Fraction(1, 20)
            max_width = right_width * Fraction(2, 5)
            max_height = target_height * Fraction(1, 4)
        elif role == RoleKind.CTA:
            max_width = right_width * Fraction(3, 5)
            max_height = target_height * Fraction(1, 3)
            anchor_x = right_x + (right_width - max_width) / 2
            anchor_y = target_height - max_height - target_height * Fraction(1, 20)
        else:
            max_width, max_height = right_width, target_height / 2
            anchor_x, anchor_y = right_x, target_height / 2
        if not _place_group(source_elements, response_elements, indices, anchor_x, anchor_y, max_width, max_height):
            _fail("explicit group cannot be represented by one positive integer transform", group_id=group_id)
        transformed.update(indices)

    text_indices = roles.get(RoleKind.HEADLINE, []) + roles.get(RoleKind.SUPPORTING_TEXT, [])
    for index in text_indices:
        element = source_elements[index]
        # Text boxes use source proportions for height, with a renderer-safe
        # minimum based on the source font size and line-height.
        width = max(1, quantize_to_int(right_width))
        source_height_fraction = to_fraction(element["height"]) / source_height
        font_floor_height = to_fraction(element.get("font_size", 1)) * to_fraction(element.get("line_height", Fraction(6, 5)))
        height = max(quantize_to_int(target_height * source_height_fraction), _ceil_fraction(font_floor_height))
        if index in transformed:
            continue
        if model.assignments[index].role == RoleKind.HEADLINE:
            y = quantize_to_int(target_height * Fraction(1, 4))
        else:
            headline_indices = roles.get(RoleKind.HEADLINE, [])
            headline_end = 0
            if headline_indices:
                headline_end = quantize_to_int(target_height * Fraction(1, 4)) + max(
                    1, quantize_to_int(target_height * (to_fraction(source_elements[headline_indices[0]]["height"]) / source_height)))
            y = headline_end + quantize_to_int(target_height * Fraction(1, 25))
        x = quantize_to_int(right_x)
        if y + height > target_height:
            y = max(0, int(target_height) - height - quantize_to_int(gutter))
        box = (x, y, width, height)
        if not _safe_box(element, box, target_canvas, None):
            _fail("text cannot fit the copy column", element_id=element["id"])
        _set_box(response_elements, index, box)
        transformed.add(index)

    # Ungrouped decorations retain their source bleed side set; other shapes
    # are placed at the opposite edge with source-proportional dimensions.
    decoration_indices = roles.get(RoleKind.DECORATION, []) + roles.get(RoleKind.SHAPE, [])
    for index in decoration_indices:
        if index in transformed:
            continue
        element = source_elements[index]
        source_aabb = rotated_aabb(element)
        bleed = source_bleed_sides(element, source_aabb, source["canvas"])
        width = max(1, quantize_to_int(target_height * to_fraction(element["width"]) / source_width))
        height = max(1, quantize_to_int(target_height * to_fraction(element["height"]) / source_height))
        if bleed is not None:
            if "left" in bleed or "right" in bleed:
                width = max(2, width)
            if "top" in bleed or "bottom" in bleed:
                height = max(2, height)
            x = _bleed_position(width, int(target_width), bleed, "left", "right")
            y = _bleed_position(height, int(target_height), bleed, "top", "bottom")
        else:
            x = max(0, int(target_width) - width - quantize_to_int(gutter))
            y = max(0, int(target_height) - height - quantize_to_int(gutter))
        box = (x, y, width, height)
        if not _safe_box(element, box, target_canvas, bleed):
            _fail("decoration cannot preserve source containment or bleed", element_id=element["id"])
        _set_box(response_elements, index, box)
        transformed.add(index)

    # Any record not covered by an inferred role is unsupported rather than
    # silently shed.  Keep its source record and fail the bounded family.
    if len(transformed) != len(source_elements):
        missing = [source_elements[index]["id"] for index in range(len(source_elements)) if index not in transformed]
        _fail("column pivot has no source-derived placement for records", element_ids=missing)

    # Renderer-in-loop text fitting is performed after geometry is serialized.
    manager = font_manager
    text_all = [index for index, element in enumerate(source_elements) if element.get("type") == "text"]
    if text_all:
        from .near_isomorphic import _renderer_components

        if manager is None:
            load_brand_font_manager = _renderer_components()[0]
            resolved_fonts_dir = fonts_dir or str(Path(__file__).resolve().parents[2] / "brand_kit" / "fonts")
            manager = load_brand_font_manager(resolved_fonts_dir)
        for index in text_all:
            element = source_elements[index]
            preferred = _preferred_font_size(to_fraction(element.get("font_size", 1)), Fraction(1))
            font_search: dict[str, Any] = {}
            selected = _largest_fitting_font_size(
                response_elements[index],
                preferred,
                manager,
                target_canvas,
                fit=_text_fits,
                search_details=font_search,
            )
            if selected is None:
                _fail(
                    "no integer text size fits the renderer bounds",
                    element_id=element["id"],
                    font_search=font_search,
                )
            response_elements[index]["font_size"] = selected

    response = {
        "canvas": {"width": int(target_width), "height": int(target_height)},
        "elements": response_elements,
    }
    try:
        validate_response(source, target_canvas, response)
    except InfeasibleLayoutError as error:
        _fail(
            "column-pivot candidate failed serialized hard validation",
            reason_code=error.reason_code.value,
            reason=error.message,
            details=error.details,
        )
    return response


def generate_column_pivot_candidate(
    source: Mapping[str, Any],
    target_canvas: Mapping[str, Any],
    *,
    font_manager=None,
    fonts_dir: str | None = None,
    assets_dir: str | None = None,
    roles: RoleModel | None = None,
) -> dict[str, Any]:
    """Generate and serialize one source-aware column-pivot candidate."""

    validate_source(source)
    validate_target_canvas(target_canvas)
    model = roles or infer_roles(source)
    if not is_column_pivot_suitable(source, target_canvas, model):
        _fail("source and target proportions do not support a column pivot")
    response = _build_column_candidate(
        source,
        target_canvas,
        model,
        font_manager=font_manager,
        fonts_dir=fonts_dir,
    )
    _render_candidate(response, assets_dir, fonts_dir, font_manager)
    validate_response(source, target_canvas, response)
    return response


def solve_column_pivot(
    source: Mapping[str, Any],
    target_canvas: Mapping[str, Any],
    *,
    font_manager=None,
    fonts_dir: str | None = None,
    assets_dir: str | None = None,
    roles: RoleModel | None = None,
) -> dict[str, Any]:
    validate_source(source)
    validate_target_canvas(target_canvas)
    model = roles or infer_roles(source)
    if not is_column_pivot_suitable(source, target_canvas, model):
        _fail("source and target proportions do not support a column pivot")
    response = _build_column_candidate(
        source,
        target_canvas,
        model,
        font_manager=font_manager,
        fonts_dir=fonts_dir,
    )
    _render_candidate(response, assets_dir, fonts_dir, font_manager)
    validate_response(source, target_canvas, response)
    return response


# Short alias for callers that treat topology families as candidate functions.
column_pivot_candidate = generate_column_pivot_candidate

__all__ = [
    "column_pivot_candidate",
    "generate_column_pivot_candidate",
    "is_column_pivot_suitable",
    "solve_column_pivot",
]
