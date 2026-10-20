"""Behavioral renderer evidence for issue #23 (F-07).

Each test measures rendered pixels (PIL sampling) or the authoritative
renderer-in-loop validator against an expectation derived from the contract,
ADR-008, or the v0.9 schema, so that a regression in the named behavior fails
the test.  Nothing here compares against hashes or copies adapter output.
"""

from __future__ import annotations

import io
import math
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from engine.contract import validate_renderer_response
    from engine.errors import InfeasibleLayoutError, InfeasibleReasonCode
    from engine.geometry.bounds import rotated_aabb
    from renderer.converter.brand_fonts import load_brand_font_manager
    from renderer.converter.convert import render_design_to_png
    from renderer.converter.wrap import char_widths
except ModuleNotFoundError:
    from chameleon.engine.contract import validate_renderer_response
    from chameleon.engine.errors import InfeasibleLayoutError, InfeasibleReasonCode
    from chameleon.engine.geometry.bounds import rotated_aabb
    from chameleon.renderer.converter.brand_fonts import load_brand_font_manager
    from chameleon.renderer.converter.convert import render_design_to_png
    from chameleon.renderer.converter.wrap import char_widths

ROOT = PROJECT_ROOT / "chameleon"
FONTS = ROOT / "brand_kit" / "fonts"
WHITE = (255, 255, 255)
RED, GREEN, BLUE = (255, 0, 0), (0, 255, 0), (0, 0, 255)
FAMILY = "Solstice Sans"


def _render(document: dict, assets_dir: Path, font_manager) -> Image.Image:
    with tempfile.TemporaryDirectory() as directory:
        output = Path(directory) / "render.png"
        render_design_to_png(
            document, assets_dir, output, fonts_dir=FONTS, max_size=2048, font_manager=font_manager
        )
        payload = output.read_bytes()
    with Image.open(io.BytesIO(payload)) as image:
        return image.convert("RGB")


def _ink(image: Image.Image) -> list[tuple[int, int]]:
    """Pixel coordinates of every non-white pixel (antialiased edges included)."""
    return [
        (index % image.width, index // image.width)
        for index, pixel in enumerate(image.getdata())
        if pixel != WHITE
    ]


def _bbox(points: list[tuple[int, int]]) -> tuple[int, int, int, int]:
    xs, ys = [x for x, _ in points], [y for _, y in points]
    return min(xs), min(ys), max(xs) + 1, max(ys) + 1


def _is_color(pixel: tuple[int, int, int], expected: tuple[int, int, int], tol: int = 40) -> bool:
    # The tolerance absorbs Lanczos ringing next to hard colour edges (<= ~18/255 observed).
    return all(abs(a - b) <= tol for a, b in zip(pixel, expected))


def _text_document(content, *, spacing=0, align="left", x=20, width=200, canvas=240) -> dict:
    return {
        "canvas": {"width": canvas, "height": 60},
        "elements": [
            {
                "id": "copy",
                "type": "text",
                "x": x,
                "y": 10,
                "width": width,
                "height": 40,
                "content": content,
                "font_family": FAMILY,
                "font_size": 24,
                "color": "rgba(0,0,0,1)",
                "text_align": align,
                "letter_spacing": spacing,
            }
        ],
    }


def _bar(width: int, height: int, rotation: int, canvas: int = 120) -> dict:
    center = canvas // 2
    return {
        "canvas": {"width": canvas, "height": canvas},
        "elements": [
            {
                "id": "bar",
                "type": "shape",
                "x": center - width // 2,
                "y": center - height // 2,
                "width": width,
                "height": height,
                "rotation": rotation,
                "shape_type": "rectangle",
                "fill_color": "rgba(0,0,0,1)",
            }
        ],
    }


class RendererBehaviorEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.font_manager = load_brand_font_manager(str(FONTS))

    # -- 1. fit semantics -------------------------------------------------

    def _render_bands(self, fit: str) -> Image.Image:
        # Opaque 64x32 source: x 0-15 red, 16-47 green, 48-63 blue.
        with tempfile.TemporaryDirectory() as directory:
            source = Image.new("RGB", (64, 32))
            for x in range(64):
                color = RED if x < 16 else GREEN if x < 48 else BLUE
                for y in range(32):
                    source.putpixel((x, y), color)
            source.save(Path(directory) / "bands.png")
            document = {
                "canvas": {"width": 40, "height": 40},
                "elements": [
                    {
                        "id": "img",
                        "type": "image",
                        "x": 0,
                        "y": 0,
                        "width": 40,
                        "height": 40,
                        "asset_id": "bands.png",
                        "fit": fit,
                    }
                ],
            }
            return _render(document, Path(directory), self.font_manager)

    def _assert_band_columns(self, image, rows):
        # Source column c maps to x = c * 40/64 for a full-width 40px render:
        # red [0,10), green [10,30), blue [30,40).  Samples keep >=2px clear of x=10/30.
        for y in rows:
            for xs, color in (((0, 4, 7), RED), ((12, 20, 27), GREEN), ((32, 36, 39), BLUE)):
                for x in xs:
                    self.assertTrue(
                        _is_color(image.getpixel((x, y)), color),
                        f"pixel ({x},{y})={image.getpixel((x, y))} expected ~{color}",
                    )

    def test_contain_letterboxes_isotropically_at_pixel_level(self):
        image = self._render_bands("contain")
        # Contract section 6: scale = min(40/64, 40/32) = 0.625 -> 40x20, centred -> rows 10..29.
        for y in (*range(0, 10), *range(30, 40)):
            for x in range(40):
                self.assertEqual(image.getpixel((x, y)), WHITE, f"letterbox pixel ({x},{y})")
        self.assertTrue(_is_color(image.getpixel((20, 10)), GREEN), "band must start at row 10")
        self.assertTrue(_is_color(image.getpixel((20, 29)), GREEN), "band must end at row 29")
        self._assert_band_columns(image, range(12, 28))

    def test_cover_center_crops_isotropically_at_pixel_level(self):
        image = self._render_bands("cover")
        # Contract section 6: scale = max(40/64, 40/32) = 1.25 -> 80x40, centre crop keeps
        # source columns 16..47 (all green); every pixel >=2px inside the box is green,
        # including all four corners.
        for y in range(2, 38):
            for x in range(2, 38):
                self.assertTrue(
                    _is_color(image.getpixel((x, y)), GREEN),
                    f"pixel ({x},{y})={image.getpixel((x, y))} expected green",
                )

    def test_fill_stretches_anisotropically_at_pixel_level(self):
        image = self._render_bands("fill")
        # Contract section 6: stretched to the element box -> bands span every row,
        # top and bottom included, with splits at x=10/30.
        self._assert_band_columns(image, range(40))

    # -- 2/3. letter spacing and alignment ---------------------------------

    def _ink_box(self, document: dict) -> tuple[int, int, int, int]:
        points = _ink(_render(document, ROOT / "brand_kit" / "assets", self.font_manager))
        self.assertGreater(len(points), 0)
        return _bbox(points)

    def test_letter_spacing_changes_ink_width_by_gap_count_times_spacing(self):
        content = "SOLSTICE"
        widths = {}
        for spacing in (-2, 0, 2):
            left, _top, right, _bottom = self._ink_box(_text_document(content, spacing=spacing))
            widths[spacing] = right - left
        # Contract section 6 / ADR-008 section 3: glyph advances include letter spacing,
        # applied between glyphs -> len-1 gaps (ASCII letters, one grapheme cluster each).
        delta = (len(content) - 1) * 2
        self.assertLess(widths[-2], widths[0])
        self.assertLess(widths[0], widths[2])
        # +/-2px: antialiased edge pixels can add or drop one column at each end.
        self.assertAlmostEqual(widths[0] - widths[-2], delta, delta=2)
        self.assertAlmostEqual(widths[2] - widths[0], delta, delta=2)
        # Absolute scale from the independent advance sum (side bearings account for <4px).
        natural = sum(char_widths(self.font_manager, FAMILY, "regular", "regular", 24, content))
        self.assertAlmostEqual(widths[0], natural, delta=4)

    def test_text_alignment_is_honored_inside_element_width(self):
        box_left, box_width = 20, 200
        box_right, box_center = box_left + box_width, box_left + box_width / 2
        boxes = {
            align: self._ink_box(_text_document("SOLSTICE", align=align, x=box_left, width=box_width))
            for align in ("left", "center", "right")
        }
        # Schema text_align + contract section 6: lines align within the element width.
        self.assertGreaterEqual(boxes["left"][0], box_left)
        self.assertLessEqual(boxes["left"][0], box_left + 4)
        self.assertAlmostEqual((boxes["center"][0] + boxes["center"][2]) / 2, box_center, delta=2)
        self.assertLessEqual(boxes["right"][2], box_right)
        self.assertGreaterEqual(boxes["right"][2], box_right - 4)

    # -- 4. hard validation honors letter spacing ---------------------------

    def _validate(self, word: str, width: int, spacing: int):
        document = _text_document(word, spacing=spacing, x=10, width=width, canvas=600)
        # letter_spacing is immutable in Stage 1: source and response share all geometry.
        return validate_renderer_response(
            document, document["canvas"], document, fonts_dir=FONTS, font_manager=self.font_manager
        )

    def _assert_width_overflow(self, word: str, width: int, spacing: int):
        with self.assertRaises(InfeasibleLayoutError) as caught:
            self._validate(word, width, spacing)
        self.assertEqual(caught.exception.reason_code, InfeasibleReasonCode.TEXT_OVERFLOW)
        # The failure must be a width failure (height 40 holds one 24*1.2 line box).
        self.assertIn("exceeds width", caught.exception.details["error"])

    def test_hard_validation_honors_negative_letter_spacing(self):
        word = "SOLSTICESOLSTICE"
        natural = sum(char_widths(self.font_manager, FAMILY, "regular", "regular", 24, word))
        width = int(natural) - 6
        self.assertGreaterEqual(natural - width, 6)
        # ADR-008 section 4: unbreakable segment wider than the box is a hard failure.
        self._assert_width_overflow(word, width, 0)
        # spacing -1 removes (16-1)*1 = 15px >= 8px of advance (>= 8px of slack remains).
        self.assertEqual(self._validate(word, width, -1), [])

    def test_hard_validation_honors_positive_letter_spacing(self):
        word = "SOLSTICESOLSTICE"
        natural = sum(char_widths(self.font_manager, FAMILY, "regular", "regular", 24, word))
        width = math.ceil(natural) + 6
        self.assertEqual(self._validate(word, width, 0), [])
        # spacing +2 adds (16-1)*2 = 30px, overflowing a 6..7px margin by >= 23px.
        self._assert_width_overflow(word, width, 2)

    # -- 5. rotation --------------------------------------------------------

    def test_rotation_matches_contract_aabb_and_pivots_about_center(self):
        for rotation in (30, -30, 45):
            with self.subTest(rotation=rotation):
                document = _bar(40, 12, rotation)
                element = document["elements"][0]
                image = _render(document, ROOT / "brand_kit" / "assets", self.font_manager)
                points = _ink(image)
                left, top, right, bottom = _bbox(points)
                # Contract section 7 envelope (Fractions -> floats for pixel comparison).
                min_x, min_y, max_x, max_y = (float(v) for v in rotated_aabb(element))
                # Sound: ink never exceeds the envelope by more than 1.5px.  The
                # margin absorbs antialiasing differences between raster backends
                # (observed ~0.3px of slack at 1px); a wrong pivot or angle misses
                # the envelope by many pixels, so the check still discriminates.
                self.assertGreaterEqual(left, min_x - 1.5)
                self.assertGreaterEqual(top, min_y - 1.5)
                self.assertLessEqual(right, max_x + 1.5)
                self.assertLessEqual(bottom, max_y + 1.5)
                # Tight: ink reaches within 2px of every envelope side.
                self.assertLessEqual(left, min_x + 2)
                self.assertLessEqual(top, min_y + 2)
                self.assertGreaterEqual(right, max_x - 2)
                self.assertGreaterEqual(bottom, max_y - 2)
                # Schema: rotation is about the element centre (60, 60).
                centroid_x = sum(x + 0.5 for x, _ in points) / len(points)
                centroid_y = sum(y + 0.5 for _, y in points) / len(points)
                self.assertAlmostEqual(centroid_x, 60, delta=1)
                self.assertAlmostEqual(centroid_y, 60, delta=1)

    def test_rotation_direction_is_clockwise(self):
        for rotation in (30, -30):
            with self.subTest(rotation=rotation):
                image = _render(_bar(60, 4, rotation), ROOT / "brand_kit" / "assets", self.font_manager)
                points = _ink(image)
                left_ys = [y for x, y in points if x < 60]
                right_ys = [y for x, y in points if x >= 60]
                difference = sum(right_ys) / len(right_ys) - sum(left_ys) / len(left_ys)
                # Schema: clockwise degrees; y grows downward, so +30 lowers the right end.
                # Half-bar centroids sit 15px from the centre along the axis:
                # dy = 2 * 15 * sin(rotation).
                expected = 2 * 15 * math.sin(math.radians(rotation))
                self.assertAlmostEqual(difference, expected, delta=2)


if __name__ == "__main__":
    unittest.main()
