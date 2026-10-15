"""
THIS IS THE PUBLIC `resize()` SEAM.

The starter pipeline includes input loading, output publication, rendering, and
Docker packaging around the public `resize()` seam. The implementation tickets
may update those modules where contract conformance requires it.
"""

from decimal import Decimal
from fractions import Fraction
from typing import Any


def _as_fraction(value: Any) -> Fraction:
    if isinstance(value, Fraction):
        return value
    if isinstance(value, Decimal):
        return Fraction(value)
    if type(value) is int:
        return Fraction(value, 1)
    if isinstance(value, float):
        return Fraction(str(value))
    raise TypeError(f"geometry value is not numeric: {type(value).__name__}")


def _scale(value: Any, factor: Fraction) -> Fraction:
    return _as_fraction(value) * factor


def resize(source: dict[str, Any], target_canvas: dict[str, Any]) -> dict[str, Any]:
    """
    Args:
        source: {"canvas": {"width": int, "height": int}, "elements": [...]}
                 — the design at its original size. See
                 chameleon_design_schema_v0.9.json for the full element spec
                 (text / image / shape, position, size, rotation, opacity,
                 z_index, group_id, and type-specific fields).
        target_canvas: {"width": int, "height": int} — the shape you're
                 resizing into.

    Returns:
        A design dict with the SAME shape as `source`:
        {"canvas": target_canvas, "elements": [...]}

        Hard requirements (see `Docs/PROJECT_CONTRACT.md` and `RULES.md`):
        - Return the same element count, unique IDs, array order, and types.
        - Preserve every immutable field; only target canvas dimensions,
          element geometry, and text `font_size` may change.
        - Serialize mutable geometry and text size as finite integers.
        - Preserve exact positive-area foreground image ratios, including
          `fit="fill"`; only the contract-classified background is exempt.
        - Contain rotated foreground bounds, except for the contract's narrow
          full-canvas background and source-bleed exceptions.
        - Preserve rigid groups and keep source-separated active elements from
          developing positive-area collisions.
        - Preserve missing asset references and original pixels; never hide,
          remove, zero-size, redraw, regenerate, or replace an element or asset.
        - Preserve text and fixed font attributes; change only `font_size`.
        - Return a hard-valid design or fail closed; do not return best effort.

    The public seam is `resize()`. Gate 1 also owns the parser, renderer,
    runner, and permanent-test conformance paths; keep this function focused on
    returning the contract-defined target design.
    """

    # ------------------------------------------------------------------
    # Uniform-stretch baseline so the starter pipeline runs out of the box.
    # It is deliberately nonconforming: it distorts foreground ratios,
    # ignores groups, rotated bounds, and collisions, and leaves quantization
    # to the staging serializer.
    # Replace the implementation; do not tune these independent scale factors.
    scale_x = _as_fraction(target_canvas["width"]) / _as_fraction(
        source["canvas"]["width"]
    )
    scale_y = _as_fraction(target_canvas["height"]) / _as_fraction(
        source["canvas"]["height"]
    )

    out_elements = []
    for el in source["elements"]:
        el = dict(el)  # shallow copy — don't mutate the input
        el["x"] = _scale(el["x"], scale_x)
        el["y"] = _scale(el["y"], scale_y)
        el["width"] = _scale(el["width"], scale_x)
        el["height"] = _scale(el["height"], scale_y)
        if el["type"] == "text":
            # font_size scaling isn't required to be uniform — this is
            # just a starting point. Floored at 1px: the schema requires
            # font_size >= 1, and an extreme downscale (e.g. a tall poster
            # squeezed into a short banner) can otherwise compute < 1.
            el["font_size"] = max(
                Fraction(1), _scale(el["font_size"], min(scale_x, scale_y))
            )
        out_elements.append(el)

    return {
        "canvas": {"width": target_canvas["width"], "height": target_canvas["height"]},
        "elements": out_elements,
    }
