"""Real-renderer helpers shared by the artifact conformance tests.

Conformance cannot be judged against canned PNGs: a canned PNG is exactly what
artifact validation must reject. Every positive case here is therefore a render
produced by the pinned adapter, and every negative case is a defect applied to
(or a different render of) such a render.
"""

import copy
import json
import sys
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

from PIL import Image, ImageDraw

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT))

from chameleon.renderer.converter.convert import render_design_to_png

try:
    from engine.artifact import validate_artifact
    from engine.errors import InfeasibleLayoutError, InfeasibleReasonCode
except ModuleNotFoundError:
    from chameleon.engine.artifact import validate_artifact
    from chameleon.engine.errors import InfeasibleLayoutError, InfeasibleReasonCode

CHAMELEON_ROOT = PROJECT_ROOT / "chameleon"
BRAND_ASSETS = CHAMELEON_ROOT / "brand_kit" / "assets"
BRAND_FONTS = CHAMELEON_ROOT / "brand_kit" / "fonts"
SAMPLES = CHAMELEON_ROOT / "input"
FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "artifact"
FIXTURE_NAMES = (
    "composite",
    "missing_asset",
    "large_canvas",
    "bleed_overlap",
    "low_contrast_text",
)


def load_json(path):
    """Decode JSON with the runner's exact-number rules."""
    return json.loads(
        Path(path).read_text(encoding="utf-8"), parse_int=int, parse_float=Decimal
    )


def load_design(name):
    return load_json(FIXTURES / f"{name}.json")


def render_to_png(design, assets_dir, png_path):
    """Production-shaped renderer: the real adapter, returning its warnings."""
    return render_design_to_png(
        design, str(assets_dir), str(png_path), fonts_dir=str(BRAND_FONTS)
    )


def render(design, assets_dir=BRAND_ASSETS):
    """Render with the real adapter; return the decoded RGBA image and warnings."""
    with tempfile.TemporaryDirectory() as directory:
        png_path = Path(directory) / "render.png"
        warnings = render_to_png(design, assets_dir, png_path)
        with Image.open(png_path) as image:
            image.load()
            return image.copy(), warnings


def element(design, element_id):
    return next(item for item in design["elements"] if item["id"] == element_id)


def only(design, *element_ids):
    """Return a copy of ``design`` that keeps just the named elements."""
    result = copy.deepcopy(design)
    result["elements"] = [
        item for item in result["elements"] if item["id"] in element_ids
    ]
    return result


def with_element(design, element_id, **changes):
    """Return a copy of ``design`` with one element's fields replaced."""
    result = copy.deepcopy(design)
    element(result, element_id).update(changes)
    return result


def blank(size):
    """An opaque white canvas, the render of a design that draws nothing."""
    return Image.new("RGBA", size, (255, 255, 255, 255))


def paint(image, box, color):
    """Fill the half-open pixel box ``(left, top, right, bottom)``."""
    left, top, right, bottom = box
    ImageDraw.Draw(image).rectangle(
        [left, top, right - 1, bottom - 1], fill=tuple(color)
    )


def synthetic_assets(directory):
    """Write deterministic assets whose every pixel is known by construction."""
    root = Path(directory)
    swatch = Image.new("RGBA", (60, 40))
    for y in range(40):
        for x in range(60):
            swatch.putpixel((x, y), (x * 4 % 256, y * 6 % 256, (x + y) * 3 % 256, 255))
    swatch.save(root / "swatch.png")

    # An opaque frame around a transparent hole whose RGB is not black: the
    # hole's colour must never matter, because alpha 0 paints nothing.
    ring = Image.new("RGBA", (40, 40), (10, 200, 60, 255))
    ImageDraw.Draw(ring).rectangle([8, 8, 31, 31], fill=(255, 0, 0, 0))
    ring.save(root / "ring.png")

    # An opaque image with one half-transparent column: a blended pixel.
    soft = Image.new("RGBA", (40, 40), (30, 30, 200, 255))
    for y in range(40):
        soft.putpixel((10, y), (30, 30, 200, 128))
    soft.save(root / "soft.png")

    Image.new("RGBA", (60, 40), (200, 40, 40, 255)).save(root / "red.png")
    return root


def image_element(element_id, asset_id, x, y, width, height, z_index=0, **extra):
    item = {
        "id": element_id,
        "type": "image",
        "x": x,
        "y": y,
        "width": width,
        "height": height,
        "z_index": z_index,
        "asset_id": asset_id,
        "fit": "fill",
    }
    item.update(extra)
    return item


def shape_element(element_id, x, y, width, height, z_index=0, **extra):
    item = {
        "id": element_id,
        "type": "shape",
        "x": x,
        "y": y,
        "width": width,
        "height": height,
        "z_index": z_index,
        "shape_type": "rectangle",
        "fill_color": "rgba(20,60,120,1)",
    }
    item.update(extra)
    return item


def text_element(element_id, x, y, width, height, z_index=0, **extra):
    item = {
        "id": element_id,
        "type": "text",
        "x": x,
        "y": y,
        "width": width,
        "height": height,
        "z_index": z_index,
        "content": "Hi",
        "font_family": "Solstice Sans",
        "font_size": 20,
        "color": "rgba(0,0,0,1)",
    }
    item.update(extra)
    return item


def design_of(width, height, *elements):
    return {"canvas": {"width": width, "height": height}, "elements": list(elements)}


class ArtifactTestCase(unittest.TestCase):
    """Base class with synthetic assets and artifact-specific assertions."""

    def setUp(self):
        self._assets = tempfile.TemporaryDirectory()
        self.addCleanup(self._assets.cleanup)
        self.assets = synthetic_assets(self._assets.name)

    def validate(self, design, image, warnings=(), assets_dir=BRAND_ASSETS):
        validate_artifact(
            design,
            image,
            assets_dir=assets_dir,
            fonts_dir=BRAND_FONTS,
            warnings=warnings,
        )

    def assertConforms(self, design, image, warnings=(), assets_dir=BRAND_ASSETS):
        try:
            self.validate(design, image, warnings, assets_dir)
        except InfeasibleLayoutError as error:
            self.fail(f"a conformant render was rejected: {error.message} {error.details}")

    def assertRejected(
        self, check, design, image, warnings=(), assets_dir=BRAND_ASSETS, **details
    ):
        with self.assertRaises(InfeasibleLayoutError) as raised:
            self.validate(design, image, warnings, assets_dir)
        error = raised.exception
        self.assertEqual(error.reason_code, InfeasibleReasonCode.RUNTIME_IO_FAILURE)
        self.assertEqual(error.details["artifact_check"], check, error.message)
        for key, value in details.items():
            self.assertEqual(error.details[key], value, key)
        return error

    def render_here(self, design):
        """Render with the synthetic assets directory."""
        return render(design, self.assets)
