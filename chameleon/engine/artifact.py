"""Hard validation for rendered PNG artifacts.

This module is deliberately a hard, deterministic gate.  It mirrors the
pinned renderer's 2048px sizing and opaque canvas, checks warning provenance,
and verifies exact source pixels for opaque one-to-one image/shape layers.  Any
layer which needs rasterisation (text, transforms, opacity, antialiasing, or
scaling) is compared with a second render from the pinned adapter.
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
import math
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Iterable, Mapping

from PIL import Image, ImageChops, ImageFilter

from .errors import InfeasibleLayoutError, InfeasibleReasonCode
from .geometry.bounds import rotated_aabb

_RENDER_LIMIT = 2048
_MARGIN = 1
_WHITE = (255, 255, 255, 255)
_DEFAULT_FONTS = Path(__file__).resolve().parents[1] / "brand_kit" / "fonts"


@dataclass
class _Layer:
    kind: str
    possible: Image.Image
    exact: bool = False
    opaque: Image.Image | None = None


def _adapter():
    try:
        from renderer.converter.assets import (
            asset_path,
            load_asset_image,
            missing_asset_warning,
        )
        from renderer.converter.shapes import render_shape
    except ModuleNotFoundError:
        from chameleon.renderer.converter.assets import (
            asset_path,
            load_asset_image,
            missing_asset_warning,
        )
        from chameleon.renderer.converter.shapes import render_shape
    return asset_path, load_asset_image, missing_asset_warning, render_shape


def _fail(check: str, message: str, **details: Any) -> None:
    details = {"artifact_check": check, **details}
    raise InfeasibleLayoutError(InfeasibleReasonCode.RUNTIME_IO_FAILURE, message, details)


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
    return _fraction(value).denominator == 1


def _effective(value: Any, default: Any) -> Any:
    return default if value is None else value


def _render_size(canvas: Mapping[str, Any]) -> tuple[tuple[float, float], tuple[int, int]]:
    """Mirror cr-renderer's ``_get_scale_size(..., max_size=2048)``."""
    width = _number(canvas["width"])
    height = _number(canvas["height"])
    scale = min(1.0, _RENDER_LIMIT / max(width, height))
    sx = sy = scale
    if round(width * sx) <= 0:
        sx = 1.0 / width
    if round(height * sy) <= 0:
        sy = 1.0 / height
    size = (round(width * sx), round(height * sy))
    if size[0] <= 0 or size[1] <= 0:
        raise ValueError(f"invalid renderer dimensions: {size!r}")
    return (sx, sy), size


def _rgba(image: Image.Image) -> Image.Image:
    return image if image.mode == "RGBA" else image.convert("RGBA")


def _binary(mask: Image.Image, predicate) -> Image.Image:
    return mask.point(lambda value: 255 if predicate(value) else 0, mode="L")


def _alpha_masks(raster: Image.Image) -> tuple[Image.Image, Image.Image, Image.Image]:
    alpha = raster.getchannel("A")
    return (
        _binary(alpha, lambda value: value == 255),
        _binary(alpha, lambda value: 0 < value < 255),
        _binary(alpha, lambda value: value > 0),
    )


def _nonwhite_mask(image: Image.Image) -> Image.Image:
    image = _rgba(image)
    mask = Image.new("L", image.size, 0)
    src = image.load()
    dst = mask.load()
    for y in range(image.height):
        for x in range(image.width):
            if src[x, y] != _WHITE:
                dst[x, y] = 255
    return mask


def _paste_mask(size: tuple[int, int], local: Image.Image, x: int, y: int) -> Image.Image:
    mask = Image.new("L", size, 0)
    mask.paste(local, (x, y), local)
    return mask


def _dilate(mask: Image.Image, margin: int = _MARGIN) -> Image.Image:
    return mask if margin <= 0 else mask.filter(ImageFilter.MaxFilter(2 * margin + 1))


def _paint_order(elements: Iterable[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    return [element for _index, element in sorted(
        enumerate(elements), key=lambda pair: (_effective(pair[1].get("z_index"), 0), pair[0])
    )]


def _local_raster(
    element: Mapping[str, Any], assets_dir: str | Path | None
) -> tuple[Image.Image | None, str]:
    _asset_path, load_asset_image, _warning, render_shape = _adapter()
    width = _number(element.get("width", 0))
    height = _number(element.get("height", 0))
    if width <= 0 or height <= 0:
        return None, str(element.get("type", "none"))
    kind = element.get("type")
    if kind == "image":
        return _rgba(load_asset_image(
            str(assets_dir) if assets_dir is not None else None,
            element.get("asset_id"), width, height, element.get("fit", "contain")
        )), "image"
    if kind == "shape":
        return _rgba(render_shape(dict(element))), "shape"
    return None, "text"


def _exact_eligible(element: Mapping[str, Any], scale: tuple[float, float], raster: Image.Image | None) -> bool:
    if element.get("type") not in {"image", "shape"} or raster is None:
        return False
    if scale != (1.0, 1.0) or not all(_integral(element.get(field, 0)) for field in ("x", "y", "width", "height")):
        return False
    if _number(element.get("rotation", 0)) % 360 != 0:
        return False
    if _number(_effective(element.get("opacity"), 1)) != 1.0:
        return False
    return raster.getchannel("A").getextrema() == (255, 255)


def _aabb_mask(
    size: tuple[int, int], element: Mapping[str, Any], scale: tuple[float, float], margin: int = 0
) -> Image.Image:
    aabb = rotated_aabb(element)
    sx, sy = scale
    left = math.floor(float(aabb.min_x) * sx) - margin
    top = math.floor(float(aabb.min_y) * sy) - margin
    right = math.ceil(float(aabb.max_x) * sx) + margin
    bottom = math.ceil(float(aabb.max_y) * sy) + margin
    mask = Image.new("L", size, 0)
    if right > left and bottom > top:
        mask.paste(255, (left, top, right, bottom))
    return mask


def _transformed_mask(
    raster: Image.Image, element: Mapping[str, Any], size: tuple[int, int], scale: tuple[float, float], margin: int
) -> Image.Image:
    sx, sy = scale
    width = max(1, round(_number(element.get("width", 0)) * sx))
    height = max(1, round(_number(element.get("height", 0)) * sy))
    local = raster.getchannel("A").resize((width, height), Image.Resampling.NEAREST)
    rotation = _number(element.get("rotation", 0))
    if rotation % 360:
        local = local.rotate(-rotation, resample=Image.Resampling.BICUBIC, expand=True)
        center_x = (_number(element.get("x", 0)) + _number(element.get("width", 0)) / 2) * sx
        center_y = (_number(element.get("y", 0)) + _number(element.get("height", 0)) / 2) * sy
        left, top = round(center_x - local.width / 2), round(center_y - local.height / 2)
    else:
        left, top = round(_number(element.get("x", 0)) * sx), round(_number(element.get("y", 0)) * sy)
    return _dilate(_paste_mask(size, _binary(local, lambda value: value > 0), left, top), margin)


def _expected_warning(element: Mapping[str, Any], assets_dir: str | Path | None) -> str | None:
    if element.get("type") != "image":
        return None
    asset_path, _load, missing_asset_warning, _shape = _adapter()
    if asset_path(str(assets_dir) if assets_dir is not None else None, element.get("asset_id")) is None:
        return missing_asset_warning(element.get("id"), element.get("asset_id"))
    return None


def _check_missing_assets(elements: Iterable[Mapping[str, Any]], assets_dir: str | Path | None, warnings: Iterable[str]) -> None:
    expected = {warning for element in elements if (warning := _expected_warning(element, assets_dir)) is not None}
    actual = {
        warning for warning in warnings or ()
        if isinstance(warning, str) and warning.startswith("Missing asset ")
    }
    if expected - actual:
        _fail("missing_asset_warning", "renderer omitted a required missing-asset warning", missing=sorted(expected - actual))
    if actual - expected:
        _fail("missing_asset_warning", "renderer reported an unexpected missing asset", unexpected=sorted(actual - expected))


def _reference_image(
    design: Mapping[str, Any], assets_dir: str | Path | None, fonts_dir: str | Path | None,
    font_manager: Any, size: tuple[int, int]
) -> Image.Image:
    try:
        from renderer.converter.convert import render_design_to_png
    except ModuleNotFoundError:
        from chameleon.renderer.converter.convert import render_design_to_png
    if fonts_dir is not None:
        resolved_fonts_dir = str(fonts_dir)
    elif assets_dir is not None:
        candidate_fonts_dir = Path(assets_dir).parent / "fonts"
        resolved_fonts_dir = str(
            candidate_fonts_dir if candidate_fonts_dir.is_dir() else _DEFAULT_FONTS
        )
    else:
        resolved_fonts_dir = str(_DEFAULT_FONTS)
    with TemporaryDirectory(prefix=".chameleon-artifact-") as directory:
        path = Path(directory) / "reference.png"
        render_design_to_png(
            dict(design), str(assets_dir) if assets_dir is not None else "",
            path, fonts_dir=resolved_fonts_dir, font_manager=font_manager
        )
        with Image.open(path) as image:
            if image.size != size:
                _fail(
                    "reference_dimensions",
                    "pinned renderer reference has unexpected dimensions",
                    expected_size=size,
                    actual_size=image.size,
                )
            image.load()
            result = _rgba(image).copy()
    return result


def _first_difference(mask: Image.Image, actual: Image.Image, expected: Image.Image):
    bbox = mask.getbbox()
    if bbox is None:
        raise AssertionError("empty difference mask")
    left, top, right, bottom = bbox
    for y in range(top, bottom):
        for x in range(left, right):
            if mask.getpixel((x, y)):
                return (x, y), expected.getpixel((x, y)), actual.getpixel((x, y))
    raise AssertionError("empty difference mask")


def _difference_mask(actual: Image.Image, expected: Image.Image, known: Image.Image) -> Image.Image:
    channels = ImageChops.difference(actual, expected).split()
    difference = channels[0]
    for channel in channels[1:]:
        difference = ImageChops.lighter(difference, channel)
    return ImageChops.darker(_binary(difference, lambda value: value != 0), known)


def _replay(
    design: Mapping[str, Any], actual: Image.Image, assets_dir: str | Path | None,
    fonts_dir: str | Path | None, font_manager: Any, scale: tuple[float, float], size: tuple[int, int]
) -> None:
    expected = Image.new("RGBA", size, _WHITE)
    known = Image.new("L", size, 255)
    strict_allowed = Image.new("L", size, 0)
    allowed = Image.new("L", size, 0)
    layers: list[_Layer] = []
    has_nonexact = False

    for element in _paint_order(design.get("elements", ())):
        kind = element.get("type")
        raster, category = _local_raster(element, assets_dir)
        if kind in {"image", "shape"} and (raster is None or _number(_effective(element.get("opacity"), 1)) == 0):
            continue
        if kind not in {"image", "shape", "text"}:
            _fail("layer_type", "renderer artifact contains an unsupported element type", type=kind)
        exact = _exact_eligible(element, scale, raster)
        if kind == "text":
            has_nonexact = True
            strict = _aabb_mask(size, element, scale)
            possible = _aabb_mask(size, element, scale, _MARGIN)
            known = ImageChops.darker(known, ImageChops.invert(possible))
            strict_allowed = ImageChops.lighter(strict_allowed, strict)
            allowed = ImageChops.lighter(allowed, possible)
            layers.append(_Layer("text", possible))
            continue
        assert raster is not None
        opaque, partial, visible = _alpha_masks(raster)
        if exact:
            x, y = round(_number(element.get("x", 0))), round(_number(element.get("y", 0)))
            opaque_canvas = _paste_mask(size, opaque, x, y)
            visible_canvas = _paste_mask(size, visible, x, y)
            expected.paste(raster, (x, y), opaque)
            known = ImageChops.lighter(known, opaque_canvas)
            strict_allowed = ImageChops.lighter(strict_allowed, visible_canvas)
            allowed = ImageChops.lighter(allowed, visible_canvas)
            layers.append(_Layer(category, visible_canvas, True, opaque_canvas))
        else:
            has_nonexact = True
            strict = _transformed_mask(raster, element, size, scale, 0)
            possible = _transformed_mask(raster, element, size, scale, _MARGIN)
            known = ImageChops.darker(known, ImageChops.invert(possible))
            strict_allowed = ImageChops.lighter(strict_allowed, strict)
            allowed = ImageChops.lighter(allowed, possible)
            layers.append(_Layer(category, possible))

    actual_nonwhite = _nonwhite_mask(actual)
    stray = ImageChops.darker(actual_nonwhite, ImageChops.invert(allowed))
    if stray.getbbox() is not None:
        point, _expected, actual_pixel = _first_difference(stray, actual, expected)
        _fail("bounds", "rendered pixels extend beyond element paint regions", pixel=point, expected=_WHITE, actual=actual_pixel, bbox=stray.getbbox())

    reference: Image.Image | None = None
    edge = ImageChops.darker(ImageChops.darker(actual_nonwhite, ImageChops.invert(strict_allowed)), allowed)
    if edge.getbbox() is not None:
        reference = _reference_image(design, assets_dir, fonts_dir, font_manager, size)
        reference_nonwhite = _nonwhite_mask(reference)
        unauthorized = ImageChops.darker(edge, ImageChops.invert(reference_nonwhite))
        if unauthorized.getbbox() is not None:
            point, expected_pixel, actual_pixel = _first_difference(unauthorized, actual, reference)
            _fail("bounds", "rendered pixels extend beyond pinned renderer paint edge", pixel=point, expected=expected_pixel, actual=actual_pixel, bbox=unauthorized.getbbox())
        edge_difference = _difference_mask(actual, reference, edge)
        if edge_difference.getbbox() is not None:
            point, expected_pixel, actual_pixel = _first_difference(edge_difference, actual, reference)
            _fail("bounds", "rendered edge pixels differ from pinned renderer", pixel=point, expected=expected_pixel, actual=actual_pixel, bbox=edge_difference.getbbox())

    differences = _difference_mask(actual, expected, known)
    if differences.getbbox() is not None:
        point, expected_pixel, actual_pixel = _first_difference(differences, actual, expected)
        check = "bounds"
        for layer in reversed(layers):
            if layer.exact and layer.opaque is not None and layer.opaque.getpixel(point):
                check = f"{layer.kind}_pixels"
                break
        _fail(check, "rendered pixels differ from deterministic source replay", pixel=point, expected=expected_pixel, actual=actual_pixel, bbox=differences.getbbox())

    if has_nonexact:
        reference = reference or _reference_image(design, assets_dir, fonts_dir, font_manager, size)
        differences = _difference_mask(actual, reference, Image.new("L", size, 255))
        if differences.getbbox() is not None:
            point, expected_pixel, actual_pixel = _first_difference(differences, actual, reference)
            _fail("render_pixels", "rendered pixels differ from pinned renderer", pixel=point, expected=expected_pixel, actual=actual_pixel, bbox=differences.getbbox())


def validate_artifact(
    design: Mapping[str, Any], image: Image.Image, *, assets_dir: str | Path | None = None,
    fonts_dir: str | Path | None = None, font_manager: Any = None, warnings: Iterable[str] = ()
) -> None:
    """Validate one decoded renderer PNG against hard artifact invariants."""
    if not isinstance(design, Mapping) or not isinstance(image, Image.Image):
        raise TypeError("validate_artifact requires a design mapping and PIL image")
    try:
        scale, expected_size = _render_size(design["canvas"])
    except (KeyError, TypeError, ValueError, OverflowError, ZeroDivisionError) as error:
        _fail("dimensions", f"cannot determine expected renderer size: {error}")
    actual = _rgba(image)
    if actual.size != expected_size:
        _fail("dimensions", "rendered PNG dimensions do not match pinned renderer", expected_size=expected_size, actual_size=actual.size)
    alpha_extrema = actual.getchannel("A").getextrema()
    if alpha_extrema[0] != 255:
        _fail("opacity", "rendered canvas is not fully opaque", alpha=alpha_extrema)
    try:
        elements = list(design.get("elements", ()))
        _check_missing_assets(elements, assets_dir, warnings)
        _replay(design, actual, assets_dir, fonts_dir, font_manager, scale, expected_size)
    except InfeasibleLayoutError:
        raise
    except (KeyError, TypeError, ValueError, OverflowError, OSError, RuntimeError) as error:
        _fail("runtime", "artifact validation failed closed", error=str(error))
