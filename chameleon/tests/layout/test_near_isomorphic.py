import copy
import json
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from engine.errors import InfeasibleLayoutError, InfeasibleReasonCode
    from engine.geometry.ratios import reduced_ratio
    from engine.layout.near_isomorphic import solve_near_isomorphic
except ModuleNotFoundError:
    from chameleon.engine.errors import InfeasibleLayoutError, InfeasibleReasonCode
    from chameleon.engine.geometry.ratios import reduced_ratio
    from chameleon.engine.layout.near_isomorphic import solve_near_isomorphic
try:
    from chameleon.renderer.converter.brand_fonts import load_brand_font_manager
except ModuleNotFoundError:
    from renderer.converter.brand_fonts import load_brand_font_manager


ROOT = Path(__file__).resolve().parents[2]
FONTS = ROOT / "brand_kit" / "fonts"


def text_element(**overrides):
    element = {
        "id": "headline",
        "type": "text",
        "x": 20,
        "y": 20,
        "width": 160,
        "height": 50,
        "content": "Chase the Light",
        "font_family": "Solstice Sans",
        "font_size": 20,
        "font_weight": "regular",
        "color": "rgba(0,0,0,1)",
    }
    element.update(overrides)
    return element


class NearIsomorphicTests(unittest.TestCase):
    def test_warmup_background_is_classified_and_filled(self):
        task = json.loads(
            (ROOT / "input" / "chameleon_sample_level1_warmup.json").read_text()
        )
        response = solve_near_isomorphic(task["source"], task["target_canvas"])
        self.assertEqual(response["canvas"], task["target_canvas"])
        self.assertEqual(response["elements"][0]["x"], 0)
        self.assertEqual(response["elements"][0]["y"], 0)
        self.assertEqual(response["elements"][0]["width"], 1080)
        self.assertEqual(response["elements"][0]["height"], 1350)

    def test_same_canvas_grouped_background_preserves_rigid_cover(self):
        source = {
            "canvas": {"width": 100, "height": 100},
            "elements": [
                {
                    "id": "grouped-background",
                    "type": "image",
                    "x": 0,
                    "y": 0,
                    "width": 100,
                    "height": 100,
                    "asset_id": "dynamic-background.png",
                    "fit": "cover",
                    "group_id": "background-unit",
                },
                {
                    "id": "background-label",
                    "type": "shape",
                    "x": 10,
                    "y": 10,
                    "width": 20,
                    "height": 20,
                    "shape_type": "rectangle",
                    "fill_color": "rgba(0,0,0,1)",
                    "group_id": "background-unit",
                },
            ],
        }
        response = solve_near_isomorphic(source, source["canvas"])
        self.assertEqual(
            response["elements"][0]["x"],
            0,
        )
        self.assertEqual(response["elements"][0]["y"], 0)
        self.assertEqual(response["elements"][0]["width"], 100)
        self.assertEqual(response["elements"][0]["height"], 100)

    def test_aspect_ratio_grouped_background_scales_rigidly_to_cover(self):
        source = {
            "canvas": {"width": 100, "height": 100},
            "elements": [
                {
                    "id": "grouped-background",
                    "type": "image",
                    "x": 0,
                    "y": 0,
                    "width": 100,
                    "height": 100,
                    "asset_id": "dynamic-background.png",
                    "fit": "cover",
                    "group_id": "background-unit",
                },
                {
                    "id": "background-label",
                    "type": "shape",
                    "x": 10,
                    "y": 10,
                    "width": 20,
                    "height": 20,
                    "shape_type": "rectangle",
                    "fill_color": "rgba(0,0,0,1)",
                    "group_id": "background-unit",
                },
            ],
        }
        response = solve_near_isomorphic(source, {"width": 100, "height": 150})
        background, label = response["elements"]
        self.assertEqual((background["x"], background["y"], background["width"], background["height"]), (-15, 0, 150, 150))
        self.assertEqual((label["x"], label["y"], label["width"], label["height"]), (0, 15, 30, 30))

    def test_grouped_background_fails_closed_when_sibling_cannot_fit_cover(self):
        source = {
            "canvas": {"width": 100, "height": 100},
            "elements": [
                {
                    "id": "grouped-background",
                    "type": "image",
                    "x": 0,
                    "y": 0,
                    "width": 100,
                    "height": 100,
                    "asset_id": "dynamic-background.png",
                    "fit": "cover",
                    "group_id": "background-unit",
                },
                {
                    "id": "background-sibling",
                    "type": "shape",
                    "x": 0,
                    "y": 0,
                    "width": 100,
                    "height": 100,
                    "shape_type": "rectangle",
                    "fill_color": "rgba(0,0,0,1)",
                    "group_id": "background-unit",
                },
            ],
        }
        with self.assertRaises(InfeasibleLayoutError) as raised:
            solve_near_isomorphic(source, {"width": 100, "height": 150})
        self.assertEqual(raised.exception.reason_code, InfeasibleReasonCode.NO_HARD_VALID_CANDIDATE)

    def test_foreground_image_uses_dynamic_asset_and_ratio_lattice(self):
        source = {
            "canvas": {"width": 200, "height": 100},
            "elements": [
                {
                    "id": "asset-with-a-generated-name",
                    "type": "image",
                    "x": 40,
                    "y": 20,
                    "width": 100,
                    "height": 50,
                    "asset_id": "not-a-hardcoded-sample-name.png",
                    "fit": "contain",
                }
            ],
        }
        response = solve_near_isomorphic(source, {"width": 180, "height": 120})
        element = response["elements"][0]
        self.assertEqual(reduced_ratio(element["width"], element["height"]), (2, 1))
        self.assertGreater(element["width"], 0)
        self.assertGreater(element["height"], 0)

    def test_source_is_unchanged_and_fields_are_preserved(self):
        source = {
            "canvas": {"width": 100, "height": 100},
            "elements": [
                {
                    "id": "shape",
                    "type": "shape",
                    "x": 10,
                    "y": 10,
                    "width": 20,
                    "height": 20,
                    "shape_type": "rectangle",
                    "fill_color": "rgba(1,2,3,1)",
                    "_extension": {"keep": True},
                }
            ],
        }
        before = copy.deepcopy(source)
        response = solve_near_isomorphic(source, {"width": 120, "height": 80})
        self.assertEqual(source, before)
        self.assertEqual(response["elements"][0]["_extension"], {"keep": True})
        self.assertEqual(response["elements"][0]["id"], "shape")
        for field in ("x", "y", "width", "height"):
            self.assertIs(type(response["elements"][0][field]), int)

    def test_text_measurement_selects_smaller_fitting_integer(self):
        source = {
            "canvas": {"width": 200, "height": 100},
            "elements": [text_element(x=10, y=10, width=45, height=40, content="WWWW", font_size=20, text_align="center")],
        }
        manager = load_brand_font_manager(str(FONTS))
        response = solve_near_isomorphic(source, source["canvas"], font_manager=manager)
        self.assertGreaterEqual(response["elements"][0]["font_size"], 1)
        self.assertLess(response["elements"][0]["font_size"], source["elements"][0]["font_size"])

    def test_impossible_text_fails_closed_with_typed_reason(self):
        source = {
            "canvas": {"width": 100, "height": 100},
            "elements": [text_element(width=1, height=100, content="WWWWWWWW")],
        }
        manager = load_brand_font_manager(str(FONTS))
        with self.assertRaises(InfeasibleLayoutError) as raised:
            solve_near_isomorphic(source, source["canvas"], font_manager=manager)
        self.assertEqual(raised.exception.reason_code, InfeasibleReasonCode.NO_HARD_VALID_CANDIDATE)


if __name__ == "__main__":
    unittest.main()
