"""Deterministic fixed-point quality scoring for hard-valid layouts.

Ranking is deliberately downstream of serialized hard validation and renderer
execution.  The functions in this module never make an invalid candidate
eligible; they only compare candidates that have already passed the contract
and renderer gates.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from fractions import Fraction
from typing import Any

from ..geometry.bounds import rotated_aabb
from ..geometry.math_util import to_fraction
from .roles import RoleKind, RoleModel, infer_roles

SCORE_SCALE = 1000


@dataclass(frozen=True, slots=True)
class QualityScore:
    """Fixed-point quality components, all in the inclusive ``0..1000`` range."""

    readability: int
    balance: int
    alignment: int
    hierarchy: int

    def __post_init__(self) -> None:
        for name in ("readability", "balance", "alignment", "hierarchy"):
            value = getattr(self, name)
            if type(value) is not int or not 0 <= value <= SCORE_SCALE:
                raise ValueError(f"{name} must be an integer in 0..{SCORE_SCALE}")

    def as_tuple(self) -> tuple[int, int, int, int]:
        """Return the accepted quality comparison order.

        Readability is the primary soft objective.  Hierarchy preservation
        follows it, then alignment, then balance/whitespace.
        """

        return (self.readability, self.hierarchy, self.alignment, self.balance)

    @property
    def quality_tuple(self) -> tuple[int, int, int, int]:
        return self.as_tuple()


@dataclass(frozen=True, slots=True)
class _Box:
    min_x: Fraction
    min_y: Fraction
    max_x: Fraction
    max_y: Fraction

    @property
    def width(self) -> Fraction:
        return max(Fraction(0), self.max_x - self.min_x)

    @property
    def height(self) -> Fraction:
        return max(Fraction(0), self.max_y - self.min_y)

    @property
    def center(self) -> tuple[Fraction, Fraction]:
        return ((self.min_x + self.max_x) / 2, (self.min_y + self.max_y) / 2)


def _clamp(value: Fraction | float | int) -> int:
    if isinstance(value, Fraction):
        scaled = value
    else:
        scaled = Fraction(value)
    if scaled <= 0:
        return 0
    if scaled >= SCORE_SCALE:
        return SCORE_SCALE
    return int(scaled)


def _ratio_score(numerator: Fraction, denominator: Fraction) -> int:
    if denominator <= 0:
        return 0
    return _clamp(numerator / denominator * SCORE_SCALE)


def _box(element: Mapping[str, Any]) -> _Box:
    aabb = rotated_aabb(element)
    return _Box(aabb[0], aabb[1], aabb[2], aabb[3])


def _background_index(roles: RoleModel | None) -> int | None:
    return roles.background_index if roles is not None else None


def _role_weight(role: RoleKind | None) -> Fraction:
    return {
        RoleKind.HERO_MEDIA: Fraction(5),
        RoleKind.LOGO: Fraction(4),
        RoleKind.HEADLINE: Fraction(5),
        RoleKind.SUPPORTING_TEXT: Fraction(2),
        RoleKind.CTA: Fraction(3),
        RoleKind.BADGE: Fraction(2),
        RoleKind.IMAGE: Fraction(3),
        RoleKind.DECORATION: Fraction(1),
        RoleKind.SHAPE: Fraction(1),
        RoleKind.BACKGROUND: Fraction(0),
    }.get(role, Fraction(1))


def _contrast_score(
    rendered_png: bytes | None,
    response_elements: Sequence[Mapping[str, Any]],
    text_indices: Sequence[int],
    canvas: Mapping[str, Any],
) -> int:
    """Return a deterministic pixel-variation proxy for text contrast.

    The renderer has already enforced actual glyph bounds.  This deliberately
    modest proxy uses the luminance range in each rendered text box, so it
    cannot admit or rescue a hard-invalid candidate and remains useful when a
    foreground is rendered over an image rather than a flat color.
    """

    if rendered_png is None or not text_indices:
        return 500 if text_indices else SCORE_SCALE
    try:
        from io import BytesIO
        from PIL import Image

        with Image.open(BytesIO(rendered_png)) as image:
            image.load()
            image = image.convert("L")
            image_width, image_height = image.size
            target_width = max(1, int(canvas["width"]))
            target_height = max(1, int(canvas["height"]))
            scores: list[int] = []
            for index in text_indices:
                element = response_elements[index]
                left = max(0, min(image_width, int(to_fraction(element["x"]) * image_width / target_width)))
                top = max(0, min(image_height, int(to_fraction(element["y"]) * image_height / target_height)))
                right = max(left + 1, min(image_width, int((to_fraction(element["x"]) + to_fraction(element["width"])) * image_width / target_width)))
                bottom = max(top + 1, min(image_height, int((to_fraction(element["y"]) + to_fraction(element["height"])) * image_height / target_height)))
                low, high = image.crop((left, top, right, bottom)).getextrema()
                spread = Fraction(high - low)
                scores.append(_clamp(spread / 128 * SCORE_SCALE))
            return int(sum(scores) / len(scores)) if scores else 500
    except (OSError, ValueError, TypeError, ZeroDivisionError) as error:
        raise RuntimeError("rendered candidate PNG could not be decoded") from error


def _readability_score(
    source_elements: Sequence[Mapping[str, Any]],
    response_elements: Sequence[Mapping[str, Any]],
    rendered_png: bytes | None,
    canvas: Mapping[str, Any],
) -> int:
    text_indices = [
        index for index, element in enumerate(response_elements) if element.get("type") == "text"
    ]
    if not text_indices:
        return SCORE_SCALE
    size_scores: list[int] = []
    for index in text_indices:
        source_size = max(Fraction(1), to_fraction(source_elements[index].get("font_size", 1)))
        response_size = max(Fraction(1), to_fraction(response_elements[index].get("font_size", 1)))
        # Ten pixels is the documented readable preference unless the source is
        # smaller.  A 24px cap preserves a useful distinction among larger,
        # still-readable text without making huge source sizes dominate.
        preferred = min(Fraction(24), max(Fraction(1), source_size))
        reference = preferred
        size_scores.append(_clamp(response_size / reference * SCORE_SCALE))
    size_score = int(sum(size_scores) / len(size_scores))
    contrast_score = _contrast_score(rendered_png, response_elements, text_indices, canvas)
    return int((size_score + contrast_score) / 2)


def _scene_indices(
    response_elements: Sequence[Mapping[str, Any]],
    background_index: int | None,
) -> list[int]:
    return [
        index
        for index, element in enumerate(response_elements)
        if index != background_index
        and to_fraction(element.get("width", 0)) > 0
        and to_fraction(element.get("height", 0)) > 0
    ]


def _balance_score(
    response_elements: Sequence[Mapping[str, Any]],
    canvas: Mapping[str, Any],
    roles: RoleModel | None,
) -> int:
    indices = _scene_indices(response_elements, _background_index(roles))
    if not indices:
        return SCORE_SCALE
    target_center = (
        to_fraction(canvas["width"]) / 2,
        to_fraction(canvas["height"]) / 2,
    )
    total_weight = Fraction(0)
    weighted_x = Fraction(0)
    weighted_y = Fraction(0)
    for index in indices:
        element = response_elements[index]
        box = _box(element)
        role = roles.assignments[index].role if roles is not None else None
        weight = max(Fraction(1), box.width * box.height) * _role_weight(role)
        center_x, center_y = box.center
        weighted_x += center_x * weight
        weighted_y += center_y * weight
        total_weight += weight
    if total_weight <= 0:
        return 0
    center_x, center_y = weighted_x / total_weight, weighted_y / total_weight
    width = max(Fraction(1), to_fraction(canvas["width"]))
    height = max(Fraction(1), to_fraction(canvas["height"]))
    normalized = (
        abs(center_x - target_center[0]) / width
        + abs(center_y - target_center[1]) / height
    )
    center_score = _clamp(max(Fraction(0), Fraction(1) - normalized) * SCORE_SCALE)

    min_x = min(_box(response_elements[index]).min_x for index in indices)
    max_x = max(_box(response_elements[index]).max_x for index in indices)
    min_y = min(_box(response_elements[index]).min_y for index in indices)
    max_y = max(_box(response_elements[index]).max_y for index in indices)
    left_gap = max(Fraction(0), min_x)
    right_gap = max(Fraction(0), width - max_x)
    top_gap = max(Fraction(0), min_y)
    bottom_gap = max(Fraction(0), height - max_y)
    gap_x = _ratio_score(min(left_gap, right_gap), max(Fraction(1), max(left_gap, right_gap)))
    gap_y = _ratio_score(min(top_gap, bottom_gap), max(Fraction(1), max(top_gap, bottom_gap)))
    return int((center_score * 2 + gap_x + gap_y) / 4)


def _alignment_score(
    response_elements: Sequence[Mapping[str, Any]],
    canvas: Mapping[str, Any],
    roles: RoleModel | None,
) -> int:
    indices = _scene_indices(response_elements, _background_index(roles))
    if len(indices) < 2:
        return SCORE_SCALE
    width = max(Fraction(1), to_fraction(canvas["width"]))
    height = max(Fraction(1), to_fraction(canvas["height"]))
    x_centers = [_box(response_elements[index]).center[0] for index in indices]
    y_centers = [_box(response_elements[index]).center[1] for index in indices]
    x_reference = min(x_centers, key=lambda value: (abs(value - width / 2), value))
    y_reference = min(y_centers, key=lambda value: (abs(value - height / 2), value))
    x_error = sum(abs(value - x_reference) for value in x_centers) / len(x_centers)
    y_error = sum(abs(value - y_reference) for value in y_centers) / len(y_centers)
    x_score = _clamp(max(Fraction(0), Fraction(1) - x_error / width) * SCORE_SCALE)
    y_score = _clamp(max(Fraction(0), Fraction(1) - y_error / height) * SCORE_SCALE)
    return int((x_score + y_score) / 2)


def _rank_order(values: Sequence[Fraction]) -> dict[int, int]:
    ordered = sorted(range(len(values)), key=lambda index: (-values[index], index))
    return {index: rank for rank, index in enumerate(ordered)}


def _hierarchy_score(
    source_elements: Sequence[Mapping[str, Any]],
    response_elements: Sequence[Mapping[str, Any]],
    roles: RoleModel | None,
) -> int:
    indices = [
        index
        for index, element in enumerate(source_elements)
        if index != _background_index(roles)
        and to_fraction(element.get("width", 0)) > 0
        and to_fraction(element.get("height", 0)) > 0
    ]
    if len(indices) < 2:
        return SCORE_SCALE
    source_values: list[Fraction] = []
    response_values: list[Fraction] = []
    for index in indices:
        source = source_elements[index]
        response = response_elements[index]
        if source.get("type") == "text":
            source_values.append(to_fraction(source.get("font_size", 1)))
            response_values.append(to_fraction(response.get("font_size", 1)))
        else:
            source_values.append(to_fraction(source.get("width", 0)) * to_fraction(source.get("height", 0)))
            response_values.append(to_fraction(response.get("width", 0)) * to_fraction(response.get("height", 0)))
    source_order = _rank_order(source_values)
    response_order = _rank_order(response_values)
    preserved = sum(source_order[index] == response_order[index] for index in range(len(indices)))
    return _ratio_score(Fraction(preserved), Fraction(len(indices)))


def score_candidate(
    source: Mapping[str, Any],
    response: Mapping[str, Any],
    rendered_png: bytes | None = None,
    *,
    roles: RoleModel | None = None,
) -> QualityScore:
    """Score one already hard-valid, rendered response in fixed-point units."""

    source_elements = source["elements"]
    response_elements = response["elements"]
    role_model = roles or infer_roles(source)
    return QualityScore(
        readability=_readability_score(source_elements, response_elements, rendered_png, response["canvas"]),
        balance=_balance_score(response_elements, response["canvas"], role_model),
        alignment=_alignment_score(response_elements, response["canvas"], role_model),
        hierarchy=_hierarchy_score(source_elements, response_elements, role_model),
    )


def ranking_key(candidate: Any) -> tuple[int, tuple[int, int, int, int], int, int, int]:
    """Return a ``max``-compatible key for the contract tie-break order.

    The public conceptual tuple is ``(hard_validity, quality_tuple,
    topology_order, candidate_index, source_order)``.  Quality is preferred
    descending; the three stable tie-break indices are preferred ascending, so
    their signs are inverted for Python's ``max`` operation.
    """

    quality = candidate.quality.as_tuple()
    return (
        int(getattr(candidate, "hard_validity", 1)),
        quality,
        -int(candidate.topology_order),
        -int(candidate.candidate_index),
        -int(candidate.source_order),
    )


def select_best(candidates: Sequence[Any]) -> Any:
    """Select the deterministic best candidate from hard-valid candidates."""

    if not candidates:
        raise ValueError("cannot select from an empty candidate set")
    invalid = [candidate for candidate in candidates if int(getattr(candidate, "hard_validity", 1)) != 1]
    if invalid:
        raise ValueError("ranking accepts hard-valid candidates only")
    return max(candidates, key=ranking_key)


def rank_candidates(candidates: Sequence[Any]) -> list[Any]:
    """Return hard-valid candidates in deterministic best-first order."""

    if any(int(getattr(candidate, "hard_validity", 1)) != 1 for candidate in candidates):
        raise ValueError("ranking accepts hard-valid candidates only")
    return sorted(candidates, key=ranking_key, reverse=True)


__all__ = [
    "QualityScore",
    "SCORE_SCALE",
    "rank_candidates",
    "ranking_key",
    "score_candidate",
    "select_best",
]
