"""Deterministic role and relationship inference for source-aware layouts.

The model is intentionally descriptive rather than prescriptive: it records the
signals used by candidate generators while keeping source mappings untouched.
No fixed element ids or universal pixel/aspect templates participate in the
classification.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from fractions import Fraction
from statistics import median
from typing import Any, Iterator, Mapping

from ..geometry.bounds import positive_aabb_intersection, rotated_aabb, source_bleed_sides
from ..geometry.math_util import to_fraction



class RoleKind(str, Enum):
    BACKGROUND = "background"
    LOGO = "logo"
    HERO_MEDIA = "hero_media"
    HEADLINE = "headline"
    SUPPORTING_TEXT = "supporting_text"
    CTA = "cta"
    BADGE = "badge"
    DECORATION = "decoration"
    SHAPE = "shape"
    IMAGE = "image"
    TEXT = "text"
    OTHER = "other"


@dataclass(frozen=True, slots=True)
class RoleAssignment:
    """One source element's inferred role and inspectable evidence."""

    index: int
    element_id: str
    role: RoleKind
    signals: Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class Relationship:
    """Pairwise source relationship used by topology generators."""

    left_index: int
    right_index: int
    left_id: str
    right_id: str
    source_overlap: bool
    same_group: bool


class RelationshipView:
    """Lazy deterministic source-relationship sequence.

    Relationship pairs are derived on demand so role inference does not reject
    contract-valid designs or allocate a quadratic tuple for sparse sources.
    """

    __slots__ = ("_aabbs", "_group_ids", "_ids")

    def __init__(
        self,
        ids: tuple[str, ...],
        group_ids: tuple[Any, ...],
        aabbs: tuple[Any, ...],
    ) -> None:
        self._ids = ids
        self._group_ids = group_ids
        self._aabbs = aabbs

    def __len__(self) -> int:
        count = len(self._ids)
        return count * (count - 1) // 2

    def _row_start(self, left: int) -> int:
        count = len(self._ids)
        return left * (2 * count - left - 1) // 2

    def _pair_for_offset(self, offset: int) -> tuple[int, int]:
        if offset < 0 or offset >= len(self):
            raise IndexError(offset)
        low, high = 0, len(self._ids) - 2
        while low <= high:
            middle = (low + high) // 2
            if self._row_start(middle) <= offset:
                low = middle + 1
            else:
                high = middle - 1
        left = high
        right = left + 1 + offset - self._row_start(left)
        return left, right

    def _relationship(self, left: int, right: int) -> "Relationship":
        return Relationship(
            left,
            right,
            self._ids[left],
            self._ids[right],
            positive_aabb_intersection(self._aabbs[left], self._aabbs[right]),
            self._group_ids[left] is not None
            and self._group_ids[left] == self._group_ids[right],
        )

    def for_pair(self, left: int, right: int) -> "Relationship":
        if left == right or min(left, right) < 0 or max(left, right) >= len(self._ids):
            raise IndexError((left, right))
        if left > right:
            left, right = right, left
        return self._relationship(left, right)

    def __iter__(self) -> Iterator["Relationship"]:
        for left in range(len(self._ids)):
            for right in range(left + 1, len(self._ids)):
                yield self._relationship(left, right)

    def __getitem__(self, index: int | slice) -> "Relationship" | tuple["Relationship", ...]:
        if isinstance(index, slice):
            return tuple(self[item] for item in range(*index.indices(len(self))))
        if index < 0:
            index += len(self)
        return self._relationship(*self._pair_for_offset(index))


@dataclass(frozen=True, slots=True)
class RoleModel:
    """Stable role assignments plus source relationships."""

    assignments: tuple[RoleAssignment, ...]
    relationships: RelationshipView
    background_index: int | None

    @property
    def by_id(self) -> Mapping[str, RoleAssignment]:
        return {assignment.element_id: assignment for assignment in self.assignments}

    @property
    def roles(self) -> tuple[RoleKind, ...]:
        return tuple(assignment.role for assignment in self.assignments)

    def role_for(self, element_id: str) -> RoleKind:
        return self.by_id[element_id].role

    def assignment_for(self, element_id: str) -> RoleAssignment:
        return self.by_id[element_id]

    def overlaps(self, left_index: int, right_index: int) -> bool:
        low, high = sorted((left_index, right_index))
        return self.relationships.for_pair(low, high).source_overlap


def _effective_z(element: Mapping[str, Any]) -> int:
    return int(element.get("z_index", 0))


def _area(element: Mapping[str, Any]) -> Fraction:
    return to_fraction(element["width"]) * to_fraction(element["height"])


def _ratio(element: Mapping[str, Any]) -> Fraction | None:
    width = to_fraction(element["width"])
    height = to_fraction(element["height"])
    if width <= 0 or height <= 0:
        return None
    return width / height


def _is_decorative_media(element: Mapping[str, Any]) -> bool:
    """Exclude translucent image overlays from hero emphasis."""
    return to_fraction(element.get("opacity", 1)) < 1


def _rotated_area(aabb: Any) -> Fraction:
    return max(Fraction(0), aabb[2] - aabb[0]) * max(Fraction(0), aabb[3] - aabb[1])


def _fit_priority(element: Mapping[str, Any]) -> int:
    return {"contain": 2, "fill": 1, "cover": 0}.get(element.get("fit", "contain"), 0)


def _content_signal(element: Mapping[str, Any]) -> dict[str, Any]:
    content = str(element.get("content", ""))
    words = tuple(word.casefold() for word in content.replace("-", " ").split())
    action_words = frozenset(
        word
        for word in words
        if word in {"shop", "buy", "learn", "discover", "explore", "get", "try", "start", "join"}
    )
    uppercase = bool(content) and content == content.upper()
    return {
        "content_length": len(content),
        "word_count": len(words),
        "action_words": tuple(sorted(action_words)),
        "uppercase": uppercase,
    }


def _background_index(source: Mapping[str, Any], aabbs: list[Any]) -> int | None:
    canvas = source["canvas"]
    candidates: list[tuple[int, Fraction, int]] = []
    for index, (element, aabb) in enumerate(zip(source["elements"], aabbs)):
        if element.get("type") != "image" or element.get("fit", "contain") != "cover":
            continue
        if not (
            aabb[0] <= 0
            and aabb[1] <= 0
            and aabb[2] >= to_fraction(canvas["width"])
            and aabb[3] >= to_fraction(canvas["height"])
        ):
            continue
        area = max(Fraction(0), aabb[2] - aabb[0]) * max(Fraction(0), aabb[3] - aabb[1])
        candidates.append((_effective_z(element), -area, index))
    return min(candidates)[2] if candidates else None


def infer_roles(source: Mapping[str, Any]) -> RoleModel:
    """Infer deterministic roles and pair relationships from source signals.

    Explicit groups are considered first.  Remaining assignments combine type,
    geometry, effective z-order, opacity/bleed, text metrics/content, source
    position/order, and peer-relative image extents.  The returned model is
    inspectable and does not add or normalize fields in ``source``.
    """

    elements = list(source["elements"])
    aabbs = [rotated_aabb(element) for element in elements]
    background_index = _background_index(source, aabbs)
    image_indices = [
        index
        for index, element in enumerate(elements)
        if element.get("type") == "image" and index != background_index
    ]
    image_ratios = [
        ratio
        for index in image_indices
        if (ratio := _ratio(elements[index])) is not None
    ]
    ratio_median = median(image_ratios) if image_ratios else None
    image_areas = {index: _area(elements[index]) for index in image_indices}
    decorative_media = {
        index for index in image_indices if _is_decorative_media(elements[index])
    }
    hero_candidates = [
        index for index in image_indices if index not in decorative_media
    ] or image_indices
    hero_index = max(
        hero_candidates,
        key=lambda index: (
            _rotated_area(aabbs[index]),
            image_areas[index],
            to_fraction(elements[index].get("opacity", 1)),
            _effective_z(elements[index]),
            _fit_priority(elements[index]),
            -index,
        ),
        default=None,
    )
    logo_candidates = [
        index
        for index in image_indices
        if ratio_median is not None
        and _ratio(elements[index]) is not None
        and _ratio(elements[index]) > ratio_median
    ]
    logo_index = min(
        logo_candidates,
        key=lambda index: (-_ratio(elements[index]), -image_areas[index], index),
        default=None,
    )
    if logo_index == hero_index and len(image_indices) > 1:
        logo_index = None

    group_indices: dict[Any, list[int]] = {}
    for index, element in enumerate(elements):
        group_id = element.get("group_id")
        if group_id is not None:
            group_indices.setdefault(group_id, []).append(index)

    group_roles: dict[Any, RoleKind] = {}
    for group_id, indices in group_indices.items():
        texts = [elements[index] for index in indices if elements[index].get("type") == "text"]
        actions = any(_content_signal(element)["action_words"] for element in texts)
        short_upper = any(
            _content_signal(element)["uppercase"] and _content_signal(element)["content_length"] <= 32
            for element in texts
        )
        group_roles[group_id] = RoleKind.CTA if actions else RoleKind.BADGE if short_upper else RoleKind.SHAPE

    text_indices = [index for index, element in enumerate(elements) if element.get("type") == "text"]
    ungrouped_text_indices = [index for index in text_indices if elements[index].get("group_id") is None]
    headline_index = max(
        ungrouped_text_indices,
        key=lambda index: (
            to_fraction(elements[index].get("font_size", 1)),
            _area(elements[index]),
            -index,
        ),
        default=None,
    )

    assignments: list[RoleAssignment] = []
    source_width = to_fraction(source["canvas"]["width"])
    source_height = to_fraction(source["canvas"]["height"])
    for index, element in enumerate(elements):
        group_id = element.get("group_id")
        bleed = source_bleed_sides(element, aabbs[index], source["canvas"])
        content = _content_signal(element) if element.get("type") == "text" else {}
        signals: dict[str, Any] = {
            "type": element.get("type"),
            "effective_z_index": _effective_z(element),
            "opacity": element.get("opacity", 1),
            "group_id": group_id,
            "source_order": index,
            "area": _area(element),
            "ratio": _ratio(element),
            "center_proportion": (
                (to_fraction(element["x"]) + to_fraction(element["width"]) / 2) / source_width,
                (to_fraction(element["y"]) + to_fraction(element["height"]) / 2) / source_height,
            ),
            "source_bleed_sides": bleed,
            "content": content,
        }
        if index == background_index:
            role = RoleKind.BACKGROUND
        elif group_id in group_roles:
            role = group_roles[group_id]
        elif index == logo_index:
            role = RoleKind.LOGO
        elif index == hero_index:
            role = RoleKind.HERO_MEDIA
        elif element.get("type") == "image":
            role = RoleKind.IMAGE
        elif element.get("type") == "text":
            role = RoleKind.HEADLINE if index == headline_index else RoleKind.SUPPORTING_TEXT
        elif element.get("type") == "shape":
            role = RoleKind.DECORATION if bleed is not None or element.get("opacity", 1) < 1 else RoleKind.SHAPE
        else:
            role = RoleKind.OTHER
        signals["role_signals"] = {
            "fit": element.get("fit"),
            "coverage": (
                min(Fraction(1), max(Fraction(0), (aabbs[index][2] - aabbs[index][0]) / source_width)),
                min(Fraction(1), max(Fraction(0), (aabbs[index][3] - aabbs[index][1]) / source_height)),
            ),
            "peer_image_ratio_median": ratio_median,
            "peer_image_area_rank": (
                sorted(image_areas, key=lambda item: (-image_areas[item], item)).index(index) + 1
                if index in image_areas
                else None
            ),
        }
        assignments.append(RoleAssignment(index, str(element["id"]), role, signals))

    relationships = RelationshipView(
        tuple(str(element["id"]) for element in elements),
        tuple(element.get("group_id") for element in elements),
        tuple(aabbs),
    )
    return RoleModel(tuple(assignments), relationships, background_index)


# Explicit aliases make the intended seam discoverable to callers while keeping
# one implementation and one deterministic result.
infer_role_model = infer_roles
infer_layout_roles = infer_roles


__all__ = [
    "Relationship",
    "RoleAssignment",
    "RoleKind",
    "RoleModel",
    "infer_layout_roles",
    "infer_role_model",
    "infer_roles",
]
