"""Exact positive image-ratio lattice operations."""

from __future__ import annotations

from fractions import Fraction
from typing import Any

from .math_util import to_fraction


def reduced_ratio(source_width: Any, source_height: Any) -> tuple[int, int] | None:
    """Return a positive source ratio reduced to ``(p, q)``, or ``None``.

    Non-positive (including zero-area) source images retain their records but
    have no ratio constraint under the contract.
    """

    width = to_fraction(source_width)
    height = to_fraction(source_height)
    if width <= 0 or height <= 0:
        return None
    ratio = width / height
    return ratio.numerator, ratio.denominator


# Names that make call sites read naturally while retaining one implementation.
source_ratio = reduced_ratio


def lattice_dimensions(ratio: tuple[int, int], multiplier: int) -> tuple[int, int]:
    """Construct the positive integer lattice point ``multiplier * (p, q)``."""

    if (
        not isinstance(ratio, tuple)
        or len(ratio) != 2
        or type(ratio[0]) is not int
        or type(ratio[1]) is not int
        or ratio[0] <= 0
        or ratio[1] <= 0
    ):
        raise ValueError("ratio must contain two positive integers")
    if type(multiplier) is not int or multiplier <= 0:
        raise ValueError("lattice multiplier must be a positive integer")
    return multiplier * ratio[0], multiplier * ratio[1]


def is_ratio_lattice(
    width: Any,
    height: Any,
    ratio: tuple[int, int],
) -> bool:
    """Return whether dimensions are a positive integer point on ``p/q``."""

    if (
        type(width) is not int
        or type(height) is not int
        or width <= 0
        or height <= 0
        or not isinstance(ratio, tuple)
        or len(ratio) != 2
        or type(ratio[0]) is not int
        or type(ratio[1]) is not int
        or ratio[0] <= 0
        or ratio[1] <= 0
    ):
        return False
    p, q = ratio
    return width * q == height * p


def preserves_source_ratio(
    output_width: Any,
    output_height: Any,
    source_width: Any,
    source_height: Any,
) -> bool:
    """Apply the validator's source-ratio rule using exact cross-products.

    A degenerate source has no ratio and therefore imposes no ratio check.
    Positive sources require positive integer output dimensions and a matching
    reduced lattice point.
    """

    ratio = reduced_ratio(source_width, source_height)
    if ratio is None:
        return True
    return is_ratio_lattice(output_width, output_height, ratio)


is_valid_ratio_lattice = is_ratio_lattice

__all__ = [
    "is_ratio_lattice",
    "is_valid_ratio_lattice",
    "lattice_dimensions",
    "preserves_source_ratio",
    "reduced_ratio",
    "source_ratio",
]
