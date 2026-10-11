from PIL import Image, ImageDraw

from .colorutil import parse_rgba


def _rgba_pixel(value: str, default: tuple[int, int, int, float]) -> tuple[int, int, int, int]:
    red, green, blue, alpha = parse_rgba(value, default=default)
    return red, green, blue, max(0, min(255, round(alpha * 255)))


def render_shape(element: dict) -> Image.Image:
    """Rasterize a shape without drawing any pixel outside its box."""
    width = max(1, round(float(element.get("width", 1))))
    height = max(1, round(float(element.get("height", 1))))
    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    fill = _rgba_pixel(
        element.get("fill_color"),
        default=(200, 200, 200, 1.0),
    )
    stroke = None
    raw_stroke_width = float(element.get("stroke_width", 0) or 0)
    stroke_width = max(1, round(raw_stroke_width)) if raw_stroke_width > 0 else 0
    if element.get("stroke_color") and stroke_width > 0:
        stroke = _rgba_pixel(
            element["stroke_color"],
            default=(0, 0, 0, 1.0),
        )

    shape_type = element.get("shape_type", "rectangle")
    bounds = [0, 0, width - 1, height - 1]
    if shape_type == "ellipse":
        draw.ellipse(bounds, fill=fill, outline=stroke, width=stroke_width)
    elif shape_type == "line":
        line_color = _rgba_pixel(
            element.get("stroke_color") or element.get("fill_color"),
            default=(0, 0, 0, 1.0),
        )
        line_width = max(1, round(float(element.get("stroke_width", 1) or 1)))
        draw.line(
            [0, height // 2, width - 1, height // 2],
            fill=line_color,
            width=line_width,
        )
    else:
        radius = max(
            0,
            min(
                round(float(element.get("corner_radius", 0) or 0)),
                width // 2,
                height // 2,
            ),
        )
        if radius > 0:
            draw.rounded_rectangle(
                bounds,
                radius=radius,
                fill=fill,
                outline=stroke,
                width=stroke_width,
            )
        else:
            draw.rectangle(bounds, fill=fill, outline=stroke, width=stroke_width)

    return image
