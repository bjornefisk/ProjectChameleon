import copy
import sys
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    import engine.resize as resize_module
    from engine.errors import InfeasibleLayoutError, InfeasibleReasonCode
except ModuleNotFoundError:
    import chameleon.engine.resize as resize_module
    from chameleon.engine.errors import InfeasibleLayoutError, InfeasibleReasonCode


class ResizeSearchStatusTests(unittest.TestCase):
    @staticmethod
    def source():
        return {
            "canvas": {"width": 100, "height": 100},
            "elements": [
                {
                    "id": "background",
                    "type": "shape",
                    "x": 0,
                    "y": 0,
                    "width": 100,
                    "height": 100,
                    "z_index": 0,
                    "shape_type": "rectangle",
                    "fill_color": "rgba(0,0,0,1)",
                }
            ],
        }

    @staticmethod
    def target():
        return {"width": 90, "height": 90}

    def _resize_with_family_failures(self, failures):
        families = (
            ("is_horizontal_ribbon_suitable", "solve_horizontal_ribbon", "horizontal_ribbon"),
            ("is_vertical_restack_suitable", "solve_vertical_restack", "vertical_restack"),
            ("is_column_pivot_suitable", "solve_column_pivot", "column_pivot"),
            (None, "solve_near_isomorphic", "near_isomorphic"),
        )
        with ExitStack() as stack:
            for suitability_name, solver_name, family_name in families:
                if suitability_name is not None:
                    stack.enter_context(
                        patch.object(resize_module, suitability_name, return_value=True)
                    )
                stack.enter_context(
                    patch.object(
                        resize_module,
                        solver_name,
                        side_effect=failures[family_name],
                    )
                )
            with self.assertRaises(InfeasibleLayoutError) as raised:
                resize_module.resize(copy.deepcopy(self.source()), self.target())
        return raised.exception

    def test_all_exhausted_families_map_to_proven_infeasibility(self):
        failures = {
            family: InfeasibleLayoutError(
                InfeasibleReasonCode.INCOMPLETE_SEARCH,
                f"{family} exhausted",
                {"search_exhausted": True},
            )
            for family in ("horizontal_ribbon", "vertical_restack", "column_pivot", "near_isomorphic")
        }

        error = self._resize_with_family_failures(failures)

        self.assertEqual(error.reason_code, InfeasibleReasonCode.NO_HARD_VALID_CANDIDATE)
        self.assertTrue(error.details["search_exhausted"])
        self.assertEqual(set(error.details["candidate_failures"]), set(failures))
        self.assertTrue(
            all(
                failure["details"]["search_exhausted"]
                for failure in error.details["candidate_failures"].values()
            )
        )

    def test_cutoff_family_keeps_aggregate_status_incomplete(self):
        failures = {
            "horizontal_ribbon": InfeasibleLayoutError(
                InfeasibleReasonCode.INCOMPLETE_SEARCH,
                "horizontal exhausted",
                {"search_exhausted": True},
            ),
            "vertical_restack": InfeasibleLayoutError(
                InfeasibleReasonCode.INCOMPLETE_SEARCH,
                "vertical cutoff",
                {"search_exhausted": False},
            ),
            "column_pivot": InfeasibleLayoutError(
                InfeasibleReasonCode.INCOMPLETE_SEARCH,
                "column exhausted",
                {"search_exhausted": True},
            ),
            "near_isomorphic": InfeasibleLayoutError(
                InfeasibleReasonCode.INCOMPLETE_SEARCH,
                "near exhausted",
                {"search_exhausted": True},
            ),
        }

        error = self._resize_with_family_failures(failures)

        self.assertEqual(error.reason_code, InfeasibleReasonCode.INCOMPLETE_SEARCH)
        self.assertFalse(error.details["search_exhausted"])
        self.assertFalse(
            error.details["candidate_failures"]["vertical_restack"]["details"]["search_exhausted"]
        )

    def test_missing_exhaustion_metadata_defaults_to_incomplete(self):
        failures = {
            family: InfeasibleLayoutError(
                InfeasibleReasonCode.INCOMPLETE_SEARCH,
                f"{family} exhausted",
                {"search_exhausted": True} if family != "column_pivot" else {},
            )
            for family in ("horizontal_ribbon", "vertical_restack", "column_pivot", "near_isomorphic")
        }

        error = self._resize_with_family_failures(failures)

        self.assertEqual(error.reason_code, InfeasibleReasonCode.INCOMPLETE_SEARCH)
        self.assertFalse(error.details["search_exhausted"])
        self.assertFalse(
            error.details["candidate_failures"]["column_pivot"]["details"]["search_exhausted"]
        )

    def test_non_boolean_exhaustion_metadata_defaults_to_incomplete(self):
        failures = {
            family: InfeasibleLayoutError(
                InfeasibleReasonCode.INCOMPLETE_SEARCH,
                f"{family} exhausted",
                {"search_exhausted": True},
            )
            for family in ("horizontal_ribbon", "vertical_restack", "column_pivot", "near_isomorphic")
        }
        failures["column_pivot"] = InfeasibleLayoutError(
            InfeasibleReasonCode.INCOMPLETE_SEARCH,
            "column metadata is not boolean",
            {"search_exhausted": "true"},
        )

        error = self._resize_with_family_failures(failures)

        self.assertEqual(error.reason_code, InfeasibleReasonCode.INCOMPLETE_SEARCH)
        self.assertFalse(error.details["search_exhausted"])
        self.assertIs(
            error.details["candidate_failures"]["column_pivot"]["details"]["search_exhausted"],
            False,
        )

    def test_outer_response_validation_rejection_is_not_exhaustion(self):
        validator_error = InfeasibleLayoutError(
            InfeasibleReasonCode.CONTAINMENT_VIOLATION,
            "candidate was not contained",
            {"index": 0},
        )
        response = {
            "canvas": self.target(),
            "elements": copy.deepcopy(self.source()["elements"]),
        }
        with ExitStack() as stack:
            for suitability_name in (
                "is_horizontal_ribbon_suitable",
                "is_vertical_restack_suitable",
                "is_column_pivot_suitable",
            ):
                stack.enter_context(
                    patch.object(resize_module, suitability_name, return_value=False)
                )
            stack.enter_context(
                patch.object(resize_module, "solve_near_isomorphic", return_value=response)
            )
            stack.enter_context(
                patch.object(resize_module, "validate_response", side_effect=validator_error)
            )
            with self.assertRaises(InfeasibleLayoutError) as raised:
                resize_module.resize(copy.deepcopy(self.source()), self.target())

        error = raised.exception
        self.assertEqual(error.reason_code, InfeasibleReasonCode.INCOMPLETE_SEARCH)
        failure = error.details["candidate_failures"]["near_isomorphic"]
        self.assertIs(failure["details"]["search_exhausted"], False)
        self.assertFalse(error.details["search_exhausted"])


if __name__ == "__main__":
    unittest.main()
