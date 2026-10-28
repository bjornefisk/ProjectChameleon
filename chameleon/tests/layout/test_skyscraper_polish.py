from copy import deepcopy
import json
import sys
import unittest
from decimal import Decimal
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from engine.contract import validate_response
    from engine.geometry.bounds import positive_aabb_intersection, rotated_aabb
    from engine.geometry.ratios import preserves_source_ratio
    from engine.layout.roles import infer_roles
    from engine.resize import resize
except ModuleNotFoundError:
    from chameleon.engine.contract import validate_response
    from chameleon.engine.geometry.bounds import positive_aabb_intersection, rotated_aabb
    from chameleon.engine.geometry.ratios import preserves_source_ratio
    from chameleon.engine.layout.roles import infer_roles
    from chameleon.engine.resize import resize

ROOT = Path(__file__).resolve().parents[2]
INPUT = ROOT / "input"
TARGET = {"width": 160, "height": 600}
SAMPLES = (
    "chameleon_sample_level1_warmup.json",
    "chameleon_sample_level2_core.json",
    "chameleon_sample_level3_advanced.json",
)


class SkyscraperPolishTests(unittest.TestCase):
    def _load_source(self, filename):
        task = json.loads(
            (INPUT / filename).read_text(encoding="utf-8"),
            parse_int=int,
            parse_float=Decimal,
        )
        return task["source"]

    def test_public_samples_use_balanced_vertical_slack_and_valid_geometry(self):
        for filename in SAMPLES:
            with self.subTest(sample=filename):
                source = self._load_source(filename)
                source_before = deepcopy(source)
                response = resize(source, TARGET)
                validate_response(source, TARGET, response)
                self.assertEqual(source, source_before)

                source_elements = source["elements"]
                elements = response["elements"]
                self.assertEqual(
                    [element["id"] for element in elements],
                    [element["id"] for element in source_elements],
                )
                self.assertEqual(
                    [element["type"] for element in elements],
                    [element["type"] for element in source_elements],
                )
                self.assertEqual(response["canvas"], TARGET)
                background = infer_roles(source).background_index
                for index, element in enumerate(elements):
                    for key in ("x", "y", "width", "height"):
                        self.assertIs(type(element[key]), int)
                    if index == background or element["type"] != "image":
                        continue
                    source_element = source_elements[index]
                    if source_element["width"] and source_element["height"]:
                        self.assertTrue(
                            preserves_source_ratio(
                                element["width"],
                                element["height"],
                                source_element["width"],
                                source_element["height"],
                            )
                        )

                foreground = [
                    rotated_aabb(element)
                    for index, element in enumerate(elements)
                    if index != background
                    and element["width"] > 0
                    and element["height"] > 0
                ]

                content_top = min(box.min_y for box in foreground)
                content_bottom = max(box.max_y for box in foreground)
                top_margin = max(0, content_top)
                bottom_margin = max(0, TARGET["height"] - content_bottom)
                self.assertLessEqual(abs(top_margin - bottom_margin), 60)
                self.assertLessEqual(bottom_margin, 100)

                if filename == "chameleon_sample_level3_advanced.json":
                    self.assertLessEqual(top_margin, 34)
                    self.assertEqual(bottom_margin, 0)

                # Grouped records form one rigid unit; ungrouped records remain
                # independent. Check only source-separated units whose output
                # envelopes are vertically adjacent and overlap horizontally.
                source_boxes = [rotated_aabb(element) for element in source_elements]
                output_boxes = [rotated_aabb(element) for element in elements]
                groups = {}
                for index, element in enumerate(source_elements):
                    unit = (
                        ("group", element["group_id"])
                        if element.get("group_id") is not None
                        else ("element", index)
                    )
                    groups.setdefault(unit, []).append(index)
                units = list(groups.values())
                minimum_gutter = None
                for left_position, left_indices in enumerate(units):
                    for right_indices in units[left_position + 1:]:
                        left_source = [source_boxes[i] for i in left_indices]
                        right_source = [source_boxes[i] for i in right_indices]
                        if any(
                            positive_aabb_intersection(a, b)
                            for a in left_source
                            for b in right_source
                        ):
                            continue
                        left_output = [output_boxes[i] for i in left_indices]
                        right_output = [output_boxes[i] for i in right_indices]
                        left_x = (
                            min(box.min_x for box in left_output),
                            max(box.max_x for box in left_output),
                        )
                        right_x = (
                            min(box.min_x for box in right_output),
                            max(box.max_x for box in right_output),
                        )
                        if min(left_x[1], right_x[1]) <= max(left_x[0], right_x[0]):
                            continue
                        left_y = (
                            min(box.min_y for box in left_output),
                            max(box.max_y for box in left_output),
                        )
                        right_y = (
                            min(box.min_y for box in right_output),
                            max(box.max_y for box in right_output),
                        )
                        if left_y[1] <= right_y[0]:
                            gutter = right_y[0] - left_y[1]
                        elif right_y[1] <= left_y[0]:
                            gutter = left_y[0] - right_y[1]
                        else:
                            self.fail("source-separated units overlap vertically")
                        self.assertGreaterEqual(gutter, 6)
                        minimum_gutter = (
                            gutter
                            if minimum_gutter is None
                            else min(minimum_gutter, gutter)
                        )

                if filename == "chameleon_sample_level3_advanced.json":
                    self.assertIsNotNone(minimum_gutter)
                    self.assertGreaterEqual(minimum_gutter, 6)

if __name__ == "__main__":
    unittest.main()
