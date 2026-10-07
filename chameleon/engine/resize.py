"""
THIS IS THE FILE YOU IMPLEMENT.

Everything else in this repo (input loading, output writing, rendering,
the Dockerfile) is plumbing so you can focus on exactly one function:
`resize()`. See RULES.md and the design schema for the full contract.
"""

from typing import Any


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

    The challenge submission may change only this file. The broader contract's
    renderer, input-parser, and batch-runner requirements are documented as
    Gate 1 blockers when they cannot be satisfied here.
    """

    # ------------------------------------------------------------------
    # Uniform-stretch baseline so the starter pipeline runs out of the box.
    # It is deliberately nonconforming: it distorts foreground ratios, emits
    # floating-point geometry, and ignores groups, rotated bounds, and collisions.
    # Replace the implementation; do not tune these independent scale factors.
    scale_x = target_canvas["width"] / source["canvas"]["width"]
    scale_y = target_canvas["height"] / source["canvas"]["height"]

    out_elements = []
    for el in source["elements"]:
        el = dict(el)  # shallow copy — don't mutate the input
        el["x"] = el["x"] * scale_x
        el["y"] = el["y"] * scale_y
        el["width"] = el["width"] * scale_x
        el["height"] = el["height"] * scale_y
        if el["type"] == "text":
            # font_size scaling isn't required to be uniform — this is
            # just a starting point. Floored at 1px: the schema requires
            # font_size >= 1, and an extreme downscale (e.g. a tall poster
            # squeezed into a short banner) can otherwise compute < 1.
            el["font_size"] = max(1.0, el["font_size"] * min(scale_x, scale_y))
        out_elements.append(el)

    return {
        "canvas": {"width": target_canvas["width"], "height": target_canvas["height"]},
        "elements": out_elements,
    }
