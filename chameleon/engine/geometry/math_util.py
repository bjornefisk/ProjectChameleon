"""Exact numeric helpers shared by Stage 1 geometry code.

Values reaching this package are expected to have been parsed with integer or
:class:`decimal.Decimal` JSON hooks.  In particular, Python binary floats are
not accepted: converting a float back to text would make the lexical source
value unknowable.
"""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_EVEN
from fractions import Fraction
from typing import Any


def to_fraction(value: Any) -> Fraction:
    """Convert an accepted exact numeric value to :class:`Fraction`.

    ``bool`` and binary ``float`` values are deliberately rejected.  Decimal
    infinities and NaNs are rejected before conversion as well.
    """

    if isinstance(value, bool):
        raise TypeError("boolean is not an exact contract number")
    if isinstance(value, Fraction):
        return value
    if isinstance(value, int):
        return Fraction(value, 1)
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise ValueError("non-finite exact contract number")
        return Fraction(value)
    if isinstance(value, float):
        raise TypeError("binary float is not an exact contract number")
    raise TypeError(f"not an exact contract number: {value!r}")


# The validator's private helper used this conventional spelling.  Keeping one
# public name makes geometry imports readable without creating a second path.
as_fraction = to_fraction


def quantize_to_int(value: Any) -> int:
    """Round an exact number to an integer using round-half-even.

    Decimal inputs use the explicit standard-library rounding mode. Fraction
    inputs use the equivalent exact numerator/denominator rule, avoiding any
    binary-float conversion.
    """

    if isinstance(value, Decimal):
        if not value.is_finite():
            raise ValueError("non-finite exact contract number")
        return int(value.to_integral_value(rounding=ROUND_HALF_EVEN))

    fraction = to_fraction(value)
    numerator = abs(fraction.numerator)
    denominator = fraction.denominator
    quotient, remainder = divmod(numerator, denominator)
    if remainder * 2 > denominator or (
        remainder * 2 == denominator and quotient % 2 == 1
    ):
        quotient += 1
    return -quotient if fraction.numerator < 0 else quotient


__all__ = ["as_fraction", "quantize_to_int", "to_fraction"]
