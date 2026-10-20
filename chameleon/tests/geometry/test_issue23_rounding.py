import copy
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

from engine import staging
from engine.contract import validate_response
from engine.errors import InfeasibleLayoutError, InfeasibleReasonCode


class Issue23RoundingRegressionTests(unittest.TestCase):
    def test_serializer_rounds_signed_geometry_and_text_ties_then_validates(self):
        source = {
            "canvas": {"width": 10, "height": 10},
            "elements": [
                {
                    "id": "bleed",
                    "type": "shape",
                    "x": Decimal("-2.5"),
                    "y": Decimal("3.5"),
                    "width": Decimal("5.5"),
                    "height": Decimal("3.5"),
                    "opacity": Decimal("0.5"),
                    "shape_type": "rectangle",
                    "fill_color": "rgba(0,0,0,1)",
                },
                {
                    "id": "label",
                    "type": "text",
                    "x": 4,
                    "y": 0,
                    "width": 6,
                    "height": 10,
                    "content": "T",
                    "font_family": "Solstice Sans",
                    "font_size": Decimal("3.5"),
                    "color": "rgba(0,0,0,1)",
                    "text_align": "center",
                },
            ],
        }

        with tempfile.TemporaryDirectory() as directory:
            serialized = staging._publish_response_json(
                copy.deepcopy(source), Path(directory) / "candidate.json"
            )

        self.assertEqual(serialized["elements"][0]["x"], -2)
        self.assertEqual(serialized["elements"][0]["y"], 4)
        self.assertEqual(serialized["elements"][0]["width"], 6)
        self.assertEqual(serialized["elements"][0]["height"], 4)
        self.assertEqual(serialized["elements"][1]["font_size"], 4)
        validate_response(source, source["canvas"], serialized)

    def test_ratio_valid_before_serialization_is_rejected_after_integer_rounding(self):
        source = {
            "canvas": {"width": 20, "height": 20},
            "elements": [
                {
                    "id": "foreground",
                    "type": "image",
                    "x": 1,
                    "y": 1,
                    "width": 5,
                    "height": 7,
                    "asset_id": "product.png",
                    "fit": "fill",
                }
            ],
        }
        response = {
            "canvas": {"width": 20, "height": 20},
            "elements": [
                {
                    **source["elements"][0],
                    "x": 2,
                    "y": 2,
                    "width": Decimal("2.5"),
                    "height": Decimal("3.5"),
                }
            ],
        }

        source_image = source["elements"][0]
        response_image = response["elements"][0]
        self.assertEqual(
            response_image["width"] * source_image["height"],
            response_image["height"] * source_image["width"],
        )
        with tempfile.TemporaryDirectory() as directory:
            serialized = staging._publish_response_json(
                response, Path(directory) / "candidate.json"
            )

        self.assertEqual(serialized["elements"][0]["width"], 2)
        self.assertEqual(serialized["elements"][0]["height"], 4)
        with self.assertRaises(InfeasibleLayoutError) as raised:
            validate_response(source, source["canvas"], serialized)
        self.assertEqual(
            raised.exception.reason_code, InfeasibleReasonCode.IMAGE_RATIO_VIOLATION
        )
        self.assertEqual(raised.exception.code, "IMAGE_RATIO_VIOLATION")
        self.assertEqual(raised.exception.details["response_width"], 2)
        self.assertEqual(raised.exception.details["response_height"], 4)


if __name__ == "__main__":
    unittest.main()
