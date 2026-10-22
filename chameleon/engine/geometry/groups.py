"""Exact rigid transforms for elements sharing an explicit group id."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import Any, Mapping, Sequence

from .math_util import quantize_to_int, to_fraction


@dataclass(frozen=True, slots=True)
class GroupTransform:
    """One common positive scale and translation for a rigid group."""

    scale: Fraction
    tx: Fraction
    ty: Fraction

    def __post_init__(self) -> None:
        scale = to_fraction(self.scale)
        tx = to_fraction(self.tx)
        ty = to_fraction(self.ty)
        if scale <= 0:
            raise ValueError("rigid group scale must be positive")
        object.__setattr__(self, "scale", scale)
        object.__setattr__(self, "tx", tx)
        object.__setattr__(self, "ty", ty)


def element_center(element: Mapping[str, Any]) -> tuple[Fraction, Fraction]:
    """Return an element center without changing the source mapping."""

    return (
        to_fraction(element["x"]) + to_fraction(element["width"]) / 2,
        to_fraction(element["y"]) + to_fraction(element["height"]) / 2,
    )


def apply_transform(
    element: Mapping[str, Any], transform: GroupTransform
) -> dict[str, Any]:
    """Return transformed geometry while preserving every other field.

    Centers and dimensions are transformed together, which avoids the
    child-specific drift caused by independently adjusting ``x`` and ``y``.
    Zero dimensions remain zero under every positive scale.
    """

    if not isinstance(transform, GroupTransform):
        raise TypeError("transform must be a GroupTransform")
    scale = transform.scale
    width = to_fraction(element["width"]) * scale
    height = to_fraction(element["height"]) * scale
    source_center_x, source_center_y = element_center(element)
    center_x = source_center_x * scale + transform.tx
    center_y = source_center_y * scale + transform.ty
    result = dict(element)
    result["x"] = center_x - width / 2
    result["y"] = center_y - height / 2
    result["width"] = width
    result["height"] = height
    return result


def _merge_scale(current: Fraction | None, candidate: Fraction) -> Fraction:
    if candidate <= 0:
        raise ValueError("rigid group scale must be positive")
    if current is not None and candidate != current:
        raise ValueError("group children do not share one scale")
    return candidate if current is None else current


def derive_common_transform(
    source_elements: Sequence[Mapping[str, Any]],
    response_elements: Sequence[Mapping[str, Any]],
) -> GroupTransform:
    """Derive and validate one exact transform for two child sequences.

    The dimensional rules intentionally mirror the semantic validator:
    nonzero source dimensions determine scale; zero source dimensions must stay
    zero; if every dimension is zero, center deltas determine scale when
    possible and otherwise the neutral scale is used.
    """

    if not source_elements or len(source_elements) != len(response_elements):
        raise ValueError("group child sequences must be non-empty and equal in length")

    scale: Fraction | None = None
    for source, response in zip(source_elements, response_elements):
        source_width = to_fraction(source["width"])
        source_height = to_fraction(source["height"])
        response_width = to_fraction(response["width"])
        response_height = to_fraction(response["height"])
        if source_width == 0:
            if response_width != 0:
                raise ValueError("zero source width changed inside a rigid group")
        else:
            scale = _merge_scale(scale, response_width / source_width)
        if source_height == 0:
            if response_height != 0:
                raise ValueError("zero source height changed inside a rigid group")
        else:
            scale = _merge_scale(scale, response_height / source_height)

    source_anchor = element_center(source_elements[0])
    response_anchor = element_center(response_elements[0])
    if scale is None:
        for source, response in zip(source_elements[1:], response_elements[1:]):
            source_center = element_center(source)
            response_center = element_center(response)
            for source_value, response_value, anchor_source, anchor_response in zip(
                source_center,
                response_center,
                source_anchor,
                response_anchor,
            ):
                source_delta = source_value - anchor_source
                response_delta = response_value - anchor_response
                if source_delta == 0:
                    if response_delta != 0:
                        raise ValueError("group children do not share one scale")
                else:
                    scale = _merge_scale(scale, response_delta / source_delta)
        if scale is None:
            scale = Fraction(1)

    translation: tuple[Fraction, Fraction] | None = None
    assert scale is not None  # established above, including all-zero groups
    for source, response in zip(source_elements, response_elements):
        source_center = element_center(source)
        response_center = element_center(response)
        candidate = (
            response_center[0] - scale * source_center[0],
            response_center[1] - scale * source_center[1],
        )
        if translation is None:
            translation = candidate
        elif candidate != translation:
            raise ValueError("group children do not share one translation")
    assert translation is not None
    return GroupTransform(scale, translation[0], translation[1])

def _constrain_scale_interval(
    low: Fraction,
    high: Fraction | None,
    source_delta: Fraction,
    response_delta: Fraction,
    tolerance: Fraction,
) -> tuple[Fraction, Fraction | None]:
    """Intersect a scale interval for one rounded linear constraint."""
    if source_delta == 0:
        if abs(response_delta) > tolerance:
            raise ValueError("group children cannot share one quantized transform")
        return low, high

    first = (response_delta - tolerance) / source_delta
    second = (response_delta + tolerance) / source_delta
    low = max(low, min(first, second))
    upper = max(first, second)
    if high is None or upper < high:
        high = upper
    if high is not None and low > high:
        raise ValueError("group children cannot share one quantized transform")
    return low, high


def derive_quantized_common_transform(
    source_elements: Sequence[Mapping[str, Any]],
    response_elements: Sequence[Mapping[str, Any]],
) -> GroupTransform:
    """Find one exact transform whose canonical geometry rounding matches output.

    Serialized positions and dimensions are rounded independently, but they
    must all be reconstructible from the same rational scale and translation.
    Text font size is deliberately outside this geometry-only relation.
    """

    if not source_elements or len(source_elements) != len(response_elements):
        raise ValueError("group child sequences must be non-empty and equal in length")

    low = Fraction(0)
    high: Fraction | None = None
    half = Fraction(1, 2)
    one = Fraction(1)

    for source, response in zip(source_elements, response_elements):
        for field in ("width", "height"):
            source_value = to_fraction(source[field])
            response_value = to_fraction(response[field])
            if source_value == 0:
                if response_value != 0:
                    raise ValueError("zero source dimension changed inside a rigid group")
                continue
            low, high = _constrain_scale_interval(
                low, high, source_value, response_value, half
            )

    for left in range(len(source_elements)):
        for right in range(left + 1, len(source_elements)):
            for field in ("x", "y"):
                source_delta = (
                    to_fraction(source_elements[right][field])
                    - to_fraction(source_elements[left][field])
                )
                response_delta = (
                    to_fraction(response_elements[right][field])
                    - to_fraction(response_elements[left][field])
                )
                if source_delta == 0:
                    if response_delta != 0:
                        raise ValueError(
                            "equal source positions must remain equal after quantization"
                        )
                    continue
                low, high = _constrain_scale_interval(
                    low, high, source_delta, response_delta, one
                )

    if high is None:
        scale = max(one, low)
    else:
        if low > high or high <= 0:
            raise ValueError("group children cannot share one positive quantized scale")
        scale = low if low == high else (low + high) / 2
    if scale <= 0:
        raise ValueError("rigid group scale must be positive")

    translations: list[Fraction] = []
    for field in ("x", "y"):
        translation_low: Fraction | None = None
        translation_high: Fraction | None = None
        for source, response in zip(source_elements, response_elements):
            source_position = to_fraction(source[field])
            response_position = to_fraction(response[field])
            interval_low = response_position - half - scale * source_position
            interval_high = response_position + half - scale * source_position
            translation_low = (
                interval_low
                if translation_low is None
                else max(translation_low, interval_low)
            )
            translation_high = (
                interval_high
                if translation_high is None
                else min(translation_high, interval_high)
            )
        assert translation_low is not None and translation_high is not None
        if translation_low > translation_high:
            raise ValueError("group children do not share one quantized translation")
        translations.append((translation_low + translation_high) / 2)

    transform = GroupTransform(scale, translations[0], translations[1])
    for source, response in zip(source_elements, response_elements):
        for field, translation in zip(("x", "y"), translations):
            if quantize_to_int(scale * to_fraction(source[field]) + translation) != to_fraction(
                response[field]
            ):
                raise ValueError("group positions do not share one quantized transform")
        for field in ("width", "height"):
            if quantize_to_int(scale * to_fraction(source[field])) != to_fraction(
                response[field]
            ):
                raise ValueError("group dimensions do not share one quantized scale")
    return transform


def has_quantized_common_transform(
    source_elements: Sequence[Mapping[str, Any]],
    response_elements: Sequence[Mapping[str, Any]],
) -> bool:
    """Return whether one exact transform reproduces the serialized geometry."""
    try:
        derive_quantized_common_transform(source_elements, response_elements)
    except (KeyError, TypeError, ValueError, OverflowError):
        return False
    return True


def has_common_transform(
    source_elements: Sequence[Mapping[str, Any]],
    response_elements: Sequence[Mapping[str, Any]],
) -> bool:
    """Return whether child sequences satisfy one positive rigid transform."""

    try:
        derive_common_transform(source_elements, response_elements)
    except (KeyError, TypeError, ValueError):
        return False
    return True


__all__ = [
    "GroupTransform",
    "apply_transform",
    "derive_common_transform",
    "derive_quantized_common_transform",
    "element_center",
    "has_common_transform",
    "has_quantized_common_transform",
]
