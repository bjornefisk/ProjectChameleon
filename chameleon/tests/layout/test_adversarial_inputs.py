import copy
import json
import sys
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from engine.contract import validate_response
    from engine.layout.roles import infer_roles
    from engine.resize import resize
    from renderer.converter.brand_fonts import load_brand_font_manager
    from renderer.converter.convert import (
        _positioned_glyph_metrics,
        _prepare_text,
        convert_chameleon_to_crello,
        render_design_to_png,
    )
except ModuleNotFoundError:
    from chameleon.engine.contract import validate_response
    from chameleon.engine.layout.roles import infer_roles
    from chameleon.engine.resize import resize
    from chameleon.renderer.converter.brand_fonts import load_brand_font_manager
    from chameleon.renderer.converter.convert import (
        _positioned_glyph_metrics,
        _prepare_text,
        convert_chameleon_to_crello,
        render_design_to_png,
    )

ROOT = PROJECT_ROOT / "chameleon"
ASSETS = ROOT / "brand_kit" / "assets"
FONTS = ROOT / "brand_kit" / "fonts"
LEVEL3_INPUT = ROOT / "input" / "chameleon_sample_level3_advanced.json"
LEVEL1_INPUT = ROOT / "input" / "chameleon_sample_level1_warmup.json"
EXTREME_TARGETS = (
    {"width": 320, "height": 50},
    {"width": 120, "height": 700},
    {"width": 3840, "height": 2160},
    {"width": 100, "height": 100},
)


class AdversarialInputTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.font_manager = load_brand_font_manager(str(FONTS))

    def test_extreme_targets_are_deterministic_and_hard_valid(self):
        task = json.loads(LEVEL1_INPUT.read_text(encoding="utf-8"), parse_float=Decimal)
        source = task["source"]
        original_source = copy.deepcopy(source)

        for target in EXTREME_TARGETS:
            with self.subTest(target=target):
                first = resize(source, target)
                second = resize(source, target)

                validate_response(source, target, first, fonts_dir=FONTS)
                validate_response(source, target, second, fonts_dir=FONTS)
                self.assertEqual(first, second)
                self.assertEqual(first["canvas"], target)
                self.assertEqual(source, original_source)

                source_ids = [element["id"] for element in source["elements"]]
                self.assertEqual(
                    [element["id"] for element in first["elements"]], source_ids
                )



    def test_arbitrary_element_and_group_ids_preserve_roles_and_resize(self):
        task = json.loads(LEVEL3_INPUT.read_text(encoding="utf-8"), parse_float=Decimal)
        original_source = task["source"]
        source = copy.deepcopy(original_source)
        source_groups = {}
        for index, element in enumerate(source["elements"]):
            element["id"] = f"el_{index}"
            group_id = element.get("group_id")
            if group_id is not None:
                source_groups.setdefault(group_id, f"grp_{len(source_groups)}")
                element["group_id"] = source_groups[group_id]

        original_roles = infer_roles(original_source)
        remapped_roles = infer_roles(source)
        self.assertEqual(
            [assignment.role for assignment in remapped_roles.assignments],
            [assignment.role for assignment in original_roles.assignments],
        )
        self.assertEqual(remapped_roles.background_index, original_roles.background_index)
        for left in range(len(source["elements"])):
            for right in range(left + 1, len(source["elements"])):
                self.assertEqual(
                    remapped_roles.relationships.for_pair(left, right).source_overlap,
                    original_roles.relationships.for_pair(left, right).source_overlap,
                )
                self.assertEqual(
                    remapped_roles.relationships.for_pair(left, right).same_group,
                    original_roles.relationships.for_pair(left, right).same_group,
                )

        before = copy.deepcopy(source)
        target = {"width": 300, "height": 250}
        response = resize(source, target)
        validate_response(source, target, response, fonts_dir=FONTS)

        expected_ids = [f"el_{index}" for index in range(len(source["elements"]))]
        self.assertEqual([element["id"] for element in source["elements"]], expected_ids)
        self.assertEqual([element["id"] for element in response["elements"]], expected_ids)
        self.assertEqual(response["canvas"], target)
        self.assertEqual(source, before)
        self.assertEqual(
            [element.get("group_id") for element in response["elements"]],
            [element.get("group_id") for element in source["elements"]],
        )

    def test_long_headline_wraps_and_resizes_without_changing_content(self):
        headline = (
            "A remarkably bright botanical discovery brings a little more golden "
            "hour to every gathering, with sparkling infusions crafted for the "
            "moments that deserve to last and the stories worth sharing "
        ) * 2
        headline = headline.strip()
        self.assertGreaterEqual(len(headline), 150)
        source = {
            "canvas": {"width": 1200, "height": 900},
            "elements": [
                {
                    "id": "headline-source",
                    "type": "text",
                    "x": 100,
                    "y": 100,
                    "width": 1000,
                    "height": 700,
                    "content": headline,
                    "font_family": "Solstice Sans",
                    "font_size": 64,
                    "font_weight": "bold",
                    "color": "rgba(255,255,255,1)",
                    "text_align": "center",
                }
            ],
        }
        before = copy.deepcopy(source)
        target = {"width": 600, "height": 450}
        response = resize(source, target)
        validate_response(source, target, response, fonts_dir=FONTS)

        text = response["elements"][0]
        self.assertEqual(text["content"], headline)
        self.assertLess(text["font_size"], source["elements"][0]["font_size"])
        self.assertEqual(source, before)

        converted, _warnings = convert_chameleon_to_crello(
            response, self.font_manager, str(ASSETS)
        )
        rendered_text = converted["text"][0]
        self.assertIn("\n", rendered_text)
        self.assertEqual(" ".join(rendered_text.split()), headline)
        with tempfile.TemporaryDirectory() as directory:
            png_path = Path(directory) / "long-headline.png"
            render_design_to_png(
                response,
                ASSETS,
                png_path,
                fonts_dir=FONTS,
                max_size=2048,
                font_manager=self.font_manager,
            )
            with Image.open(png_path) as image:
                image.load()
                self.assertEqual(image.size, (target["width"], target["height"]))


    def test_left_aligned_negative_bearing_glyphs_fit_after_transient_inset(self):
        target = {"width": 240, "height": 240}
        checked_negative_bearings = 0
        for glyph in ("T", "V", "W", '"', "‘", "j", "f"):
            source = {
                "canvas": dict(target),
                "elements": [
                    {
                        "id": "leading-glyph",
                        "type": "text",
                        "x": 70,
                        "y": 65,
                        "width": 64,
                        "height": 100,
                        "color": "rgba(0,0,0,1)",
                        "content": glyph,
                        "font_family": "Solstice Sans",
                        "font_size": 64,
                        "text_align": "left",
                        "rotation": 27,
                    }
                ],
            }
            before = copy.deepcopy(source)
            element = source["elements"][0]
            prepared = _prepare_text(element, self.font_manager)
            (
                horizontal_inset,
                vertical_inset,
                minimum_left,
                maximum_right,
                minimum_top,
                maximum_bottom,
            ) = _positioned_glyph_metrics(
                prepared.wrapped,
                prepared.line_indices,
                prepared.line_count,
                element,
                self.font_manager,
                prepared.family,
                prepared.size,
                prepared.line_height,
                prepared.letter_spacing,
                prepared.colors,
                prepared.bold_flags,
                prepared.italic_flags,
            )
            if minimum_left is None or minimum_left >= 0:
                continue

            checked_negative_bearings += 1
            response = {
                "canvas": dict(target),
                "elements": copy.deepcopy(source["elements"]),
            }
            validate_response(source, target, response, fonts_dir=FONTS)
            self.assertEqual(response["elements"], source["elements"])
            self.assertEqual(source, before)

            converted, _warnings = convert_chameleon_to_crello(
                response, self.font_manager, str(ASSETS)
            )
            self.assertAlmostEqual(
                converted["left"][0] + converted["width"][0] / 2,
                float(element["x"]) + element["width"] / 2,
            )
            self.assertAlmostEqual(
                converted["top"][0] + converted["height"][0] / 2,
                float(element["y"]) + element["height"] / 2,
            )
            self.assertAlmostEqual(converted["width"][0], 64 - 2 * horizontal_inset)
            self.assertAlmostEqual(converted["height"][0], 100 - 2 * vertical_inset)
            self.assertGreater(horizontal_inset, 0)
            self.assertGreaterEqual(minimum_left + horizontal_inset, 0)
            self.assertLessEqual(
                maximum_right + horizontal_inset,
                element["width"] - horizontal_inset,
            )
            self.assertGreaterEqual(minimum_top + vertical_inset, 0)
            self.assertLessEqual(
                maximum_bottom + vertical_inset,
                element["height"] - vertical_inset,
            )

        self.assertGreater(checked_negative_bearings, 0)
    def test_missing_asset_is_preserved_and_renders_diagnostic_placeholder(self):
        source = {
            "canvas": {"width": 200, "height": 120},
            "elements": [
                {
                    "id": "el_missing_asset",
                    "type": "image",
                    "x": 10,
                    "y": 10,
                    "width": 100,
                    "height": 100,
                    "z_index": 0,
                    "asset_id": "absent_hero.png",
                    "fit": "contain",
                },
                {
                    "id": "el_chip",
                    "type": "shape",
                    "x": 130,
                    "y": 20,
                    "width": 50,
                    "height": 30,
                    "z_index": 1,
                    "shape_type": "rectangle",
                    "fill_color": "rgba(200,30,30,1)",
                },
            ],
        }
        before = copy.deepcopy(source)
        target = {"width": 200, "height": 120}
        response = resize(source, target)
        validate_response(source, target, response, fonts_dir=FONTS)

        self.assertEqual(source, before)
        self.assertEqual(
            [element["id"] for element in response["elements"]],
            ["el_missing_asset", "el_chip"],
        )
        self.assertEqual(response["elements"][0]["asset_id"], "absent_hero.png")
        with tempfile.TemporaryDirectory() as directory:
            png_path = Path(directory) / "missing-asset.png"
            warnings = render_design_to_png(
                response,
                ASSETS,
                png_path,
                fonts_dir=FONTS,
                max_size=2048,
                font_manager=self.font_manager,
            )
            self.assertEqual(
                warnings,
                [
                    "Missing asset 'absent_hero.png' for element "
                    "'el_missing_asset' - rendered a placeholder."
                ],
            )
            with Image.open(png_path) as image:
                image.load()
                self.assertEqual(image.size, (target["width"], target["height"]))
                self.assertEqual(image.getpixel((20, 20)), (214, 214, 214, 255))


if __name__ == "__main__":
    unittest.main()
