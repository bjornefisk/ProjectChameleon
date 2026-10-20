"""Hard validation for rendered PNG artifacts.

The validator mirrors the pinned renderer's output dimensions and opaque-canvas
invariant, enforces the missing-asset warning contract, replays fully opaque
one-to-one image and shape pixels from adapter rasters, and checks rendered ink
against adapter-derived paint regions. For any non-exact layer it also compares
the decoded output with a second render from the pinned adapter, so text,
rotation, blending, resampling, and antialias edges cannot be replaced by
arbitrary pixels. Soft visual quality is not part of this gate.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
import math
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Iterable, Mapping

from PIL import Image, ImageChops, ImageFilter

try:
    from .errors import InfeasibleLayoutError, InfeasibleReasonCode
    from .geometry.bounds import rotated_aabb
except ImportError:  # pragma: no cover - Docker imports engine as a top-level package.
    from engine.errors import InfeasibleLayoutError, InfeasibleReasonCode
    from engine.geometry.bounds import rotated_aabb


_RENDER_LIMIT = 2048
_MARGIN_PX = 1
_WHITE = (255, 255, 255, 255)
_DEFAULT_FONTS_DIR = Path(__file__).resolve().parents[1] / "brand_kit" / "fonts"


@dataclass
class _Layer:
    element: Mapping[str, Any]
    category: str
    # Pixels that the element may legitimately paint. This is intentionally
    # more precise than an AABB for raster shapes/images, so an ellipse corner
    # or an image's transparent hole cannot obstruct a prior exact layer.
    possible: Image.Image
    exact: bool = False
    opaque: Image.Image | None = None


def _adapter():
    """Import adapter primitives lazily so syntax checks remain lightweight."""

    try:
        from renderer.converter.assets import (  # type: ignore
            asset_path,
            load_asset_image,
            missing_asset_warning,
        )
        from renderer.converter.shapes import render_shape  # type: ignore
    except ModuleNotFoundError:
        from chameleon.renderer.converter.assets import (  # type: ignore
            asset_path,
            load_asset_image,
            missing_asset_warning,
        )
        from chameleon.renderer.converter.shapes import render_shape  # type: ignore
    return asset_path, load_asset_image, missing_asset_warning, render_shape


def _number(value: Any) -> float:
    result = float(value)
    if not math.isfinite(result):
        raise ValueError("artifact geometry must be finite")
    return result


def _fraction(value: Any) -> Fraction:
    if isinstance(value, Fraction):
        return value
    if isinstance(value, int) and not isinstance(value, bool):
        return Fraction(value)
    try:
        return Fraction(value)
    except (TypeError, ValueError, ZeroDivisionError) as error:
        raise ValueError(f"artifact geometry is not numeric: {value!r}") from error


def _integral(value: Any) -> bool:
    fraction = _fraction(value)
    return fraction.denominator == 1


def _effective(value: Any, default: Any) -> Any:
    return default if value is None else value


def _paint_order(elements: Iterable[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    """Mirror the adapter's stable effective-z-index sort."""

    ordered = sorted(
        enumerate(elements),
        key=lambda pair: (_effective(pair[1].get("z_index"), 0), pair[0]),
    )
    return [element for _index, element in ordered]


def _render_size(canvas: Mapping[str, Any]) -> tuple[tuple[float, float], tuple[int, int]]:
    """Mirror pinned cr-renderer's ``_get_scale_size`` for max_size=2048."""

    width = _number(canvas["width"])
    height = _number(canvas["height"])
    scale = min(1.0, _RENDER_LIMIT / max(width, height))
    sx = sy = scale
    if round(width * sx) <= 0:
        sx = 1.0 / width
    if round(height * sy) <= 0:
        sy = 1.0 / height
    size = (round(sx * width), round(sy * height))
    if size[0] <= 0 or size[1] <= 0:
        raise ValueError(f"invalid rendered size {size!r}")
    return (sx, sy), size


def _fail(check: str, message: str, **details: Any) -> None:
    payload = {"artifact_check": check}
    payload.update(details)
    raise InfeasibleLayoutError(
        InfeasibleReasonCode.RUNTIME_IO_FAILURE,
        message,
        payload,
    )


def _rgba(image: Image.Image) -> Image.Image:
    return image if image.mode == "RGBA" else image.convert("RGBA")


def _nonwhite_mask(image: Image.Image) -> Image.Image:
    rgba = _rgba(image)
    mask = Image.new("L", rgba.size, 0)
    pixels = rgba.load()
    output = mask.load()
    for y in range(rgba.height):
        for x in range(rgba.width):
            if pixels[x, y] != _WHITE:
                output[x, y] = 255
    return mask


def _binary(mask: Image.Image, predicate) -> Image.Image:
    return mask.point(lambda value: 255 if predicate(value) else 0, mode="L")


def _alpha_masks(raster: Image.Image) -> tuple[Image.Image, Image.Image, Image.Image]:
    alpha = raster.getchannel("A")
    opaque = _binary(alpha, lambda value: value == 255)
    partial = _binary(alpha, lambda value: 0 < value < 255)
    visible = _binary(alpha, lambda value: value > 0)
    return opaque, partial, visible


def _paste_mask(canvas_size: tuple[int, int], local: Image.Image, x: int, y: int) -> Image.Image:
    mask = Image.new("L", canvas_size, 0)
    mask.paste(local, (x, y), local)
    return mask


def _dilate(mask: Image.Image, margin: int = _MARGIN_PX) -> Image.Image:
    if margin <= 0:
        return mask
    # A MaxFilter is a one-pixel Chebyshev expansion and clips at canvas edges.
    return mask.filter(ImageFilter.MaxFilter(2 * margin + 1))


def _aabb_mask(
    canvas_size: tuple[int, int], element: Mapping[str, Any], scale: tuple[float, float], margin: int
) -> Image.Image:
    aabb = rotated_aabb(element)
    sx, sy = scale
    left = math.floor(float(aabb.min_x) * sx) - margin
    top = math.floor(float(aabb.min_y) * sy) - margin
    right = math.ceil(float(aabb.max_x) * sx) + margin
    bottom = math.ceil(float(aabb.max_y) * sy) + margin
    mask = Image.new("L", canvas_size, 0)
    if right <= 0 or bottom <= 0 or left >= canvas_size[0] or top >= canvas_size[1]:
        return mask
    mask.paste(255, (left, top, right, bottom))
    return mask


def _local_raster(
    element: Mapping[str, Any], assets_dir: str | Path | None
) -> tuple[Image.Image | None, str]:
    asset_path, load_asset_image, _missing_asset_warning, render_shape = _adapter()
    kind = element.get("type")
    width = _number(element.get("width", 0))
    height = _number(element.get("height", 0))
    if width <= 0 or height <= 0:
        return None, "none"
    if kind == "image":
        raster = load_asset_image(
            str(assets_dir) if assets_dir is not None else None,
            element.get("asset_id"),
            width,
            height,
            element.get("fit", "contain"),
        )
        return _rgba(raster), "image"
    if kind == "shape":
        return _rgba(render_shape(dict(element))), "shape"
    return None, "text"


def _scaled_rotated_mask(
    raster: Image.Image,
    element: Mapping[str, Any],
    canvas_size: tuple[int, int],
    scale: tuple[float, float],
    margin: int = _MARGIN_PX,
) -> Image.Image:
    """Return visible pixels with an optional renderer-edge tolerance."""

    sx, sy = scale
    width = max(1, round(_number(element.get("width", 0)) * sx))
    height = max(1, round(_number(element.get("height", 0)) * sy))
    local = raster.getchannel("A").resize((width, height), Image.Resampling.NEAREST)
    rotation = _number(element.get("rotation", 0))
    if rotation % 360:
        local = local.rotate(-rotation, resample=Image.Resampling.BICUBIC, expand=True)
        center_x = (
            _number(element.get("x", 0)) + _number(element.get("width", 0)) / 2
        ) * sx
        center_y = (
            _number(element.get("y", 0)) + _number(element.get("height", 0)) / 2
        ) * sy
        left = round(center_x - local.width / 2)
        top = round(center_y - local.height / 2)
    else:
        left = round(_number(element.get("x", 0)) * sx)
        top = round(_number(element.get("y", 0)) * sy)
    visible = _binary(local, lambda value: value > 0)
    return _dilate(_paste_mask(canvas_size, visible, left, top), margin)

def _exact_eligible(
    element: Mapping[str, Any], scale: tuple[float, float], raster: Image.Image | None
) -> bool:
    if element.get("type") not in {"image", "shape"} or raster is None:
        return False
    if scale != (1.0, 1.0):
        return False
    if not all(
        _integral(element.get(field, 0))
        for field in ("x", "y", "width", "height")
    ):
        return False
    if _number(element.get("rotation", 0)) % 360 != 0:
        return False
    if _number(_effective(element.get("opacity"), 1)) != 1.0:
        return False
    alpha = raster.getchannel("A")
    return alpha.getextrema() == (255, 255)


def _expected_warning(element: Mapping[str, Any], assets_dir: str | Path | None) -> str | None:
    if element.get("type") != "image":
        return None
    asset_path, _load_asset_image, missing_asset_warning, _render_shape = _adapter()
    if asset_path(str(assets_dir) if assets_dir is not None else None, element.get("asset_id")) is None:
        return missing_asset_warning(element.get("id"), element.get("asset_id"))
    return None


def _check_missing_assets(
    elements: Iterable[Mapping[str, Any]], assets_dir: str | Path | None, warnings: Iterable[str]
) -> None:
    actual = list(warnings or ())
    expected = {
        warning
        for element in elements
        if (warning := _expected_warning(element, assets_dir)) is not None
    }
    present_missing = {
        warning
        for warning in actual
        if isinstance(warning, str) and warning.startswith("Missing asset ")
    }
    if not expected.issubset(present_missing):
        missing = sorted(expected - present_missing)
        _fail("missing_asset_warning", "renderer omitted a required missing-asset warning", missing=missing)
    unexpected = present_missing - expected
    if unexpected:
        _fail(
            "missing_asset_warning",
            "renderer reported a missing asset that is present or not in the design",
            unexpected=sorted(unexpected),
        )


def _reference_image(
    design: Mapping[str, Any],
    assets_dir: str | Path | None,
    fonts_dir: str | Path | None,
    font_manager: Any,
    canvas_size: tuple[int, int],
) -> Image.Image:
    """Return the pinned adapter's reference image for pixel provenance."""

    try:
        from renderer.converter.convert import render_design_to_png  # type: ignore
    except ModuleNotFoundError:
        from chameleon.renderer.converter.convert import (  # type: ignore
            render_design_to_png,
        )

    resolved_assets_dir = str(assets_dir) if assets_dir is not None else ""
    resolved_fonts_dir = str(fonts_dir or _DEFAULT_FONTS_DIR)
    with TemporaryDirectory(prefix=".chameleon-artifact-") as directory:
        reference_path = Path(directory) / "reference.png"
        render_design_to_png(
            dict(design),
            resolved_assets_dir,
            reference_path,
            fonts_dir=resolved_fonts_dir,
            font_manager=font_manager,
        )
        with Image.open(reference_path) as reference:
            reference.load()
            reference_image = _rgba(reference).copy()
    if reference_image.size != canvas_size:
        _fail(
            "reference_dimensions",
            "pinned renderer reference has unexpected dimensions",
            expected_size=canvas_size,
            actual_size=reference_image.size,
        )
    return reference_image


def _first_difference(mask: Image.Image, actual: Image.Image, expected: Image.Image) -> tuple[tuple[int, int], tuple[int, ...], tuple[int, ...]]:
    bbox = mask.getbbox()
    if bbox is None:
        raise AssertionError("difference mask has no bbox")
    left, top, right, bottom = bbox
    for y in range(top, bottom):
        for x in range(left, right):
            if mask.getpixel((x, y)):
                return (x, y), expected.getpixel((x, y)), actual.getpixel((x, y))
    raise AssertionError("difference mask has no pixel")


def _difference_mask(actual: Image.Image, expected: Image.Image, known: Image.Image) -> Image.Image:
    channels = ImageChops.difference(actual, expected).split()
    difference = channels[0]
    for channel in channels[1:]:
        difference = ImageChops.lighter(difference, channel)
    difference = _binary(difference, lambda value: value != 0)
    return ImageChops.darker(difference, known)


def _classify_difference(
    point: tuple[int, int], layers: list[_Layer], actual: Image.Image, expected: Image.Image
) -> str:
    x, y = point
    # The last deterministic exact layer owning the pixel gives the most
    # useful check name. If no exact owner exists, it is a bounds violation.
    for layer in reversed(layers):
        if layer.exact and layer.opaque is not None and layer.opaque.getpixel((x, y)):
            return f"{layer.category}_pixels"
    return "bounds"


def _replay(
    design: Mapping[str, Any],
    actual: Image.Image,
    assets_dir: str | Path | None,
    fonts_dir: str | Path | None,
    font_manager: Any,
    scale: tuple[float, float],
    canvas_size: tuple[int, int],
) -> None:
    expected = Image.new("RGBA", canvas_size, _WHITE)
    known = Image.new("L", canvas_size, 255)
    strict_allowed = Image.new("L", canvas_size, 0)
    allowed = Image.new("L", canvas_size, 0)
    layers: list[_Layer] = []
    has_nonexact_layer = False

    for element in _paint_order(design.get("elements", ())):
        kind = element.get("type")
        opacity = _number(_effective(element.get("opacity"), 1))
        raster, category = _local_raster(element, assets_dir)
        if kind in {"image", "shape"} and (raster is None or opacity == 0):
            continue

        exact = _exact_eligible(element, scale, raster)
        if kind == "text":
            has_nonexact_layer = True
            strict = _aabb_mask(canvas_size, element, scale, 0)
            possible = _aabb_mask(canvas_size, element, scale, _MARGIN_PX)
            layer = _Layer(element, "text", possible, exact=False)
            known = ImageChops.darker(known, ImageChops.invert(possible))
            strict_allowed = ImageChops.lighter(strict_allowed, strict)
            allowed = ImageChops.lighter(allowed, possible)
            layers.append(layer)
            continue

        assert raster is not None
        opaque, partial, visible = _alpha_masks(raster)
        if exact:
            x = round(_number(element.get("x", 0)))
            y = round(_number(element.get("y", 0)))
            opaque_canvas = _paste_mask(canvas_size, opaque, x, y)
            partial_canvas = _paste_mask(canvas_size, partial, x, y)
            visible_canvas = _paste_mask(canvas_size, visible, x, y)
            expected.paste(raster, (x, y), opaque)
            known = ImageChops.lighter(known, opaque_canvas)
            known = ImageChops.darker(known, ImageChops.invert(partial_canvas))
            strict_allowed = ImageChops.lighter(strict_allowed, visible_canvas)
            allowed = ImageChops.lighter(allowed, visible_canvas)
            layers.append(
                _Layer(
                    element,
                    category,
                    visible_canvas,
                    exact=True,
                    opaque=opaque_canvas,
                )
            )
        else:
            has_nonexact_layer = True
            strict = _scaled_rotated_mask(
                raster, element, canvas_size, scale, margin=0
            )
            possible = _scaled_rotated_mask(
                raster, element, canvas_size, scale, margin=_MARGIN_PX
            )
            # Alpha-bearing raster pixels only can obstruct an earlier layer;
            # the one-pixel expansion is checked against the pinned render
            # below, so it does not authorize arbitrary exterior ink.
            known = ImageChops.darker(known, ImageChops.invert(possible))
            strict_allowed = ImageChops.lighter(strict_allowed, strict)
            allowed = ImageChops.lighter(allowed, possible)
            layers.append(
                _Layer(element, category, possible, exact=False)
            )

    rgb = actual.convert("RGBA")
    actual_nonwhite = _nonwhite_mask(rgb)
    stray = ImageChops.darker(actual_nonwhite, ImageChops.invert(allowed))
    if stray.getbbox() is not None:
        point, _expected_pixel, actual_pixel = _first_difference(
            stray, rgb, expected
        )
        _fail(
            "bounds",
            "rendered pixels extend beyond the element paint regions",
            pixel=point,
            expected=_WHITE,
            actual=actual_pixel,
            bbox=stray.getbbox(),
        )

    reference: Image.Image | None = None
    edge = ImageChops.darker(
        ImageChops.darker(actual_nonwhite, ImageChops.invert(strict_allowed)),
        allowed,
    )
    if edge.getbbox() is not None:
        reference = _reference_image(
            design,
            assets_dir,
            fonts_dir,
            font_manager,
            canvas_size,
        )
        reference_nonwhite = _nonwhite_mask(reference)
        unauthorized = ImageChops.darker(edge, ImageChops.invert(reference_nonwhite))
        if unauthorized.getbbox() is not None:
            point, _expected_pixel, actual_pixel = _first_difference(
                unauthorized, rgb, reference
            )
            _fail(
                "bounds",
                "rendered pixels extend beyond the pinned renderer's paint edge",
                pixel=point,
                expected=reference.getpixel(point),
                actual=actual_pixel,
                bbox=unauthorized.getbbox(),
            )
        edge_difference = _difference_mask(rgb, reference, edge)
        if edge_difference.getbbox() is not None:
            point, expected_pixel, actual_pixel = _first_difference(
                edge_difference, rgb, reference
            )
            _fail(
                "bounds",
                "rendered edge pixels differ from the pinned renderer",
                pixel=point,
                expected=expected_pixel,
                actual=actual_pixel,
                bbox=edge_difference.getbbox(),
            )

    differences = _difference_mask(rgb, expected, known)
    if differences.getbbox() is not None:
        point, expected_pixel, actual_pixel = _first_difference(
            differences, rgb, expected
        )
        check = _classify_difference(point, layers, rgb, expected)
        _fail(
            check,
            "rendered pixels differ from the deterministic source replay",
            pixel=point,
            expected=expected_pixel,
            actual=actual_pixel,
            bbox=differences.getbbox(),
        )

    if has_nonexact_layer:
        reference = (
            reference
            if reference is not None
            else _reference_image(
                design,
                assets_dir,
                fonts_dir,
                font_manager,
                canvas_size,
            )
        )
        reference_difference = _difference_mask(
            rgb, reference, Image.new("L", canvas_size, 255)
        )
        if reference_difference.getbbox() is not None:
            point, expected_pixel, actual_pixel = _first_difference(
                reference_difference, rgb, reference
            )
            _fail(
                "render_pixels",
                "rendered pixels differ from the pinned renderer",
                pixel=point,
                expected=expected_pixel,
                actual=actual_pixel,
                bbox=reference_difference.getbbox(),
            )
def validate_artifact(
    design: Mapping[str, Any],
    image: Image.Image,
    *,
    assets_dir: str | Path | None = None,
    fonts_dir: str | Path | None = None,
    font_manager: Any = None,
    warnings: Iterable[str] = (),
) -> None:
    """Validate one decoded renderer PNG against hard artifact invariants."""

    if not isinstance(design, Mapping) or not isinstance(image, Image.Image):
        raise TypeError("validate_artifact requires a design mapping and PIL image")
    try:
        scale, expected_size = _render_size(design["canvas"])
    except (KeyError, TypeError, ValueError, OverflowError) as error:
        _fail("dimensions", f"cannot determine expected renderer size: {error}")
    actual = _rgba(image)
    if actual.size != expected_size:
        _fail("dimensions", "rendered PNG dimensions do not match the pinned renderer", expected_size=expected_size, actual_size=actual.size)
    alpha = actual.getchannel("A")
    alpha_extrema = alpha.getextrema()
    if alpha_extrema[0] != 255:
        bad = next((index for index, value in enumerate(alpha.getdata()) if value != 255), None)
        pixel = (bad % actual.width, bad // actual.width) if bad is not None else None
        _fail("opacity", "rendered canvas is not fully opaque", pixel=pixel, alpha=alpha_extrema[0])
    elements = list(design.get("elements", ()))
    _check_missing_assets(elements, assets_dir, warnings)
    _replay(
        design,
        actual,
        assets_dir,
        fonts_dir,
        font_manager,
        scale,
        expected_size,
    )


__all__ = ["validate_artifact"]
