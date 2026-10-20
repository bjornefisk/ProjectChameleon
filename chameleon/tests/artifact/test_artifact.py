from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from PIL import Image

try:
    from engine.artifact import validate_artifact
    from engine.errors import InfeasibleLayoutError, InfeasibleReasonCode
    from renderer.converter.convert import render_design_to_png
    from tests.artifact.support import (
        load_artifact_fixture,
        shape_design,
        shape_render,
    )
except ModuleNotFoundError:
    from chameleon.engine.artifact import validate_artifact
    from chameleon.engine.errors import InfeasibleLayoutError, InfeasibleReasonCode
    from chameleon.renderer.converter.convert import render_design_to_png
    from chameleon.tests.artifact.support import (
        load_artifact_fixture,
        shape_design,
        shape_render,
    )

class ArtifactValidationTests(unittest.TestCase):
    def assert_runtime_failure(self, design, image, **kwargs):
        with self.assertRaises(InfeasibleLayoutError) as context:
            validate_artifact(design, image, **kwargs)
        self.assertEqual(context.exception.reason_code, InfeasibleReasonCode.RUNTIME_IO_FAILURE)

    def test_valid_opaque_shape_raster_is_accepted(self):
        design = shape_design()
        validate_artifact(design, shape_render(design))

    def test_wrong_opaque_shape_pixels_are_rejected(self):
        design = shape_design()
        image = shape_render(design)
        image.putpixel((2, 2), (255, 0, 0, 255))
        self.assert_runtime_failure(design, image)

    def test_wrong_dimensions_and_alpha_are_rejected(self):
        design = shape_design()
        self.assert_runtime_failure(design, Image.new("RGBA", (1, 1), "white"))
        self.assert_runtime_failure(
            design,
            Image.new("RGBA", (16, 12), (255, 255, 255, 0)),
        )

    def test_exterior_ink_is_rejected(self):
        design = shape_design()
        image = shape_render(design)
        image.putpixel((0, 0), (1, 2, 3, 255))
        self.assert_runtime_failure(design, image)

    def test_missing_warning_provenance_is_exact(self):
        design = {
            "canvas": {"width": 8, "height": 8},
            "elements": [{
                "id": "photo", "type": "image", "x": 0, "y": 0,
                "width": 2, "height": 2, "asset_id": "missing.png",
            }],
        }
        image = Image.new("RGBA", (8, 8), "white")
        self.assert_runtime_failure(design, image, warnings=())

    def test_white_image_cannot_replace_nonexact_text(self):
        design = {
            "canvas": {"width": 100, "height": 40},
            "elements": [{
                "id": "label", "type": "text", "x": 4, "y": 4,
                "width": 90, "height": 30, "content": "hello",
                "font_family": "Solstice Sans", "font_size": 16,
                "color": "rgba(0,0,0,1)",
            }],
        }
        self.assert_runtime_failure(design, Image.new("RGBA", (100, 40), "white"))


    def test_exact_image_pixels_are_replayed_without_repair(self):
        design = {
            "canvas": {"width": 6, "height": 6},
            "elements": [{
                "id": "photo",
                "type": "image",
                "x": 1,
                "y": 1,
                "width": 2,
                "height": 2,
                "asset_id": "photo.png",
            }],
        }
        with tempfile.TemporaryDirectory() as directory:
            assets_dir = Path(directory)
            asset = Image.new("RGBA", (2, 2), (20, 40, 60, 255))
            asset.save(assets_dir / "photo.png", format="PNG")
            image = Image.new("RGBA", (6, 6), "white")
            image.alpha_composite(asset, (1, 1))
            validate_artifact(design, image, assets_dir=assets_dir)

            image.putpixel((1, 1), (200, 100, 50, 255))
            with self.assertRaises(InfeasibleLayoutError) as context:
                validate_artifact(design, image, assets_dir=assets_dir)

            self.assertEqual(
                context.exception.details["artifact_check"],
                "image_pixels",
            )
            self.assertEqual(image.getpixel((1, 1)), (200, 100, 50, 255))

    def test_missing_asset_placeholder_is_valid_with_exact_warning(self):
        design = load_artifact_fixture("missing_asset.json")
        with tempfile.TemporaryDirectory() as directory:
            assets_dir = Path(directory)
            png_path = assets_dir / "missing.png"
            warnings = render_design_to_png(
                design,
                assets_dir,
                png_path,
                fonts_dir=Path(__file__).resolve().parents[2] / "brand_kit" / "fonts",
            )
            with Image.open(png_path) as image:
                image.load()
                validate_artifact(
                    design,
                    image,
                    assets_dir=assets_dir,
                    warnings=warnings,
                )

    def test_low_contrast_text_is_hard_valid(self):
        design = load_artifact_fixture("low_contrast_text.json")
        root = Path(__file__).resolve().parents[2]
        with tempfile.TemporaryDirectory() as directory:
            png_path = Path(directory) / "low-contrast.png"
            warnings = render_design_to_png(
                design,
                root / "brand_kit" / "assets",
                png_path,
                fonts_dir=root / "brand_kit" / "fonts",
            )
            with Image.open(png_path) as image:
                image.load()
                validate_artifact(
                    design,
                    image,
                    assets_dir=root / "brand_kit" / "assets",
                    fonts_dir=root / "brand_kit" / "fonts",
                    warnings=warnings,
                )


    def test_conformance_fixtures_are_accepted_by_the_artifact_gate(self):
        root = Path(__file__).resolve().parents[2]
        assets_dir = root / "brand_kit" / "assets"
        fonts_dir = root / "brand_kit" / "fonts"
        for name in ("composite.json", "bleed_overlap.json", "large_canvas.json"):
            design = load_artifact_fixture(name)
            with self.subTest(fixture=name), tempfile.TemporaryDirectory() as directory:
                png_path = Path(directory) / "fixture.png"
                warnings = render_design_to_png(
                    design,
                    assets_dir,
                    png_path,
                    fonts_dir=fonts_dir,
                )
                with Image.open(png_path) as image:
                    image.load()
                    validate_artifact(
                        design,
                        image,
                        assets_dir=assets_dir,
                        fonts_dir=fonts_dir,
                        warnings=warnings,
                    )


if __name__ == "__main__":
    unittest.main()
