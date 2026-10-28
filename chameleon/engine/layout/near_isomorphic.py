"""Level 1 safe, near-isomorphic geometry generation.

The solver deliberately generates one finite candidate. It does not rank
alternatives: if the candidate cannot satisfy the hard geometry invariants it
reports ``INCOMPLETE_SEARCH`` because the bounded path does not exhaust the
full candidate space.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from collections.abc import Mapping
from fractions import Fraction
from math import gcd
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, NoReturn

from PIL import Image

from ..artifact import validate_artifact
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
from .candidate import RenderedCandidate


@lru_cache(maxsize=1)
def _renderer_components():
    """Load renderer dependencies only when a candidate is evaluated."""

    try:
        from chameleon.renderer.converter.brand_fonts import (
            load_brand_font_manager,
        )
        from chameleon.renderer.converter.convert import (
            convert_chameleon_to_crello,
            render_design_to_png,
        )
        from chameleon.renderer.converter.wrap import TextLayoutError
    except ModuleNotFoundError:
        from renderer.converter.brand_fonts import load_brand_font_manager
        from renderer.converter.convert import (
            convert_chameleon_to_crello,
            render_design_to_png,
        )
        from renderer.converter.wrap import TextLayoutError
    return (
        load_brand_font_manager,
        convert_chameleon_to_crello,
        render_design_to_png,
        TextLayoutError,
    )


_GEOMETRY_FIELDS = ("x", "y", "width", "height")
logger = logging.getLogger(__name__)


def _floor_fraction(value: Fraction) -> int:
    return value.numerator // value.denominator


def _ceil_fraction(value: Fraction) -> int:
    return -((-value.numerator) // value.denominator)




def _fail(message: str, **details: Any) -> NoReturn:
    details = {"search_kind": "near_isomorphic", "search_exhausted": False, **details}
    raise InfeasibleLayoutError(
        InfeasibleReasonCode.INCOMPLETE_SEARCH,
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


def _bleed_position_candidates(
    element: Mapping[str, Any],
    scale: Fraction,
    tx: Fraction,
    ty: Fraction,
    source_canvas: Mapping[str, Any],
    target_canvas: Mapping[str, Any],
    expected_bleed: frozenset[str],
) -> list[tuple[Fraction, Fraction]]:
    source_width = to_fraction(source_canvas["width"])
    source_height = to_fraction(source_canvas["height"])
    target_width = to_fraction(target_canvas["width"])
    target_height = to_fraction(target_canvas["height"])
    x_translations = [tx]
    y_translations = [ty]
    if "left" in expected_bleed:
        x_translations.append(Fraction(0))
    if "right" in expected_bleed:
        x_translations.append(target_width - source_width * scale)
    if "top" in expected_bleed:
        y_translations.append(Fraction(0))
    if "bottom" in expected_bleed:
        y_translations.append(target_height - source_height * scale)

    candidates: list[tuple[Fraction, Fraction]] = []
    for candidate_tx in x_translations:
        for candidate_ty in y_translations:
            raw_x, raw_y, _raw_width, _raw_height = _transformed_box(
                element, scale, candidate_tx, candidate_ty
            )
            for position in _position_candidates(raw_x, raw_y):
                if position not in candidates:
                    candidates.append(position)
    return candidates


def _position_candidates(x: Fraction, y: Fraction) -> list[tuple[Fraction, Fraction]]:
    candidates: list[tuple[Fraction, Fraction]] = []
    for radius in range(3):
        for dx, dy in ((0, 0), (-radius, 0), (radius, 0), (0, -radius), (0, radius)):
            item = (x + dx, y + dy)
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

def _preserves_source_separation(
    source_elements: list[Mapping[str, Any]],
    response_elements: list[Mapping[str, Any]],
) -> bool:
    source_aabbs = [rotated_aabb(element) for element in source_elements]
    response_aabbs = [rotated_aabb(element) for element in response_elements]
    for left in range(len(source_elements)):
        if (
            to_fraction(response_elements[left]["width"]) <= 0
            or to_fraction(response_elements[left]["height"]) <= 0
        ):
            continue
        for right in range(left + 1, len(source_elements)):
            if (
                to_fraction(response_elements[right]["width"]) <= 0
                or to_fraction(response_elements[right]["height"]) <= 0
            ):
                continue
            if positive_aabb_intersection(source_aabbs[left], source_aabbs[right]):
                continue
            if positive_aabb_intersection(response_aabbs[left], response_aabbs[right]):
                return False
    return True

def _choose_ratio_dimensions(
    element: Mapping[str, Any],
    raw_width: Fraction,
    raw_height: Fraction,
    raw_x: Fraction,
    raw_y: Fraction,
    target: Mapping[str, Any],
    expected_bleed: frozenset[str] | None,
    *,
    raw_positions: list[tuple[Fraction, Fraction]] | None = None,
) -> tuple[Fraction, Fraction, Fraction, Fraction] | None:
    positions = raw_positions or _position_candidates(raw_x, raw_y)
    ratio = (
        reduced_ratio(element["width"], element["height"])
        if element.get("type") == "image"
        else None
    )
    if ratio is None:
        for x, y in positions:
            geometry = (x, y, raw_width, raw_height)
            if _safe_geometry(element, *geometry, target, expected_bleed):
                return geometry
        return None

    p, q = ratio
    preferred = raw_width / p
    floor_multiplier = _floor_fraction(preferred)
    # Prefer the source-proportional lattice point, then reduce only when the
    # exact AABB containment check rejects that point.

    multipliers: list[int] = []
    for multiplier in (floor_multiplier, floor_multiplier + 1):
        if multiplier >= 1 and multiplier not in multipliers:
            multipliers.append(multiplier)
    for multiplier in range(max(1, floor_multiplier - 1), 0, -1):
        if multiplier not in multipliers:
            multipliers.append(multiplier)
    for multiplier in multipliers:
        width, height = Fraction(multiplier * p), Fraction(multiplier * q)
        position_list = raw_positions or _position_candidates(
            raw_x + (raw_width - width) / 2,
            raw_y + (raw_height - height) / 2,
        )
        for x, y in position_list:
            geometry = (x, y, width, height)
            if _safe_geometry(element, *geometry, target, expected_bleed):
                return geometry
    return None


def _group_candidate(
    elements: list[Mapping[str, Any]],
    scale: Fraction,
    target: Mapping[str, Any],
    *,
    cover_element_id: Any | None = None,
    preferred_translation: tuple[Fraction, Fraction] | None = None,
    occupied: list[tuple[Mapping[str, Any], Mapping[str, Any]]] | None = None,
) -> tuple[dict[str, tuple[Fraction, Fraction, Fraction, Fraction]], Fraction] | None:
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

    cover_element = next(
        (element for element in elements if element["id"] == cover_element_id),
        None,
    )
    source_aabbs = [rotated_aabb(element) for element in elements]
    minimum_scale = scale
    if cover_element is not None:
        cover_aabb = rotated_aabb(cover_element)
        minimum_scale = max(
            minimum_scale,
            to_fraction(target["width"]) / (cover_aabb[2] - cover_aabb[0]),
            to_fraction(target["height"]) / (cover_aabb[3] - cover_aabb[1]),
        )

    def _scale_candidates() -> list[Fraction]:
        if cover_element is not None:
            return [unit * max(1, _ceil_fraction(minimum_scale / unit))]

        source_min_x = min(aabb[0] for aabb in source_aabbs)
        source_max_x = max(aabb[2] for aabb in source_aabbs)
        source_min_y = min(aabb[1] for aabb in source_aabbs)
        source_max_y = max(aabb[3] for aabb in source_aabbs)
        max_scale: Fraction | None = None
        x_span = source_max_x - source_min_x
        y_span = source_max_y - source_min_y
        if x_span > 0:
            max_scale = to_fraction(target["width"]) / x_span
        if y_span > 0:
            y_limit = to_fraction(target["height"]) / y_span
            max_scale = y_limit if max_scale is None else min(max_scale, y_limit)

        desired_multiplier = scale / unit
        multipliers = {
            max(1, _floor_fraction(desired_multiplier)),
            max(1, _ceil_fraction(desired_multiplier)),
        }
        if max_scale is not None:
            maximum_multiplier = _floor_fraction(max_scale / unit)
            if maximum_multiplier < 1:
                return []
            multipliers.add(maximum_multiplier)
            multipliers = {
                min(multiplier, maximum_multiplier)
                for multiplier in multipliers
                if multiplier >= 1
            }
        return [
            unit * multiplier
            for multiplier in sorted(
                multipliers,
                key=lambda multiplier: (abs(unit * multiplier - scale), -multiplier),
            )
        ]

    def _translation_candidates(
        group_scale: Fraction,
        axis: int,
        first_coordinate: Fraction,
        target_size: Fraction,
        preferred_translation: Fraction | None = None,
    ) -> list[Fraction]:
        source_center = (
            min(aabb[axis] for aabb in source_aabbs)
            + max(aabb[axis + 2] for aabb in source_aabbs)
        ) / 2
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
            return []
        minimum_anchor = _ceil_fraction(anchor_lower)
        maximum_anchor = _floor_fraction(anchor_upper)
        if minimum_anchor > maximum_anchor:
            return []
        desired_anchor = (
            target_size / 2
            - group_scale * source_center
            + group_scale * first_coordinate
        )
        proposed_anchors: list[Fraction] = []
        if preferred_translation is not None:
            proposed_anchors.append(
                group_scale * first_coordinate + preferred_translation
            )
        proposed_anchors.extend(
            (
                _floor_fraction(desired_anchor),
                _ceil_fraction(desired_anchor),
                minimum_anchor,
                maximum_anchor,
            )
        )
        anchors: list[Fraction] = []
        for proposed in proposed_anchors:
            anchor = min(Fraction(maximum_anchor), max(Fraction(minimum_anchor), proposed))
            if anchor not in anchors:
                anchors.append(anchor)
        return [anchor - group_scale * first_coordinate for anchor in anchors]

    for group_scale in _scale_candidates():
        x_translations = _translation_candidates(
            group_scale,
            0,
            first_x,
            to_fraction(target["width"]),
            preferred_translation=(
                preferred_translation[0] if preferred_translation is not None else None
            ),
        )
        y_translations = _translation_candidates(
            group_scale,
            1,
            first_y,
            to_fraction(target["height"]),
            preferred_translation=(
                preferred_translation[1] if preferred_translation is not None else None
            ),
        )
        for tx in x_translations:
            for ty in y_translations:
                result: dict[str, tuple[Fraction, Fraction, Fraction, Fraction]] = {}
                valid = True
                for element in elements:
                    raw_box = (
                        to_fraction(element["x"]) * group_scale + tx,
                        to_fraction(element["y"]) * group_scale + ty,
                        to_fraction(element["width"]) * group_scale,
                        to_fraction(element["height"]) * group_scale,
                    )
                    geometry = raw_box
                    x, y, width, height = geometry
                    candidate = dict(element)
                    candidate.update(dict(zip(_GEOMETRY_FIELDS, geometry)))
                    aabb = rotated_aabb(candidate)
                    if element["id"] == cover_element_id:
                        target_width = to_fraction(target["width"])
                        target_height = to_fraction(target["height"])
                        valid = (
                            aabb[0] <= 0
                            and aabb[1] <= 0
                            and aabb[2] >= target_width
                            and aabb[3] >= target_height
                        )
                    else:
                        valid = _safe_geometry(element, x, y, width, height, target, None)
                    if not valid:
                        break
                    result[element["id"]] = geometry
                if valid:
                    candidate_elements = []
                    for element in elements:
                        candidate = dict(element)
                        candidate.update(
                            dict(zip(_GEOMETRY_FIELDS, result[element["id"]]))
                        )
                        candidate_elements.append(candidate)
                    source_for_check = list(elements)
                    response_for_check = candidate_elements
                    if occupied:
                        source_for_check.extend(source for source, _ in occupied)
                        response_for_check.extend(response for _, response in occupied)
                    if _preserves_source_separation(
                        source_for_check, response_for_check
                    ):
                        return result, group_scale
    return None

def _serialize_candidate(response: Mapping[str, Any]) -> dict[str, Any]:
    """Apply one half-even serialization at the complete response boundary."""

    serialized = {"canvas": dict(response["canvas"]), "elements": []}
    for element in response["elements"]:
        serialized_element = dict(element)
        for field in _GEOMETRY_FIELDS:
            serialized_element[field] = quantize_to_int(element[field])
        if element.get("type") == "text":
            serialized_element["font_size"] = quantize_to_int(element["font_size"])
        serialized["elements"].append(serialized_element)
    return serialized


def _text_fits(
    element: Mapping[str, Any],
    font_size: int,
    font_manager,
    target: Mapping[str, Any],
) -> bool:
    _, convert_chameleon_to_crello, _, TextLayoutError = _renderer_components()
    candidate = dict(element)
    candidate["font_size"] = font_size
    try:
        # Use the production converter here. It checks style runs, Unicode wrapping,
        # line height, letter spacing, and glyph bounds together.
        convert_chameleon_to_crello(
            {"canvas": dict(target), "elements": [candidate]}, font_manager
        )
    except TextLayoutError:
        return False
    return True

_MAX_FONT_SEARCH_STEPS = 64
_FONT_SEARCH_PREFERENCE_PROBE_LIMIT = 10
_MAX_FONT_SEARCH_BITS = 63
_MAX_RENDERER_FONT_SIZE = 1 << 20

_MAX_FONT_SEARCH_PROBES = (
    _MAX_FONT_SEARCH_STEPS + _FONT_SEARCH_PREFERENCE_PROBE_LIMIT
)


def _font_size_probe_order(preferred: int) -> tuple[int, ...]:
    """Return the bounded deterministic font-size probe sequence."""
    search_start = max(1, int(preferred))
    if (
        search_start > _MAX_RENDERER_FONT_SIZE
        or search_start.bit_length() > _MAX_FONT_SEARCH_BITS
    ):
        search_start = _MAX_RENDERER_FONT_SIZE
    main_count = min(search_start, _MAX_FONT_SEARCH_STEPS)
    sizes = list(range(search_start, search_start - main_count, -1))
    seen = set(sizes)
    sizes.extend(
        size
        for size in range(
            min(search_start, _FONT_SEARCH_PREFERENCE_PROBE_LIMIT), 0, -1
        )
        if size not in seen
    )
    return tuple(sizes)


def _largest_fitting_font_size(
    element: Mapping[str, Any],
    preferred: int,
    font_manager,
    target: Mapping[str, Any],
    *,
    fit=None,
    search_details: dict[str, Any] | None = None,
) -> int | None:
    """Find a fitting integer with a deterministic bounded search.

    Very large source font sizes are clamped only as a renderer probe ceiling;
    the search also probes the soft-preference band through size one so a
    smaller hard-valid candidate is not rejected solely because the source is
    large.
    """

    preferred = max(1, int(preferred))
    search_start = preferred
    preferred_clamped = False
    if preferred > _MAX_RENDERER_FONT_SIZE or preferred.bit_length() > _MAX_FONT_SEARCH_BITS:
        search_start = _MAX_RENDERER_FONT_SIZE
        preferred_clamped = True

    fits = fit or _text_fits
    tested_sizes: list[int] = []

    def try_size(size: int) -> bool:
        if size in tested_sizes:
            return False
        tested_sizes.append(size)
        return bool(fits(element, size, font_manager, target))

    for size in _font_size_probe_order(search_start):
        if try_size(size):
            return size

    if search_details is not None:
        exhausted_size_one = 1 in tested_sizes
        search_exhausted = len(tested_sizes) == search_start
        search_details.update(
            {
                "preferred_size": preferred,
                "search_start": search_start,
                "preferred_clamped": preferred_clamped,
                "max_steps": _MAX_FONT_SEARCH_STEPS,
                "preference_probe_limit": _FONT_SEARCH_PREFERENCE_PROBE_LIMIT,
                "max_bits": _MAX_FONT_SEARCH_BITS,
                "max_renderer_size": _MAX_RENDERER_FONT_SIZE,
                "candidate_order": "descending_with_soft_preference_probe",
                "work_unit": "font_size_candidate",
                "attempted": bool(tested_sizes),
                "no_attempt": not tested_sizes,
                "tested_size_range": (
                    [max(tested_sizes), min(tested_sizes)] if tested_sizes else None
                ),
                "tested_size_count": len(tested_sizes),
                "search_exhausted": search_exhausted,
                "exhausted_size_one": exhausted_size_one,
                "hit_cutoff": not search_exhausted,
                "status_reason": (
                    "font_search_exhausted_at_size_one"
                    if search_exhausted
                    else "font_search_step_limit_reached"
                ),
            }
        )
    return None


def _render_candidate(
    response: Mapping[str, Any],
    assets_dir: str | None,
    fonts_dir: str | None,
    font_manager,
) -> tuple[bytes, tuple[str, ...]]:
    _, _, render_candidate_to_png, _ = _renderer_components()
    resolved_assets_dir = assets_dir or str(Path(__file__).resolve().parents[2] / "brand_kit" / "assets")
    resolved_fonts_dir = fonts_dir or str(Path(__file__).resolve().parents[2] / "brand_kit" / "fonts")
    with TemporaryDirectory(prefix=".chameleon-layout-") as directory:
        png_path = Path(directory) / "candidate.png"
        raw_warnings = render_candidate_to_png(
            dict(response),
            resolved_assets_dir,
            png_path,
            fonts_dir=resolved_fonts_dir,
            font_manager=font_manager,
        )
        warnings = tuple(str(warning) for warning in raw_warnings or [])
        for warning in warnings:
            logger.warning("renderer warning: %r", warning)
        with Image.open(png_path) as image:
            if image.format != "PNG":
                raise ValueError("renderer did not produce a PNG artifact")
            image.verify()
        with Image.open(png_path) as image:
            image.load()
            validate_artifact(
                response,
                image,
                assets_dir=resolved_assets_dir,
                fonts_dir=resolved_fonts_dir,
                font_manager=font_manager,
                warnings=warnings,
            )
        return png_path.read_bytes(), warnings


def _preferred_font_size(source_size: Fraction, scale: Fraction) -> int:
    """Choose a serialized search ceiling without enlarging small source text."""

    source_limit = (
        _floor_fraction(source_size)
        if source_size < Fraction(10)
        else quantize_to_int(source_size)
    )
    readability_preference = min(source_limit, 10)
    scaled_size = quantize_to_int(source_size * scale)
    preferred = min(source_limit, max(readability_preference, scaled_size))
    return max(1, preferred)


def solve_near_isomorphic(
    source: Mapping[str, Any],
    target_canvas: Mapping[str, Any],
    *,
    variant: str = "source_proportional",
    font_manager=None,
    fonts_dir: str | None = None,
    assets_dir: str | None = None,
) -> RenderedCandidate:
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
    target_width = to_fraction(target_canvas["width"])
    target_height = to_fraction(target_canvas["height"])

    # Place ungrouped records first. Group placement can then choose among
    # several legal translations without creating a new collision with the
    # already transformed source topology.
    for index, element in enumerate(source_elements):
        if element.get("group_id") is not None:
            continue
        if index == background_index:
            transformed[index] = (0, 0, int(target_width), int(target_height))
            continue
        raw_x, raw_y, raw_width, raw_height = _transformed_box(element, scale, tx, ty)
        expected_bleed = source_bleed_sides(element, source_aabbs[index], source["canvas"])
        raw_positions = (
            _bleed_position_candidates(
                element,
                scale,
                tx,
                ty,
                source["canvas"],
                target_canvas,
                expected_bleed,
            )
            if expected_bleed is not None
            else None
        )
        geometry = _choose_ratio_dimensions(
            element,
            raw_width,
            raw_height,
            raw_x,
            raw_y,
            target_canvas,
            expected_bleed,
            raw_positions=raw_positions,
        )
        if geometry is None:
            _fail(
                "foreground geometry cannot be represented as safe integer bounds",
                element_id=element["id"],
            )
        transformed[index] = geometry

    for group_id, indices in group_indices.items():
        cover_element_id = (
            source_elements[background_index]["id"]
            if background_index in indices
            else None
        )
        occupied = []
        for occupied_index, geometry in transformed.items():
            occupied_element = dict(source_elements[occupied_index])
            occupied_element.update(dict(zip(_GEOMETRY_FIELDS, geometry)))
            occupied.append((source_elements[occupied_index], occupied_element))
        group = _group_candidate(
            [source_elements[index] for index in indices],
            scale,
            target_canvas,
            cover_element_id=cover_element_id,
            preferred_translation=(tx, ty) if cover_element_id is None else None,
            occupied=occupied,
        )
        if group is None:
            _fail(
                "explicit group cannot be represented by one positive integer transform",
                group_id=group_id,
            )
        geometries, _group_scale = group
        for index in indices:
            transformed[index] = geometries[source_elements[index]["id"]]
    for index, geometry in transformed.items():
        response_elements[index].update(dict(zip(_GEOMETRY_FIELDS, geometry)))

    text_indices = [index for index, element in enumerate(source_elements) if element["type"] == "text"]
    if text_indices:
        if font_manager is None:
            load_brand_font_manager = _renderer_components()[0]
            resolved_fonts_dir = fonts_dir or str(Path(__file__).resolve().parents[2] / "brand_kit" / "fonts")
            font_manager = load_brand_font_manager(resolved_fonts_dir)
        for index in text_indices:
            element = source_elements[index]
            preferred = _preferred_font_size(to_fraction(element["font_size"]), scale)
            font_search: dict[str, Any] = {}
            selected = _largest_fitting_font_size(
                response_elements[index],
                preferred,
                font_manager,
                target_canvas,
                search_details=font_search,
            )
            if selected is None:
                _fail(
                    "no integer text size fits the renderer bounds",
                    element_id=element["id"],
                    font_search=font_search,
                )
            response_elements[index]["font_size"] = selected

    raw_response = {
        "canvas": {"width": int(target_width), "height": int(target_height)},
        "elements": response_elements,
    }
    response = _serialize_candidate(raw_response)
    try:
        validate_response(
            source,
            target_canvas,
            response,
            font_manager=font_manager,
            fonts_dir=fonts_dir,
        )
    except InfeasibleLayoutError as error:
        if error.reason_code is InfeasibleReasonCode.RUNTIME_IO_FAILURE:
            raise
        _fail(
            "candidate failed serialized hard validation",
            reason_code=error.reason_code.value,
            reason=error.message,
            details=error.details,
        )
    rendered_png, warnings = _render_candidate(response, assets_dir, fonts_dir, font_manager)
    return RenderedCandidate(
        response=response,
        rendered_png=rendered_png,
        warnings=warnings,
    )


__all__ = ["solve_near_isomorphic"]
