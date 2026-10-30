"""Regression coverage for source-derived wide-landscape layouts."""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
import unittest

try:
    from engine.contract import validate_response
    from engine.geometry.bounds import (
        positive_aabb_intersection,
        rotated_aabb,
        source_bleed_sides,
    )
    from engine.layout.roles import infer_roles
    from engine.resize import resize
except ModuleNotFoundError:
    from chameleon.engine.contract import validate_response
    from chameleon.engine.geometry.bounds import (
        positive_aabb_intersection,
        rotated_aabb,
        source_bleed_sides,
    )
    from chameleon.engine.layout.roles import infer_roles
    from chameleon.engine.resize import resize


ROOT = Path(__file__).resolve().parents[2]
FONTS = ROOT / "brand_kit" / "fonts"
FIXTURES = (
    ("chameleon_sample_level1_warmup.json", 0.151, 48),
    ("chameleon_sample_level3_advanced.json", 0.233, 331),
)
TARGET = {"width": 1200, "height": 630}
MUTABLE_FIELDS = {"x", "y", "width", "height", "font_size"}


def _load_source(filename: str) -> dict:
    with (ROOT / "input" / filename).open(encoding="utf-8") as fixture:
        return json.load(fixture)["source"]


def _metrics(source: dict, response: dict) -> tuple[float, tuple[float, float, float, float]]:
    model = infer_roles(source)
    foreground = [
        element
        for index, element in enumerate(response["elements"])
        if index != model.background_index
    ]
    boxes = [rotated_aabb(element) for element in foreground]
    x_edges = sorted({edge for box in boxes for edge in (box[0], box[2])})
    union_area = 0.0
    for left, right in zip(x_edges, x_edges[1:]):
        intervals = sorted(
            (box[1], box[3])
            for box in boxes
            if box[0] < right and box[2] > left
        )
        if not intervals:
            continue
        covered_height = 0.0
        interval_top, interval_bottom = intervals[0]
        for top, bottom in intervals[1:]:
            if top <= interval_bottom:
                interval_bottom = max(interval_bottom, bottom)
            else:
                covered_height += interval_bottom - interval_top
                interval_top, interval_bottom = top, bottom
        covered_height += interval_bottom - interval_top
        union_area += (right - left) * covered_height
    utilization = union_area / (TARGET["width"] * TARGET["height"])
    margins = (
        min(box[0] for box in boxes),
        min(box[1] for box in boxes),
        TARGET["width"] - max(box[2] for box in boxes),
        TARGET["height"] - max(box[3] for box in boxes),
    )
    return utilization, margins


class LandscapeUtilizationTests(unittest.TestCase):
    def test_wide_landscape_copy_allocation_and_balance_remain_hard_valid(self):
        for fixture, baseline_utilization, baseline_margin_difference in FIXTURES:
            with self.subTest(fixture=fixture):
                source = _load_source(fixture)
                source_before = json.loads(json.dumps(source))
                response = resize(source, TARGET)
                validate_response(source, TARGET, response, fonts_dir=str(FONTS))

                self.assertEqual(source, source_before)
                self.assertEqual(response["canvas"], TARGET)
                self.assertEqual(
                    [element["id"] for element in response["elements"]],
                    [element["id"] for element in source["elements"]],
                )
                for source_element, output_element in zip(
                    source["elements"], response["elements"]
                ):
                    self.assertEqual(source_element.keys(), output_element.keys())
                    for field in source_element.keys() - MUTABLE_FIELDS:
                        self.assertEqual(output_element[field], source_element[field])
                    for field in MUTABLE_FIELDS.intersection(output_element):
                        self.assertIs(type(output_element[field]), int)

                utilization, margins = _metrics(source, response)
                self.assertGreater(utilization, baseline_utilization + 0.02)
                margin_difference = abs(margins[0] - margins[2])
                if "level3_advanced" in fixture:
                    self.assertLess(margins[2], 331)
                self.assertLess(margin_difference, baseline_margin_difference)
                self.assertLessEqual(margin_difference, 120)

                model = infer_roles(source)
                for first in range(len(source["elements"])):
                    if first == model.background_index:
                        continue
                    source_first = rotated_aabb(source["elements"][first])
                    output_first = rotated_aabb(response["elements"][first])
                    for second in range(first + 1, len(source["elements"])):
                        if second == model.background_index:
                            continue
                        if positive_aabb_intersection(
                            source_first, rotated_aabb(source["elements"][second])
                        ):
                            continue
                        self.assertFalse(
                            positive_aabb_intersection(
                                output_first,
                                rotated_aabb(response["elements"][second]),
                            ),
                            msg=(
                                f"new foreground collision between "
                                f"{source['elements'][first]['id']} and "
                                f"{source['elements'][second]['id']}"
                            ),
                        )

    def test_nonportrait_foreground_envelope_is_centered_on_both_axes(self):
        cases = (
            ("chameleon_sample_level1_warmup.json", 1200, 630),
            ("chameleon_sample_level1_warmup.json", 970, 250),
            ("chameleon_sample_level1_warmup.json", 300, 250),
            ("chameleon_sample_level2_core.json", 1200, 630),
            ("chameleon_sample_level2_core.json", 300, 250),
            ("chameleon_sample_level2_core.json", 600, 600),
        )
        for fixture, width, height in cases:
            with self.subTest(fixture=fixture, target=(width, height)):
                source_document = json.loads(
                    (ROOT / "input" / fixture).read_text(encoding="utf-8"),
                    parse_float=Decimal,
                )
                source = source_document["source"]
                target = {"width": width, "height": height}
                response = resize(source, target)
                validate_response(
                    source, target, response, fonts_dir=str(FONTS)
                )

                roles = infer_roles(source)
                foreground_boxes = [
                    rotated_aabb(response["elements"][index])
                    for index, source_element in enumerate(source["elements"])
                    if index != roles.background_index
                    and source_bleed_sides(
                        source_element,
                        rotated_aabb(source_element),
                        source["canvas"],
                    )
                    is None
                ]
                margins = (
                    min(box.min_x for box in foreground_boxes),
                    min(box.min_y for box in foreground_boxes),
                    width - max(box.max_x for box in foreground_boxes),
                    height - max(box.max_y for box in foreground_boxes),
                )
                self.assertLessEqual(abs(margins[0] - margins[2]), 1)
                self.assertLessEqual(abs(margins[1] - margins[3]), 1)

if __name__ == "__main__":
    unittest.main()
