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
    from engine.geometry.bounds import (
        positive_aabb_intersection,
        rotated_aabb,
        source_bleed_sides,
    )
    from engine.geometry.groups import has_common_transform
    from engine.geometry.ratios import preserves_source_ratio
    from engine.layout.column_pivot import is_column_pivot_suitable
    from engine.layout.roles import RoleKind, infer_roles
    from engine.resize import resize
except ModuleNotFoundError:
    from chameleon.engine.contract import validate_response
    from chameleon.engine.geometry.bounds import (
        positive_aabb_intersection,
        rotated_aabb,
        source_bleed_sides,
    )
    from chameleon.engine.geometry.groups import has_common_transform
    from chameleon.engine.geometry.ratios import preserves_source_ratio
    from chameleon.engine.layout.column_pivot import is_column_pivot_suitable
    from chameleon.engine.layout.roles import RoleKind, infer_roles
    from chameleon.engine.resize import resize

try:
    from chameleon.renderer.converter.convert import render_design_to_png
except ModuleNotFoundError:
    from renderer.converter.convert import render_design_to_png

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "input" / "chameleon_sample_level2_core.json"
ASSETS = ROOT / "brand_kit" / "assets"


class Level2IntegrationTests(unittest.TestCase):
    def _load_task(self):
        return json.loads(FIXTURE.read_text(encoding="utf-8"), parse_int=int, parse_float=Decimal)

    def test_role_model_is_source_aware_and_inspectable(self):
        task = self._load_task()
        source = task["source"]
        model = infer_roles(source)
        roles = {assignment.element_id: assignment.role for assignment in model.assignments}

        self.assertEqual(roles["bg"], RoleKind.BACKGROUND)
        self.assertEqual(roles["product"], RoleKind.HERO_MEDIA)
        self.assertEqual(roles["headline"], RoleKind.HEADLINE)
        self.assertEqual(roles["badge_bg"], RoleKind.BADGE)
        self.assertEqual(roles["cta_bg"], RoleKind.CTA)
        self.assertIn("effective_z_index", model.assignment_for("headline").signals)
        self.assertIn("source_bleed_sides", model.assignment_for("deco_circle_1").signals)
        self.assertTrue(any(relationship.source_overlap for relationship in model.relationships))
        self.assertTrue(is_column_pivot_suitable(source, task["target_canvas"], model))

    def test_resize_preserves_identity_and_semantics_in_source_order(self):
        task = self._load_task()
        source = task["source"]
        target = task["target_canvas"]
        before = copy.deepcopy(source)

        response = resize(source, target)
        validate_response(source, target, response)

        self.assertEqual(source, before)
        self.assertEqual(response["canvas"], target)
        self.assertEqual(
            [(element["id"], element["type"]) for element in response["elements"]],
            [(element["id"], element["type"]) for element in source["elements"]],
        )
        for element in response["elements"]:
            for field in ("x", "y", "width", "height"):
                self.assertIs(type(element[field]), int)
            if element["type"] == "text":
                self.assertIs(type(element["font_size"]), int)
        for source_element, response_element in zip(source["elements"], response["elements"]):
            if source_element["type"] == "image" and source_element.get("fit", "contain") != "cover":
                self.assertTrue(
                    preserves_source_ratio(
                        response_element["width"],
                        response_element["height"],
                        source_element["width"],
                        source_element["height"],
                    )
                )

    def test_pivot_columns_and_rigid_assemblies(self):
        task = self._load_task()
        source = task["source"]
        response = resize(source, task["target_canvas"])
        by_id = {element["id"]: element for element in response["elements"]}

        product_center = (by_id["product"]["x"] + by_id["product"]["width"] / 2)
        headline_center = (by_id["headline"]["x"] + by_id["headline"]["width"] / 2)
        self.assertLess(product_center, headline_center)
        self.assertGreaterEqual(by_id["badge_label"]["y"], by_id["badge_bg"]["y"])
        self.assertLessEqual(
            by_id["badge_label"]["y"] + by_id["badge_label"]["height"],
            by_id["badge_bg"]["y"] + by_id["badge_bg"]["height"],
        )
        self.assertGreaterEqual(by_id["cta_label"]["y"], by_id["cta_bg"]["y"])
        self.assertLessEqual(
            by_id["cta_label"]["y"] + by_id["cta_label"]["height"],
            by_id["cta_bg"]["y"] + by_id["cta_bg"]["height"],
        )
        source_by_id = {element["id"]: element for element in source["elements"]}
        self.assertTrue(has_common_transform(
            [source_by_id["badge_bg"], source_by_id["badge_label"]],
            [by_id["badge_bg"], by_id["badge_label"]],
        ))
        self.assertTrue(has_common_transform(
            [source_by_id["cta_bg"], source_by_id["cta_label"]],
            [by_id["cta_bg"], by_id["cta_label"]],
        ))

    def test_bleed_and_source_separated_pairs_follow_contract(self):
        task = self._load_task()
        source = task["source"]
        response = resize(source, task["target_canvas"])
        source_aabbs = [rotated_aabb(element) for element in source["elements"]]
        response_aabbs = [rotated_aabb(element) for element in response["elements"]]

        bleed_index = next(index for index, element in enumerate(source["elements"]) if element["id"] == "deco_circle_1")
        expected_bleed = source_bleed_sides(source["elements"][bleed_index], source_aabbs[bleed_index], source["canvas"])
        actual = response_aabbs[bleed_index]
        self.assertEqual(expected_bleed, frozenset({"left", "top"}))
        self.assertLess(actual[0], 0)
        self.assertLess(actual[1], 0)
        self.assertGreater(actual[2], 0)
        self.assertGreater(actual[3], 0)

        for left in range(len(source["elements"])):
            for right in range(left + 1, len(source["elements"])):
                if positive_aabb_intersection(source_aabbs[left], source_aabbs[right]):
                    continue
                self.assertFalse(
                    positive_aabb_intersection(response_aabbs[left], response_aabbs[right]),
                    (source["elements"][left]["id"], source["elements"][right]["id"]),
                )

    def test_public_output_renders_deterministically(self):
        task = self._load_task()
        response = resize(task["source"], task["target_canvas"])
        with tempfile.TemporaryDirectory() as directory:
            first = Path(directory) / "first.png"
            second = Path(directory) / "second.png"
            self.assertEqual(render_design_to_png(response, ASSETS, first), [])
            self.assertEqual(render_design_to_png(response, ASSETS, second), [])
            self.assertEqual(hashlib.sha256(first.read_bytes()).digest(), hashlib.sha256(second.read_bytes()).digest())
            with Image.open(first) as image:
                self.assertEqual(image.format, "PNG")
                self.assertEqual(image.size, (1600, 400))


if __name__ == "__main__":
    unittest.main()
