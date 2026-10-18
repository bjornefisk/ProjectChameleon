import copy
import json
import subprocess
import sys
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

from PIL import UnidentifiedImageError


PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from engine.contract import validate_response
    from engine.errors import InfeasibleLayoutError, InfeasibleReasonCode
    from engine.geometry.ratios import reduced_ratio
    from engine.layout.near_isomorphic import solve_near_isomorphic
except ModuleNotFoundError:
    from chameleon.engine.contract import validate_response
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

    def test_source_bleed_follows_target_edge_when_canvas_widens(self):
        source = {
            "canvas": {"width": 100, "height": 100},
            "elements": [
                {
                    "id": "bleed",
                    "type": "shape",
                    "x": -10,
                    "y": 10,
                    "width": 20,
                    "height": 20,
                    "opacity": Decimal("0.5"),
                    "shape_type": "rectangle",
                    "fill_color": "rgba(1,2,3,1)",
                }
            ],
        }

        response = solve_near_isomorphic(source, {"width": 200, "height": 100})

        validate_response(source, {"width": 200, "height": 100}, response)
        self.assertEqual(response["elements"][0]["x"], -10)

    def test_group_can_choose_smaller_integral_scale_when_global_scale_does_not_fit(self):
        source = {
            "canvas": {"width": 100, "height": 100},
            "elements": [
                {
                    "id": "left",
                    "type": "shape",
                    "x": 0,
                    "y": 0,
                    "width": 2,
                    "height": 2,
                    "shape_type": "rectangle",
                    "fill_color": "rgba(1,2,3,1)",
                    "group_id": "unit",
                },
                {
                    "id": "right",
                    "type": "shape",
                    "x": 88,
                    "y": 0,
                    "width": 2,
                    "height": 2,
                    "shape_type": "rectangle",
                    "fill_color": "rgba(1,2,3,1)",
                    "group_id": "unit",
                },
            ],
        }

        response = solve_near_isomorphic(source, {"width": 80, "height": 80})

        validate_response(source, {"width": 80, "height": 80}, response)
        self.assertEqual(response["elements"][0]["width"], 1)
        self.assertEqual(response["elements"][1]["width"], 1)

    def test_grouped_elements_prefer_source_transform_before_centering(self):
        task = json.loads(
            (ROOT / "input" / "chameleon_sample_level2_core.json").read_text(),
            parse_int=int,
            parse_float=Decimal,
        )

        response = solve_near_isomorphic(task["source"], task["target_canvas"])

        validate_response(task["source"], task["target_canvas"], response)

    def test_small_source_font_is_not_enlarged_by_target_scale(self):
        source = {
            "canvas": {"width": 100, "height": 100},
            "elements": [
                text_element(
                    x=10,
                    y=10,
                    width=80,
                    height=30,
                    content="A",
                    font_size=5,
                    text_align="center",
                )
            ],
        }
        manager = load_brand_font_manager(str(FONTS))

        response = solve_near_isomorphic(
            source,
            {"width": 200, "height": 200},
            font_manager=manager,
        )

        self.assertLessEqual(response["elements"][0]["font_size"], 5)

    def test_renderer_failure_is_checked_before_candidate_return(self):
        source = {
            "canvas": {"width": 100, "height": 100},
            "elements": [
                {
                    "id": "corrupt",
                    "type": "image",
                    "x": 10,
                    "y": 10,
                    "width": 20,
                    "height": 20,
                    "asset_id": "corrupt.png",
                    "fit": "contain",
                }
            ],
        }

        with tempfile.TemporaryDirectory() as directory:
            corrupt_asset = Path(directory) / "corrupt.png"
            corrupt_asset.write_text("not a PNG", encoding="utf-8")
            with self.assertRaises(UnidentifiedImageError):
                solve_near_isomorphic(
                    source,
                    source["canvas"],
                    assets_dir=directory,
                    fonts_dir=str(FONTS),
                )


    def test_half_even_font_size_ceiling_is_preserved(self):
        source = {
            "canvas": {"width": 200, "height": 100},
            "elements": [
                text_element(
                    x=10,
                    y=10,
                    width=160,
                    height=40,
                    content="A",
                    font_size=Decimal("10.6"),
                    text_align="center",
                )
            ],
        }
        manager = load_brand_font_manager(str(FONTS))

        response = solve_near_isomorphic(
            source,
            source["canvas"],
            font_manager=manager,
        )

        self.assertEqual(response["elements"][0]["font_size"], 11)

    def test_renderer_gate_uses_supplied_font_manager(self):
        source = {
            "canvas": {"width": 200, "height": 100},
            "elements": [
                text_element(
                    x=10,
                    y=10,
                    width=160,
                    height=40,
                    content="A",
                    font_family="Custom Family",
                    font_size=12,
                    text_align="center",
                )
            ],
        }
        with tempfile.TemporaryDirectory() as directory:
            custom_fonts = Path(directory) / "fonts"
            custom_fonts.mkdir()
            (
                custom_fonts / "CustomFamily-Regular.ttf"
            ).write_bytes((FONTS / "SolsticeSans-Regular.ttf").read_bytes())
            manager = load_brand_font_manager(str(custom_fonts))

            response = solve_near_isomorphic(
                source,
                source["canvas"],
                font_manager=manager,
                fonts_dir=str(FONTS),
            )

        self.assertEqual(response["elements"][0]["font_family"], "Custom Family")

    def test_renderer_warnings_are_logged(self):
        source = {
            "canvas": {"width": 100, "height": 100},
            "elements": [
                {
                    "id": "missing-image",
                    "type": "image",
                    "x": 10,
                    "y": 10,
                    "width": 20,
                    "height": 20,
                    "asset_id": "missing.png",
                    "fit": "contain",
                }
            ],
        }
        with tempfile.TemporaryDirectory() as directory:
            with self.assertLogs(level="WARNING") as captured:
                solve_near_isomorphic(
                    source,
                    source["canvas"],
                    assets_dir=directory,
                )

        self.assertTrue(
            any("Missing asset 'missing.png'" in message for message in captured.output)
        )


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


    def test_non_image_geometry_is_not_forced_to_image_ratio_lattice(self):
        source = {
            "canvas": {"width": 6, "height": 4},
            "elements": [
                {
                    "id": "shape",
                    "type": "shape",
                    "x": 0,
                    "y": 0,
                    "width": 3,
                    "height": 4,
                    "shape_type": "rectangle",
                    "fill_color": "rgba(0,0,0,1)",
                }
            ],
        }

        response = solve_near_isomorphic(source, {"width": 2, "height": 1})

        validate_response(source, {"width": 2, "height": 1}, response)
        self.assertEqual(
            (response["elements"][0]["x"], response["elements"][0]["y"]),
            (0, 0),
        )
        self.assertEqual(
            (response["elements"][0]["width"], response["elements"][0]["height"]),
            (1, 1),
        )

    def test_renderer_dependencies_are_lazy_until_candidate_evaluation(self):
        script = """
import builtins

real_import = builtins.__import__

def block_renderer_imports(name, *args, **kwargs):
    if name.split(".", 1)[0] in {"cr_renderer", "skia"}:
        raise ModuleNotFoundError(name=name)
    return real_import(name, *args, **kwargs)

builtins.__import__ = block_renderer_imports
import engine.resize
"""
        result = subprocess.run(
            [sys.executable, "-c", script],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

if __name__ == "__main__":
    unittest.main()
