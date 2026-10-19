"""Golden seam between the Chameleon adapter and pinned cr-renderer.

The reference payload below is intentionally assembled without
``convert_chameleon_to_crello``.  It describes the corresponding upstream
Crello-v5 records directly, so adapter sorting, line-map, style-map, spacing,
and shape-preprocessing regressions cannot make both sides of the comparison
change together.
"""

import json
import hashlib
import io
import sys
import tempfile
import unittest
from importlib.metadata import distribution
from pathlib import Path

from PIL import Image, ImageDraw

PROJECT_ROOT = Path(__file__).parents[3]
sys.path.insert(0, str(PROJECT_ROOT))

from cr_renderer import CrelloV5Renderer

from chameleon.renderer.converter.brand_fonts import load_brand_font_manager
from chameleon.renderer.converter.convert import (
    convert_chameleon_to_crello,
    render_design_to_png,
)


ROOT = Path(__file__).parents[2]
FONT_DIR = ROOT / "brand_kit" / "fonts"
ASSETS_DIR = ROOT / "brand_kit" / "assets"

# This seam is tied to cr-renderer commit a17e1fb9a732959dd6c21ae168d5ee09d74bd64f,
# the immutable revision named by PROJECT_CONTRACT.md §6 and ADR-002.
PINNED_RENDERER_SHA = "a17e1fb9a732959dd6c21ae168d5ee09d74bd64f"


def _reference_shape() -> Image.Image:
    """Build the expected upstream image record without the shape adapter."""
    image = Image.new("RGBA", (28, 48), (30, 70, 140, 255))
    ImageDraw.Draw(image).rectangle(
        (0, 0, 27, 47),
        fill=(30, 70, 140, 255),
        outline=(255, 210, 20, 255),
        width=2,
    )
    return image


def _reference_payload() -> dict:
    """Return a hand-authored pinned-renderer payload for the corpus."""
    blank = Image.new("RGBA", (1, 1), (0, 0, 0, 0))
    white = "rgba(255,255,255,1)"
    return {
        "canvas_width": 96.0,
        "canvas_height": 64.0,
        "length": 2,
        # The reference is already in the upstream renderer's stable z order.
        "left": [60.0, 4.0],
        "top": [8.0, 4.0],
        "width": [28.0, 52.0],
        "height": [48.0, 38.0],
        "angle": [0.0, 0.0],
        "type": ["ImageElement", "TextElement"],
        "color": [[], []],
        "opacity": [1.0, 1.0],
        "text": ["", "A B\nCD"],
        "font_size": [1.0, 14],
        "font": ["", "Solstice Sans"],
        "line_height": [1.0, 1.2],
        "text_align": ["left", "center"],
        "capitalize": [False, False],
        "letter_spacing": [0.0, 1.5],
        "font_bold": [[], [True, False, False, False, False, False]],
        "font_italic": [[], [False, False, False, False, False, False]],
        "text_color": [[], [white, white, white, white, white, white]],
        # cr-renderer's lineMap is inclusive; these dense values become
        # [0, 2] and [3, 5] ranges in its pinned text utility.
        "text_line": [[], [0, 0, 0, 1, 1, 1]],
        "image": [_reference_shape(), blank],
    }


class RendererGoldenTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.font_manager = load_brand_font_manager(str(FONT_DIR))

    def test_adapter_matches_independent_pinned_renderer_reference(self):
        direct_url = json.loads(
            distribution("cr-renderer").read_text("direct_url.json")
        )
        self.assertEqual(
            direct_url["vcs_info"]["commit_id"],
            PINNED_RENDERER_SHA,
        )
        document = {
            "canvas": {"width": 96, "height": 64},
            "elements": [
                {
                    "id": "shape",
                    "type": "shape",
                    "z_index": 0,
                    "x": 60,
                    "y": 8,
                    "width": 28,
                    "height": 48,
                    "shape_type": "rectangle",
                    "fill_color": "rgba(30,70,140,1)",
                    "stroke_color": "rgba(255,210,20,1)",
                    "stroke_width": 2,
                },
                {
                    "id": "copy",
                    "type": "text",
                    "z_index": 1,
                    "x": 4,
                    "y": 4,
                    "width": 52,
                    "height": 38,
                    "content": "A B\nCD",
                    "font_family": "Solstice Sans",
                    "font_size": 14,
                    "font_weight": "regular",
                    "font_style": "normal",
                    "color": "rgba(255,255,255,1)",
                    "text_align": "center",
                    "line_height": 1.2,
                    "letter_spacing": 1.5,
                    "style_runs": [{"start": 0, "end": 1, "font_weight": "bold"}],
                },
            ],
        }

        with tempfile.TemporaryDirectory() as directory:
            output_path = Path(directory) / "adapter.png"
            warnings = render_design_to_png(
                document,
                ASSETS_DIR,
                output_path,
                fonts_dir=FONT_DIR,
                max_size=2048,
                font_manager=self.font_manager,
            )
            actual_png = output_path.read_bytes()

        self.assertEqual(warnings, [])
        converted, conversion_warnings = convert_chameleon_to_crello(
            document, self.font_manager, str(ASSETS_DIR)
        )
        self.assertEqual(conversion_warnings, [])

        # These are independent, observable adapter values: a changed z-sort,
        # end-exclusive run, spacing, explicit line map, or geometry fails here.
        self.assertEqual(converted["canvas_width"], 96.0)
        self.assertEqual(converted["canvas_height"], 64.0)
        self.assertEqual(converted["length"], 2)
        self.assertEqual(converted["left"], [60.0, 4.0])
        self.assertEqual(converted["top"], [8.0, 4.0])
        self.assertEqual(converted["width"], [28.0, 52.0])
        self.assertEqual(converted["height"], [48.0, 38.0])
        self.assertEqual(converted["text"], ["", "A B\nCD"])
        self.assertEqual(converted["text_line"], [[], [0, 0, 0, 1, 1, 1]])
        self.assertEqual(
            converted["font_bold"], [[], [True, False, False, False, False, False]]
        )
        self.assertEqual(converted["letter_spacing"], [0.0, 1.5])

        reference = _reference_payload()
        renderer = CrelloV5Renderer.__new__(CrelloV5Renderer)
        renderer.features = {key: None for key in reference}
        renderer.font_manager = self.font_manager
        reference_png = renderer.render(reference, max_size=2048, format="png")

        # Hash equality compares the real project adapter's output to a
        # separately assembled call into the pinned native Skia renderer.
        self.assertEqual(
            hashlib.sha256(actual_png).hexdigest(),
            hashlib.sha256(reference_png).hexdigest(),
        )
        self.assertEqual(Image.open(io.BytesIO(actual_png)).size, (96, 64))
        self.assertEqual(Image.open(io.BytesIO(reference_png)).size, (96, 64))


if __name__ == "__main__":
    unittest.main()
