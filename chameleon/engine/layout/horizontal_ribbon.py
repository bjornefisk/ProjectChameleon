"""Deterministic horizontal-ribbon and spatial-compression candidates.

The ribbon family is source driven. Explicit ``group_id`` records remain rigid
units, source order is used as the stable tie-break, and the candidate packer
uses the actual rotated AABBs rather than a fixed element-role template.
"""

from collections.abc import Mapping
from fractions import Fraction
from pathlib import Path
from typing import Any, NoReturn

from ..contract import validate_response, validate_source, validate_target_canvas
from ..errors import InfeasibleLayoutError, InfeasibleReasonCode
from ..geometry.bounds import (
    clipped_sides,
    intersects_canvas,
    is_contained_in_canvas,
    positive_aabb_intersection,
    rotated_aabb,
    source_bleed_sides,
)
from ..geometry.math_util import quantize_to_int, to_fraction
from ..geometry.ratios import reduced_ratio
from .near_isomorphic import (
    _largest_fitting_font_size,
    _preferred_font_size,
    _render_candidate,
    _smallest_integral_scale,
)
from .roles import RoleModel, infer_roles

_GEOMETRY_FIELDS = ("x", "y", "width", "height")


def _fail(message: str, **details: Any) -> NoReturn:
    raise InfeasibleLayoutError(
        InfeasibleReasonCode.INCOMPLETE_SEARCH,
        message,
        {"search_kind": "horizontal_ribbon", "search_exhausted": False, **details},
    )


def _ceil_fraction(value: Fraction) -> int:
    return -((-value.numerator) // value.denominator)


def _floor_fraction(value: Fraction) -> int:
    return value.numerator // value.denominator


def is_horizontal_ribbon_suitable(
    source: Mapping[str, Any], target_canvas: Mapping[str, Any]
) -> bool:
    """Return whether source evidence supports a short, horizontal ribbon.

    Suitability uses source/target geometry and foreground extents. It does not
    expose a fixed aspect-ratio-delta threshold or an element-id route.
    """

    source_width = to_fraction(source["canvas"]["width"])
    source_height = to_fraction(source["canvas"]["height"])
    target_width = to_fraction(target_canvas["width"])
    target_height = to_fraction(target_canvas["height"])
    if not source["elements"] or target_width <= target_height:
        return False
    model = infer_roles(source)
    foreground_heights = [
        rotated_aabb(element)[3] - rotated_aabb(element)[1]
        for index, element in enumerate(source["elements"])
        if index != model.background_index and to_fraction(element["width"]) > 0 and to_fraction(element["height"]) > 0
    ]
    if not foreground_heights:
        return False
    return (
        target_width < source_width
        and target_width / target_height > source_width / source_height
        and target_height < source_height
        and target_height <= max(foreground_heights)
    )


def _group_units(source: Mapping[str, Any]) -> list[tuple[int, list[int]]]:
    groups: dict[Any, list[int]] = {}
    for index, element in enumerate(source["elements"]):
        if element.get("group_id") is not None:
            groups.setdefault(element["group_id"], []).append(index)
    units: list[tuple[int, list[int]]] = []
    seen: set[int] = set()
    for index, element in enumerate(source["elements"]):
        if index in seen or element.get("group_id") is None:
            continue
        indices = groups[element["group_id"]]
        seen.update(indices)
        units.append((index, indices))
    return units


def _source_span(elements: list[Mapping[str, Any]]) -> tuple[Fraction, Fraction, Fraction, Fraction]:
    aabbs = [rotated_aabb(element) for element in elements]
    return (
        min(aabb[0] for aabb in aabbs),
        min(aabb[1] for aabb in aabbs),
        max(aabb[2] for aabb in aabbs),
        max(aabb[3] for aabb in aabbs),
    )


def _group_scale(elements: list[Mapping[str, Any]], desired: Fraction) -> Fraction:
    values: list[Fraction] = []
    first_x = to_fraction(elements[0]["x"])
    first_y = to_fraction(elements[0]["y"])
    for element in elements:
        values.extend(
            (
                to_fraction(element["width"]),
                to_fraction(element["height"]),
                to_fraction(element["x"]) - first_x,
                to_fraction(element["y"]) - first_y,
            )
        )
    unit = _smallest_integral_scale(values)
    if desired <= unit:
        return unit
    multiplier = (desired / unit).numerator // (desired / unit).denominator
    return unit * max(1, multiplier)


def _relative_group_boxes(
    elements: list[Mapping[str, Any]], scale: Fraction
) -> list[tuple[int, int, int, int]]:
    first_x = to_fraction(elements[0]["x"])
    first_y = to_fraction(elements[0]["y"])
    boxes: list[tuple[int, int, int, int]] = []
    for element in elements:
        boxes.append(
            (
                quantize_to_int((to_fraction(element["x"]) - first_x) * scale),
                quantize_to_int((to_fraction(element["y"]) - first_y) * scale),
                quantize_to_int(to_fraction(element["width"]) * scale),
                quantize_to_int(to_fraction(element["height"]) * scale),
            )
        )
    return boxes


def _image_dimensions(
    element: Mapping[str, Any], max_width: int, max_height: int
) -> tuple[int, int] | None:
    ratio = reduced_ratio(element["width"], element["height"])
    if ratio is None:
        return max(1, max_width), max(1, max_height)
    p, q = ratio
    multiplier = min(max_width // p, max_height // q)
    if multiplier < 1:
        return None
    return multiplier * p, multiplier * q


def _extent_size(aabb: tuple[Any, Any, Any, Any]) -> tuple[int, int]:
    return max(0, _ceil_fraction(to_fraction(aabb[2] - aabb[0]))), max(
        0, _ceil_fraction(to_fraction(aabb[3] - aabb[1]))
    )


def _candidate_units(
    source: Mapping[str, Any], background: int | None
) -> list[tuple[int, list[int]]]:
    units = _group_units(source)
    grouped = {index for _, indices in units for index in indices}
    result = list(units)
    result.extend(
        (index, [index])
        for index in range(len(source["elements"]))
        if index not in grouped and index != background
    )
    return result


def _singleton_dimensions(
    element: Mapping[str, Any],
    target_width: int,
    target_height: int,
    unit_count: int,
    axis: str,
    source_canvas: Mapping[str, Any],
    *,
    text_dimensions: tuple[int, int] | None = None,
    art_scale: Fraction = Fraction(1),
) -> tuple[int, int] | None:
    source_width = to_fraction(element["width"])
    source_height = to_fraction(element["height"])
    if source_width <= 0 or source_height <= 0:
        return 0, 0
    if element["type"] == "image":
        if axis == "horizontal":
            scale = min(Fraction(1), Fraction(target_height, 1) / to_fraction(source_canvas["height"]))
        else:
            scale = min(Fraction(1), Fraction(target_width, 1) / to_fraction(source_canvas["width"]))
        scale *= art_scale
        desired_width = max(1, quantize_to_int(source_width * scale))
        desired_height = max(1, quantize_to_int(source_height * scale))
        return _image_dimensions(element, desired_width, desired_height)
    if element["type"] == "text":
        if text_dimensions is not None:
            return (
                min(target_width, max(1, text_dimensions[0])),
                min(target_height, max(1, text_dimensions[1])),
            )
    if element["type"] == "text":
        if axis == "horizontal":
            # More independent units produce narrower, denser text columns;
            # the actual font search below is renderer-in-the-loop.
            width_divisor = max(12, unit_count + 8)
            width = max(12, target_width // width_divisor)
            height = max(8, target_height // 5)
        else:
            width = max(8, target_width // 2)
            height = max(12, target_height // max(3, unit_count // 2 + 1))
        return min(target_width, width), min(target_height, height)
    if axis == "horizontal":
        scale = min(Fraction(1), Fraction(target_height, 1) / to_fraction(source_canvas["height"]))
    else:
        scale = min(Fraction(1), Fraction(target_width, 1) / to_fraction(source_canvas["width"]))
    scale *= art_scale
    return max(1, min(target_width, quantize_to_int(source_width * scale))), max(
        1, min(target_height, quantize_to_int(source_height * scale))
    )


def _make_plan(
    source_elements: list[Mapping[str, Any]],
    first: int,
    indices: list[int],
    *,
    source_canvas: Mapping[str, Any],
    target_width: int,
    target_height: int,
    unit_count: int,
    group_budget: Fraction,
    axis: str,
    text_dimensions_by_index: Mapping[int, tuple[int, int]] | None = None,
    art_scale: Fraction = Fraction(1),
) -> dict[str, Any] | None:
    if len(indices) > 1:
        elements = [source_elements[index] for index in indices]
        span = _source_span(elements)
        primary_extent = span[2] - span[0] if axis == "horizontal" else span[3] - span[1]
        cross_extent = span[3] - span[1] if axis == "horizontal" else span[2] - span[0]
        primary_limit = Fraction(target_width if axis == "horizontal" else target_height)
        cross_limit = Fraction(target_height if axis == "horizontal" else target_width)
        desired = min(
            group_budget,
            primary_limit / max(Fraction(1), primary_extent),
            cross_limit / max(Fraction(1), cross_extent),
        )
        scale = _group_scale(elements, desired)
        boxes = _relative_group_boxes(elements, scale)
        local = []
        for element, box in zip(elements, boxes):
            candidate = dict(element)
            candidate.update(dict(zip(_GEOMETRY_FIELDS, box)))
            local.append(candidate)
        base_span = _source_span(local)
        footprint = _extent_size(base_span)
        if footprint[0] > target_width or footprint[1] > target_height:
            return None
        return {
            "first": first,
            "indices": tuple(indices),
            "kind": "group",
            "boxes": tuple(boxes),
            "base_aabbs": tuple(rotated_aabb(element) for element in local),
            "base_span": base_span,
            "footprint": footprint,
            "bleed": None,
            "pack_priority": 0,
        }

    element = source_elements[first]
    dimensions = _singleton_dimensions(
        element,
        target_width,
        target_height,
        unit_count,
        axis,
        source_canvas,
        text_dimensions=None if text_dimensions_by_index is None else text_dimensions_by_index.get(first),
        art_scale=art_scale,
    )
    if dimensions is None:
        return None
    width, height = dimensions
    box_x = 1 if element["type"] == "text" else 0
    box_y = 1 if element["type"] == "text" else 0
    candidate = dict(element)
    candidate.update({"x": box_x, "y": box_y, "width": width, "height": height})
    base_aabb = rotated_aabb(candidate)
    bleed = source_bleed_sides(element, rotated_aabb(element), source_canvas)
    return {
        "first": first,
        "indices": (first,),
        "kind": "single",
        "boxes": ((box_x, box_y, width, height),),
        "base_aabbs": (base_aabb,),
        "base_span": base_aabb,
        "footprint": _extent_size(base_aabb),
        "pack_priority": 1 if element["type"] == "image" else 2 if element["type"] == "shape" else 3,
        "bleed": bleed,
    }



def _materialize_plan(
    plan: Mapping[str, Any], source_elements: list[Mapping[str, Any]], anchor_x: int, anchor_y: int
) -> tuple[list[tuple[int, int, int, int]], list[Any]]:
    boxes = [
        (x + anchor_x, y + anchor_y, width, height)
        for x, y, width, height in plan["boxes"]
    ]
    aabbs = []
    for element, box in zip((source_elements[index] for index in plan["indices"]), boxes):
        candidate = dict(element)
        candidate.update(dict(zip(_GEOMETRY_FIELDS, box)))
        aabbs.append(rotated_aabb(candidate))
    return boxes, aabbs


def _axis_candidates(
    plan: Mapping[str, Any], occupied: list[tuple[tuple[int, ...], list[Any]]], target_width: int, target_height: int
) -> tuple[list[int], list[int]]:
    base_span = plan["base_span"]
    min_x = _ceil_fraction(-to_fraction(base_span[0]))
    max_x = _floor_fraction(Fraction(target_width) - to_fraction(base_span[2]))
    min_y = _ceil_fraction(-to_fraction(base_span[1]))
    max_y = _floor_fraction(Fraction(target_height) - to_fraction(base_span[3]))
    xs = {min_x, max_x}
    ys = {min_y, max_y}
    for _indices, aabbs in occupied:
        for aabb in aabbs:
            xs.add(_ceil_fraction(to_fraction(aabb[2]) - to_fraction(base_span[0])))
            xs.add(_floor_fraction(to_fraction(aabb[0]) - to_fraction(base_span[2])))
            ys.add(_ceil_fraction(to_fraction(aabb[3]) - to_fraction(base_span[1])))
            ys.add(_floor_fraction(to_fraction(aabb[1]) - to_fraction(base_span[3])))
    if plan["bleed"]:
        if "left" in plan["bleed"]:
            xs.add(min_x - 1)
        if "right" in plan["bleed"]:
            xs.add(max_x + 1)
        if "top" in plan["bleed"]:
            ys.add(min_y - 1)
        if "bottom" in plan["bleed"]:
            ys.add(max_y + 1)
    return sorted(xs), sorted(ys)


def _valid_plan_placement(
    plan: Mapping[str, Any],
    source_elements: list[Mapping[str, Any]],
    boxes: list[tuple[int, int, int, int]],
    aabbs: list[Any],
    occupied: list[tuple[tuple[int, ...], list[Any]]],
    target_canvas: Mapping[str, Any],
    model: RoleModel,
) -> bool:
    bleed = plan["bleed"]
    for aabb in aabbs:
        if bleed is None:
            if not is_contained_in_canvas(aabb, target_canvas):
                return False
        elif clipped_sides(aabb, target_canvas) != bleed or not intersects_canvas(aabb, target_canvas):
            return False
    for indices, occupied_aabbs in occupied:
        for new_index, new_aabb in zip(plan["indices"], aabbs):
            for old_index, old_aabb in zip(indices, occupied_aabbs):
                if model.overlaps(new_index, old_index):
                    continue
                if positive_aabb_intersection(new_aabb, old_aabb):
                    return False
    return True


def _build_extreme_candidate(
    source: Mapping[str, Any],
    target_canvas: Mapping[str, Any],
    *,
    variant: str = "source_proportional",
    axis: str = "horizontal",
    font_manager=None,
    fonts_dir: str | None = None,
) -> dict[str, Any]:
    validate_source(source)
    validate_target_canvas(target_canvas)
    model = infer_roles(source)
    source_elements = list(source["elements"])
    target_width = int(target_canvas["width"])
    target_height = int(target_canvas["height"])
    background = model.background_index
    units = _candidate_units(source, background)
    unit_count = len(units)
    group_source_spans = []
    for _first, indices in units:
        if len(indices) > 1:
            span = _source_span([source_elements[index] for index in indices])
            group_source_spans.append(
                span[2] - span[0] if axis == "horizontal" else span[3] - span[1]
            )
    primary_limit = Fraction(target_width if axis == "horizontal" else target_height)
    group_budget = min(
        Fraction(1),
        primary_limit / sum(group_source_spans) if group_source_spans else Fraction(1),
    )

    text_variants: list[Mapping[int, tuple[int, int]] | None] = [None]
    wide_text: dict[int, tuple[int, int]] = {}
    for index, element in enumerate(source_elements):
        if element["type"] != "text" or element.get("group_id") is not None:
            continue
        if axis == "horizontal":
            wide_text[index] = (
                max(12, target_width // 6),
                max(12, target_height // 3),
            )
        else:
            wide_text[index] = (
                max(12, target_width // 2),
                max(12, target_height // 2),
            )
    if wide_text:
        text_variants.append(wide_text)

    attempts: list[dict[str, Any]] = []
    art_scales = (
        (Fraction(1), Fraction(1, 2))
        if variant != "dominant_copy"
        else (Fraction(1, 2), Fraction(1))
    )
    ordered_text_variants = (
        tuple(reversed(text_variants))
        if variant == "dominant_copy"
        else tuple(text_variants)
    )
    for art_scale in art_scales:
        for text_dimensions in ordered_text_variants:
            plans: list[dict[str, Any]] = []
            for first, indices in units:
                plan = _make_plan(
                    source_elements,
                    first,
                    indices,
                    source_canvas=source["canvas"],
                    target_width=target_width,
                    target_height=target_height,
                    unit_count=unit_count,
                    group_budget=group_budget,
                    axis=axis,
                    text_dimensions_by_index=text_dimensions,
                    art_scale=art_scale,
                )
                if plan is None:
                    plans = []
                    break
                plans.append(plan)
            if not plans:
                attempts.append(
                    {
                        "art_scale": str(art_scale),
                        "text_variant": text_dimensions is not None,
                        "status": "geometry",
                    }
                )
                continue

            orderings = (
                "priority",
                "area",
                "primary",
            )
            for order in orderings:
                if order == "area":
                    ordered_plans = sorted(
                        plans,
                        key=lambda plan: (
                            -(plan["footprint"][0] * plan["footprint"][1]),
                            -max(plan["footprint"]),
                            plan["first"],
                        ),
                    )
                elif order == "primary":
                    ordered_plans = sorted(
                        plans,
                        key=lambda plan: (
                            -(plan["footprint"][0] if axis == "horizontal" else plan["footprint"][1]),
                            -(plan["footprint"][0] * plan["footprint"][1]),
                            plan["first"],
                        ),
                    )
                else:
                    ordered_plans = sorted(
                        plans,
                        key=lambda plan: (
                            plan["pack_priority"],
                            -(plan["footprint"][0] * plan["footprint"][1]),
                            -max(plan["footprint"]),
                            plan["first"],
                        ),
                    )
                response = [dict(element) for element in source_elements]
                if background is not None:
                    if source_elements[background].get("group_id") is not None:
                        _fail(
                            "extreme topology cannot transform a grouped cover background",
                            element_id=source_elements[background]["id"],
                        )
                    response[background].update(
                        {"x": 0, "y": 0, "width": target_width, "height": target_height}
                    )
                occupied: list[tuple[tuple[int, ...], list[Any]]] = []
                failed_plan = None
                for plan in ordered_plans:
                    xs, ys = _axis_candidates(plan, occupied, target_width, target_height)
                    placements = (
                        [(x, y) for y in ys for x in xs]
                        if axis == "horizontal"
                        else [(x, y) for x in xs for y in ys]
                    )
                    selected = None
                    for anchor_x, anchor_y in placements:
                        boxes, aabbs = _materialize_plan(
                            plan, source_elements, anchor_x, anchor_y
                        )
                        if _valid_plan_placement(
                            plan,
                            source_elements,
                            boxes,
                            aabbs,
                            occupied,
                            target_canvas,
                            model,
                        ):
                            selected = boxes, aabbs
                            break
                    if selected is None:
                        failed_plan = plan
                        break
                    boxes, aabbs = selected
                    for index, box in zip(plan["indices"], boxes):
                        response[index].update(dict(zip(_GEOMETRY_FIELDS, box)))
                    occupied.append((plan["indices"], aabbs))
                attempts.append(
                    {
                        "art_scale": str(art_scale),
                        "text_variant": text_dimensions is not None,
                        "order": order,
                        "status": "packing" if failed_plan is not None else "packed",
                        "failed_ids": []
                        if failed_plan is None
                        else [source_elements[index]["id"] for index in failed_plan["indices"]],
                    }
                )
                if failed_plan is not None:
                    continue

                if font_manager is None and any(element["type"] == "text" for element in source_elements):
                    from .near_isomorphic import _renderer_components

                    load_brand_font_manager = _renderer_components()[0]
                    resolved_fonts_dir = fonts_dir or str(Path(__file__).resolve().parents[2] / "brand_kit" / "fonts")
                    font_manager = load_brand_font_manager(resolved_fonts_dir)
                text_failed = False
                for index, element in enumerate(source_elements):
                    if element["type"] != "text":
                        continue
                    source_size = to_fraction(element["font_size"])
                    scale = (
                        min(
                            Fraction(1),
                            Fraction(target_height, 1) / to_fraction(source["canvas"]["height"]),
                        )
                        if axis == "horizontal"
                        else min(
                            Fraction(1),
                            Fraction(target_width, 1) / to_fraction(source["canvas"]["width"]),
                        )
                    )
                    selected_size = _largest_fitting_font_size(
                        response[index],
                        _preferred_font_size(source_size, scale),
                        font_manager,
                        target_canvas,
                    )
                    if selected_size is None:
                        text_failed = True
                        break
                    response[index]["font_size"] = selected_size
                if text_failed:
                    continue
                result = {
                    "canvas": {"width": target_width, "height": target_height},
                    "elements": response,
                }
                try:
                    validate_response(source, target_canvas, result)
                except InfeasibleLayoutError:
                    continue
                return result

    _fail(
        "bounded extreme-topology search exhausted without a hard-valid candidate",
        attempts=attempts,
        search_exhausted=True,
    )


def generate_horizontal_ribbon_candidate(
    source: Mapping[str, Any],
    target_canvas: Mapping[str, Any],
    *,
    variant: str = "source_proportional",
    font_manager=None,
    fonts_dir: str | None = None,
    assets_dir: str | None = None,
    rendered_output: dict[str, Any] | None = None,
) -> dict[str, Any]:
    validate_source(source)
    validate_target_canvas(target_canvas)
    if not is_horizontal_ribbon_suitable(source, target_canvas):
        _fail("source and target proportions do not support a horizontal ribbon")
    response = _build_extreme_candidate(
        source,
        target_canvas,
        font_manager=font_manager,
        fonts_dir=fonts_dir,
        variant=variant,
    )
    rendered_png = _render_candidate(response, assets_dir, fonts_dir, font_manager)
    if rendered_output is not None:
        rendered_output["png"] = rendered_png
    return response


solve_horizontal_ribbon = generate_horizontal_ribbon_candidate
horizontal_ribbon_candidate = generate_horizontal_ribbon_candidate
generate_horizontal_ribbon = generate_horizontal_ribbon_candidate

__all__ = [
    "generate_horizontal_ribbon",
    "generate_horizontal_ribbon_candidate",
    "horizontal_ribbon_candidate",
    "is_horizontal_ribbon_suitable",
    "solve_horizontal_ribbon",
]
