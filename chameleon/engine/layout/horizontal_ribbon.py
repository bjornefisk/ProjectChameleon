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
    _MAX_FONT_SEARCH_PROBES,
    _font_size_probe_order,
    _largest_fitting_font_size,
    _preferred_font_size,
    _render_candidate,
)
from .candidate import RenderedCandidate
from .roles import RoleKind, RoleModel, infer_roles

_GEOMETRY_FIELDS = ("x", "y", "width", "height")

_MAX_GROUP_SCALE_REFINEMENT_STEPS = _MAX_FONT_SEARCH_PROBES


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
    """Return whether a horizontal target can use a ribbon-layout attempt.

    This is a topology gate, not a feasibility verdict. Candidate geometry is
    still subject to the serialized hard validator.
    """

    source_width = to_fraction(source["canvas"]["width"])
    source_height = to_fraction(source["canvas"]["height"])
    target_width = to_fraction(target_canvas["width"])
    target_height = to_fraction(target_canvas["height"])
    if (
        not source["elements"]
        or target_width < target_height
        or target_width >= source_width
        or target_height >= source_height
    ):
        return False
    model = infer_roles(source)
    foreground_heights = [
        rotated_aabb(element)[3] - rotated_aabb(element)[1]
        for index, element in enumerate(source["elements"])
        if index != model.background_index
        and to_fraction(element["width"]) > 0
        and to_fraction(element["height"]) > 0
    ]
    return bool(foreground_heights)


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


def _minimum_positive_group_scale(elements: list[Mapping[str, Any]]) -> Fraction:
    """Keep every positive source dimension positive after integer output."""
    scale = Fraction(0)
    for element in elements:
        for field in ("width", "height"):
            dimension = to_fraction(element[field])
            if dimension > 0:
                scale = max(scale, Fraction(3, 4) / dimension)
    return scale


def _group_scale(elements: list[Mapping[str, Any]], desired: Fraction) -> Fraction:
    return max(desired, _minimum_positive_group_scale(elements))


def _relative_group_boxes(
    elements: list[Mapping[str, Any]], scale: Fraction
) -> list[tuple[Fraction, Fraction, Fraction, Fraction]]:
    """Construct exact group-relative geometry; serialization happens later."""
    first_x = to_fraction(elements[0]["x"])
    first_y = to_fraction(elements[0]["y"])
    boxes: list[tuple[Fraction, Fraction, Fraction, Fraction]] = []
    for element in elements:
        boxes.append(
            (
                (to_fraction(element["x"]) - first_x) * scale,
                (to_fraction(element["y"]) - first_y) * scale,
                to_fraction(element["width"]) * scale,
                to_fraction(element["height"]) * scale,
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
) -> tuple[Fraction, Fraction] | None:
    source_width = to_fraction(element["width"])
    source_height = to_fraction(element["height"])
    if source_width <= 0 or source_height <= 0:
        return Fraction(0), Fraction(0)
    if element["type"] == "image":
        if axis == "horizontal":
            scale = min(Fraction(1), Fraction(target_height, 1) / to_fraction(source_canvas["height"]))
        else:
            scale = min(Fraction(1), Fraction(target_width, 1) / to_fraction(source_canvas["width"]))
        scale *= art_scale
        desired_width = max(Fraction(1), source_width * scale)
        desired_height = max(Fraction(1), source_height * scale)
        return _image_dimensions(element, desired_width, desired_height)
    if element["type"] == "text":
        if text_dimensions is not None:
            return (
                Fraction(min(target_width, max(1, text_dimensions[0]))),
                Fraction(min(target_height, max(1, text_dimensions[1]))),
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
        return Fraction(min(target_width, width)), Fraction(min(target_height, height))
    if axis == "horizontal":
        scale = min(Fraction(1), Fraction(target_height, 1) / to_fraction(source_canvas["height"]))
    else:
        scale = min(Fraction(1), Fraction(target_width, 1) / to_fraction(source_canvas["width"]))
    scale *= art_scale
    return (
        max(Fraction(1), min(Fraction(target_width), source_width * scale)),
        max(Fraction(1), min(Fraction(target_height), source_height * scale)),
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
    if len(indices) > 1 or source_elements[first].get("group_id") is not None:
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
        if len(elements) == 1 and elements[0]["type"] == "text":
            x, y, width, height = boxes[0]
            boxes = ((x + 1, y + 1, width, height),)
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
    bleed = source_bleed_sides(element, rotated_aabb(element), source_canvas)
    if element["type"] != "image":
        if bleed and {"left", "right"} & bleed:
            width = max(width, Fraction(2))
        if bleed and {"top", "bottom"} & bleed:
            height = max(height, Fraction(2))
    if element["type"] == "text":
        box_x = 1
        box_y = 0 if axis == "horizontal" else 1
    else:
        box_x = 0
        box_y = 0
    candidate = dict(element)
    candidate.update({"x": box_x, "y": box_y, "width": width, "height": height})
    base_aabb = rotated_aabb(candidate)
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
        if aabb[2] <= aabb[0] or aabb[3] <= aabb[1]:
            continue
        if bleed is None:
            if not is_contained_in_canvas(aabb, target_canvas):
                return False
        elif clipped_sides(aabb, target_canvas) != bleed or not intersects_canvas(aabb, target_canvas):
            return False
    for indices, occupied_aabbs in occupied:
        for new_index, new_aabb in zip(plan["indices"], aabbs):
            if new_aabb[2] <= new_aabb[0] or new_aabb[3] <= new_aabb[1]:
                continue
            for old_index, old_aabb in zip(indices, occupied_aabbs):
                if old_aabb[2] <= old_aabb[0] or old_aabb[3] <= old_aabb[1]:
                    continue
                if model.overlaps(new_index, old_index):
                    continue
                if positive_aabb_intersection(new_aabb, old_aabb):
                    return False
    return True


def _serialize_extreme_candidate(response: Mapping[str, Any]) -> dict[str, Any]:
    """Apply the single half-even serialization at the render boundary."""

    serialized = {"canvas": dict(response["canvas"]), "elements": []}
    for element in response["elements"]:
        serialized_element = dict(element)
        for field in _GEOMETRY_FIELDS:
            serialized_element[field] = quantize_to_int(element[field])
        if element.get("type") == "text":
            serialized_element["font_size"] = quantize_to_int(element["font_size"])
        serialized["elements"].append(serialized_element)
    return serialized


def _group_plan(
    source_elements: list[Mapping[str, Any]],
    first: int,
    indices: list[int],
    scale: Fraction,
    target_width: int,
    target_height: int,
) -> dict[str, Any] | None:
    elements = [source_elements[index] for index in indices]
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


def _group_scale_for_text(
    elements: list[Mapping[str, Any]],
    font_sizes: Mapping[int, int],
    source_indices: list[int],
    font_manager,
    measure_text_height,
    desired_scale: Fraction,
    work_diagnostics: dict[str, Any] | None = None,
) -> Fraction | None:
    scale = max(desired_scale, _minimum_positive_group_scale(elements))
    for element in elements:
        if element["type"] == "text" and to_fraction(element["height"]) <= 0:
            return None

    if work_diagnostics is not None:
        work_diagnostics["group_scale_refinement_invocations"] = (
            work_diagnostics.get("group_scale_refinement_invocations", 0) + 1
        )
        work_diagnostics["group_scale_refinement_status"] = "running"

    def required_scale_at(candidate_scale: Fraction) -> Fraction:
        required = _minimum_positive_group_scale(elements)
        for index, element in zip(source_indices, elements):
            if element["type"] != "text":
                continue
            source_width = to_fraction(element["width"])
            width = quantize_to_int(source_width * candidate_scale)
            if source_width > 0:
                width = max(1, width)
            minimum_height = measure_text_height(
                element,
                width,
                font_sizes[index],
                font_manager,
            )
            required = max(
                required,
                Fraction(minimum_height, 1) / to_fraction(element["height"]),
            )
        return required

    refinement_steps = 0
    for _ in range(_MAX_GROUP_SCALE_REFINEMENT_STEPS):
        refinement_steps += 1
        if work_diagnostics is not None:
            work_diagnostics["group_scale_refinement_iterations"] = (
                work_diagnostics.get("group_scale_refinement_iterations", 0) + 1
            )
        required = required_scale_at(scale)
        if required > scale:
            scale = required
            continue
        if required == scale:
            return scale
        try:
            smaller_required = required_scale_at(required)
        except InfeasibleLayoutError:
            raise
        except (TypeError, ValueError, OverflowError):
            return scale
        if smaller_required <= required:
            return required
        if smaller_required >= scale:
            return scale
        scale = smaller_required

    if work_diagnostics is not None:
        work_diagnostics["group_scale_refinement_status"] = "cutoff"
    _fail(
        "grouped-text scale refinement reached its deterministic step limit",
        group_scale_refinement_iterations=refinement_steps,
        group_scale_refinement_step_limit=_MAX_GROUP_SCALE_REFINEMENT_STEPS,
        candidate_work={
            "dominant_copy_layout": dict(work_diagnostics or {}),
        },
    )

def _build_copy_band_candidate(
    source: Mapping[str, Any],
    target_canvas: Mapping[str, Any],
    model: RoleModel,
    source_elements: list[Mapping[str, Any]],
    units: list[tuple[int, list[int]]],
    font_manager,
    fonts_dir: str | None,
    work_diagnostics: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Try one measured, full-width copy-band layout for the dominant-copy variant."""
    if work_diagnostics is not None:
        work_diagnostics.update(
            {
                "status": "not_applicable",
                "font_size_probe_limit": _MAX_FONT_SEARCH_PROBES,
                "font_measurement_calls": 0,
                "group_scale_refinement_iterations": 0,
                "group_scale_refinement_invocations": 0,
                "group_scale_refinement_step_limit": _MAX_GROUP_SCALE_REFINEMENT_STEPS,
                "group_scale_refinement_status": "not_started",
                "layout_configurations_considered": 0,
                "semantic_validation_attempts": 0,
            }
        )
    if __package__.startswith("chameleon."):
        from chameleon.renderer.converter.convert import minimum_text_box_height
    else:
        from renderer.converter.convert import minimum_text_box_height

    if font_manager is None:
        from .near_isomorphic import _renderer_components

        load_brand_font_manager = _renderer_components()[0]
        resolved_fonts_dir = fonts_dir or str(
            Path(__file__).resolve().parents[2] / "brand_kit" / "fonts"
        )
        font_manager = load_brand_font_manager(resolved_fonts_dir)

    background = model.background_index
    if background is not None and source_elements[background].get("group_id") is not None:
        return None
    copy_indices = [
        index
        for index, element in enumerate(source_elements)
        if element["type"] == "text" and element.get("group_id") is None
    ]
    if not copy_indices:
        return None

    target_width = int(target_canvas["width"])
    target_height = int(target_canvas["height"])
    font_scale = min(
        Fraction(1),
        Fraction(target_height, 1) / to_fraction(source["canvas"]["height"]),
    )
    preferred_sizes = {
        index: _preferred_font_size(
            to_fraction(source_elements[index]["font_size"]), font_scale
        )
        for index, element in enumerate(source_elements)
        if element["type"] == "text"
    }
    grouped_units = [
        (first, indices)
        for first, indices in units
        if len(indices) > 1 or source_elements[first].get("group_id") is not None
    ]
    row_units = [
        (first, indices)
        for first, indices in units
        if not (len(indices) == 1 and indices[0] in copy_indices)
    ]
    grouped_text_indices = [
        index
        for _first, indices in grouped_units
        for index in indices
        if source_elements[index]["type"] == "text"
    ]

    copy_levels = _font_size_probe_order(
        max(preferred_sizes[index] for index in copy_indices)
    )
    group_levels = (
        _font_size_probe_order(
            max(preferred_sizes[index] for index in grouped_text_indices)
        )
        if grouped_text_indices
        else ()
    )
    font_measurement_calls = 0

    def measure_height(element, width, font_size, manager):
        nonlocal font_measurement_calls
        font_measurement_calls += 1
        if work_diagnostics is not None:
            work_diagnostics["font_measurement_calls"] = font_measurement_calls
        return minimum_text_box_height(element, width, font_size, manager)

    copy_options: list[tuple[dict[int, int], dict[int, int]]] = []
    seen_copy_options: set[tuple[tuple[int, int], ...]] = set()
    for level in copy_levels:
        sizes = {
            index: min(level, preferred_sizes[index]) for index in copy_indices
        }
        key = tuple(sizes.items())
        if key in seen_copy_options:
            continue
        seen_copy_options.add(key)
        try:
            heights = {
                index: measure_height(
                    source_elements[index], target_width, size, font_manager
                )
                for index, size in sizes.items()
            }
        except (TypeError, ValueError, OverflowError):
            continue
        copy_options.append((sizes, heights))

    if not copy_options:
        if work_diagnostics is not None:
            work_diagnostics.update(
                {
                    "status": "no_copy_font_option",
                    "copy_font_size_probe_count": len(copy_levels),
                    "group_font_size_probe_count": len(group_levels),
                    "font_size_probe_limit": _MAX_FONT_SEARCH_PROBES,
                    "font_measurement_calls": font_measurement_calls,
                    "layout_configurations_considered": 0,
                    "semantic_validation_attempts": 0,
                }
            )
        return None

    group_spans = [
        _source_span([source_elements[index] for index in indices])
        for _first, indices in grouped_units
    ]
    group_primary_extent = sum(
        (span[2] - span[0] for span in group_spans),
        Fraction(0),
    )
    group_budget = min(
        Fraction(1),
        Fraction(target_width, 1) / group_primary_extent
        if group_primary_extent > 0
        else Fraction(1),
    )
    group_options: list[tuple[dict[int, int], dict[int, Fraction]]] = []
    levels = group_levels or (0,)
    seen_group_options: set[tuple[tuple[int, int], ...]] = set()
    for level in levels:
        sizes = {
            index: min(level, preferred_sizes[index])
            for index in grouped_text_indices
        }
        key = tuple(sizes.items())
        if key in seen_group_options:
            continue
        seen_group_options.add(key)
        scales: dict[int, Fraction] = {}
        valid = True
        for first, indices in grouped_units:
            elements = [source_elements[index] for index in indices]
            if any(element["type"] == "text" for element in elements):
                try:
                    scale = _group_scale_for_text(
                        elements,
                        sizes,
                        indices,
                        font_manager,
                        measure_height,
                        group_budget,
                        work_diagnostics,
                    )
                except InfeasibleLayoutError:
                    raise
                except (TypeError, ValueError, OverflowError):
                    valid = False
                    break
                if scale is None:
                    valid = False
                    break
                scales[first] = scale
        if valid:
            group_options.append((sizes, scales))

    if work_diagnostics is not None and grouped_text_indices:
        work_diagnostics["group_scale_refinement_status"] = "complete"

    art_scales = (Fraction(1), Fraction(1, 2))
    configuration_limit = (
        len(copy_levels) * max(1, len(group_levels)) * len(art_scales)
    )
    configurations_considered = 0
    semantic_validation_attempts = 0
    diagnostic_base = {
        "copy_font_size_probe_count": len(copy_levels),
        "group_font_size_probe_count": len(group_levels),
        "font_size_probe_limit": _MAX_FONT_SEARCH_PROBES,
        "font_measurement_calls": font_measurement_calls,
        "group_scale_refinement_iterations": (
            work_diagnostics.get("group_scale_refinement_iterations", 0)
            if work_diagnostics is not None
            else 0
        ),
        "group_scale_refinement_invocations": (
            work_diagnostics.get("group_scale_refinement_invocations", 0)
            if work_diagnostics is not None
            else 0
        ),
        "group_scale_refinement_step_limit": _MAX_GROUP_SCALE_REFINEMENT_STEPS,
    }

    def record_work(status: str) -> None:
        if work_diagnostics is not None:
            work_diagnostics.update(
                {
                    **diagnostic_base,
                    "layout_configurations_considered": configurations_considered,
                    "layout_configuration_limit": configuration_limit,
                    "semantic_validation_attempts": semantic_validation_attempts,
                    "status": status,
                }
            )

    if not group_options:
        record_work("no_group_font_option")
        return None

    best_quality: tuple[Any, ...] | None = None
    best_response: dict[str, Any] | None = None

    for copy_sizes, copy_heights in copy_options:
        copy_height = sum(copy_heights.values())
        available_height = target_height - copy_height
        if available_height <= 0:
            continue
        for group_sizes, group_scales in group_options:
            for art_scale in art_scales:
                configurations_considered += 1
                plans: list[dict[str, Any]] = []
                for first, indices in row_units:
                    elements = [source_elements[index] for index in indices]
                    if (
                        len(indices) > 1
                        or source_elements[first].get("group_id") is not None
                    ):
                        if first in group_scales:
                            scale = group_scales[first]
                        else:
                            span = _source_span(elements)
                            primary_extent = span[2] - span[0]
                            cross_extent = span[3] - span[1]
                            desired = min(
                                group_budget,
                                Fraction(target_width, 1)
                                / max(Fraction(1), primary_extent),
                                Fraction(available_height, 1)
                                / max(Fraction(1), cross_extent),
                            )
                            scale = max(
                                desired, _minimum_positive_group_scale(elements)
                            )
                        plan = _group_plan(
                            source_elements,
                            first,
                            indices,
                            scale,
                            target_width,
                            target_height,
                        )
                    else:
                        plan = _make_plan(
                            source_elements,
                            first,
                            indices,
                            source_canvas=source["canvas"],
                            target_width=target_width,
                            target_height=target_height,
                            unit_count=len(units),
                            group_budget=group_budget,
                            axis="horizontal",
                            art_scale=art_scale,
                        )
                    if plan is None:
                        plans = []
                        break
                    plans.append(plan)
                if row_units and not plans:
                    continue

                response = [dict(element) for element in source_elements]
                if background is not None:
                    response[background].update(
                        {"x": 0, "y": 0, "width": target_width, "height": target_height}
                    )
                for index, size in group_sizes.items():
                    response[index]["font_size"] = size

                occupied: list[tuple[tuple[int, ...], list[Any]]] = []
                cursor = 0
                row_bottom = 0
                placement_failed = False
                for plan in sorted(plans, key=lambda item: item["first"]):
                    base_span = plan["base_span"]
                    anchor_x = _ceil_fraction(
                        Fraction(cursor) - to_fraction(base_span[0])
                    )
                    anchor_y = _ceil_fraction(-to_fraction(base_span[1]))
                    boxes, aabbs = _materialize_plan(
                        plan, source_elements, anchor_x, anchor_y
                    )
                    if not _valid_plan_placement(
                        plan,
                        source_elements,
                        boxes,
                        aabbs,
                        occupied,
                        target_canvas,
                        model,
                    ):
                        placement_failed = True
                        break
                    for index, box in zip(plan["indices"], boxes):
                        response[index].update(dict(zip(_GEOMETRY_FIELDS, box)))
                    occupied.append((plan["indices"], aabbs))
                    cursor = _ceil_fraction(
                        max(to_fraction(aabb[2]) for aabb in aabbs)
                    )
                    row_bottom = max(
                        row_bottom,
                        _ceil_fraction(max(to_fraction(aabb[3]) for aabb in aabbs)),
                    )
                if placement_failed or cursor > target_width or row_bottom > available_height:
                    continue

                text_cursor = row_bottom
                for index in copy_indices:
                    element = source_elements[index]
                    width = target_width
                    height = copy_heights[index]
                    local = dict(element)
                    local.update(
                        {"x": 0, "y": 0, "width": width, "height": height}
                    )
                    local["font_size"] = copy_sizes[index]
                    base_aabb = rotated_aabb(local)
                    anchor_x = _ceil_fraction(-to_fraction(base_aabb[0]))
                    anchor_y = _ceil_fraction(
                        Fraction(text_cursor) - to_fraction(base_aabb[1])
                    )
                    candidate = dict(local)
                    candidate.update({"x": anchor_x, "y": anchor_y})
                    aabb = rotated_aabb(candidate)
                    plan = {
                        "indices": (index,),
                        "bleed": source_bleed_sides(
                            element, rotated_aabb(element), source["canvas"]
                        ),
                    }
                    if not _valid_plan_placement(
                        plan,
                        source_elements,
                        [(anchor_x, anchor_y, width, height)],
                        [aabb],
                        occupied,
                        target_canvas,
                        model,
                    ):
                        placement_failed = True
                        break
                    response[index].update(
                        {
                            "x": anchor_x,
                            "y": anchor_y,
                            "width": width,
                            "height": height,
                            "font_size": copy_sizes[index],
                        }
                    )
                    occupied.append(((index,), [aabb]))
                    text_cursor = _ceil_fraction(to_fraction(aabb[3]))
                if placement_failed or text_cursor > target_height:
                    continue

                text_sizes = list(copy_sizes.values()) + list(group_sizes.values())
                quality = (
                    min(text_sizes),
                    sum(copy_sizes.values()),
                    sum(group_sizes.values()),
                    art_scale,
                )
                if best_quality is None or quality > best_quality:
                    best_quality = quality
                    best_response = {
                        "canvas": dict(target_canvas),
                        "elements": response,
                    }

    if best_response is None:
        record_work("no_geometric_candidate")
        return None
    result = _serialize_extreme_candidate(best_response)
    semantic_validation_attempts = 1
    try:
        validate_response(
            source,
            target_canvas,
            result,
            font_manager=font_manager,
            fonts_dir=fonts_dir,
        )
    except InfeasibleLayoutError as error:
        if error.reason_code is InfeasibleReasonCode.RUNTIME_IO_FAILURE:
            raise
        record_work("semantic_validation_rejected")
        return None
    record_work("hard_valid")
    return result


def _compact_group_placement(
    source_elements: list[Mapping[str, Any]],
    response_elements: list[dict[str, Any]],
    indices: list[int],
    slot: tuple[int, int, int, int],
) -> Fraction | None:
    """Fit one rigid source group into a compact grid cell."""
    elements = [source_elements[index] for index in indices]
    source_span = _source_span(elements)
    source_width = source_span[2] - source_span[0]
    source_height = source_span[3] - source_span[1]
    if source_width <= 0 or source_height <= 0:
        return None

    desired_scale = min(
        Fraction(slot[2], 1) / source_width,
        Fraction(slot[3], 1) / source_height,
    )
    scale = _group_scale(elements, desired_scale)
    boxes = _relative_group_boxes(elements, scale)
    local_elements = []
    for element, box in zip(elements, boxes):
        local = dict(element)
        local.update(dict(zip(_GEOMETRY_FIELDS, box)))
        local_elements.append(local)
    local_span = _source_span(local_elements)
    width = local_span[2] - local_span[0]
    height = local_span[3] - local_span[1]
    if width > slot[2] or height > slot[3]:
        return None

    translate_x = Fraction(slot[0], 1) + (Fraction(slot[2], 1) - width) / 2 - local_span[0]
    translate_y = Fraction(slot[1], 1) + (Fraction(slot[3], 1) - height) / 2 - local_span[1]
    for index, box in zip(indices, boxes):
        response_elements[index].update(
            {
                "x": box[0] + translate_x,
                "y": box[1] + translate_y,
                "width": box[2],
                "height": box[3],
            }
        )
    return scale


def _compact_image_placement(
    source_element: Mapping[str, Any],
    response_element: dict[str, Any],
    slot: tuple[int, int, int, int],
) -> bool:
    dimensions = _image_dimensions(source_element, slot[2], slot[3])
    if dimensions is None:
        return False
    width, height = dimensions
    response_element.update(
        {
            "x": slot[0] + (slot[2] - width) // 2,
            "y": slot[1] + (slot[3] - height) // 2,
            "width": width,
            "height": height,
        }
    )
    return True


def _build_compact_grid_candidate(
    source: Mapping[str, Any],
    target_canvas: Mapping[str, Any],
    model: RoleModel,
    source_elements: list[Mapping[str, Any]],
    units: list[tuple[int, list[int]]],
    variant: str,
    font_manager,
    fonts_dir: str | None,
    work_diagnostics: dict[str, Any],
) -> dict[str, Any] | None:
    """Try a renderer-checked compact grid for the dense banner profile."""
    target_width = int(target_canvas["width"])
    target_height = int(target_canvas["height"])
    work_diagnostics.update(
        {"status": "not_applicable", "text_fit_attempts": 0, "hard_validation_attempts": 0}
    )
    if target_width >= 350 and target_height >= 300:
        return None

    background = model.background_index
    if background is None or source_elements[background].get("group_id") is not None:
        work_diagnostics["status"] = "unsupported_background"
        return None

    badges: list[tuple[int, list[int]]] = []
    cta = None
    ribbon = None
    art_images: list[int] = []
    secondary_images: list[int] = []
    headlines: list[int] = []
    supporting_text: list[int] = []

    for first, indices in units:
        if first == background:
            continue
        element = source_elements[first]
        role = model.assignments[first].role
        grouped = len(indices) > 1 or element.get("group_id") is not None
        if grouped:
            roles = {model.assignments[index].role for index in indices}
            members = [source_elements[index] for index in indices]
            rotated = any(to_fraction(member.get("rotation", 0)) != 0 for member in members)
            if rotated and RoleKind.BADGE in roles and ribbon is None:
                ribbon = (first, indices)
            elif RoleKind.CTA in roles and not rotated and cta is None:
                cta = (first, indices)
            elif RoleKind.BADGE in roles and not rotated:
                badges.append((first, indices))
            else:
                work_diagnostics["status"] = "unsupported_group"
                return None
            continue

        if element["type"] == "text" and to_fraction(element.get("rotation", 0)) == 0:
            if role is RoleKind.HEADLINE:
                headlines.append(first)
            elif role is RoleKind.SUPPORTING_TEXT:
                supporting_text.append(first)
            else:
                work_diagnostics["status"] = "unsupported_text"
                return None
        elif element["type"] == "image" and to_fraction(element.get("rotation", 0)) == 0:
            if role in (RoleKind.LOGO, RoleKind.HERO_MEDIA):
                art_images.append(first)
            elif role is RoleKind.IMAGE:
                secondary_images.append(first)
            else:
                work_diagnostics["status"] = "unsupported_image"
                return None
        else:
            work_diagnostics["status"] = "unsupported_element"
            return None

    badges.sort(key=lambda unit: unit[0])
    headlines.sort()
    supporting_text.sort()
    body_text = headlines + supporting_text
    text_indices = [
        index for index, element in enumerate(source_elements) if element["type"] == "text"
    ]
    if (
        len(badges) != 3
        or cta is None
        or ribbon is None
        or len(art_images) != 2
        or len(secondary_images) != 1
        or len(headlines) != 1
        or len(supporting_text) != 2
    ):
        work_diagnostics["status"] = "unsupported_dense_profile"
        return None

    padding_x = max(2, target_width // 50)
    padding_y = max(2, target_height // 80)
    gap = max(2, min(target_width, target_height) // 90)
    inner_width = target_width - 2 * padding_x
    inner_height = target_height - 2 * padding_y
    if inner_width <= 0 or inner_height <= 0:
        work_diagnostics["status"] = "insufficient_canvas"
        return None

    media_height = min(inner_height // 3, inner_width // 2)
    if target_height >= 2 * target_width:
        badge_height = max(1, min(inner_height // 24, inner_width // 7))
        group_rows = [
            ([badges[0]], 1, badge_height),
            ([badges[1]], 1, badge_height),
            ([badges[2]], 1, badge_height),
            ([cta], 1, max(1, min(inner_height // 12, inner_width // 4))),
            ([ribbon], 1, max(1, min(inner_height // 8, inner_width // 2))),
        ]
    else:
        group_rows = [
            (
                badges[:2],
                2,
                min(inner_height // 10, inner_width // 5),
            ),
            (
                [badges[2], cta, ribbon],
                3,
                min(inner_height // 8, inner_width // 4),
            ),
        ]
    if media_height < 1 or any(height < 1 for _units, _columns, height in group_rows):
        work_diagnostics["status"] = "insufficient_canvas"
        return None

    gap_count = len(group_rows) + 3
    text_space = (
        inner_height
        - media_height
        - sum(height for _units, _columns, height in group_rows)
        - gap_count * gap
    )
    if text_space < len(body_text):
        work_diagnostics["status"] = "insufficient_text_space"
        return None

    def row_slots(y: int, height: int, columns: int) -> list[tuple[int, int, int, int]]:
        available_width = inner_width - gap * (columns - 1)
        base_width, remainder = divmod(available_width, columns)
        slots = []
        x = padding_x
        for column in range(columns):
            width = base_width + int(column < remainder)
            slots.append((x, y, width, height))
            x += width + gap
        return slots

    response_elements = [dict(element) for element in source_elements]
    response_elements[background].update(
        {"x": 0, "y": 0, "width": target_width, "height": target_height}
    )
    for index, slot in zip(
        [*art_images, *secondary_images], row_slots(padding_y, media_height, 3)
    ):
        if not _compact_image_placement(
            source_elements[index], response_elements[index], slot
        ):
            work_diagnostics.update(
                {"status": "image_ratio_does_not_fit", "failed_element_id": source_elements[index]["id"]}
            )
            return None

    group_scales: dict[int, Fraction] = {}
    dummy_row_y: list[int] = []
    y = padding_y
    for row_units, columns, height in group_rows:
        dummy_row_y.append(y)
        for unit, slot in zip(row_units, row_slots(y, height, columns)):
            first, indices = unit
            scale = _compact_group_placement(
                source_elements, response_elements, indices, slot
            )
            if scale is None:
                work_diagnostics.update(
                    {
                        "status": "group_does_not_fit",
                        "failed_group_id": source_elements[first].get("group_id"),
                    }
                )
                return None
            group_scales.update((index, scale) for index in indices)
        y += height + gap

    weights = (4, 4, 2) if variant == "dominant_copy" else (5, 3, 2)
    allocations = [text_space * weight // sum(weights) for weight in weights]
    allocations[0] += text_space - sum(allocations)
    for index, height in zip(body_text, allocations):
        response_elements[index].update(
            {"x": padding_x, "y": padding_y, "width": inner_width, "height": height}
        )

    if font_manager is None:
        from .near_isomorphic import _renderer_components

        load_brand_font_manager = _renderer_components()[0]
        resolved_fonts_dir = fonts_dir or str(
            Path(__file__).resolve().parents[2] / "brand_kit" / "fonts"
        )
        font_manager = load_brand_font_manager(resolved_fonts_dir)
    if __package__.startswith("chameleon."):
        from chameleon.renderer.converter.convert import minimum_text_box_height
    else:
        from renderer.converter.convert import minimum_text_box_height

    canvas_scale = min(
        Fraction(1),
        Fraction(target_width, 1) / to_fraction(source["canvas"]["width"]),
        Fraction(target_height, 1) / to_fraction(source["canvas"]["height"]),
    )
    variant_scale = {
        "dominant_copy": Fraction(6, 5),
        "dominant_media": Fraction(4, 5),
    }.get(variant, Fraction(1))
    result = _serialize_extreme_candidate(
        {
            "canvas": {"width": target_width, "height": target_height},
            "elements": response_elements,
        }
    )

    selected_sizes: dict[int, int] = {}
    minimum_body_heights: dict[int, int] = {}
    for index in text_indices:
        scale = min(
            Fraction(1),
            group_scales.get(index, canvas_scale) * variant_scale,
        )
        selected_size = _largest_fitting_font_size(
            result["elements"][index],
            _preferred_font_size(
                to_fraction(source_elements[index]["font_size"]), scale
            ),
            font_manager,
            target_canvas,
        )
        work_diagnostics["text_fit_attempts"] += 1
        if selected_size is None:
            work_diagnostics.update(
                {"status": "text_fit_exhausted", "failed_element_id": source_elements[index]["id"]}
            )
            return None
        selected_sizes[index] = selected_size
        required_height = minimum_text_box_height(
            result["elements"][index],
            result["elements"][index]["width"],
            selected_size,
            font_manager,
        )
        if required_height > result["elements"][index]["height"]:
            work_diagnostics.update(
                {"status": "text_box_too_short", "failed_element_id": source_elements[index]["id"]}
            )
            return None
        if index in body_text:
            minimum_body_heights[index] = required_height

    slack = text_space - sum(minimum_body_heights.values())
    if slack < 0:
        work_diagnostics["status"] = "insufficient_text_space"
        return None
    extra, remainder = divmod(slack, gap_count)
    spacers = [gap + extra + int(position < remainder) for position in range(gap_count)]
    cursor = padding_y + media_height + spacers[0]
    spacer_index = 1
    for index in body_text[:2]:
        height = minimum_body_heights[index]
        response_elements[index].update(
            {"x": padding_x, "y": cursor, "width": inner_width, "height": height}
        )
        cursor += height + spacers[spacer_index]
        spacer_index += 1

    final_row_y = []
    for _row_units, _columns, height in group_rows:
        final_row_y.append(cursor)
        cursor += height + spacers[spacer_index]
        spacer_index += 1
    legal_index = body_text[2]
    response_elements[legal_index].update(
        {
            "x": padding_x,
            "y": cursor,
            "width": inner_width,
            "height": minimum_body_heights[legal_index],
        }
    )

    for row, original_y, final_y in zip(group_rows, dummy_row_y, final_row_y):
        for _first, indices in row[0]:
            for index in indices:
                response_elements[index]["y"] += final_y - original_y
    for index, size in selected_sizes.items():
        response_elements[index]["font_size"] = size

    result = _serialize_extreme_candidate(
        {
            "canvas": {"width": target_width, "height": target_height},
            "elements": response_elements,
        }
    )
    work_diagnostics["hard_validation_attempts"] += 1
    try:
        validate_response(
            source,
            target_canvas,
            result,
            font_manager=font_manager,
            fonts_dir=fonts_dir,
        )
    except InfeasibleLayoutError as error:
        if error.reason_code is InfeasibleReasonCode.RUNTIME_IO_FAILURE:
            raise
        work_diagnostics.update(
            {
                "status": "hard_validation_failed",
                "failure_reason_code": error.reason_code.value,
                "failure_details": error.details,
            }
        )
        return None
    work_diagnostics["status"] = "hard_valid"
    return result



def _build_extreme_candidate(
    source: Mapping[str, Any],
    target_canvas: Mapping[str, Any],
    *,
    variant: str = "source_proportional",
    axis: str = "horizontal",
    font_manager=None,
    fonts_dir: str | None = None,
    work_diagnostics: dict[str, Any] | None = None,
) -> dict[str, Any]:
    validate_source(source)
    validate_target_canvas(target_canvas)
    model = infer_roles(source)
    source_elements = list(source["elements"])
    target_width = int(target_canvas["width"])
    target_height = int(target_canvas["height"])
    background = model.background_index
    units = _candidate_units(source, background)

    if variant == "dominant_copy" and axis == "horizontal":
        copy_band_work: dict[str, Any] = {}
        compact = _build_copy_band_candidate(
            source,
            target_canvas,
            model,
            source_elements,
            units,
            font_manager,
            fonts_dir,
            copy_band_work,
        )
        if work_diagnostics is not None:
            work_diagnostics["dominant_copy_layout"] = copy_band_work
        if compact is not None:
            return compact
    unit_count = len(units)
    group_source_spans = []
    for _first, indices in units:
        if len(indices) > 1:
            span = _source_span([source_elements[index] for index in indices])
            group_source_spans.append(
                span[2] - span[0] if axis == "horizontal" else span[3] - span[1]
            )
    primary_limit = Fraction(target_width if axis == "horizontal" else target_height)
    group_span = sum(group_source_spans)
    group_budget = min(
        Fraction(1),
        primary_limit / group_span if group_span > 0 else Fraction(1),
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
                            plan["first"],
                            -(plan["footprint"][0] * plan["footprint"][1]),
                            -max(plan["footprint"]),
                        ),
                    )
                elif order == "primary":
                    ordered_plans = sorted(
                        plans,
                        key=lambda plan: (
                            plan["first"],
                            -(plan["footprint"][0] if axis == "horizontal" else plan["footprint"][1]),
                            -(plan["footprint"][0] * plan["footprint"][1]),
                        ),
                    )
                else:
                    ordered_plans = sorted(
                        plans,
                        key=lambda plan: (
                            plan["first"],
                            plan["pack_priority"],
                            -(plan["footprint"][0] * plan["footprint"][1]),
                            -max(plan["footprint"]),
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
                raw_result = {
                    "canvas": {"width": target_width, "height": target_height},
                    "elements": response,
                }
                result = _serialize_extreme_candidate(raw_result)
                try:
                    validate_response(
                        source,
                        target_canvas,
                        result,
                        font_manager=font_manager,
                        fonts_dir=fonts_dir,
                    )
                except InfeasibleLayoutError as error:
                    if error.reason_code is InfeasibleReasonCode.RUNTIME_IO_FAILURE:
                        raise
                    continue
                return result

    compact_work: dict[str, Any] = {}
    compact = _build_compact_grid_candidate(
        source,
        target_canvas,
        model,
        source_elements,
        units,
        variant,
        font_manager,
        fonts_dir,
        compact_work,
    )
    if work_diagnostics is not None:
        work_diagnostics["compact_grid_fallback"] = compact_work
    if compact is not None:
        return compact

    failure_details: dict[str, Any] = {
        "attempts": attempts,
        "search_exhausted": True,
    }
    if work_diagnostics is not None:
        failure_details["candidate_work"] = work_diagnostics
    _fail(
        "bounded extreme-topology search exhausted without a hard-valid candidate",
        **failure_details,
    )


def generate_horizontal_ribbon_candidate(
    source: Mapping[str, Any],
    target_canvas: Mapping[str, Any],
    *,
    variant: str = "source_proportional",
    font_manager=None,
    fonts_dir: str | None = None,
    assets_dir: str | None = None,
) -> RenderedCandidate:
    validate_source(source)
    validate_target_canvas(target_canvas)
    if not is_horizontal_ribbon_suitable(source, target_canvas):
        _fail("source and target proportions do not support a horizontal ribbon")
    work_diagnostics: dict[str, Any] = {}
    response = _build_extreme_candidate(
        source,
        target_canvas,
        font_manager=font_manager,
        fonts_dir=fonts_dir,
        variant=variant,
        work_diagnostics=work_diagnostics,
    )
    rendered_png, warnings = _render_candidate(response, assets_dir, fonts_dir, font_manager)
    return RenderedCandidate(
        response=response,
        rendered_png=rendered_png,
        warnings=warnings,
        diagnostics=work_diagnostics,
    )


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
