import json
import math
import sys
import unittest
from decimal import Decimal
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
CHAMELEON_ROOT = PROJECT_ROOT / "chameleon"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(CHAMELEON_ROOT) not in sys.path:
    sys.path.insert(0, str(CHAMELEON_ROOT))

from engine.contract import validate_response
from engine.geometry.bounds import rotated_aabb
from engine.layout.near_isomorphic import _text_fits
from engine.resize import resize
from renderer.converter.brand_fonts import load_brand_font_manager

FIXTURE = CHAMELEON_ROOT / "input" / "chameleon_sample_level3_advanced.json"


FONTS = CHAMELEON_ROOT / "brand_kit" / "fonts"


def _gap(left, right):
    dx = max(left[0] - right[2], right[0] - left[2], 0)
    dy = max(left[1] - right[3], right[1] - left[3], 0)
    return math.hypot(dx, dy)


def _group_aabb(elements):
    bounds = [rotated_aabb(element) for element in elements]
    return (
        min(box[0] for box in bounds),
        min(box[1] for box in bounds),
        max(box[2] for box in bounds),
        max(box[3] for box in bounds),
    )


class MediumRectanglePolishTests(unittest.TestCase):
    def test_l3_medium_rectangle_compact_profile_polishes_spacing_and_type(self):
        source_document = json.loads(
            FIXTURE.read_text(encoding="utf-8"), parse_float=Decimal
        )
        source = source_document["source"]
        target = {"width": 300, "height": 250}
        serialized = json.loads(
            json.dumps(resize(source, target)), parse_float=Decimal
        )

        validate_response(source, target, serialized)
        source_ids = [element["id"] for element in source["elements"]]
        output_ids = [element["id"] for element in serialized["elements"]]
        self.assertEqual(output_ids, source_ids)
        self.assertEqual(len(serialized["elements"]), len(source["elements"]))

        output = {element["id"]: element for element in serialized["elements"]}
        foreground = [
            element for element in serialized["elements"] if element["id"] != "bg"
        ]
        foreground_aabbs = [rotated_aabb(element) for element in foreground]
        margins = (
            min(box[0] for box in foreground_aabbs),
            min(box[1] for box in foreground_aabbs),
            target["width"] - max(box[2] for box in foreground_aabbs),
            target["height"] - max(box[3] for box in foreground_aabbs),
        )
        for margin in margins:
            with self.subTest(margin=margin):
                self.assertGreaterEqual(margin, 6)
                self.assertLessEqual(margin, 10)

        badge_boxes = [
            _group_aabb(
                [
                    element
                    for element in serialized["elements"]
                    if element.get("group_id") == f"badge{number}"
                ]
            )
            for number in (1, 2, 3)
        ]
        badge_gaps = [
            _gap(left, right)
            for index, left in enumerate(badge_boxes)
            for right in badge_boxes[index + 1 :]
        ]
        self.assertGreaterEqual(min(badge_gaps), 6)

        source_units = {}
        output_units = {}
        for source_element, output_element in zip(
            source["elements"], serialized["elements"]
        ):
            if source_element["id"] == "bg":
                continue
            unit = source_element.get("group_id") or source_element["id"]
            source_units.setdefault(unit, []).append(source_element)
            output_units.setdefault(unit, []).append(output_element)
        independent_gaps = []
        source_unit_boxes = [
            _group_aabb(elements) for elements in source_units.values()
        ]
        output_unit_boxes = [
            _group_aabb(output_units[unit]) for unit in source_units
        ]
        for index, source_left in enumerate(source_unit_boxes):
            for right_index in range(index + 1, len(source_unit_boxes)):
                if _gap(source_left, source_unit_boxes[right_index]) > 0:
                    independent_gaps.append(
                        _gap(output_unit_boxes[index], output_unit_boxes[right_index])
                    )
        self.assertTrue(independent_gaps)
        self.assertGreaterEqual(min(independent_gaps), 4)

        font_manager = load_brand_font_manager(str(FONTS))
        headline = output["headline"]
        if _text_fits(headline, 11, font_manager, target):
            self.assertGreaterEqual(headline["font_size"], 11)
        for element_id in ("subhead", "legal_text"):
            text = output[element_id]
            if _text_fits(text, 8, font_manager, target):
                self.assertGreaterEqual(text["font_size"], 8)
            elif _text_fits(text, 7, font_manager, target):
                self.assertGreaterEqual(text["font_size"], 7)


if __name__ == "__main__":
    unittest.main()
