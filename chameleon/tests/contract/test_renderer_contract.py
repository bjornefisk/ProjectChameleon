import math
import unittest
from pathlib import Path

from engine.contract import validate_response
from engine.errors import InfeasibleLayoutError, InfeasibleReasonCode
from renderer.converter.brand_fonts import load_brand_font_manager
from renderer.converter.wrap import char_widths


FONTS = Path(__file__).parents[2] / "brand_kit" / "fonts"
FAMILY = "Solstice Sans"


def text_document(
    *,
    content: str,
    width: int = 200,
    height: int = 100,
    font_size: int = 20,
    **overrides,
):
    element = {
        "id": "copy",
        "type": "text",
        "x": 10,
        "y": 10,
        "width": width,
        "height": height,
        "content": content,
        "font_family": FAMILY,
        "font_size": font_size,
        "color": "rgba(255,255,255,1)",
    }
    element.update(overrides)
    return {
        "canvas": {"width": max(400, width + 30), "height": max(200, height + 30)},
        "elements": [element],
    }


class RendererAwareContractTests(unittest.TestCase):
    def assert_reason(self, document, expected):
        with self.assertRaises(InfeasibleLayoutError) as raised:
            validate_response(document, document["canvas"], document)
        self.assertEqual(raised.exception.reason_code, expected)
        self.assertTrue(raised.exception.details)

    def test_width_wrapping_and_unbreakable_segments_are_authoritative(self):
        document = text_document(content="SOLSTICE", width=1)
        self.assert_reason(document, InfeasibleReasonCode.TEXT_OVERFLOW)

    def test_unicode_mandatory_breaks_and_forced_empty_lines_are_authoritative(self):
        max_lines_document = text_document(content="A\u2028B", max_lines=1)
        self.assert_reason(max_lines_document, InfeasibleReasonCode.TEXT_OVERFLOW)

        height_document = text_document(
            content="A\u2028B",
            max_lines=2,
            height=20,
            font_size=20,
            line_height=1,
        )
        self.assert_reason(height_document, InfeasibleReasonCode.TEXT_OVERFLOW)

        empty_line_document = text_document(content="\u2028", max_lines=1)
        self.assert_reason(empty_line_document, InfeasibleReasonCode.TEXT_OVERFLOW)

    def test_effective_style_face_metrics_are_authoritative(self):
        manager = load_brand_font_manager(str(FONTS))
        content = "WW WW"
        regular_width = sum(
            char_widths(manager, FAMILY, "regular", "regular", 24, content)
        )
        bold_width = sum(char_widths(manager, FAMILY, "bold", "bold", 24, content))
        self.assertLess(regular_width, bold_width)
        width = math.floor((regular_width + bold_width) / 2)

        document = text_document(
            content=content,
            width=width,
            height=100,
            font_size=24,
            max_lines=1,
            style_runs=[{"start": 0, "end": len(content), "font_weight": "bold"}],
        )
        self.assert_reason(document, InfeasibleReasonCode.TEXT_OVERFLOW)

    def test_letter_spacing_is_authoritative(self):
        manager = load_brand_font_manager(str(FONTS))
        content = "SOLSTICESOLSTICE"
        natural_width = sum(
            char_widths(manager, FAMILY, "regular", "regular", 24, content)
        )
        width = math.ceil(natural_width) + 6

        fits = text_document(
            content=content,
            width=width,
            height=100,
            font_size=24,
            letter_spacing=0,
        )
        validate_response(fits, fits["canvas"], fits)

        overflows = text_document(
            content=content,
            width=width,
            height=100,
            font_size=24,
            letter_spacing=2,
        )
        self.assert_reason(overflows, InfeasibleReasonCode.TEXT_OVERFLOW)

    def test_alignment_and_positioned_glyph_bounds_are_authoritative(self):
        document = text_document(
            content="j",
            width=6,
            height=100,
            font_size=24,
            font_style="italic",
            text_align="center",
        )
        self.assert_reason(document, InfeasibleReasonCode.TEXT_OVERFLOW)

    def test_missing_effective_font_face_is_a_hard_runtime_failure(self):
        document = text_document(content="copy", font_family="Not Installed")
        self.assert_reason(document, InfeasibleReasonCode.RUNTIME_IO_FAILURE)


if __name__ == "__main__":
    unittest.main()
