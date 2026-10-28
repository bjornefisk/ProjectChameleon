import copy
import hashlib
import json
import sys
import tempfile
import unittest
from decimal import Decimal
from fractions import Fraction
from pathlib import Path

from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT))

from chameleon.renderer.converter.convert import render_design_to_png

try:
    from engine.contract import validate_response
    from engine.geometry.bounds import rotated_aabb
    from engine.geometry.ratios import preserves_source_ratio
    from engine.layout.roles import infer_roles
    from engine.layout.vertical_restack import _distribute_vertical_slack
    from engine.resize import resize
except ModuleNotFoundError:
    from chameleon.engine.contract import validate_response
    from chameleon.engine.geometry.bounds import rotated_aabb
    from chameleon.engine.geometry.ratios import preserves_source_ratio
    from chameleon.engine.layout.roles import infer_roles
    from chameleon.engine.layout.vertical_restack import _distribute_vertical_slack
    from chameleon.engine.resize import resize


ROOT = Path(__file__).resolve().parents[2]
LEVEL1 = ROOT / "input" / "chameleon_sample_level1_warmup.json"
ASSETS = ROOT / "brand_kit" / "assets"


class Level1IntegrationTests(unittest.TestCase):
    def _load_task(self):
        return json.loads(
            LEVEL1.read_text(encoding="utf-8"),
            parse_int=int,
            parse_float=Decimal,
        )

    def test_warmup_resizes_validates_and_renders_without_distortion(self):
        task = self._load_task()
        source = task["source"]
        target_canvas = task["target_canvas"]
        before = copy.deepcopy(source)

        response = resize(source, target_canvas)
        validate_response(source, target_canvas, response)

        self.assertEqual(source, before)
        self.assertEqual(response["canvas"], target_canvas)
        self.assertEqual(
            [element["id"] for element in response["elements"]],
            [element["id"] for element in source["elements"]],
        )

        background, logo, headline, cta = response["elements"]
        self.assertEqual(
            (background["x"], background["y"], background["width"], background["height"]),
            (0, 0, 1080, 1350),
        )
        self.assertTrue(
            preserves_source_ratio(
                logo["width"],
                logo["height"],
                source["elements"][1]["width"],
                source["elements"][1]["height"],
            )
        )
        for element in (headline, cta):
            self.assertIs(type(element["font_size"]), int)
            self.assertGreaterEqual(element["font_size"], 1)

        with tempfile.TemporaryDirectory() as directory:
            png_path = Path(directory) / "level1.png"
            repeat_path = Path(directory) / "level1-repeat.png"
            warnings = render_design_to_png(response, ASSETS, png_path)
            repeat_warnings = render_design_to_png(response, ASSETS, repeat_path)
            self.assertEqual(warnings, [])
            self.assertEqual(repeat_warnings, [])
            self.assertEqual(
                hashlib.sha256(png_path.read_bytes()).digest(),
                hashlib.sha256(repeat_path.read_bytes()).digest(),
            )
            with Image.open(png_path) as image:
                self.assertEqual(image.format, "PNG")
                self.assertEqual(image.size, (1080, 1350))

    def test_story_distributes_vertical_slack_across_semantic_blocks(self):
        task = self._load_task()
        source = task["source"]
        target = {"width": 1080, "height": 1920}
        before = copy.deepcopy(source)

        response = resize(source, target)
        validate_response(source, target, response)

        self.assertEqual(source, before)
        self.assertEqual(response["canvas"], target)
        roles = infer_roles(source)
        foreground_boxes = [
            rotated_aabb(element)
            for index, element in enumerate(response["elements"])
            if index != roles.background_index
            and element["width"] > 0
            and element["height"] > 0
        ]
        content_top = min(box.min_y for box in foreground_boxes)
        content_bottom = max(box.max_y for box in foreground_boxes)
        coverage = (content_bottom - content_top) / target["height"]
        self.assertGreaterEqual(coverage, Fraction(55, 100))
        self.assertLessEqual(coverage, Fraction(70, 100))

        top_margin = content_top
        bottom_margin = target["height"] - content_bottom
        self.assertLessEqual(
            abs(top_margin - bottom_margin),
            Fraction(target["height"], 10),
        )

        logo = next(element for element in response["elements"] if element["id"] == "logo")
        source_logo = next(element for element in source["elements"] if element["id"] == "logo")
        self.assertTrue(
            preserves_source_ratio(
                logo["width"], logo["height"], source_logo["width"], source_logo["height"]
            )
        )

    def test_compact_square_balances_margins_and_unit_gutters(self):
        task = self._load_task()
        source = task["source"]
        target = {"width": 600, "height": 600}
        response = resize(source, target)
        validate_response(source, target, response)

        roles = infer_roles(source)
        foreground = [
            rotated_aabb(element)
            for index, element in enumerate(response["elements"])
            if index != roles.background_index
            and element["width"] > 0
            and element["height"] > 0
        ]
        content_top = min(box.min_y for box in foreground)
        content_bottom = max(box.max_y for box in foreground)
        top_margin = content_top
        bottom_margin = target["height"] - content_bottom
        self.assertGreaterEqual(top_margin, 90)
        self.assertLessEqual(top_margin, 130)
        self.assertGreaterEqual(bottom_margin, 90)
        self.assertLessEqual(bottom_margin, 130)
        self.assertLessEqual(abs(top_margin - bottom_margin), 20)

        ordered = sorted(foreground, key=lambda box: box.min_y)
        gutters = [
            right.min_y - left.max_y
            for left, right in zip(ordered, ordered[1:])
        ]
        self.assertGreaterEqual(min(gutters), 12)

        # The refinement is reserved for square-ish canvases with spare
        # vertical room; non-square targets outside the gate stay untouched.
        for gated_target in (
            {"width": 540, "height": 600},
            {"width": 660, "height": 600},
        ):
            gated_response = resize(source, gated_target)
            validate_response(source, gated_target, gated_response)
            gated_boxes = [
                rotated_aabb(element)
                for index, element in enumerate(gated_response["elements"])
                if index != roles.background_index
                and element["width"] > 0
                and element["height"] > 0
            ]
            gated_top = min(box.min_y for box in gated_boxes)
            gated_bottom = max(box.max_y for box in gated_boxes)
            self.assertLessEqual(abs(gated_top - (600 - gated_bottom)), 20)
            gated_bottom_margin = 600 - gated_bottom
            self.assertGreaterEqual(gated_top, 90)
            self.assertLessEqual(gated_top, 130)
            self.assertGreaterEqual(gated_bottom_margin, 90)
            self.assertLessEqual(gated_bottom_margin, 130)
            gated_ordered = sorted(gated_boxes, key=lambda box: box.min_y)
            gated_gutters = [
                right.min_y - left.max_y
                for left, right in zip(gated_ordered, gated_ordered[1:])
            ]
            self.assertGreaterEqual(min(gated_gutters), 12)
        for outside_target in (
            {"width": 539, "height": 600},
            {"width": 661, "height": 600},
        ):
            outside_response = resize(source, outside_target)
            validate_response(source, outside_target, outside_response)
            unadjusted = copy.deepcopy(outside_response)
            _distribute_vertical_slack(
                source, outside_target, outside_response
            )
            self.assertEqual(outside_response, unadjusted)


if __name__ == "__main__":
    unittest.main()
