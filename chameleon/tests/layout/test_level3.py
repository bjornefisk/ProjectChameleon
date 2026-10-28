import contextlib
import io
import copy
import hashlib
import json
import sys
import tempfile
import unittest
from decimal import Decimal
from fractions import Fraction
from pathlib import Path
from unittest.mock import patch

from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from engine import main as runner_main
    from engine.contract import validate_response
    from engine.errors import InfeasibleLayoutError, InfeasibleReasonCode
    from engine.geometry.bounds import positive_aabb_intersection, rotated_aabb
    from engine.geometry.ratios import preserves_source_ratio
    from engine.layout.roles import infer_roles
    from engine.layout.horizontal_ribbon import (
        _MAX_GROUP_SCALE_REFINEMENT_STEPS,
        _group_scale_for_text,
        generate_horizontal_ribbon_candidate,
    )
    from engine.layout.search import search
    from engine.resize import resize
    from renderer.converter.convert import render_design_to_png
except ModuleNotFoundError:
    from chameleon.engine import main as runner_main
    from chameleon.engine.contract import validate_response
    from chameleon.engine.errors import InfeasibleLayoutError, InfeasibleReasonCode
    from chameleon.engine.geometry.bounds import positive_aabb_intersection, rotated_aabb
    from chameleon.engine.geometry.ratios import preserves_source_ratio
    from chameleon.engine.layout.roles import infer_roles
    from chameleon.engine.layout.horizontal_ribbon import (
        _MAX_GROUP_SCALE_REFINEMENT_STEPS,
        _group_scale_for_text,
        generate_horizontal_ribbon_candidate,
    )
    from chameleon.renderer.converter.convert import render_design_to_png
    from chameleon.engine.resize import resize

ROOT = PROJECT_ROOT / "chameleon"
FIXTURE = ROOT / "input" / "chameleon_sample_level3_advanced.json"
ASSETS = ROOT / "brand_kit" / "assets"


class Level3IntegrationTests(unittest.TestCase):
    def _load_task(self):
        return json.loads(FIXTURE.read_text(encoding="utf-8"), parse_float=Decimal)

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

    def test_level3_sample_publishes_stable_hard_valid_pair(self):
        task = self._load_task()
        source = task["source"]
        target = task["target_canvas"]
        before = copy.deepcopy(source)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            input_dir = root / "input"
            output_dir = root / "output"
            input_dir.mkdir()
            output_dir.mkdir()
            (input_dir / "public_level3.json").write_bytes(FIXTURE.read_bytes())

            signatures = []
            with patch.multiple(
                runner_main,
                INPUT_DIR=input_dir,
                OUTPUT_DIR=output_dir,
                ASSETS_DIR=ASSETS,
            ):
                for _repeat in range(2):
                    stdout = io.StringIO()
                    stderr = io.StringIO()
                    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(
                        stderr
                    ):
                        exit_code = runner_main.main()
                    self.assertEqual(exit_code, 0, stderr.getvalue())
                    self.assertIn(
                        "[public_level3.json] status=SUCCESS", stdout.getvalue()
                    )

                    json_files = list(output_dir.glob("*_output.json"))
                    png_files = list(output_dir.glob("*_output.png"))
                    self.assertEqual(
                        [path.name for path in json_files],
                        ["public_level3_output.json"],
                    )
                    self.assertEqual(
                        [path.name for path in png_files],
                        ["public_level3_output.png"],
                    )
                    serialized_bytes = json_files[0].read_bytes()
                    response = json.loads(
                        serialized_bytes.decode("utf-8"), parse_float=Decimal
                    )
                    validate_response(
                        source,
                        target,
                        response,
                        fonts_dir=ROOT / "brand_kit" / "fonts",
                    )
                    self.assertEqual(source, before)
                    self.assertEqual(response["canvas"], target)
                    self.assertEqual(
                        [element["id"] for element in response["elements"]],
                        [element["id"] for element in source["elements"]],
                    )
                    for element in response["elements"]:
                        for field in ("x", "y", "width", "height"):
                            self.assertIs(type(element[field]), int)
                        if element["type"] == "text":
                            self.assertIs(type(element["font_size"]), int)

                    with Image.open(png_files[0]) as artifact:
                        artifact.verify()
                    with Image.open(png_files[0]) as artifact:
                        self.assertEqual(artifact.size, (728, 90))
                    signatures.append(
                        (
                            hashlib.sha256(serialized_bytes).digest(),
                            hashlib.sha256(png_files[0].read_bytes()).digest(),
                        )
                    )

            self.assertEqual(signatures[0], signatures[1])

    def test_story_keeps_missing_asset_placeholder_clear_of_legal_copy(self):
        task = self._load_task()
        source = task["source"]
        target = {"width": 1080, "height": 1920}
        before = copy.deepcopy(source)

        response = resize(source, target)
        validate_response(source, target, response)

        self.assertEqual(source, before)
        elements = {element["id"]: element for element in response["elements"]}
        placeholder = elements["holiday_watermark"]
        legal = elements["legal_text"]
        self.assertEqual(
            placeholder["asset_id"],
            next(
                element["asset_id"]
                for element in source["elements"]
                if element["id"] == "holiday_watermark"
            ),
        )
        placeholder_box = rotated_aabb(placeholder)
        legal_box = rotated_aabb(legal)
        self.assertFalse(positive_aabb_intersection(placeholder_box, legal_box))

        horizontal_gutter = max(
            Fraction(0),
            legal_box.min_x - placeholder_box.max_x,
            placeholder_box.min_x - legal_box.max_x,
        )
        vertical_gutter = max(
            Fraction(0),
            legal_box.min_y - placeholder_box.max_y,
            placeholder_box.min_y - legal_box.max_y,
        )
        self.assertGreaterEqual(
            max(horizontal_gutter, vertical_gutter),
            Fraction(legal["font_size"]),
        )

    def test_dominant_copy_reports_bounded_font_and_layout_work(self):
        task = self._load_task()
        result = search(
            task["source"],
            task["target_canvas"],
            assets_dir=ASSETS,
            fonts_dir=ROOT / "brand_kit" / "fonts",
        )
        self.assertLessEqual(result.diagnostics["candidate_count"], 12)
        work = next(
            item
            for item in result.diagnostics["candidate_work"]
            if item["topology"] == "horizontal_ribbon"
            and item["variant"] == "dominant_copy"
        )
        details = work["details"]["dominant_copy_layout"]
        self.assertEqual(details["status"], "hard_valid")
        self.assertLessEqual(details["copy_font_size_probe_count"], 74)
        self.assertLessEqual(details["group_font_size_probe_count"], 74)
        self.assertGreater(details["font_measurement_calls"], 0)
        self.assertLessEqual(
            details["layout_configurations_considered"],
            details["layout_configuration_limit"],
        )
        self.assertEqual(
            details["group_scale_refinement_step_limit"],
            _MAX_GROUP_SCALE_REFINEMENT_STEPS,
        )
        self.assertLessEqual(
            details["group_scale_refinement_iterations"],
            details["group_scale_refinement_invocations"]
            * _MAX_GROUP_SCALE_REFINEMENT_STEPS,
        )
        self.assertGreater(details["group_scale_refinement_invocations"], 0)

    def test_grouped_text_scale_refinement_hits_typed_cutoff(self):
        diagnostics = {
            "group_scale_refinement_iterations": 0,
            "group_scale_refinement_invocations": 0,
            "group_scale_refinement_step_limit": _MAX_GROUP_SCALE_REFINEMENT_STEPS,
        }
        elements = [{"type": "text", "width": 1, "height": 1}]

        with self.assertRaises(InfeasibleLayoutError) as raised:
            _group_scale_for_text(
                elements,
                {0: 1},
                [0],
                None,
                lambda _element, width, _font_size, _manager: width + 1,
                Fraction(1),
                diagnostics,
            )

        error = raised.exception
        self.assertEqual(
            error.reason_code,
            InfeasibleReasonCode.INCOMPLETE_SEARCH,
        )
        self.assertFalse(error.details["search_exhausted"])
        self.assertEqual(
            error.details["group_scale_refinement_iterations"],
            _MAX_GROUP_SCALE_REFINEMENT_STEPS,
        )
        self.assertEqual(
            error.details["candidate_work"]["dominant_copy_layout"][
                "group_scale_refinement_status"
            ],
            "cutoff",
        )
        self.assertEqual(
            diagnostics["group_scale_refinement_iterations"],
            _MAX_GROUP_SCALE_REFINEMENT_STEPS,
        )

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

    def test_wide_billboard_uses_balanced_three_column_ribbon(self):
        task = self._load_task()
        source = task["source"]
        target = {"width": 970, "height": 250}
        response = resize(source, target)
        validate_response(source, target, response)
        self.assertEqual(
            [element["id"] for element in response["elements"]],
            [element["id"] for element in source["elements"]],
        )

        model = infer_roles(source)
        elements = response["elements"]
        foreground = [
            element
            for index, element in enumerate(elements)
            if index != model.background_index
        ]
        boxes = [rotated_aabb(element) for element in foreground]
        left = min(box[0] for box in boxes)
        top = min(box[1] for box in boxes)
        right = max(box[2] for box in boxes)
        bottom = max(box[3] for box in boxes)
        left_margin = left
        top_margin = top
        right_margin = target["width"] - right
        bottom_margin = target["height"] - bottom
        self.assertGreaterEqual(top_margin, 35)
        self.assertLessEqual(top_margin, 50)
        self.assertGreaterEqual(bottom_margin, 35)
        self.assertLessEqual(bottom_margin, 50)
        self.assertGreaterEqual(left_margin, 20)
        self.assertGreaterEqual(right_margin, 20)
        self.assertLessEqual(abs(left_margin - right_margin), 8)

        unit_boxes = {}
        for index, element in enumerate(elements):
            if index == model.background_index:
                continue
            group_id = element.get("group_id")
            key = ("group", group_id) if group_id is not None else ("element", index)
            box = rotated_aabb(element)
            previous = unit_boxes.get(key)
            if previous is None:
                unit_boxes[key] = box
            else:
                unit_boxes[key] = (
                    min(previous[0], box[0]),
                    min(previous[1], box[1]),
                    max(previous[2], box[2]),
                    max(previous[3], box[3]),
                )

        def gap_squared(first, second):
            gap_x = max(Fraction(0), first[0] - second[2], second[0] - first[2])
            gap_y = max(Fraction(0), first[1] - second[3], second[1] - first[3])
            return gap_x**2 + gap_y**2

        boxes_by_unit = list(unit_boxes.values())
        unit_gaps = [
            gap_squared(boxes_by_unit[left_index], boxes_by_unit[right_index])
            for left_index in range(len(boxes_by_unit))
            for right_index in range(left_index + 1, len(boxes_by_unit))
        ]
        self.assertGreaterEqual(min(unit_gaps), Fraction(64))
        badge_boxes = [unit_boxes[("group", f"badge{index}")] for index in range(1, 4)]
        badge_gaps = [
            gap_squared(badge_boxes[left_index], badge_boxes[right_index])
            for left_index in range(len(badge_boxes))
            for right_index in range(left_index + 1, len(badge_boxes))
        ]
        self.assertGreaterEqual(min(badge_gaps), Fraction(36))

        text = {
            element["id"]: element
            for element in elements
            if element["type"] == "text"
        }
        self.assertGreaterEqual(text["headline"]["font_size"], 13)
        self.assertGreater(text["headline"]["font_size"], text["cta_label"]["font_size"])
        self.assertGreaterEqual(text["subhead"]["font_size"], 8)
        self.assertLessEqual(text["subhead"]["font_size"], 9)
        self.assertGreaterEqual(text["cta_label"]["font_size"], 9)
        self.assertLessEqual(text["cta_label"]["font_size"], 11)


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
