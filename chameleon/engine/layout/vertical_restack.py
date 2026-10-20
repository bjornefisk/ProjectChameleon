"""Deterministic vertical re-stack topology for tall, narrow targets."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ..contract import validate_source, validate_target_canvas
from ..errors import InfeasibleLayoutError
from ..geometry.bounds import rotated_aabb
from ..geometry.math_util import to_fraction
from .horizontal_ribbon import (
    _build_extreme_candidate,
    _fail,
    _render_candidate,
)
from .candidate import RenderedCandidate
from .roles import infer_roles


def is_vertical_restack_suitable(
    source: Mapping[str, Any], target_canvas: Mapping[str, Any]
) -> bool:
    """Return whether source evidence supports a tall, narrow re-stack."""

    source_width = to_fraction(source["canvas"]["width"])
    source_height = to_fraction(source["canvas"]["height"])
    target_width = to_fraction(target_canvas["width"])
    target_height = to_fraction(target_canvas["height"])
    if not source["elements"] or target_height <= target_width:
        return False
    model = infer_roles(source)
    foreground_widths = [
        rotated_aabb(element)[2] - rotated_aabb(element)[0]
        for index, element in enumerate(source["elements"])
        if index != model.background_index and to_fraction(element["width"]) > 0 and to_fraction(element["height"]) > 0
    ]
    if not foreground_widths:
        return False
    return (
        target_height > source_height
        and target_width < source_width
        and target_height / target_width > source_height / source_width
        and target_width <= max(foreground_widths)
    )


def generate_vertical_restack_candidate(
    source: Mapping[str, Any],
    target_canvas: Mapping[str, Any],
    *,
    font_manager=None,
    fonts_dir: str | None = None,
    assets_dir: str | None = None,
) -> RenderedCandidate:
    validate_source(source)
    validate_target_canvas(target_canvas)
    if not is_vertical_restack_suitable(source, target_canvas):
        _fail("source and target proportions do not support a vertical restack")
    response = _build_extreme_candidate(
        source,
        target_canvas,
        axis="vertical",
        font_manager=font_manager,
        fonts_dir=fonts_dir,
    )
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
