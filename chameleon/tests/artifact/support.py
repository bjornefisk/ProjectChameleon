from __future__ import annotations

from pathlib import Path
from typing import Any

from PIL import Image

try:
    from renderer.converter.shapes import render_shape
except ModuleNotFoundError:
    from chameleon.renderer.converter.shapes import render_shape


def shape_design(width: int = 16, height: int = 12) -> dict[str, Any]:
    return {
        "canvas": {"width": width, "height": height},
        "elements": [{
            "id": "box",
            "type": "shape",
            "x": 2,
            "y": 2,
            "width": 5,
            "height": 4,
            "shape_type": "rectangle",
            "fill_color": "rgba(12,34,56,1)",
        }],
    }


def shape_render(design: dict[str, Any]) -> Image.Image:
    canvas = design["canvas"]
    image = Image.new("RGBA", (int(canvas["width"]), int(canvas["height"])), "white")
    element = design["elements"][0]
    image.alpha_composite(render_shape(element), (int(element["x"]), int(element["y"])))
    return image


def save_png(image: Image.Image, path: Path) -> None:
    image.save(path, format="PNG")
