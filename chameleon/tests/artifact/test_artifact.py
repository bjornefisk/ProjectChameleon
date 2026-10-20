from __future__ import annotations

import unittest

from PIL import Image

try:
    from engine.artifact import validate_artifact
    from engine.errors import InfeasibleLayoutError, InfeasibleReasonCode
    from tests.artifact.support import shape_design, shape_render
except ModuleNotFoundError:
    from chameleon.engine.artifact import validate_artifact
    from chameleon.engine.errors import InfeasibleLayoutError, InfeasibleReasonCode
    from chameleon.tests.artifact.support import shape_design, shape_render

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


if __name__ == "__main__":
    unittest.main()
