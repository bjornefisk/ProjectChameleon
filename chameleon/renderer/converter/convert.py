"""CHAMELEON design schema (v0.9) -> Crello v5 normalized/encoded example.

`convert_chameleon_to_crello` accepts either shape the engine hands it:
- the flat `{"canvas": ..., "elements": [...]}` design object (schema
  v0.9 - what `engine/main.py` passes to the renderer for both the source
  design and `resize()`'s output), or
- an older `{"source": {"canvas": ..., "elements": [...]}, ...}` wrapper,
  for backward compatibility with the original sample-task files.

`render_design_to_png` is the integration entry point `engine/main.py`
looks for (`renderer.converter.convert.render_design_to_png`) - it wires
the conversion above to a brand-kit-backed `CrelloV5Renderer` and writes
the result straight to a PNG file.
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from PIL import Image

from cr_renderer import CrelloV5Renderer
from cr_renderer.fonts import FONT_WEIGHTS

from .assets import asset_path, load_asset_image
from .brand_fonts import load_brand_font_manager
from .features_stub import make_stub_features
from .shapes import render_shape
from .wrap import char_widths, enforce_text_limits, visual_line_count, wrap_text

logger = logging.getLogger(__name__)

_BLANK_IMAGE = Image.new("RGBA", (1, 1), (0, 0, 0, 0))
_DEFAULT_LINE_HEIGHT = 1.2
_BOLD_WEIGHTS = {"bold", "semibold", "extrabold", "black"}


def convert_chameleon_to_crello(
    doc: Dict[str, Any],
    font_manager,
    assets_dir: Optional[str] = None,
) -> Tuple[Dict[str, Any], List[str]]:
    """Convert a CHAMELEON design document to a Crello v5 example.

    `font_manager` is a `cr_renderer.fonts.FontManager` instance, reused
    from the renderer so text-wrap width measurements use the exact same
    font lookups/fallbacks that will later render the glyphs.
    """
    design = doc["source"] if "source" in doc else doc
    canvas = design["canvas"]
    canvas_width = float(canvas["width"])
    canvas_height = float(canvas["height"])
    elements = sorted(design["elements"], key=lambda e: e.get("z_index", 0))

    out: Dict[str, Any] = {
        "canvas_width": canvas_width,
        "canvas_height": canvas_height,
        "length": len(elements),
        "left": [],
        "top": [],
        "width": [],
        "height": [],
        "angle": [],
        "type": [],
        "color": [],
        "opacity": [],
        "text": [],
        "font_size": [],
        "font": [],
        "line_height": [],
        "text_align": [],
        "capitalize": [],
        "letter_spacing": [],
        "font_bold": [],
        "font_italic": [],
        "text_color": [],
        "text_line": [],
        "image": [],
    }
    warnings: List[str] = []

    for element in elements:
        etype = element.get("type")
        eid = element.get("id", "?")

        out["left"].append(float(element.get("x", 0.0)))
        out["top"].append(float(element.get("y", 0.0)))
        out["width"].append(float(element.get("width", 1.0)))
        out["height"].append(float(element.get("height", 1.0)))
        out["angle"].append(float(element.get("rotation", 0.0)))
        out["opacity"].append(float(element.get("opacity", 1.0)))
        out["color"].append([])

        if etype == "text":
            out["type"].append("TextElement")
            _append_text(out, element, font_manager)
            out["image"].append(_BLANK_IMAGE)
        elif etype == "shape":
            out["type"].append("ImageElement")
            _append_blank_text(out)
            out["image"].append(render_shape(element))
        elif etype == "image":
            out["type"].append("ImageElement")
            _append_blank_text(out)
            asset_id = element.get("asset_id")
            if asset_id and asset_path(assets_dir, asset_id) is None:
                warnings.append(
                    f"Missing asset '{asset_id}' for element '{eid}' - rendered a placeholder."
                )
            out["image"].append(
                load_asset_image(
                    assets_dir,
                    asset_id,
                    element.get("width", 1.0),
                    element.get("height", 1.0),
                    element.get("fit", "contain"),
                )
            )
        else:
            warnings.append(f"Unknown element type '{etype}' for '{eid}' - skipped (blank).")
            out["type"].append("ImageElement")
            _append_blank_text(out)
            w = max(1, round(element.get("width", 1.0)))
            h = max(1, round(element.get("height", 1.0)))
            out["image"].append(Image.new("RGBA", (w, h), (0, 0, 0, 0)))

    return out, warnings


def _append_blank_text(out: Dict[str, Any]) -> None:
    """Fill the text-only columns with inert defaults for a non-text element."""
    out["text"].append("")
    out["font_size"].append(1.0)
    out["font"].append("")
    out["line_height"].append(1.0)
    out["text_align"].append("left")
    out["capitalize"].append(False)
    out["letter_spacing"].append(0.0)
    out["font_bold"].append([])
    out["font_italic"].append([])
    out["text_color"].append([])
    out["text_line"].append([])


def _is_italic(value: Optional[Union[str, bool]]) -> bool:
    """Accepts either the v0.9 schema's `font_style: "normal"/"italic"` or a
    plain boolean `italic` flag, for flexibility across schema revisions."""
    if isinstance(value, bool):
        return value
    return value == "italic"


def _style_maps(
    element: Dict[str, Any], content_length: int
) -> Tuple[List[str], List[bool], List[bool]]:
    """Resolve external code-point style runs with later-property precedence."""
    base_color = element.get("color", "rgba(0,0,0,1)")
    base_weight = _normalize_weight(element.get("font_weight"))
    base_bold = base_weight in _BOLD_WEIGHTS
    base_italic = _is_italic(element.get("font_style") or element.get("italic"))

    colors = [base_color] * content_length
    bold_flags = [base_bold] * content_length
    italic_flags = [base_italic] * content_length

    for run_index, run in enumerate(element.get("style_runs") or []):
        start = int(run.get("start", 0))
        end = int(run.get("end", 0))
        if start < 0 or start > end or end > content_length:
            raise ValueError(
                f"style_runs[{run_index}] must satisfy 0 <= start <= end <= content length"
            )
        for index in range(start, end):
            if "color" in run:
                colors[index] = run["color"]
            if "font_weight" in run:
                bold_flags[index] = _normalize_weight(run["font_weight"]) in _BOLD_WEIGHTS
            if "font_style" in run or "italic" in run:
                italic_flags[index] = _is_italic(
                    run.get("font_style") if "font_style" in run else run.get("italic")
                )
    return colors, bold_flags, italic_flags


def _measure_text(
    content: str,
    font_manager,
    family: str,
    size: float,
    letter_spacing: float,
    colors: List[str],
    bold_flags: List[bool],
    italic_flags: List[bool],
):
    """Measure ranges exactly as cr-renderer's per-style text spans do."""

    def measure(start: int, end: int) -> float:
        total = 0.0
        span_start = start
        while span_start < end:
            state = (colors[span_start], bold_flags[span_start], italic_flags[span_start])
            span_end = span_start + 1
            while span_end < end:
                next_state = (colors[span_end], bold_flags[span_end], italic_flags[span_end])
                if next_state != state:
                    break
                span_end += 1

            _color, is_bold, is_italic = state
            weight = "bold" if is_bold else "regular"
            style = _weight_style_to_font_style(is_bold, is_italic)
            advances = char_widths(
                font_manager,
                family,
                weight,
                style,
                size,
                content[span_start:span_end],
            )
            total += sum(advances)
            total += letter_spacing * max(0, len(advances) - 1)
            span_start = span_end
        return total

    return measure


def _line_indices(text: str) -> List[int]:
    """Encode visual lines for cr-renderer's inclusive internal line map."""
    if not text:
        return [0]

    values: List[int] = []
    current_line = 0
    for index, char in enumerate(text):
        if char != "\n":
            values.append(current_line)
            continue
        if index == 0 or text[index - 1] == "\n":
            values.append(current_line)
            current_line += 1
        else:
            current_line += 1
            values.append(current_line)

    line_count = visual_line_count(text)
    represented = set(values)
    for line_index in range(line_count):
        if line_index not in represented:
            values.append(line_index)
    return values


def _append_text(out: Dict[str, Any], element: Dict[str, Any], font_manager) -> None:
    content = str(element.get("content", ""))
    family = element.get("font_family", "Montserrat")
    size = float(element.get("font_size", 24))
    line_height = float(element.get("line_height", _DEFAULT_LINE_HEIGHT))
    letter_spacing = float(element.get("letter_spacing", 0.0))
    colors, bold_flags, italic_flags = _style_maps(element, len(content))
    measure = _measure_text(
        content,
        font_manager,
        family,
        size,
        letter_spacing,
        colors,
        bold_flags,
        italic_flags,
    )

    wrapped = wrap_text(
        content,
        (),
        float(element.get("width", 1.0)),
        measure=measure,
    )
    enforce_text_limits(
        wrapped,
        size,
        line_height,
        element.get("max_lines"),
        float(element.get("height", 1.0)),
    )

    out["text"].append(wrapped)
    out["font_size"].append(size)
    out["font"].append(family)
    out["line_height"].append(line_height)
    out["text_align"].append(element.get("text_align", "left"))
    out["capitalize"].append(bool(element.get("capitalize", False)))
    out["letter_spacing"].append(letter_spacing)
    out["font_bold"].append(bold_flags)
    out["font_italic"].append(italic_flags)
    out["text_color"].append(colors)
    out["text_line"].append(_line_indices(wrapped))


def _normalize_weight(weight: Optional[str]) -> str:
    if not weight:
        return "regular"
    weight = weight.lower()
    return weight if weight in FONT_WEIGHTS else "regular"


def _weight_style_to_font_style(is_bold: bool, is_italic: bool) -> str:
    """Mirror cr_renderer.text_utils.make_text_blob's own weight/style
    derivation, so the font used to *measure* wrap widths matches the font
    that will actually be *rendered* (cr-renderer recomputes this itself at
    render time from the bold/italic per-character maps - if this measuring
    step used a different rule, it would just cause wrap widths to be
    measured against the wrong font)."""
    if is_bold and is_italic:
        return "bolditalic"
    if is_bold:
        return "bold"
    if is_italic:
        return "italic"
    return "regular"


# --------------------------------------------------------------------------
# Integration entry point for engine/main.py
# --------------------------------------------------------------------------

_STUB_FEATURES = make_stub_features()
_renderer_cache: Dict[str, CrelloV5Renderer] = {}


def _get_renderer(fonts_dir: str) -> CrelloV5Renderer:
    """Build (and cache, per fonts_dir) a `CrelloV5Renderer` backed by local
    brand-kit fonts - no network access, no `fonts.pickle` download."""
    renderer = _renderer_cache.get(fonts_dir)
    if renderer is None:
        renderer = CrelloV5Renderer.__new__(CrelloV5Renderer)
        renderer.features = _STUB_FEATURES
        renderer.font_manager = load_brand_font_manager(fonts_dir)
        _renderer_cache[fonts_dir] = renderer
    return renderer


def render_design_to_png(
    design: Dict[str, Any],
    assets_dir: Union[str, Path],
    png_path: Union[str, Path],
    fonts_dir: Optional[Union[str, Path]] = None,
    max_size: Optional[int] = None,
) -> List[str]:
    """Render a CHAMELEON design (flat `{"canvas", "elements"}` shape) to a
    PNG file. This is what `engine/main.py` calls
    (`renderer.converter.convert.render_design_to_png`).

    `fonts_dir` defaults to a `fonts/` folder next to `assets_dir` (i.e.
    `brand_kit/assets` + `brand_kit/fonts`), matching this repo's layout.
    Returns the list of conversion warnings (missing assets, unknown
    element types, etc.) for the caller to log.
    """
    assets_dir = str(assets_dir)
    fonts_dir = str(fonts_dir) if fonts_dir is not None else str(Path(assets_dir).parent / "fonts")

    renderer = _get_renderer(fonts_dir)
    example, warnings = convert_chameleon_to_crello(design, renderer.font_manager, assets_dir)
    image_bytes = renderer.render(example, max_size=max_size or 2048, format="png")
    Path(png_path).write_bytes(image_bytes)
    return warnings
