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

from dataclasses import dataclass
from math import ceil
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import skia  # type: ignore

from PIL import Image

from cr_renderer import CrelloV5Renderer
from cr_renderer.fonts import FONT_WEIGHTS

from .assets import asset_path, load_asset_image, missing_asset_warning
from .brand_fonts import load_brand_font_manager, lookup_exact_font
from .features_stub import make_stub_features
from .shapes import render_shape
from .wrap import (
    MalformedTextError,
    TextOverflowError,
    _collapse_crlf,
    char_widths,
    enforce_text_limits,
    wrap_text_with_line_map,
)

logger = logging.getLogger(__name__)

_BLANK_IMAGE = Image.new("RGBA", (1, 1), (0, 0, 0, 0))
_DEFAULT_LINE_HEIGHT = 1.2
_BOLD_WEIGHTS = {"bold", "semibold", "extrabold", "black"}


@dataclass(frozen=True, slots=True)
class _PreparedText:
    wrapped: str
    line_indices: List[int]
    line_count: int
    family: str
    size: int
    line_height: float
    letter_spacing: float
    colors: List[str]
    bold_flags: List[bool]
    italic_flags: List[bool]


def convert_chameleon_to_crello(
    doc: Dict[str, Any],
    font_manager,
    assets_dir: Optional[str] = None,
) -> Tuple[Dict[str, Any], List[str]]:
    """Convert a CHAMELEON design document to a Crello v5 example.

    `font_manager` is a `cr_renderer.fonts.FontManager` instance, reused
    from the renderer so text-wrap width measurements use the exact same
    font face lookups that will later render the glyphs.
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
            horizontal_inset, vertical_inset = _append_text(out, element, font_manager)
            out["left"][-1] += horizontal_inset
            out["top"][-1] += vertical_inset
            if float(element.get("rotation", 0.0)) % 360.0:
                out["width"][-1] -= 2 * horizontal_inset
                out["height"][-1] -= 2 * vertical_inset
            out["image"].append(_BLANK_IMAGE)
        elif etype == "shape":
            out["type"].append("ImageElement")
            _append_blank_text(out)
            out["image"].append(render_shape(element))
        elif etype == "image":
            out["type"].append("ImageElement")
            _append_blank_text(out)
            asset_id = element.get("asset_id")
            if asset_path(assets_dir, asset_id) is None:
                warnings.append(missing_asset_warning(eid, asset_id))
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
        try:
            start, end = run["start"], run["end"]
        except (KeyError, TypeError) as error:
            raise MalformedTextError(
                f"style_runs[{run_index}] must provide integer start and end"
            ) from error
        if (
            isinstance(start, bool)
            or isinstance(end, bool)
            or not isinstance(start, int)
            or not isinstance(end, int)
            or start < 0
            or start > end
            or end > content_length
        ):
            raise MalformedTextError(
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


def _style_spans(
    start: int,
    end: int,
    colors: List[str],
    bold_flags: List[bool],
    italic_flags: List[bool],
) -> List[Tuple[int, int, Tuple[str, bool, bool]]]:
    spans: List[Tuple[int, int, Tuple[str, bool, bool]]] = []
    span_start = start
    while span_start < end:
        state = (colors[span_start], bold_flags[span_start], italic_flags[span_start])
        span_end = span_start + 1
        while span_end < end:
            next_state = (colors[span_end], bold_flags[span_end], italic_flags[span_end])
            if next_state != state:
                break
            span_end += 1
        spans.append((span_start, span_end, state))
        span_start = span_end
    return spans


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
    """Measure ranges from precomputed glyph advances for their styled spans."""

    runs: List[Tuple[int, int, List[float]]] = []
    for span_start, span_end, (_color, is_bold, is_italic) in _style_spans(
        0, len(content), colors, bold_flags, italic_flags
    ):
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
        runs.append((span_start, span_end, advances))

    def measure(start: int, end: int) -> float:
        total = 0.0
        for span_start, span_end, advances in runs:
            if span_end <= start:
                continue
            if span_start >= end:
                break
            local_start = max(start, span_start) - span_start
            local_end = min(end, span_end) - span_start
            segment = advances[local_start:local_end]
            total += sum(segment)
            total += letter_spacing * max(0, len(segment) - 1)
        return total

    return measure


def _validate_font_faces(
    font_manager,
    family: str,
    element: Dict[str, Any],
    bold_flags: List[bool],
    italic_flags: List[bool],
) -> None:
    """Preflight every effective face before upstream rendering can fall back."""
    states = set(zip(bold_flags, italic_flags))
    if not states:
        base_weight = _normalize_weight(element.get("font_weight"))
        states.add(
            (
                base_weight in _BOLD_WEIGHTS,
                _is_italic(element.get("font_style") or element.get("italic")),
            )
        )
    for is_bold, is_italic in states:
        weight = "bold" if is_bold else "regular"
        style = _weight_style_to_font_style(is_bold, is_italic)
        lookup_exact_font(font_manager, family, weight, style)


def _line_ranges(
    line_indices: List[int], line_count: int, content_length: int
) -> List[Tuple[int, int, int]]:
    """Return inclusive-upstream line ranges as half-open Python slices."""
    if not line_indices:
        return [(0, 0, 0)]

    ranges: List[Tuple[int, int, int]] = []
    range_start = 0
    current_line = line_indices[0]
    for index in range(1, len(line_indices)):
        if line_indices[index] == current_line:
            continue
        ranges.append((current_line, range_start, min(index, content_length)))
        range_start = index
        current_line = line_indices[index]
    ranges.append((current_line, range_start, min(len(line_indices), content_length)))

    represented = {line for line, _start, _end in ranges}
    for line in range(line_count):
        if line not in represented:
            ranges.append((line, content_length, content_length))
    return sorted(ranges)


def _positioned_glyph_metrics(
    wrapped: str,
    line_indices: List[int],
    line_count: int,
    element: Dict[str, Any],
    font_manager,
    family: str,
    size: float,
    line_height: float,
    letter_spacing: float,
    colors: List[str],
    bold_flags: List[bool],
    italic_flags: List[bool],
) -> tuple[float, float, float | None, float | None, float | None, float | None]:
    """Return minimal x/y insets and the unadjusted tight glyph envelope."""
    element_width = float(element.get("width", 1.0))
    text_align = element.get("text_align", "left")
    capitalize = bool(element.get("capitalize", False))
    minimum_left = float("inf")
    maximum_right = float("-inf")
    minimum_top = float("inf")
    maximum_bottom = float("-inf")

    for line_index, line_start, line_end in _line_ranges(
        line_indices, line_count, len(wrapped)
    ):
        if line_start >= line_end:
            continue

        blobs: List[Tuple[Any, List[Any], List[float], List[Any], Any, float]] = []
        total_width = 0.0
        for span_start, span_end, (_color, is_bold, is_italic) in _style_spans(
            line_start, line_end, colors, bold_flags, italic_flags
        ):
            span_text = wrapped[span_start:span_end].strip("\n")
            if not span_text:
                continue
            if capitalize:
                span_text = span_text.upper()

            weight = "bold" if is_bold else "regular"
            style = _weight_style_to_font_style(is_bold, is_italic)
            typeface = skia.Typeface.MakeFromData(
                lookup_exact_font(font_manager, family, weight, style)
            )
            font = skia.Font(typeface, int(size))
            glyphs = font.textToGlyphs(span_text)
            positions = [
                x_position + letter_spacing * glyph_index
                for glyph_index, x_position in enumerate(font.getXPos(glyphs))
            ]
            glyph_bounds = list(font.getBounds(glyphs))
            span_width = sum(font.getWidths(glyphs))
            span_width += letter_spacing * max(0, len(glyphs) - 1)
            blobs.append(
                (font, glyphs, positions, glyph_bounds, font.getMetrics(), span_width)
            )
            total_width += span_width

        if text_align == "center":
            line_offset = (element_width - total_width) / 2.0
        elif text_align == "right":
            line_offset = element_width - total_width
        else:
            line_offset = 0.0

        span_offset = line_offset
        for _font, _glyphs, positions, glyph_bounds, metrics, span_width in blobs:
            baseline = line_index * size * line_height - metrics.fAscent
            for position, glyph_bound in zip(positions, glyph_bounds):
                left = span_offset + position + glyph_bound.left()
                right = span_offset + position + glyph_bound.right()
                top = baseline + glyph_bound.top()
                bottom = baseline + glyph_bound.bottom()
                minimum_left = min(minimum_left, left)
                maximum_right = max(maximum_right, right)
                minimum_top = min(minimum_top, top)
                maximum_bottom = max(maximum_bottom, bottom)
            span_offset += span_width

    if minimum_top == float("inf"):
        return 0.0, 0.0, None, None, None, None
    horizontal_inset = (
        max(0.0, -minimum_left) if text_align == "left" else 0.0
    )
    vertical_inset = max(0.0, -minimum_top)
    return (
        horizontal_inset,
        vertical_inset,
        minimum_left,
        maximum_right,
        minimum_top,
        maximum_bottom,
    )


def _validate_positioned_glyph_bounds(
    wrapped: str,
    line_indices: List[int],
    line_count: int,
    element: Dict[str, Any],
    font_manager,
    family: str,
    size: float,
    line_height: float,
    letter_spacing: float,
    colors: List[str],
    bold_flags: List[bool],
    italic_flags: List[bool],
) -> Tuple[float, float]:
    """Reject glyph envelopes outside the box after minimal x/y insets."""
    (
        horizontal_inset,
        vertical_inset,
        minimum_left,
        maximum_right,
        minimum_top,
        maximum_bottom,
    ) = _positioned_glyph_metrics(
        wrapped,
        line_indices,
        line_count,
        element,
        font_manager,
        family,
        size,
        line_height,
        letter_spacing,
        colors,
        bold_flags,
        italic_flags,
    )
    if minimum_left is None:
        return horizontal_inset, vertical_inset
    element_width = float(element.get("width", 1.0))
    element_height = float(element.get("height", 1.0))
    rotated = float(element.get("rotation", 0.0)) % 360.0 != 0.0
    adjusted_minimum_left = minimum_left + horizontal_inset
    adjusted_maximum_right = maximum_right + horizontal_inset
    adjusted_minimum_top = minimum_top + vertical_inset
    adjusted_maximum_bottom = maximum_bottom + vertical_inset
    right_limit = element_width - horizontal_inset if rotated else element_width
    bottom_limit = element_height - vertical_inset if rotated else element_height
    if (
        adjusted_minimum_left < 0
        or adjusted_maximum_right > right_limit
        or adjusted_minimum_top < 0
        or adjusted_maximum_bottom > bottom_limit
    ):
        raise TextOverflowError(
            "positioned glyph bounds exceed text element "
            f"(bounds=({adjusted_minimum_left:g}, {adjusted_minimum_top:g}, "
            f"{adjusted_maximum_right:g}, {adjusted_maximum_bottom:g}), "
            f"box=({element_width:g}, {element_height:g}), "
            f"adjusted_limits=({right_limit:g}, {bottom_limit:g}))"
        )
    return horizontal_inset, vertical_inset


def _prepare_text(element: Dict[str, Any], font_manager) -> _PreparedText:
    content = str(element.get("content", ""))
    transient_content, source_indices = _collapse_crlf(content)
    family = element.get("font_family", "Montserrat")
    raw_size = element.get("font_size", 24)
    if type(raw_size) is not int or raw_size < 1:
        raise MalformedTextError("font_size must be a serialized integer")
    size = raw_size
    line_height = float(element.get("line_height", _DEFAULT_LINE_HEIGHT))
    letter_spacing = float(element.get("letter_spacing", 0.0))
    colors, bold_flags, italic_flags = _style_maps(element, len(content))
    transient_colors = [colors[index] for index in source_indices]
    transient_bold_flags = [bold_flags[index] for index in source_indices]
    transient_italic_flags = [italic_flags[index] for index in source_indices]
    _validate_font_faces(font_manager, family, element, bold_flags, italic_flags)
    measure = _measure_text(
        transient_content,
        font_manager,
        family,
        size,
        letter_spacing,
        transient_colors,
        transient_bold_flags,
        transient_italic_flags,
    )
    wrapped, line_indices, line_count = wrap_text_with_line_map(
        transient_content,
        (),
        float(element.get("width", 1.0)),
        measure=measure,
    )
    return _PreparedText(
        wrapped,
        line_indices,
        line_count,
        family,
        size,
        line_height,
        letter_spacing,
        transient_colors,
        transient_bold_flags,
        transient_italic_flags,
    )


def _append_text(
    out: Dict[str, Any], element: Dict[str, Any], font_manager
) -> Tuple[float, float]:
    prepared = _prepare_text(element, font_manager)
    enforce_text_limits(
        prepared.wrapped,
        prepared.size,
        prepared.line_height,
        element.get("max_lines"),
        float(element.get("height", 1.0)),
        prepared.line_count,
    )
    horizontal_inset, vertical_inset = _validate_positioned_glyph_bounds(
        prepared.wrapped,
        prepared.line_indices,
        prepared.line_count,
        element,
        font_manager,
        prepared.family,
        prepared.size,
        prepared.line_height,
        prepared.letter_spacing,
        prepared.colors,
        prepared.bold_flags,
        prepared.italic_flags,
    )

    out["text"].append(prepared.wrapped)
    out["font_size"].append(prepared.size)
    out["font"].append(prepared.family)
    out["line_height"].append(prepared.line_height)
    out["text_align"].append(element.get("text_align", "left"))
    out["capitalize"].append(bool(element.get("capitalize", False)))
    out["letter_spacing"].append(prepared.letter_spacing)
    out["font_bold"].append(prepared.bold_flags)
    out["font_italic"].append(prepared.italic_flags)
    out["text_color"].append(prepared.colors)
    out["text_line"].append(prepared.line_indices)
    return horizontal_inset, vertical_inset


def minimum_text_box_height(
    element: Dict[str, Any],
    width: int,
    font_size: int,
    font_manager,
) -> int:
    """Measure the smallest integer box height passing the renderer hard checks."""
    candidate = dict(element)
    candidate["width"] = width
    candidate["font_size"] = font_size
    prepared = _prepare_text(candidate, font_manager)
    enforce_text_limits(
        prepared.wrapped,
        prepared.size,
        prepared.line_height,
        candidate.get("max_lines"),
        float("inf"),
        prepared.line_count,
    )
    (
        horizontal_inset,
        vertical_inset,
        minimum_left,
        maximum_right,
        _minimum_top,
        maximum_bottom,
    ) = _positioned_glyph_metrics(
        prepared.wrapped,
        prepared.line_indices,
        prepared.line_count,
        candidate,
        font_manager,
        prepared.family,
        prepared.size,
        prepared.line_height,
        prepared.letter_spacing,
        prepared.colors,
        prepared.bold_flags,
        prepared.italic_flags,
    )
    rotated = float(candidate.get("rotation", 0.0)) % 360.0 != 0.0
    right_limit = width - horizontal_inset if rotated else width
    if minimum_left is not None and (
        minimum_left + horizontal_inset < 0
        or maximum_right + horizontal_inset > right_limit
    ):
        raise TextOverflowError(
            "positioned glyph bounds exceed text element "
            f"(x=({minimum_left + horizontal_inset:g}, "
            f"{maximum_right + horizontal_inset:g}), width={right_limit:g})"
        )
    glyph_bottom = (
        0.0
        if maximum_bottom is None
        else maximum_bottom + vertical_inset * (2 if rotated else 1)
    )
    line_box_height = prepared.line_count * prepared.size * prepared.line_height
    return ceil(max(line_box_height, glyph_bottom))


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
    font_manager=None,
) -> List[str]:
    """Render a CHAMELEON design (flat `{"canvas", "elements"}` shape) to a
    PNG file. This is what `engine/main.py` calls
    (`renderer.converter.convert.render_design_to_png`).

    `fonts_dir` defaults to a `fonts/` folder next to `assets_dir` (i.e.
    `brand_kit/assets` + `brand_kit/fonts`), matching this repo's layout.
    Pass `font_manager` when conversion and rendering must share a caller-owned
    font registry. Returns conversion warnings (missing assets, unknown element
    types, etc.) for the caller to log.
    """
    assets_dir = str(assets_dir)
    fonts_dir = str(fonts_dir) if fonts_dir is not None else str(Path(assets_dir).parent / "fonts")

    if font_manager is None:
        renderer = _get_renderer(fonts_dir)
    else:
        renderer = CrelloV5Renderer.__new__(CrelloV5Renderer)
        renderer.features = _STUB_FEATURES
        renderer.font_manager = font_manager
    example, warnings = convert_chameleon_to_crello(design, renderer.font_manager, assets_dir)
    image_bytes = renderer.render(example, max_size=max_size or 2048, format="png")
    Path(png_path).write_bytes(image_bytes)
    return warnings
