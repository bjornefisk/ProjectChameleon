import contextlib
import io
import json
import sys
import tempfile
import unittest
from decimal import Decimal
from PIL import Image
from pathlib import Path
from unittest.mock import patch

from engine.geometry.bounds import rotated_aabb
from engine.geometry.groups import derive_quantized_common_transform

PROJECT_ROOT = Path(__file__).resolve().parents[3]
CHAMELEON_ROOT = PROJECT_ROOT / "chameleon"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(CHAMELEON_ROOT) not in sys.path:
    sys.path.insert(0, str(CHAMELEON_ROOT))

from scripts.generate_synthetic_cases import generate_cases

from engine import main as runner_main
from engine.contract import validate_response
from engine.errors import InfeasibleLayoutError, InfeasibleReasonCode
from engine.layout.roles import infer_roles
from engine.layout.horizontal_ribbon import (
    generate_horizontal_ribbon_candidate,
    is_horizontal_ribbon_suitable,
)
from engine.layout.vertical_restack import (
    generate_vertical_restack_candidate,
    is_vertical_restack_suitable,
)
from engine.resize import resize


SYNTHETIC_SOURCE = CHAMELEON_ROOT / "input"
ASSETS = CHAMELEON_ROOT / "brand_kit" / "assets"
FONTS = CHAMELEON_ROOT / "brand_kit" / "fonts"
ISSUE_81_CASES = (
    "chameleon_sample_level2_core_skyscraper",
    "chameleon_sample_level2_core_compact_square",
    "chameleon_sample_level3_advanced_skyscraper",
    "chameleon_sample_level3_advanced_medium_rectangle",
    "chameleon_sample_level3_advanced_compact_square",
)
REQUIRED_SUCCESS_CASES = frozenset(
    {
        "chameleon_sample_level2_core_skyscraper",
        "chameleon_sample_level2_core_compact_square",
        "chameleon_sample_level3_advanced_skyscraper",
        "chameleon_sample_level3_advanced_medium_rectangle",
        "chameleon_sample_level3_advanced_compact_square",
    }
)
VERTICAL_CASES = frozenset(
    {
        "chameleon_sample_level2_core_skyscraper",
        "chameleon_sample_level2_core_compact_square",
        "chameleon_sample_level3_advanced_skyscraper",
        "chameleon_sample_level3_advanced_compact_square",
    }
)
HORIZONTAL_CASES = frozenset(
    {
        "chameleon_sample_level2_core_compact_square",
        "chameleon_sample_level3_advanced_medium_rectangle",
        "chameleon_sample_level3_advanced_compact_square",
    }
)


class SyntheticRestackFallbackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._synthetic_directory = tempfile.TemporaryDirectory(
            prefix="chameleon-issue-81-cases-"
        )
        cls.synthetic_root = Path(cls._synthetic_directory.name)
        generate_cases(SYNTHETIC_SOURCE, cls.synthetic_root)

    @classmethod
    def tearDownClass(cls):
        cls._synthetic_directory.cleanup()

    def _load_task(self, stem):
        return json.loads(
            (self.synthetic_root / f"{stem}.json").read_text(encoding="utf-8"),
            parse_float=Decimal,
        )


    def test_dense_level3_targets_produce_hard_valid_layouts(self):
        public_task = json.loads(
            (
                CHAMELEON_ROOT
                / "input"
                / "chameleon_sample_level3_advanced.json"
            ).read_text(encoding="utf-8"),
            parse_float=Decimal,
        )
        source = public_task["source"]
        cases = (
            (
                "medium_rectangle",
                {"width": 300, "height": 250},
                generate_horizontal_ribbon_candidate,
            ),
            (
                "skyscraper",
                {"width": 160, "height": 600},
                generate_vertical_restack_candidate,
            ),
        )

        for name, target, solve in cases:
            with self.subTest(target=name):
                candidate = solve(
                    source,
                    target,
                    assets_dir=ASSETS,
                    fonts_dir=FONTS,
                )
                response = candidate.response
                validate_response(
                    source,
                    target,
                    response,
                    fonts_dir=FONTS,
                )
                self.assertEqual(response["canvas"], target)
                self.assertEqual(
                    [element["id"] for element in response["elements"]],
                    [element["id"] for element in source["elements"]],
                )

    def test_level3_compact_square_restack_has_visible_unit_gutters(self):
        public_task = json.loads(
            (
                CHAMELEON_ROOT
                / "input"
                / "chameleon_sample_level3_advanced.json"
            ).read_text(encoding="utf-8"),
            parse_float=Decimal,
        )
        source = public_task["source"]
        target = {"width": 600, "height": 600}
        response = generate_vertical_restack_candidate(
            source,
            target,
            assets_dir=ASSETS,
            fonts_dir=FONTS,
        ).response

        validate_response(source, target, response, fonts_dir=FONTS)
        self.assertEqual(len(response["elements"]), len(source["elements"]))
        self.assertEqual(
            {element.get("group_id") for element in source["elements"]} - {None},
            {"badge1", "badge2", "badge3", "cta", "ribbon"},
        )
        self.assertEqual(
            {
                element.get("group_id")
                for element in response["elements"]
                if element.get("group_id") is not None
            },
            {"badge1", "badge2", "badge3", "cta", "ribbon"},
        )
        for source_group in {
            element["group_id"]
            for element in source["elements"]
            if element.get("group_id") is not None
        }:
            source_group_elements = [
                element
                for element in source["elements"]
                if element.get("group_id") == source_group
            ]
            response_group_elements = [
                element
                for element in response["elements"]
                if element.get("group_id") == source_group
            ]
            derive_quantized_common_transform(
                source_group_elements, response_group_elements
            )

        self.assertGreaterEqual(
            min(
                element["font_size"]
                for element in response["elements"]
                if element["type"] == "text"
            ),
            10,
        )
        badge_bounds = {}
        for badge in ("badge1", "badge2", "badge3"):
            boxes = [
                rotated_aabb(element)
                for element in response["elements"]
                if element.get("group_id") == badge
            ]
            badge_bounds[badge] = (
                min(box[0] for box in boxes),
                min(box[1] for box in boxes),
                max(box[2] for box in boxes),
                max(box[3] for box in boxes),
            )
        for index, first in enumerate(badge_bounds.values()):
            for second in list(badge_bounds.values())[index + 1 :]:
                dx = max(0, first[0] - second[2], second[0] - first[2])
                dy = max(0, first[1] - second[3], second[1] - first[3])
                self.assertGreaterEqual(dx * dx + dy * dy, 36)

        background_index = infer_roles(source).background_index
        source_units = {}
        response_units = {}
        for index, (source_element, response_element) in enumerate(
            zip(source["elements"], response["elements"])
        ):
            if index == background_index:
                continue
            key = (
                ("group", source_element["group_id"])
                if source_element.get("group_id") is not None
                else ("element", index)
            )
            source_units.setdefault(key, []).append(rotated_aabb(source_element))
            response_units.setdefault(key, []).append(rotated_aabb(response_element))

        def intersects(first, second):
            return (
                min(first[2], second[2]) > max(first[0], second[0])
                and min(first[3], second[3]) > max(first[1], second[1])
            )

        source_unit_items = list(source_units.items())
        response_unit_boxes = response_units
        minimum_gap_squared = None
        for index, (first_key, first_boxes) in enumerate(source_unit_items):
            for second_key, second_boxes in source_unit_items[index + 1 :]:
                if any(
                    intersects(first, second)
                    for first in first_boxes
                    for second in second_boxes
                ):
                    continue
                for first, second in (
                    (first, second)
                    for first in response_unit_boxes[first_key]
                    for second in response_unit_boxes[second_key]
                ):
                    dx = max(0, first[0] - second[2], second[0] - first[2])
                    dy = max(0, first[1] - second[3], second[1] - first[3])
                    gap_squared = dx * dx + dy * dy
                    minimum_gap_squared = (
                        gap_squared
                        if minimum_gap_squared is None
                        else min(minimum_gap_squared, gap_squared)
                    )
        self.assertIsNotNone(minimum_gap_squared)
        self.assertGreaterEqual(minimum_gap_squared, 36)

        independent_rows = [
            rotated_aabb(element)
            for element in response["elements"]
            if element["type"] == "text"
            and element.get("group_id") is None
            and element["id"] in {"headline", "subhead", "legal_text"}
        ]
        independent_rows.sort(key=lambda box: box[1])
        for upper, lower in zip(independent_rows, independent_rows[1:]):
            self.assertGreaterEqual(lower[1] - upper[3], 6)

    def test_issue_81_targets_admit_directional_restack_fallbacks(self):
        for stem in ISSUE_81_CASES:
            with self.subTest(case=stem):
                task = self._load_task(stem)
                source = task["source"]
                target = task["target_canvas"]
                if stem in VERTICAL_CASES:
                    self.assertTrue(is_vertical_restack_suitable(source, target))
                if stem in HORIZONTAL_CASES:
                    self.assertTrue(is_horizontal_ribbon_suitable(source, target))

    def test_issue_81_cases_publish_valid_pairs_or_fail_closed(self):
        with tempfile.TemporaryDirectory(prefix="chameleon-issue-81-") as directory:
            root = Path(directory)
            input_dir = root / "input"
            output_dir = root / "output"
            input_dir.mkdir()
            output_dir.mkdir()
            for stem in ISSUE_81_CASES:
                (input_dir / f"{stem}.json").write_bytes(
                    (self.synthetic_root / f"{stem}.json").read_bytes()
                )

            stdout = io.StringIO()
            stderr = io.StringIO()
            with patch.multiple(
                runner_main,
                INPUT_DIR=input_dir,
                OUTPUT_DIR=output_dir,
                ASSETS_DIR=ASSETS,
            ), contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                exit_code = runner_main.main()

            expected_names = set()
            saw_incomplete = False
            for stem in ISSUE_81_CASES:
                task = self._load_task(stem)
                target = task["target_canvas"]
                response_path = output_dir / f"{stem}_output.json"
                png_path = output_dir / f"{stem}_output.png"
                commit_path = output_dir / f".{stem}_output.commit"
                success_line = f"[{stem}.json] status=SUCCESS" in stdout.getvalue()
                incomplete_line = (
                    f"[{stem}.json] status=INCOMPLETE_SEARCH" in stderr.getvalue()
                )
                self.assertNotEqual(
                    success_line, incomplete_line, f"{stem} had no unique terminal status"
                )
                if stem in REQUIRED_SUCCESS_CASES:
                    self.assertTrue(success_line, stderr.getvalue())

                if success_line:
                    expected_names.update(
                        {
                            response_path.name,
                            png_path.name,
                            commit_path.name,
                        }
                    )
                    self.assertTrue(response_path.is_file())
                    self.assertTrue(png_path.is_file())
                    self.assertTrue(commit_path.is_file())
                    response = json.loads(
                        response_path.read_text(encoding="utf-8"),
                        parse_float=Decimal,
                    )
                    validate_response(
                        task["source"], target, response, fonts_dir=FONTS
                    )
                    with Image.open(png_path) as artifact:
                        artifact.verify()
                    with Image.open(png_path) as artifact:
                        self.assertEqual(
                            artifact.size, (target["width"], target["height"])
                        )
                else:
                    saw_incomplete = True
                    with self.assertRaises(InfeasibleLayoutError) as failure:
                        resize(task["source"], target)
                    error = failure.exception
                    self.assertEqual(
                        error.reason_code, InfeasibleReasonCode.INCOMPLETE_SEARCH
                    )
                    self.assertEqual(
                        error.details["status"], "INCOMPLETE_SEARCH"
                    )
                    self.assertFalse(error.details["search_exhausted"])
                    self.assertTrue(error.details["unexamined_work"])
                    self.assertGreater(error.details["evaluated_candidates"], 0)
                    self.assertLessEqual(
                        error.details["evaluated_candidates"],
                        error.details["candidate_count"],
                    )
                    self.assertTrue(error.details["failures"])
                    self.assertFalse(response_path.exists())
                    self.assertFalse(png_path.exists())
                    self.assertFalse(commit_path.exists())

            self.assertEqual(exit_code, int(saw_incomplete), stderr.getvalue())
            self.assertEqual(
                {path.name for path in output_dir.iterdir()}, expected_names
            )



if __name__ == "__main__":
    unittest.main()
