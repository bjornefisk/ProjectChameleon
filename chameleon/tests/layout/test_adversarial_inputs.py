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
        convert_chameleon_to_crello,
        render_design_to_png,
    )
except ModuleNotFoundError:
    from chameleon.engine.contract import validate_response
    from chameleon.engine.layout.roles import infer_roles
    from chameleon.engine.resize import resize
    from chameleon.renderer.converter.brand_fonts import load_brand_font_manager
    from chameleon.renderer.converter.convert import (
        convert_chameleon_to_crello,
        render_design_to_png,
    )

ROOT = PROJECT_ROOT / "chameleon"
ASSETS = ROOT / "brand_kit" / "assets"
FONTS = ROOT / "brand_kit" / "fonts"
LEVEL3_INPUT = ROOT / "input" / "chameleon_sample_level3_advanced.json"


class AdversarialInputTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.font_manager = load_brand_font_manager(str(FONTS))

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
