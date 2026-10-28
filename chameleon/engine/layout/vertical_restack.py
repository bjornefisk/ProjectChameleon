"""Deterministic vertical re-stack topology for tall, narrow targets."""

from __future__ import annotations

from collections.abc import Mapping
from fractions import Fraction
from math import ceil
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
from .candidate import RenderedCandidate
from .roles import infer_roles


def _distribute_vertical_slack(
    source: Mapping[str, Any],
    target_canvas: Mapping[str, Any],
    response: dict[str, Any],
    *,
    font_manager=None,
    fonts_dir: str | None = None,
) -> None:
    """Spread unused vertical space over the stack while keeping units rigid."""

    elements = response["elements"]
    ratio = to_fraction(target_canvas["width"]) / to_fraction(target_canvas["height"])
    compact_square = Fraction(9, 10) <= ratio <= Fraction(11, 10)
    if not compact_square and ratio > Fraction(35, 100):
        return
    gutter = 12 if compact_square else 6
    background = infer_roles(source).background_index
    foreground_bottoms = [
        rotated_aabb(element).max_y
        for index, element in enumerate(elements)
        if index != background
        and to_fraction(element["width"]) > 0
        and to_fraction(element["height"]) > 0
    ]
    if (
        foreground_bottoms
        and to_fraction(target_canvas["height"]) - max(foreground_bottoms) <= gutter
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
        if error.reason_code is InfeasibleReasonCode.RUNTIME_IO_FAILURE:
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
