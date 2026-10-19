import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).parents[3]
sys.path.insert(0, str(PROJECT_ROOT))

from chameleon.renderer.converter.brand_fonts import MissingFontError, load_brand_font_manager
from chameleon.renderer.converter.convert import convert_chameleon_to_crello
from chameleon.engine.errors import InfeasibleLayoutError, InfeasibleReasonCode
from chameleon.renderer.converter.shapes import render_shape
from chameleon.renderer.converter.wrap import (
    MalformedTextError,
    TextOverflowError,
    UnbreakableTextError,
    _grapheme_clusters,
    char_widths,
    wrap_text,
    wrap_text_with_line_map,
)


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
            "text_align": "center",
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

    def test_invalid_style_range_is_typed_input_failure(self):
        with self.assertRaises(MalformedTextError):
            self.convert_text(style_runs=[{"start": 4, "end": 5}])


    def test_missing_font_family_fails_instead_of_falling_back(self):
        with self.assertRaises(MissingFontError):
            self.convert_text(font_family="Not Installed")

    def test_missing_font_fails_for_newline_only_content(self):
        with self.assertRaises(MissingFontError):
            self.convert_text(content="\n", font_family="Not Installed")

    def test_missing_font_style_fails_instead_of_falling_back(self):
        with self.assertRaises(MissingFontError):
            self.convert_text(
                font_family="Solstice Serif",
                font_weight="bold",
                font_style="italic",
            )

    def test_empty_asset_id_emits_missing_asset_warning(self):
        document = {
            "canvas": {"width": 10, "height": 10},
            "elements": [
                {
                    "id": "image",
                    "type": "image",
                    "x": 0,
                    "y": 0,
                    "width": 10,
                    "height": 10,
                    "asset_id": "",
                }
            ],
        }
        _converted, warnings = convert_chameleon_to_crello(
            document, self.font_manager, str(ROOT / "brand_kit" / "assets")
        )

        self.assertEqual(
            warnings, ["Missing asset '' for element 'image' - rendered a placeholder."]
        )

    def test_style_run_typeface_width_changes_wrapping(self):
        candidates = (
            "WW WW",
            "MM MM",
            "AA AA",
            "SS SS",
            "OO OO",
            "CC CC",
            "HH HH",
            "nn nn",
            "ii ii",
            "BB BB",
        )
        metrics = []
        for content in candidates:
            regular_width = sum(
                char_widths(
                    self.font_manager,
                    "Solstice Sans",
                    "regular",
                    "regular",
                    24,
                    content,
                )
            )
            bold_width = sum(
                char_widths(
                    self.font_manager,
                    "Solstice Sans",
                    "bold",
                    "bold",
                    24,
                    content,
                )
            )
            metrics.append((content, regular_width, bold_width))

        content, regular_width, bold_width = max(
            metrics, key=lambda item: item[2] - item[1]
        )
        self.assertGreater(bold_width, regular_width)
        width = (regular_width + bold_width) / 2

        plain = self.convert_text(content=content, width=width, height=100)
        styled = self.convert_text(
            content=content,
            width=width,
            height=100,
            style_runs=[{"start": 0, "end": len(content), "font_weight": "bold"}],
        )

        self.assertEqual(plain["text"][0], content)
        self.assertNotEqual(styled["text"][0], content)
        self.assertEqual(styled["text"][0], content.replace(" ", "\n", 1))

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

    def test_regional_indicator_pairs_break_between_flags(self):
        text = "\U0001f1e6\U0001f1e7\U0001f1e8\U0001f1e9"
        wrapped, line_indices, line_count = wrap_text_with_line_map(
            text,
            [4.0] * len(text),
            8.0,
        )

        self.assertEqual(wrapped, text)
        self.assertEqual(line_indices, [0, 0, 1, 1])
        self.assertEqual(line_count, 2)

    def test_explicit_newlines_and_max_lines_are_hard_limits(self):
        accepted = self.convert_text(content="A\nB", max_lines=2, height=60)
        self.assertEqual(accepted["text_line"][0], [0, 1, 1])

        with self.assertRaises(TextOverflowError):
            self.convert_text(content="A\nB", max_lines=1)

        with self.assertRaises(TextOverflowError):
            self.convert_text(content="A\nB", height=40)

        with self.assertRaises(TextOverflowError):
            self.convert_text(content="\n", max_lines=1)

    def test_non_space_breaks_preserve_line_map_offsets(self):
        for text in ("ab-cd", "ab/cd"):
            wrapped, line_indices, line_count = wrap_text_with_line_map(
                text,
                [3.0] * len(text),
                9.0,
            )
            self.assertEqual(wrapped, text)
            self.assertEqual(line_indices, [0, 0, 0, 1, 1])
            self.assertEqual(line_count, 2)

        wrapped, line_indices, line_count = wrap_text_with_line_map(
            "甲乙丙",
            [4.0, 4.0, 4.0],
            8.0,
        )
        self.assertEqual(wrapped, "甲乙丙")
        self.assertEqual(line_indices, [0, 0, 1])
        self.assertEqual(line_count, 2)

    def test_mandatory_unicode_breaks_are_forced_and_counted(self):
        wrapped, line_indices, line_count = wrap_text_with_line_map(
            "A\u2028B\u2029C",
            [4.0] * 5,
            100.0,
        )
        self.assertEqual(wrapped, "A\nB\nC")
        self.assertEqual(line_indices, [0, 1, 1, 2, 2])
        self.assertEqual(line_count, 3)

        wrapped, line_indices, line_count = wrap_text_with_line_map(
            "A\r\nB",
            [4.0] * 4,
            100.0,
        )
        self.assertEqual(wrapped, "A\nB")
        self.assertEqual(line_indices, [0, 1, 1])
        self.assertEqual(line_count, 2)
        converted = self.convert_text(content="A\r\nB")
        self.assertEqual(converted["text"][0], "A\nB")
        self.assertEqual(converted["text_line"][0], [0, 1, 1])

    def test_renderer_requires_serialized_integer_font_size(self):
        with self.assertRaises(MalformedTextError):
            self.convert_text(font_size=24.9)

    def test_non_breaking_line_classes_are_not_wrappable(self):
        for text in ("A\u2007B", "A\u2060B"):
            with self.assertRaises(UnbreakableTextError):
                wrap_text(text, [4.0, 0.0, 4.0], 4.0)

    def test_grapheme_properties_cover_indic_and_emoji_tag_sequences(self):
        self.assertEqual(
            [(cluster.start, cluster.end) for cluster in _grapheme_clusters("क्a")],
            [(0, 2), (2, 3)],
        )
        self.assertEqual(
            [
                (cluster.start, cluster.end)
                for cluster in _grapheme_clusters(
                    "\U0001f3f4\U000e0067\U000e0062\U000e0065"
                    "\U000e006e\U000e0067\U000e007f"
                )
            ],
            [(0, 7)],
        )

        self.assertEqual(
            [
                (cluster.start, cluster.end)
                for cluster in _grapheme_clusters("\u1000\u1039\u1001")
            ],
            [(0, 3)],
        )

    def test_grapheme_zwj_and_prepend_properties_are_exact(self):
        self.assertEqual(
            [(cluster.start, cluster.end) for cluster in _grapheme_clusters("👩\u200d🔬")],
            [(0, 3)],
        )
        self.assertEqual(
            [(cluster.start, cluster.end) for cluster in _grapheme_clusters("\U000111C2A")],
            [(0, 2)],
        )
        self.assertEqual(
            [(cluster.start, cluster.end) for cluster in _grapheme_clusters("\U000110BEA")],
            [(0, 1), (1, 2)],
        )

    def test_positioned_italic_glyph_bounds_are_hard_limits(self):
        with self.assertRaises(TextOverflowError):
            self.convert_text(
                content="j",
                width=6,
                height=100,
                font_style="italic",
            )

    def test_fractional_positive_stroke_width_remains_visible(self):
        image = render_shape(
            {
                "type": "shape",
                "shape_type": "rectangle",
                "width": 12,
                "height": 10,
                "fill_color": "rgba(255,255,255,1)",
                "stroke_color": "rgba(255,0,0,1)",
                "stroke_width": 0.4,
            }
        )
        self.assertEqual(image.getpixel((0, 0))[:3], (255, 0, 0))

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
