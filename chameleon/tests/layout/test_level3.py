import copy
import hashlib
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
    from engine.errors import InfeasibleLayoutError, InfeasibleReasonCode
    from engine.geometry.bounds import positive_aabb_intersection, rotated_aabb
    from engine.geometry.ratios import preserves_source_ratio
    from engine.layout.horizontal_ribbon import generate_horizontal_ribbon_candidate
    from engine.resize import resize
    from renderer.converter.convert import render_design_to_png
except ModuleNotFoundError:
    from chameleon.engine.contract import validate_response
    from chameleon.engine.errors import InfeasibleLayoutError, InfeasibleReasonCode
    from chameleon.engine.geometry.bounds import positive_aabb_intersection, rotated_aabb
    from chameleon.engine.geometry.ratios import preserves_source_ratio
    from chameleon.engine.layout.horizontal_ribbon import generate_horizontal_ribbon_candidate
    from chameleon.engine.resize import resize
    from chameleon.renderer.converter.convert import render_design_to_png

ROOT = PROJECT_ROOT / "chameleon"
FIXTURE = ROOT / "input" / "chameleon_sample_level3_advanced.json"
ASSETS = ROOT / "brand_kit" / "assets"


class Level3IntegrationTests(unittest.TestCase):
    def _load_task(self):
        return json.loads(FIXTURE.read_text(encoding="utf-8"))
    def _horizontal_fixture(self):
        return (
            {
                "canvas": {"width": 1000, "height": 1000},
                "elements": [
                    {
                        "id": "bg",
                        "type": "image",
                        "x": 0,
                        "y": 0,
                        "width": 1000,
                        "height": 1000,
                        "asset_id": "solstice_bg_gradient.png",
                        "fit": "cover",
                    },
                    {
                        "id": "art",
                        "type": "image",
                        "x": 300,
                        "y": 200,
                        "width": 400,
                        "height": 200,
                        "asset_id": "solstice_logo_lockup.png",
                        "fit": "contain",
                    },
                    {
                        "id": "ribbon_bg",
                        "type": "shape",
                        "x": 300,
                        "y": 50,
                        "width": 300,
                        "height": 54,
                        "z_index": 4,
                        "rotation": -12,
                        "shape_type": "rectangle",
                        "fill_color": "rgba(220,60,50,1)",
                        "group_id": "ribbon",
                    },
                    {
                        "id": "ribbon_label",
                        "type": "text",
                        "x": 300,
                        "y": 60,
                        "width": 300,
                        "height": 34,
                        "z_index": 6,
                        "rotation": -12,
                        "content": "SALE",
                        "font_family": "Solstice Sans",
                        "font_size": 20,
                        "font_weight": "bold",
                        "color": "rgba(255,255,255,1)",
                        "text_align": "center",
                        "group_id": "ribbon",
                    },
                    {
                        "id": "copy",
                        "type": "text",
                        "x": 100,
                        "y": 500,
                        "width": 800,
                        "height": 100,
                        "content": "Chase light",
                        "font_family": "Solstice Sans",
                        "font_size": 22,
                        "color": "rgba(255,255,255,1)",
                        "text_align": "center",
                    },
                ],
            },
            {"width": 400, "height": 80},
        )

    def test_level3_sample_fails_closed_after_bounded_search(self):
        task = self._load_task()
        source = task["source"]
        before = copy.deepcopy(source)
        with self.assertRaises(InfeasibleLayoutError) as raised:
            resize(source, task["target_canvas"])
        self.assertEqual(raised.exception.reason_code, InfeasibleReasonCode.INCOMPLETE_SEARCH)
        self.assertEqual(source, before)
        failures = [
            failure
            for failure in raised.exception.details["failures"]
            if failure["topology"] == "horizontal_ribbon"
        ]
        self.assertTrue(failures)
        self.assertTrue(failures[0]["details"]["search_exhausted"])

    def test_horizontal_ribbon_preserves_rotated_groups(self):
        source, target = self._horizontal_fixture()
        before = copy.deepcopy(source)
        response = resize(source, target)
        validate_response(source, target, response)
        self.assertEqual(source, before)
        self.assertEqual(response["canvas"], target)
        self.assertEqual(
            [element["id"] for element in response["elements"]],
            [element["id"] for element in source["elements"]],
        )
        ribbon = next(element for element in response["elements"] if element["id"] == "ribbon_bg")
        self.assertEqual(ribbon["rotation"], -12)
        response_aabbs = [rotated_aabb(element) for element in response["elements"]]
        for aabb in response_aabbs:
            self.assertGreaterEqual(aabb[0], 0)
            self.assertGreaterEqual(aabb[1], 0)
            self.assertLessEqual(aabb[2], target["width"])
            self.assertLessEqual(aabb[3], target["height"])
        source_aabbs = [rotated_aabb(element) for element in source["elements"]]
        for left in range(len(source_aabbs)):
            for right in range(left + 1, len(source_aabbs)):
                if positive_aabb_intersection(source_aabbs[left], source_aabbs[right]):
                    continue
                self.assertFalse(
                    positive_aabb_intersection(response_aabbs[left], response_aabbs[right])
                )

    def test_repeated_render_hash_is_deterministic(self):
        source, target = self._horizontal_fixture()
        response = resize(source, target)
        with tempfile.TemporaryDirectory() as directory:
            first = Path(directory) / "first.png"
            second = Path(directory) / "second.png"
            render_design_to_png(response, ASSETS, first)
            render_design_to_png(response, ASSETS, second)
            self.assertEqual(
                hashlib.sha256(first.read_bytes()).digest(),
                hashlib.sha256(second.read_bytes()).digest(),
            )

    def test_zero_span_group_does_not_raise_runtime_error(self):
        source = {
            "canvas": {"width": 100, "height": 100},
            "elements": [
                {
                    "id": "bg",
                    "type": "image",
                    "x": 0,
                    "y": 0,
                    "width": 100,
                    "height": 100,
                    "asset_id": "missing-bg.png",
                    "fit": "cover",
                },
                {
                    "id": "zero-a",
                    "type": "shape",
                    "x": 10,
                    "y": 10,
                    "width": 0,
                    "height": 0,
                    "group_id": "zero",
                    "shape_type": "rectangle",
                    "fill_color": "rgba(255,0,0,1)",
                },
                {
                    "id": "zero-b",
                    "type": "shape",
                    "x": 10,
                    "y": 10,
                    "width": 0,
                    "height": 0,
                    "group_id": "zero",
                    "shape_type": "rectangle",
                    "fill_color": "rgba(0,255,0,1)",
                },
                {
                    "id": "later",
                    "type": "shape",
                    "x": 50,
                    "y": 10,
                    "width": 10,
                    "height": 20,
                    "shape_type": "rectangle",
                    "fill_color": "rgba(0,0,255,1)",
                },
            ],
        }
        target = {"width": 80, "height": 20}

        response = generate_horizontal_ribbon_candidate(source, target).response

        validate_response(source, target, response)

    def test_singleton_group_keeps_uniform_transform(self):
        source = {
            "canvas": {"width": 100, "height": 100},
            "elements": [
                {
                    "id": "bg",
                    "type": "image",
                    "x": 0,
                    "y": 0,
                    "width": 100,
                    "height": 100,
                    "asset_id": "missing-bg.png",
                    "fit": "cover",
                },
                {
                    "id": "copy",
                    "type": "text",
                    "x": 20,
                    "y": 20,
                    "width": 30,
                    "height": 10,
                    "content": "A",
                    "font_family": "Solstice Sans",
                    "font_size": 12,
                    "color": "rgba(255,255,255,1)",
                    "text_align": "center",
                    "group_id": "copy",
                },
            ],
        }
        target = {"width": 80, "height": 10}

        response = generate_horizontal_ribbon_candidate(source, target).response

        validate_response(source, target, response)
        copy_element = response["elements"][1]
        self.assertEqual(copy_element["width"] * 10, copy_element["height"] * 30)

    def test_bleeding_singleton_keeps_positive_canvas_intersection(self):
        source = {
            "canvas": {"width": 100, "height": 100},
            "elements": [
                {
                    "id": "bleed",
                    "type": "shape",
                    "x": -1,
                    "y": 20,
                    "width": 3,
                    "height": 20,
                    "opacity": Decimal("0.5"),
                    "shape_type": "rectangle",
                    "fill_color": "rgba(255,0,0,1)",
                },
                {
                    "id": "later",
                    "type": "shape",
                    "x": 50,
                    "y": 20,
                    "width": 10,
                    "height": 20,
                    "shape_type": "rectangle",
                    "fill_color": "rgba(0,255,0,1)",
                },
            ],
        }
        target = {"width": 80, "height": 20}

        response = generate_horizontal_ribbon_candidate(source, target).response

        validate_response(source, target, response)
        bleed = response["elements"][0]
        self.assertGreaterEqual(bleed["width"], 2)

    def test_ribbon_packing_preserves_source_order(self):
        source = {
            "canvas": {"width": 100, "height": 100},
            "elements": [
                {
                    "id": "bg",
                    "type": "image",
                    "x": 0,
                    "y": 0,
                    "width": 100,
                    "height": 100,
                    "asset_id": "missing-bg.png",
                    "fit": "cover",
                },
                {
                    "id": "copy",
                    "type": "text",
                    "x": 10,
                    "y": 10,
                    "width": 30,
                    "height": 20,
                    "content": "SALE",
                    "font_family": "Solstice Sans",
                    "font_size": 12,
                    "color": "rgba(255,255,255,1)",
                    "text_align": "center",
                },
                {
                    "id": "later-shape",
                    "type": "shape",
                    "x": 60,
                    "y": 10,
                    "width": 20,
                    "height": 20,
                    "shape_type": "rectangle",
                    "fill_color": "rgba(255,0,0,1)",
                },
            ],
        }
        target = {"width": 80, "height": 20}

        response = generate_horizontal_ribbon_candidate(source, target).response

        validate_response(source, target, response)
        self.assertEqual(
            [element["id"] for element in response["elements"]],
            [element["id"] for element in source["elements"]],
        )
        self.assertLess(response["elements"][1]["x"], response["elements"][2]["x"])

    def test_vertical_restack_with_synthetic_source(self):
        source = {
            "canvas": {"width": 1200, "height": 300},
            "elements": [
                {
                    "id": "bg",
                    "type": "image",
                    "x": 0,
                    "y": 0,
                    "width": 1200,
                    "height": 300,
                    "z_index": 0,
                    "asset_id": "solstice_bg_gradient.png",
                    "fit": "cover",
                },
                {
                    "id": "copy",
                    "type": "text",
                    "x": 200,
                    "y": 80,
                    "width": 800,
                    "height": 100,
                    "content": "A compact vertical restack",
                    "font_family": "Solstice Sans",
                    "font_size": 22,
                    "color": "rgba(255,255,255,1)",
                    "text_align": "center",
                },
                {
                    "id": "badge",
                    "type": "shape",
                    "x": 450,
                    "y": 200,
                    "width": 300,
                    "height": 50,
                    "shape_type": "rectangle",
                    "fill_color": "rgba(232,106,58,1)",
                },
            ],
        }
        target = {"width": 200, "height": 900}
        response = resize(source, target)
        validate_response(source, target, response)
        self.assertEqual(response["canvas"], target)
        self.assertEqual([item["id"] for item in response["elements"]], ["bg", "copy", "badge"])


if __name__ == "__main__":
    unittest.main()
