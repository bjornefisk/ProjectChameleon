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
    from engine.geometry.bounds import (
        positive_aabb_intersection,
        rotated_aabb,
        source_bleed_sides,
    )
    from engine.geometry.groups import has_common_transform
    from engine.geometry.ratios import preserves_source_ratio
    from engine.layout.column_pivot import is_column_pivot_suitable
    from engine.layout.near_isomorphic import solve_near_isomorphic
    from engine.layout.roles import RoleKind, infer_roles
    from engine.resize import resize
except ModuleNotFoundError:
    from chameleon.engine.contract import validate_response
    from chameleon.engine.errors import InfeasibleLayoutError, InfeasibleReasonCode
    from chameleon.engine.geometry.bounds import (
        positive_aabb_intersection,
        rotated_aabb,
        source_bleed_sides,
    )
    from chameleon.engine.geometry.groups import has_common_transform
    from chameleon.engine.geometry.ratios import preserves_source_ratio
    from chameleon.engine.layout.column_pivot import is_column_pivot_suitable
    from chameleon.engine.layout.near_isomorphic import solve_near_isomorphic
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
    def test_logo_only_media_signal_routes_supported_column_builder(self):
        task = self._load_task()
        source = copy.deepcopy(task["source"])
        product = next(element for element in source["elements"] if element["id"] == "product")
        product.update({"group_id": "hero", "width": 200, "height": 200})
        model = infer_roles(source)
        self.assertEqual(model.assignment_for("product").role, RoleKind.SHAPE)
        self.assertEqual(model.assignment_for("logo").role, RoleKind.LOGO)
        self.assertTrue(is_column_pivot_suitable(source, task["target_canvas"], model))
        response = resize(source, task["target_canvas"])
        validate_response(source, task["target_canvas"], response)


    def test_resize_preserves_immutable_and_omitted_fields(self):
        task = self._load_task()
        source = copy.deepcopy(task["source"])
        response = resize(source, task["target_canvas"])
        geometry = {"x", "y", "width", "height"}
        for source_element, response_element in zip(source["elements"], response["elements"]):
            for key, value in source_element.items():
                if key not in geometry and not (key == "font_size" and source_element["type"] == "text"):
                    self.assertEqual(response_element[key], value, (source_element["id"], key))
            self.assertEqual(
                set(response_element) - geometry - {"font_size"},
                set(source_element) - geometry - {"font_size"},
            )
        subhead = next(element for element in response["elements"] if element["id"] == "subhead")
        self.assertNotIn("font_weight", subhead)

    def test_resize_reports_both_failed_candidate_families(self):
        task = self._load_task()
        source = copy.deepcopy(task["source"])
        headline = next(element for element in source["elements"] if element["id"] == "headline")
        headline["font_size"] = 10**100
        with self.assertRaises(InfeasibleLayoutError) as raised:
            resize(source, task["target_canvas"])
        self.assertEqual(raised.exception.reason_code, InfeasibleReasonCode.INCOMPLETE_SEARCH)
        failures = raised.exception.details["candidate_failures"]
        self.assertEqual(set(failures), {"column_pivot", "near_isomorphic"})
        self.assertEqual(failures["column_pivot"]["reason_code"], InfeasibleReasonCode.INCOMPLETE_SEARCH.value)
        self.assertEqual(failures["near_isomorphic"]["reason_code"], InfeasibleReasonCode.INCOMPLETE_SEARCH.value)

    def test_role_relationship_generation_has_deterministic_bound(self):
        source = {
            "canvas": {"width": 100, "height": 100},
            "elements": [
                {
                    "id": f"shape-{index}",
                    "type": "shape",
                    "x": 0,
                    "y": 0,
                    "width": 1,
                    "height": 1,
                }
                for index in range(130)
            ],
        }
        with self.assertRaises(InfeasibleLayoutError) as raised:
            infer_roles(source)
        self.assertEqual(raised.exception.reason_code, InfeasibleReasonCode.INCOMPLETE_SEARCH)
        self.assertEqual(raised.exception.details["relationship_count"], 8385)
        self.assertEqual(raised.exception.details["relationship_cap"], 8192)
        self.assertFalse(raised.exception.details["search_exhausted"])

    def test_small_right_bottom_bleed_survives_integer_serialization(self):
        task = self._load_task()
        source = copy.deepcopy(task["source"])
        decoration = next(element for element in source["elements"] if element["id"] == "deco_circle_2")
        decoration.update({"x": Decimal("1079.5"), "y": Decimal("1079.5"), "width": 1, "height": 1})
        response = resize(source, task["target_canvas"])
        validate_response(source, task["target_canvas"], response)
        index = next(index for index, element in enumerate(source["elements"]) if element["id"] == decoration["id"])
        source_aabb = rotated_aabb(source["elements"][index])
        response_aabb = rotated_aabb(response["elements"][index])
        self.assertEqual(source_bleed_sides(decoration, source_aabb, source["canvas"]), frozenset({"right", "bottom"}))
        self.assertEqual(
            source_bleed_sides(decoration, response_aabb, task["target_canvas"]),
            frozenset({"right", "bottom"}),
        )
        self.assertTrue(
            positive_aabb_intersection(
                response_aabb,
                (0, 0, task["target_canvas"]["width"], task["target_canvas"]["height"]),
            )
        )


    def test_huge_font_size_fails_with_reproducible_search_diagnostics(self):
        source = {
            "canvas": {"width": 100, "height": 100},
            "elements": [
                {
                    "id": "headline",
                    "type": "text",
                    "x": 0,
                    "y": 0,
                    "width": 100,
                    "height": 100,
                    "content": "A",
                    "font_family": "Solstice Sans",
                    "font_size": 10**100,
                    "color": "rgba(0,0,0,1)",
                }
            ],
        }
        with self.assertRaises(InfeasibleLayoutError) as raised:
            solve_near_isomorphic(source, source["canvas"], font_manager=object())
        self.assertEqual(raised.exception.reason_code, InfeasibleReasonCode.INCOMPLETE_SEARCH)
        font_search = raised.exception.details["font_search"]
        self.assertEqual(font_search["preferred_size"], 10**100)
        self.assertEqual(font_search["max_steps"], 64)
        self.assertEqual(font_search["max_bits"], 63)
        self.assertEqual(font_search["candidate_order"], "descending")
        self.assertEqual(font_search["work_unit"], "font_size_candidate")
        self.assertFalse(font_search["search_exhausted"])
        self.assertTrue(font_search["no_attempt"])
        self.assertIsNone(font_search["tested_size_range"])
        self.assertEqual(font_search["tested_size_count"], 0)
        self.assertFalse(font_search["exhausted_size_one"])
        self.assertTrue(font_search["hit_cutoff"])
        self.assertEqual(font_search["status_reason"], "preferred_size_bit_limit_exceeded")



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
