import copy
import hashlib
import json
import sys
from fractions import Fraction
from unittest.mock import patch
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
    from engine.layout.column_pivot import (
        _build_column_candidate,
        _image_dimensions,
        _serialize_column_candidate,
        is_column_pivot_suitable,
    )
    from engine.layout.near_isomorphic import (
        _MAX_FONT_SEARCH_PROBES,
        _MAX_RENDERER_FONT_SIZE,
        _font_size_probe_order,
        _largest_fitting_font_size,
    )
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
    from chameleon.engine.layout.column_pivot import (
        _build_column_candidate,
        _image_dimensions,
        _serialize_column_candidate,
        is_column_pivot_suitable,
    )
    from chameleon.engine.layout.near_isomorphic import (
        _MAX_FONT_SEARCH_PROBES,
        _MAX_RENDERER_FONT_SIZE,
        _font_size_probe_order,
        _largest_fitting_font_size,
    )
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

    def test_hero_selection_excludes_translucent_watermark_overlay(self):
        source = {
            "canvas": {"width": 1000, "height": 1000},
            "elements": [
                {
                    "id": "watermark",
                    "type": "image",
                    "x": 0,
                    "y": 0,
                    "width": 900,
                    "height": 900,
                    "asset_id": "watermark.png",
                    "opacity": Decimal("0.2"),
                    "z_index": -10,
                    "fit": "contain",
                },
                {
                    "id": "product",
                    "type": "image",
                    "x": 300,
                    "y": 300,
                    "width": 200,
                    "height": 200,
                    "asset_id": "product.png",
                    "opacity": 1,
                    "z_index": 1,
                    "fit": "contain",
                },
            ],
        }
        roles = infer_roles(source)
        self.assertEqual(roles.assignment_for("product").role, RoleKind.HERO_MEDIA)
        self.assertNotEqual(roles.assignment_for("watermark").role, RoleKind.HERO_MEDIA)

    def test_column_text_box_ignores_mutable_source_font_size(self):
        task = self._load_task()
        source = copy.deepcopy(task["source"])
        headline = next(element for element in source["elements"] if element["id"] == "headline")
        headline["font_size"] = 10**100
        roles = infer_roles(source)
        with patch("engine.layout.column_pivot._largest_fitting_font_size", return_value=10):
            response = _build_column_candidate(
                source,
                task["target_canvas"],
                roles,
                font_manager=object(),
            )
        expected_height = max(
            Fraction(1),
            Fraction(task["target_canvas"]["height"])
            * Fraction(
                source["elements"][source["elements"].index(headline)]["height"]
            )
            / Fraction(source["canvas"]["height"]),
        )
        output_headline = next(element for element in response["elements"] if element["id"] == "headline")
        self.assertEqual(output_headline["height"], expected_height)

    def test_column_candidate_keeps_fractional_geometry_until_final_serialization(self):
        source = {
            "canvas": {"width": 100, "height": 100},
            "elements": [
                {
                    "id": "hero",
                    "type": "image",
                    "x": 10,
                    "y": 10,
                    "width": 20,
                    "height": 20,
                    "asset_id": "hero.png",
                    "fit": "contain",
                },
                {
                    "id": "copy",
                    "type": "text",
                    "x": 60,
                    "y": 60,
                    "width": 30,
                    "height": 20,
                    "content": "A",
                    "font_family": "Solstice Sans",
                    "font_size": 20,
                    "color": "rgba(0,0,0,1)",
                },
            ],
        }
        roles = infer_roles(source)
        with patch("engine.layout.column_pivot._largest_fitting_font_size", return_value=10):
            response = _build_column_candidate(
                source,
                {"width": 101, "height": 50},
                roles,
                font_manager=object(),
            )

        raw_copy = next(element for element in response["elements"] if element["id"] == "copy")
        self.assertIsInstance(raw_copy["x"], Fraction)
        self.assertEqual(raw_copy["x"], Fraction(1111, 40))


        serialized = _serialize_column_candidate(response)
        output_copy = next(element for element in serialized["elements"] if element["id"] == "copy")
        self.assertEqual(output_copy["x"], 28)
        self.assertIs(type(output_copy["x"]), int)

    def test_image_ratio_lattice_uses_unrounded_desired_bounds(self):
        element = {"width": 2, "height": 1}
        self.assertIsNone(
            _image_dimensions(element, Fraction(3, 2), Fraction(3, 2))
        )

    def test_grouped_cover_background_falls_back_without_losing_coverage(self):
        task = self._load_task()
        source = copy.deepcopy(task["source"])
        background = next(element for element in source["elements"] if element["id"] == "bg")
        background["group_id"] = "cover-group"
        response = resize(source, task["target_canvas"])
        validate_response(source, task["target_canvas"], response)
        output_background = next(element for element in response["elements"] if element["id"] == "bg")
        output_aabb = rotated_aabb(output_background)
        self.assertLessEqual(output_aabb[0], 0)
        self.assertLessEqual(output_aabb[1], 0)
        self.assertGreaterEqual(output_aabb[2], task["target_canvas"]["width"])
        self.assertGreaterEqual(output_aabb[3], task["target_canvas"]["height"])
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
        headline["content"] = "X" * 10_000
        with self.assertRaises(InfeasibleLayoutError) as raised:
            resize(source, task["target_canvas"])
        self.assertEqual(raised.exception.reason_code, InfeasibleReasonCode.INCOMPLETE_SEARCH)
        failures = raised.exception.details["failures"]
        self.assertEqual(
            {failure["topology"] for failure in failures},
            {
                "column_pivot",
                "near_isomorphic",
                "horizontal_ribbon",
                "vertical_restack",
            },
        )
        self.assertTrue(
            all(
                failure["reason_code"] == InfeasibleReasonCode.INCOMPLETE_SEARCH.value
                for failure in failures
            )
        )

    def test_role_relationship_generation_is_lazy_for_large_sources(self):
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
        model = infer_roles(source)
        self.assertEqual(len(model.relationships), 8385)
        self.assertTrue(model.relationships[0].source_overlap)
        self.assertEqual((model.relationships[-1].left_index, model.relationships[-1].right_index), (128, 129))
        self.assertTrue(model.overlaps(0, 129))

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


    def test_huge_font_size_finds_fitting_soft_preference(self):
        element = {
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
        calls = []

        def fits(_element, size, _font_manager, _target):
            calls.append(size)
            return size <= 10

        result = _largest_fitting_font_size(
            element,
            10**100,
            object(),
            {"width": 100, "height": 100},
            fit=fits,
        )
        self.assertEqual(result, 10)
        self.assertTrue(calls)
        self.assertLessEqual(max(calls), 1 << 20)

    def test_huge_preferred_font_size_reports_cutoff_after_small_size_probes(self):
        element = {
            "id": "headline",
            "type": "text",
            "x": 0,
            "y": 0,
            "width": 100,
            "height": 100,
            "content": "A",
            "font_family": "Solstice Sans",
            "font_size": 10,
            "color": "rgba(0,0,0,1)",
        }
        calls = []

        def fits(_element, size, _font_manager, _target):
            calls.append(size)
            return False

        details = {}
        result = _largest_fitting_font_size(
            element,
            1 << 62,
            object(),
            {"width": 100, "height": 100},
            fit=fits,
            search_details=details,
        )
        self.assertIsNone(result)
        self.assertEqual(len(calls), 74)
        self.assertLessEqual(max(calls), 1 << 20)
        self.assertEqual(min(calls), 1)
        self.assertTrue(details["preferred_clamped"])
        self.assertTrue(details["attempted"])
        self.assertFalse(details["no_attempt"])
        self.assertEqual(details["candidate_order"], "descending_with_soft_preference_probe")
        self.assertTrue(details["hit_cutoff"])
        self.assertEqual(details["status_reason"], "font_search_step_limit_reached")
        self.assertFalse(details["search_exhausted"])



    def test_story_resize_centers_foreground_without_moving_source_bleed(self):
        task = self._load_task()
        source = task["source"]
        target = {"width": 1080, "height": 1920}
        response = resize(source, target)
        validate_response(source, target, response)

        model = infer_roles(source)
        source_by_id = {element["id"]: element for element in source["elements"]}
        response_by_id = {element["id"]: element for element in response["elements"]}
        bleed = source_by_id["deco_circle_1"]
        expected_bleed = source_bleed_sides(
            bleed, rotated_aabb(bleed), source["canvas"]
        )
        self.assertEqual(expected_bleed, frozenset({"left", "top"}))
        self.assertEqual(
            source_bleed_sides(
                response_by_id[bleed["id"]],
                rotated_aabb(response_by_id[bleed["id"]]),
                target,
            ),
            expected_bleed,
        )

        foreground = [
            rotated_aabb(element)
            for index, element in enumerate(response["elements"])
            if index != model.background_index
            and model.assignments[index].signals["source_bleed_sides"] is None
            and element["width"] > 0
            and element["height"] > 0
        ]
        top = min(box.min_y for box in foreground)
        bottom = max(box.max_y for box in foreground)
        self.assertLessEqual(abs(top - (target["height"] - bottom)), target["height"] / 10)
        source_boxes = [rotated_aabb(element) for element in source["elements"]]
        response_boxes = [rotated_aabb(element) for element in response["elements"]]
        for left in range(len(source_boxes)):
            for right in range(left + 1, len(source_boxes)):
                if positive_aabb_intersection(source_boxes[left], source_boxes[right]):
                    continue
                self.assertFalse(
                    positive_aabb_intersection(response_boxes[left], response_boxes[right]),
                    (source["elements"][left]["id"], source["elements"][right]["id"]),
                )

    def test_story_bleed_excludes_entire_rigid_group_from_slack_distribution(self):
        task = self._load_task()
        source = copy.deepcopy(task["source"])
        target = {"width": 1080, "height": 1920}
        bleed = next(element for element in source["elements"] if element["id"] == "deco_circle_1")
        sibling = next(element for element in source["elements"] if element["id"] == "deco_circle_2")
        bleed["group_id"] = sibling["group_id"] = "bleed-decoration"
        response = resize(source, target)
        validate_response(source, target, response)

        source_group = [bleed, sibling]
        response_by_id = {element["id"]: element for element in response["elements"]}
        response_group = [response_by_id[element["id"]] for element in source_group]
        self.assertTrue(has_common_transform(source_group, response_group))
        expected_bleed = source_bleed_sides(
            bleed, rotated_aabb(bleed), source["canvas"]
        )
        self.assertEqual(
            source_bleed_sides(
                response_by_id[bleed["id"]],
                rotated_aabb(response_by_id[bleed["id"]]),
                target,
            ),
            expected_bleed,
        )

        model = infer_roles(source)
        foreground = [
            rotated_aabb(element)
            for index, element in enumerate(response["elements"])
            if index != model.background_index
            and element.get("group_id") != "bleed-decoration"
            and model.assignments[index].signals["source_bleed_sides"] is None
            and element["width"] > 0
            and element["height"] > 0
        ]
        top = min(box.min_y for box in foreground)
        bottom = max(box.max_y for box in foreground)
        self.assertLessEqual(abs(top - (target["height"] - bottom)), target["height"] / 10)
        source_boxes = [rotated_aabb(element) for element in source["elements"]]
        response_boxes = [rotated_aabb(element) for element in response["elements"]]
        for left in range(len(source_boxes)):
            for right in range(left + 1, len(source_boxes)):
                if positive_aabb_intersection(source_boxes[left], source_boxes[right]):
                    continue
                self.assertFalse(
                    positive_aabb_intersection(response_boxes[left], response_boxes[right]),
                    (source["elements"][left]["id"], source["elements"][right]["id"]),
                )


    def test_billboard_resize_uses_slack_for_legible_centered_foreground(self):
        task = self._load_task()
        source = task["source"]
        target = {"width": 970, "height": 250}
        response = resize(source, target)
        validate_response(source, target, response)

        model = infer_roles(source)
        foreground = [
            rotated_aabb(element)
            for index, element in enumerate(response["elements"])
            if index != model.background_index
            and model.assignments[index].signals["source_bleed_sides"] is None
            and element["width"] > 0
            and element["height"] > 0
        ]
        top = min(box.min_y for box in foreground)
        bottom = max(box.max_y for box in foreground)
        self.assertLessEqual(abs(top - (target["height"] - bottom)), target["height"] / 10)
        response_by_id = {element["id"]: element for element in response["elements"]}
        self.assertGreaterEqual(response_by_id["subhead"]["font_size"], 8)

        source_by_id = {element["id"]: element for element in source["elements"]}
        response_by_id = {element["id"]: element for element in response["elements"]}
        for element_id, source_element in source_by_id.items():
            expected_bleed = source_bleed_sides(
                source_element, rotated_aabb(source_element), source["canvas"]
            )
            if expected_bleed is not None:
                self.assertEqual(
                    source_bleed_sides(
                        response_by_id[element_id],
                        rotated_aabb(response_by_id[element_id]),
                        target,
                    ),
                    expected_bleed,
                )

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

    def test_font_size_probe_order_caps_schema_valid_large_values(self):
        levels = _font_size_probe_order(10**100)
        self.assertEqual(len(levels), _MAX_FONT_SEARCH_PROBES)
        self.assertEqual(levels[0], _MAX_RENDERER_FONT_SIZE)
        self.assertEqual(levels[-10:], tuple(range(10, 0, -1)))
        self.assertEqual(levels, _font_size_probe_order(10**100))

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

    def test_compact_square_separates_source_overlapping_subhead_from_cta(self):
        task = json.loads(
            (
                ROOT
                / "input_synthetic"
                / "chameleon_sample_level2_core_compact_square.json"
            ).read_text(encoding="utf-8"),
            parse_int=int,
            parse_float=Decimal,
        )
        source = task["source"]
        target = task["target_canvas"]
        response = resize(source, target)
        validate_response(source, target, response)

        response_by_id = {element["id"]: element for element in response["elements"]}
        model = infer_roles(source)
        subhead_index = next(
            index
            for index, element in enumerate(source["elements"])
            if element["id"] == "subhead"
        )
        subhead_box = rotated_aabb(response_by_id["subhead"])
        self.assertGreaterEqual(response_by_id["subhead"]["font_size"], 13)
        for element_id in ("cta_bg", "cta_label"):
            cta_index = next(
                index
                for index, element in enumerate(source["elements"])
                if element["id"] == element_id
            )
            self.assertTrue(model.overlaps(subhead_index, cta_index))
            self.assertFalse(
                positive_aabb_intersection(
                    subhead_box, rotated_aabb(response_by_id[element_id])
                ),
                msg=f"subhead must not cover {element_id}",
            )

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
