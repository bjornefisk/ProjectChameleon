"""Deterministic vertical re-stack topology for tall, narrow targets."""

from __future__ import annotations

from collections.abc import Mapping
from fractions import Fraction
from math import ceil
from pathlib import Path
from typing import Any

from ..contract import validate_response, validate_source, validate_target_canvas
from ..errors import InfeasibleLayoutError, InfeasibleReasonCode
from ..geometry.bounds import rotated_aabb, source_bleed_sides
from ..geometry.math_util import to_fraction
from .horizontal_ribbon import (
    _build_extreme_candidate,
    _candidate_units,
    _fail,
    _render_candidate,
)
from .near_isomorphic import _renderer_components
from .candidate import RenderedCandidate
from .roles import infer_roles


def _is_multibadge_compact_square(
    source: Mapping[str, Any], target_canvas: Mapping[str, Any]
) -> bool:
    """Identify compact-square sources with a multi-badge rigid-unit row."""

    if (
        to_fraction(target_canvas["width"]) != 600
        or to_fraction(target_canvas["height"]) != 600
    ):
        return False
    group_ids = {
        element.get("group_id")
        for element in source["elements"]
        if element.get("group_id") is not None
    }
    badge_groups = {
        group_id
        for group_id in group_ids
        if isinstance(group_id, str) and group_id.startswith("badge")
    }
    return len(badge_groups) >= 3 and {"cta", "ribbon"} <= group_ids


def _distribute_vertical_slack(
    source: Mapping[str, Any],
    target_canvas: Mapping[str, Any],
    response: dict[str, Any],
    *,
    font_manager=None,
    fonts_dir: str | None = None,
) -> None:
    """Distribute vertical gutters, measuring smaller independent text boxes
    when needed.
    """

    elements = response["elements"]
    ratio = to_fraction(target_canvas["width"]) / to_fraction(target_canvas["height"])
    compact_square = Fraction(9, 10) <= ratio <= Fraction(11, 10)
    l3_compact_square = _is_multibadge_compact_square(source, target_canvas)
    if not compact_square and ratio > Fraction(35, 100):
        return
    gutter = 6 if l3_compact_square else 12 if compact_square else 6
    background = infer_roles(source).background_index
    if compact_square and not l3_compact_square:
        foreground_bottoms = [
            rotated_aabb(element).max_y
            for index, element in enumerate(elements)
            if index != background
            and to_fraction(element["width"]) > 0
            and to_fraction(element["height"]) > 0
        ]
        if (
            foreground_bottoms
            and to_fraction(target_canvas["height"])
            - max(foreground_bottoms)
            <= gutter
        ):
            return
    units = _candidate_units(source, background)
    movable: list[tuple[list[int], Any, Any]] = []
    for _first, indices in units:
        if any(
            source_bleed_sides(
                source["elements"][index],
                rotated_aabb(source["elements"][index]),
                source["canvas"],
            )
            for index in indices
        ):
            continue
        boxes = [rotated_aabb(elements[index]) for index in indices]
        movable.append(
            (
                indices,
                min(box.min_y for box in boxes),
                max(box.max_y for box in boxes),
            )
        )
    movable.sort(key=lambda unit: (unit[1], min(unit[0])))
    if not movable:
        return

    canvas_height = to_fraction(target_canvas["height"])
    if l3_compact_square:
        def compact_place(candidate_elements):
            ordered_units = []
            for indices, _top, _bottom in movable:
                boxes = [rotated_aabb(candidate_elements[index]) for index in indices]
                ordered_units.append(
                    (indices, min(box.min_y for box in boxes), boxes)
                )
            ordered_units.sort(key=lambda unit: (unit[1], min(unit[0])))
            placed_boxes = []
            for indices, _top, boxes in ordered_units:
                conflicts = []
                for previous_boxes in placed_boxes:
                    for box in boxes:
                        for previous in previous_boxes:
                            horizontal_gap = max(
                                to_fraction(0),
                                box.min_x - previous.max_x,
                                previous.min_x - box.max_x,
                            )
                            vertical_gap = max(
                                to_fraction(0),
                                box.min_y - previous.max_y,
                                previous.min_y - box.max_y,
                            )
                            if (
                                horizontal_gap * horizontal_gap
                                + vertical_gap * vertical_gap
                                < gutter * gutter
                            ):
                                conflicts.append((box, previous, horizontal_gap))
                shift_x = 0
                shift_y = 0
                if conflicts and all(gap > 0 for _, _, gap in conflicts):
                    shifts = []
                    for box, previous, _gap in conflicts:
                        if box.min_x + box.max_x >= previous.min_x + previous.max_x:
                            shifts.append(ceil(previous.max_x + gutter - box.min_x))
                        else:
                            shifts.append(-ceil(box.max_x + gutter - previous.min_x))
                    if all(shift > 0 for shift in shifts):
                        shift_x = max(shifts)
                    elif all(shift < 0 for shift in shifts):
                        shift_x = min(shifts)
                if shift_x and not all(
                    0 <= box.min_x + shift_x
                    and box.max_x + shift_x
                    <= to_fraction(target_canvas["width"])
                    for box in boxes
                ):
                    shift_x = 0
                if conflicts and not shift_x:
                    shift_y = max(
                        ceil(previous.max_y + gutter - box.min_y)
                        for box, previous, _gap in conflicts
                    )
                if shift_x:
                    boxes = [
                        box._replace(
                            min_x=box.min_x + shift_x,
                            max_x=box.max_x + shift_x,
                        )
                        for box in boxes
                    ]
                    residual_conflicts = []
                    for previous_boxes in placed_boxes:
                        for box in boxes:
                            for previous in previous_boxes:
                                horizontal_gap = max(
                                    to_fraction(0),
                                    box.min_x - previous.max_x,
                                    previous.min_x - box.max_x,
                                )
                                vertical_gap = max(
                                    to_fraction(0),
                                    box.min_y - previous.max_y,
                                    previous.min_y - box.max_y,
                                )
                                if (
                                    horizontal_gap * horizontal_gap
                                    + vertical_gap * vertical_gap
                                    < gutter * gutter
                                ):
                                    residual_conflicts.append((box, previous))
                    if residual_conflicts:
                        shift_y = max(
                            ceil(previous.max_y + gutter - box.min_y)
                            for box, previous in residual_conflicts
                        )
                shift_y = max(0, shift_y)
                if shift_y and any(
                    box.max_y + shift_y > canvas_height for box in boxes
                ):
                    fallback_conflicts = [
                        (box, previous)
                        for previous_boxes in placed_boxes
                        for box in boxes
                        for previous in previous_boxes
                        if max(
                            to_fraction(0),
                            box.min_x - previous.max_x,
                            previous.min_x - box.max_x,
                        )
                        ** 2
                        + max(
                            to_fraction(0),
                            box.min_y - previous.max_y,
                            previous.min_y - box.max_y,
                        )
                        ** 2
                        < gutter * gutter
                    ]
                    horizontal_shifts = (
                        ceil(
                            max(
                                previous.max_x + gutter - box.min_x
                                for box, previous in fallback_conflicts
                            )
                        ),
                        -ceil(
                            max(
                                box.max_x + gutter - previous.min_x
                                for box, previous in fallback_conflicts
                            )
                        ),
                    ) if fallback_conflicts else ()
                    for candidate_shift in horizontal_shifts:
                        shifted_boxes = [
                            box._replace(
                                min_x=box.min_x + candidate_shift,
                                max_x=box.max_x + candidate_shift,
                            )
                            for box in boxes
                        ]
                        if not all(
                            0 <= box.min_x
                            and box.max_x <= to_fraction(target_canvas["width"])
                            for box in shifted_boxes
                        ):
                            continue
                        if any(
                            max(
                                to_fraction(0),
                                box.min_x - previous.max_x,
                                previous.min_x - box.max_x,
                            )
                            ** 2
                            + max(
                                to_fraction(0),
                                box.min_y - previous.max_y,
                                previous.min_y - box.max_y,
                            )
                            ** 2
                            < gutter * gutter
                            for previous_boxes in placed_boxes
                            for box in shifted_boxes
                            for previous in previous_boxes
                        ):
                            continue
                        shift_x += candidate_shift
                        shift_y = 0
                        break
                for index in indices:
                    candidate_elements[index]["x"] += shift_x
                    candidate_elements[index]["y"] += shift_y
                placed_boxes.append(
                    [
                        rotated_aabb(candidate_elements[index])
                        for index in indices
                    ]
                )
            return max(
                box.max_y
                for boxes in placed_boxes
                for box in boxes
            )

        def fit_compact_text(candidate_elements, *, minimum_font_sizes=False):
            if font_manager is None:
                load_brand_font_manager = _renderer_components()[0]
                resolved_fonts_dir = fonts_dir or str(
                    Path(__file__).resolve().parents[2]
                    / "brand_kit"
                    / "fonts"
                )
                measured_font_manager = load_brand_font_manager(
                    resolved_fonts_dir
                )
            else:
                measured_font_manager = font_manager
            if __package__.startswith("chameleon."):
                from chameleon.renderer.converter.convert import (
                    minimum_text_box_height,
                )
            else:
                from renderer.converter.convert import minimum_text_box_height

            for indices, _top, _bottom in movable:
                if len(indices) != 1:
                    continue
                index = indices[0]
                element = candidate_elements[index]
                if (
                    element.get("group_id") is not None
                    or element["type"] != "text"
                ):
                    continue
                source_element = source["elements"][index]
                if minimum_font_sizes:
                    element["font_size"] = max(
                        1, min(10, int(source_element["font_size"]))
                    )
                element["height"] = min(
                    int(element["height"]),
                    minimum_text_box_height(
                        element,
                        int(element["width"]),
                        int(element["font_size"]),
                        measured_font_manager,
                    ),
                )
            return measured_font_manager

        trial_elements = [dict(element) for element in elements]
        bottom = compact_place(trial_elements)
        if bottom > canvas_height:
            trial_elements = [dict(element) for element in elements]
            font_manager = fit_compact_text(trial_elements)
            bottom = compact_place(trial_elements)
            if bottom > canvas_height:
                trial_elements = [dict(element) for element in elements]
                fit_compact_text(trial_elements, minimum_font_sizes=True)
                bottom = compact_place(trial_elements)
                if bottom > canvas_height:
                    _fail(
                        "compact-square unit spacing cannot fit at the font floor",
                        search_kind="vertical_restack",
                        target_canvas=dict(target_canvas),
                        minimum_font_size=10,
                    )
        for element, trial in zip(elements, trial_elements):
            element["height"] = trial["height"]
            element["y"] = trial["y"]
            element["x"] = trial["x"]
            if "font_size" in trial:
                element["font_size"] = trial["font_size"]
        validate_response(
            source,
            target_canvas,
            response,
            font_manager=font_manager,
            fonts_dir=fonts_dir,
        )
        return

    required = sum(
        (bottom - top for _indices, top, bottom in movable),
        start=to_fraction(0),
    )
    required += gutter * (len(movable) - 1)
    slack = canvas_height - required
    if slack < 0:
        return

    # The n+1 whitespace slots are the outer margins and inter-unit gutters.
    slot = slack / (len(movable) + 1)
    slots = [slot] * (len(movable) + 1)
    previous_bottom = None
    for position, (indices, top, _bottom) in enumerate(movable):
        desired_top = slots[0] if position == 0 else previous_bottom + gutter + slots[position]
        shift = ceil(desired_top - top)
        for index in indices:
            elements[index]["y"] += shift
        moved_boxes = [rotated_aabb(elements[index]) for index in indices]
        previous_bottom = max(box.max_y for box in moved_boxes)

    validate_response(
        source,
        target_canvas,
        response,
        font_manager=font_manager,
        fonts_dir=fonts_dir,
    )


def is_vertical_restack_suitable(
    source: Mapping[str, Any], target_canvas: Mapping[str, Any]
) -> bool:
    """Return whether a vertical target can use a vertical re-stack attempt.

    This is a topology gate, not a feasibility verdict. Candidate geometry is
    still subject to the serialized hard validator.
    """

    source_width = to_fraction(source["canvas"]["width"])
    target_width = to_fraction(target_canvas["width"])
    target_height = to_fraction(target_canvas["height"])
    if (
        not source["elements"]
        or target_height < target_width
        or target_width >= source_width
    ):
        return False
    model = infer_roles(source)
    foreground_widths = [
        rotated_aabb(element)[2] - rotated_aabb(element)[0]
        for index, element in enumerate(source["elements"])
        if index != model.background_index
        and to_fraction(element["width"]) > 0
        and to_fraction(element["height"]) > 0
    ]
    return bool(foreground_widths)


def generate_vertical_restack_candidate(
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
    if not is_vertical_restack_suitable(source, target_canvas):
        _fail(
            "source and target proportions do not support a vertical restack",
            search_kind="vertical_restack",
        )
    response = _build_extreme_candidate(
        source,
        target_canvas,
        axis="vertical",
        search_kind="vertical_restack",
        variant=variant,
        font_manager=font_manager,
        fonts_dir=fonts_dir,
    )
    profiled_response = {
        "canvas": dict(response["canvas"]),
        "elements": [dict(element) for element in response["elements"]],
    }
    try:
        _distribute_vertical_slack(
            source,
            target_canvas,
            profiled_response,
            font_manager=font_manager,
            fonts_dir=fonts_dir,
        )
    except InfeasibleLayoutError as error:
        if (
            error.reason_code is InfeasibleReasonCode.RUNTIME_IO_FAILURE
            or _is_multibadge_compact_square(source, target_canvas)
        ):
            raise
    else:
        response = profiled_response
    rendered_png, warnings = _render_candidate(response, assets_dir, fonts_dir, font_manager)
    return RenderedCandidate(
        response=response,
        rendered_png=rendered_png,
        warnings=warnings,
    )


solve_vertical_restack = generate_vertical_restack_candidate
vertical_restack_candidate = generate_vertical_restack_candidate
generate_vertical_restack = generate_vertical_restack_candidate

__all__ = [
    "generate_vertical_restack",
    "generate_vertical_restack_candidate",
    "is_vertical_restack_suitable",
    "solve_vertical_restack",
    "vertical_restack_candidate",
]
