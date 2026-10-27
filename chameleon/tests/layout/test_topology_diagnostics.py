import unittest
from unittest.mock import patch

from engine.errors import InfeasibleLayoutError, InfeasibleReasonCode
from engine.layout.horizontal_ribbon import generate_horizontal_ribbon_candidate
from engine.layout.vertical_restack import generate_vertical_restack_candidate


class TopologyDiagnosticTests(unittest.TestCase):
    def setUp(self):
        self.source = {
            "canvas": {"width": 100, "height": 100},
            "elements": [
                {
                    "id": "content",
                    "type": "shape",
                    "x": 20,
                    "y": 20,
                    "width": 30,
                    "height": 20,
                    "shape_type": "rectangle",
                    "fill_color": "rgba(255,0,0,1)",
                }
            ],
        }

    def _assert_incomplete_topology(self, error, expected_kind):
        self.assertEqual(
            error.exception.reason_code, InfeasibleReasonCode.INCOMPLETE_SEARCH
        )
        self.assertEqual(error.exception.details["search_kind"], expected_kind)
        self.assertFalse(error.exception.details["search_exhausted"])

    def test_vertical_restack_failure_identifies_its_topology(self):
        with self.assertRaises(InfeasibleLayoutError) as error:
            generate_vertical_restack_candidate(
                self.source, {"width": 200, "height": 100}
            )

        self._assert_incomplete_topology(error, "vertical_restack")

    @patch("engine.layout.horizontal_ribbon._valid_plan_placement", return_value=False)
    def test_vertical_restack_exhaustion_keeps_its_topology_identity(
        self, _valid_plan_placement
    ):
        with self.assertRaises(InfeasibleLayoutError) as error:
            generate_vertical_restack_candidate(
                self.source, {"width": 10, "height": 200}
            )

        self.assertEqual(
            error.exception.reason_code, InfeasibleReasonCode.INCOMPLETE_SEARCH
        )
        self.assertEqual(error.exception.details["search_kind"], "vertical_restack")
        self.assertTrue(error.exception.details["search_exhausted"])

    def test_horizontal_ribbon_failure_keeps_its_topology_identity(self):
        with self.assertRaises(InfeasibleLayoutError) as error:
            generate_horizontal_ribbon_candidate(
                self.source, {"width": 100, "height": 200}
            )

        self._assert_incomplete_topology(error, "horizontal_ribbon")


if __name__ == "__main__":
    unittest.main()
