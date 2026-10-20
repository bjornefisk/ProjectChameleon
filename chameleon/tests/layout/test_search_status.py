import copy
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    import engine.layout.search as search_module
    from engine.errors import InfeasibleLayoutError, InfeasibleReasonCode
    from engine.layout.search import CandidateSpec
except ModuleNotFoundError:
    import chameleon.engine.layout.search as search_module
    from chameleon.engine.errors import InfeasibleLayoutError, InfeasibleReasonCode
    from chameleon.engine.layout.search import CandidateSpec


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

    def _search_with_family_failures(self, failures, *, max_candidates=4):
        specs = tuple(
            CandidateSpec(family, "source_proportional", index, 0, 0, index)
            for index, family in enumerate(failures)
        )

        def solver_for(family):
            def solver(_source, _target, **_kwargs):
                raise failures[family]

            return solver

        solvers = tuple(solver_for(family) for family in failures)
        with patch.object(search_module, "enumerate_candidate_specs", return_value=specs):
            with patch.object(search_module, "_TOPOLOGY_SOLVERS", solvers):
                with self.assertRaises(InfeasibleLayoutError) as raised:
                    search_module.search(
                        copy.deepcopy(self.source()),
                        self.target(),
                        max_candidates=max_candidates,
                    )
        return raised.exception

    def test_all_exhausted_families_map_to_proven_infeasibility(self):
        failures = {
            family: InfeasibleLayoutError(
                InfeasibleReasonCode.INCOMPLETE_SEARCH,
                f"{family} exhausted",
                {"search_exhausted": True},
            )
            for family in (
                "horizontal_ribbon",
                "vertical_restack",
                "column_pivot",
                "near_isomorphic",
            )
        }

        error = self._search_with_family_failures(failures)

        self.assertEqual(error.reason_code, InfeasibleReasonCode.NO_HARD_VALID_CANDIDATE)
        self.assertTrue(error.details["search_exhausted"])
        self.assertEqual(
            {failure["topology"] for failure in error.details["failures"]},
            set(failures),
        )
        self.assertTrue(
            all(
                failure["details"]["search_exhausted"]
                for failure in error.details["failures"]
            )
        )

    def test_cutoff_keeps_aggregate_status_incomplete(self):
        failures = {
            family: InfeasibleLayoutError(
                InfeasibleReasonCode.INCOMPLETE_SEARCH,
                f"{family} exhausted",
                {"search_exhausted": True},
            )
            for family in (
                "near_isomorphic",
                "column_pivot",
                "horizontal_ribbon",
                "vertical_restack",
            )
        }
        error = self._search_with_family_failures(failures, max_candidates=3)
        self.assertEqual(error.reason_code, InfeasibleReasonCode.INCOMPLETE_SEARCH)
        self.assertFalse(error.details["search_exhausted"])
        self.assertTrue(error.details["cutoff"])

    def test_missing_exhaustion_metadata_defaults_to_incomplete(self):
        failures = {
            family: InfeasibleLayoutError(
                InfeasibleReasonCode.INCOMPLETE_SEARCH,
                f"{family} exhausted",
                {"search_exhausted": True} if family != "column_pivot" else {},
            )
            for family in (
                "horizontal_ribbon",
                "vertical_restack",
                "column_pivot",
                "near_isomorphic",
            )
        }
        error = self._search_with_family_failures(failures)
        self.assertEqual(error.reason_code, InfeasibleReasonCode.INCOMPLETE_SEARCH)
        self.assertFalse(error.details["search_exhausted"])
        self.assertFalse(
            next(
                failure["details"]["search_exhausted"]
                for failure in error.details["failures"]
                if failure["topology"] == "column_pivot"
            )
        )

    def test_non_boolean_exhaustion_metadata_defaults_to_incomplete(self):
        failures = {
            family: InfeasibleLayoutError(
                InfeasibleReasonCode.INCOMPLETE_SEARCH,
                f"{family} exhausted",
                {"search_exhausted": True},
            )
            for family in (
                "horizontal_ribbon",
                "vertical_restack",
                "column_pivot",
                "near_isomorphic",
            )
        }
        failures["column_pivot"] = InfeasibleLayoutError(
            InfeasibleReasonCode.INCOMPLETE_SEARCH,
            "column metadata is not boolean",
            {"search_exhausted": "true"},
        )
        error = self._search_with_family_failures(failures)
        self.assertEqual(error.reason_code, InfeasibleReasonCode.INCOMPLETE_SEARCH)
        self.assertFalse(error.details["search_exhausted"])
        self.assertIs(
            next(
                failure["details"]["search_exhausted"]
                for failure in error.details["failures"]
                if failure["topology"] == "column_pivot"
            ),
            False,
        )

    def test_outer_response_validation_rejection_is_not_exhaustion(self):
        validator_error = InfeasibleLayoutError(
            InfeasibleReasonCode.CONTAINMENT_VIOLATION,
            "candidate was not contained",
            {"index": 0},
        )
        specs = (CandidateSpec("near_isomorphic", "source_proportional", 0, 0, 0, 0),)
        response = {
            "canvas": self.target(),
            "elements": copy.deepcopy(self.source()["elements"]),
        }
        with patch.object(search_module, "enumerate_candidate_specs", return_value=specs):
            with patch.object(
                search_module,
                "_TOPOLOGY_SOLVERS",
                (lambda _source, _target, **_kwargs: response,),
            ):
                with patch.object(
                    search_module, "validate_response", side_effect=validator_error
                ):
                    with self.assertRaises(InfeasibleLayoutError) as raised:
                        search_module.search(copy.deepcopy(self.source()), self.target())

        error = raised.exception
        self.assertEqual(error.reason_code, InfeasibleReasonCode.INCOMPLETE_SEARCH)
        self.assertFalse(error.details["search_exhausted"])
        self.assertFalse(error.details["failures"][0]["details"]["search_exhausted"])

if __name__ == "__main__":
    unittest.main()
