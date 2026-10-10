import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).parents[3]
sys.path.insert(0, str(PROJECT_ROOT))

from chameleon.renderer.converter.brand_fonts import load_brand_font_manager
from chameleon.renderer.converter.convert import convert_chameleon_to_crello
from chameleon.renderer.converter.shapes import render_shape
from chameleon.renderer.converter.wrap import TextOverflowError, UnbreakableTextError, wrap_text


ROOT = Path(__file__).parents[2]
FONT_DIR = ROOT / "brand_kit" / "fonts"


class RendererConformanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.font_manager = load_brand_font_manager(str(FONT_DIR))

    def convert_text(self, **overrides):
        element = {
            "id": "text",
            "type": "text",
            "x": 0,
            "y": 0,
            "width": 400,
            "height": 100,
            "content": "ABCD",
            "font_family": "Solstice Sans",
            "font_size": 24,
            "color": "rgba(255,255,255,1)",
        }
        element.update(overrides)
        document = {"canvas": {"width": 400, "height": 100}, "elements": [element]}
        return convert_chameleon_to_crello(document, self.font_manager)[0]

    def test_style_runs_are_end_exclusive_and_later_properties_win(self):
        red = "rgba(255,0,0,1)"
        blue = "rgba(0,0,255,1)"
        output = self.convert_text(
            style_runs=[
                {"start": 0, "end": 3, "color": red, "font_weight": "bold"},
                {"start": 1, "end": 2, "color": blue, "font_style": "italic"},
            ]
        )

        self.assertEqual(output["text_color"][0], [red, blue, red, "rgba(255,255,255,1)"])
        self.assertEqual(output["font_bold"][0], [True, True, True, False])
        self.assertEqual(output["font_italic"][0], [False, True, False, False])

    def test_style_run_typeface_width_changes_wrapping(self):
        plain = self.convert_text(content="WW WW", width=101, height=100)
        styled = self.convert_text(
            content="WW WW",
            width=101,
            height=100,
            style_runs=[{"start": 0, "end": 2, "font_weight": "bold"}],
        )

        self.assertEqual(plain["text"][0], "WW WW")
        self.assertEqual(styled["text"][0], "WW\nWW")

    def test_letter_spacing_participates_in_greedy_wrapping(self):
        self.assertEqual(
            wrap_text("A B", [4.0, 0.0, 4.0], 5.0, letter_spacing=2.0),
            "A\nB",
        )

    def test_unbreakable_grapheme_cluster_is_not_split(self):
        text = "👩\u200d🔬 B"
        widths = [4.0, 0.0, 4.0, 0.0, 4.0]
        with self.assertRaises(UnbreakableTextError):
            wrap_text(text, widths, 7.0)

        wrapped = wrap_text(text, widths, 8.0)
        self.assertEqual(wrapped, "👩\u200d🔬\nB")
        self.assertEqual(len(wrapped), len(text))
        self.assertNotIn("\n", wrapped[:3])

    def test_explicit_newlines_and_max_lines_are_hard_limits(self):
        accepted = self.convert_text(content="A\nB", max_lines=2, height=60)
        self.assertEqual(accepted["text_line"][0], [0, 1, 1])

        with self.assertRaises(TextOverflowError):
            self.convert_text(content="A\nB", max_lines=1)

        with self.assertRaises(TextOverflowError):
            self.convert_text(content="A\nB", height=40)

        with self.assertRaises(TextOverflowError):
            self.convert_text(content="\n", max_lines=1)

    def test_rectangle_and_ellipse_strokes_stay_inside_element_box(self):
        for shape_type in ("rectangle", "ellipse"):
            image = render_shape(
                {
                    "type": "shape",
                    "width": 12,
                    "height": 10,
                    "shape_type": shape_type,
                    "fill_color": "rgba(1,2,3,1)",
                    "stroke_color": "rgba(255,0,0,1)",
                    "stroke_width": 20,
                }
            )
            self.assertEqual(image.size, (12, 10))
            red_pixels = [
                (x, y)
                for y in range(image.height)
                for x in range(image.width)
                if image.getpixel((x, y))[:3] == (255, 0, 0)
            ]
            self.assertTrue(red_pixels)
            self.assertTrue(all(0 <= x < 12 and 0 <= y < 10 for x, y in red_pixels))

    def test_transparent_fill_preserves_declared_stroke(self):
        image = render_shape(
            {
                "type": "shape",
                "width": 10,
                "height": 10,
                "shape_type": "rectangle",
                "fill_color": "rgba(1,2,3,0)",
                "stroke_color": "rgba(255,0,0,1)",
                "stroke_width": 2,
            }
        )

        self.assertEqual(image.getpixel((5, 5))[3], 0)
        self.assertEqual(image.getpixel((0, 0))[:3], (255, 0, 0))


if __name__ == "__main__":
    unittest.main()
