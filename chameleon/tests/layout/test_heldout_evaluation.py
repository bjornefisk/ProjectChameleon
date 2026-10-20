import sys
import unittest
from collections import Counter
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.evaluate_heldout_search import evaluate_corpus, load_corpus


CORPUS = PROJECT_ROOT / "chameleon" / "tests" / "fixtures" / "heldout_search_cases.json"
REQUIRED_FAMILIES = {
    "near_isomorphic",
    "column_pivot",
    "horizontal_ribbon",
    "vertical_restack",
}
# Each authored case was designed to exercise one family's route
# (Docs/IMPLEMENTATION/tickets/08-heldout-evaluation.md, "Corpus provenance and
# scope").  ADR-009 section 3 only describes the regime each family serves; the
# per-case pairing is corpus design intent, so a failure below means the corpus no
# longer exercises that route and the corpus or solver change must be reviewed,
# not that the ADR mandates the pairing.
INTENDED_FAMILY = {
    "isomorphic-gallery": "near_isomorphic",
    "column-pivot-catalog": "column_pivot",
    "horizontal-ribbon-journal": "horizontal_ribbon",
    "vertical-restack-studio": "vertical_restack",
}
SOFT_COMPONENTS = {"readability", "balance", "alignment", "hierarchy"}
# ADR-009 section 3: at most twelve candidates before any rejection.
ADR_009_MAX_CANDIDATES = 12
# ranking.SCORE_SCALE: fixed-point components are integers in 0..1000.
SCORE_SCALE = 1000


class HeldoutEvaluationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # The real search is slow; run the evaluator exactly once for the class.
        cls.corpus = load_corpus(CORPUS)
        cls.report = evaluate_corpus(cls.corpus, repeats=2)
        cls.cases = {case["id"]: case for case in cls.report["cases"]}

    def test_report_covers_exactly_the_corpus_cases_in_order(self):
        self.assertEqual(
            [case["id"] for case in self.report["cases"]],
            [case["id"] for case in self.corpus["cases"]],
        )
        self.assertEqual(self.report["hard_evidence"]["case_count"], len(self.corpus["cases"]))
        self.assertEqual(set(INTENDED_FAMILY) | {"missing-asset-diagnostic"}, set(self.cases))

    def test_every_case_is_hard_valid_stable_and_within_the_candidate_bound(self):
        for case_id, case in self.cases.items():
            hard = case["hard_evidence"]
            with self.subTest(case=case_id):
                # ADR-006/ADR-009 section 6: SUCCESS requires a hard-valid candidate.
                self.assertEqual(hard["status"], "SUCCESS")
                # Independent validate_response over every admitted candidate and the
                # selected response (evaluator records any failure here).
                self.assertEqual(hard["hard_validation_errors"], [])
                self.assertIs(hard["source_unchanged"], True)
                self.assertIs(hard["deterministic_repeated"], True)
                self.assertIs(hard["cutoff"], False)
                self.assertLessEqual(hard["candidate_count"], ADR_009_MAX_CANDIDATES)
                # No cutoff means the whole bounded work set was evaluated.
                self.assertEqual(hard["evaluated_candidates"], hard["candidate_count"])
                self.assertGreater(hard["admitted_candidates"], 0)
                self.assertEqual(hard["hard_valid_candidates"], hard["admitted_candidates"])
                # Every evaluated work item is either admitted or a recorded typed
                # rejection (ADR-009 section 4: admission only if all hard checks
                # pass; section 8: each hard-failure reason code is recorded). A
                # SUCCESS case has no top-level reason code, so the reason histogram
                # counts exactly the per-item rejections.
                self.assertEqual(
                    sum(hard["reason_code_distribution"].values()),
                    hard["evaluated_candidates"] - hard["admitted_candidates"],
                )

    def test_intended_family_is_admitted_for_each_authored_case(self):
        # Admission evidence: the family appears among hard-valid, rendered
        # candidates, not merely in the enumerated work set.
        for case_id, family in INTENDED_FAMILY.items():
            with self.subTest(case=case_id, family=family):
                admitted = self.cases[case_id]["hard_evidence"]["admitted_topology_coverage"]
                self.assertIn(family, admitted)

    def test_union_of_admitted_families_covers_all_four_topologies(self):
        admitted_union = set()
        for case in self.report["cases"]:
            admitted_union.update(case["hard_evidence"]["admitted_topology_coverage"])
        # Per-case admitted coverage, NOT the aggregate topology_coverage, which also
        # unions the always-complete enumerated work set.
        self.assertEqual(admitted_union, REQUIRED_FAMILIES)

    def test_work_set_coverage_is_enumeration_evidence_only(self):
        # ADR-009 section 3 generates all four families and enumeration does not
        # filter by target (engine/layout/search.py), so this holds for every case
        # regardless of admission. It is enumeration evidence, NOT proof that any
        # family produced a hard-valid layout (see the admitted tests above).
        for case_id, case in self.cases.items():
            with self.subTest(case=case_id):
                self.assertEqual(
                    set(case["hard_evidence"]["work_set_topology_coverage"]),
                    REQUIRED_FAMILIES,
                )

    def test_admission_is_selective_so_rejected_attempts_stay_exercised(self):
        # engine/layout/search.py: unsuitable families remain explicit rejected
        # attempts (ADR-009 section 8 records each hard-failure reason code).
        # If admitted coverage equalled the always-complete work set in every case
        # (for example an evaluator that reports the enumerated families as
        # admitted), the per-family admission assertions above would silently
        # degrade into enumeration checks.  This guards that failure mode.
        cases = [case["hard_evidence"] for case in self.report["cases"]]
        rejected = sum(c["evaluated_candidates"] - c["admitted_candidates"] for c in cases)
        self.assertGreater(rejected, 0)
        self.assertTrue(
            any(set(c["admitted_topology_coverage"]) < REQUIRED_FAMILIES for c in cases),
            "every case admitted all four families; refresh the corpus so rejections "
            "of unsuitable families remain observable",
        )

    def test_missing_asset_case_preserves_source_identity_in_selected_response(self):
        source_case = next(
            case for case in self.corpus["cases"] if case["id"] == "missing-asset-diagnostic"
        )
        hard = self.cases["missing-asset-diagnostic"]["hard_evidence"]
        self.assertEqual(hard["status"], "SUCCESS")

        response = hard["selected_signature"]["response"]
        source_elements = source_case["source"]["elements"]
        # Contract section 5: IDs, order, type, and asset reference are immutable.
        self.assertEqual(
            [element["id"] for element in response["elements"]],
            [element["id"] for element in source_elements],
        )
        self.assertEqual(
            [element["type"] for element in response["elements"]],
            [element["type"] for element in source_elements],
        )
        missing = [element for element in source_elements if element["type"] == "image"]
        self.assertEqual(len(missing), 1)
        response_by_id = {element["id"]: element for element in response["elements"]}
        self.assertEqual(
            response_by_id[missing[0]["id"]]["asset_id"], missing[0]["asset_id"]
        )
        self.assertEqual(response["canvas"], source_case["target_canvas"])

    def test_aggregate_metrics_match_recomputation_from_per_case_numbers(self):
        hard = self.report["hard_evidence"]
        evaluated = sum(c["hard_evidence"]["evaluated_candidates"] for c in self.report["cases"])
        hard_valid = sum(c["hard_evidence"]["hard_valid_candidates"] for c in self.report["cases"])
        self.assertGreater(evaluated, 0)
        self.assertEqual(hard["hard_valid_rate"], hard_valid / evaluated)
        self.assertEqual(
            hard["status_distribution"],
            dict(Counter(c["hard_evidence"]["status"] for c in self.report["cases"])),
        )
        self.assertEqual(
            hard["selected_topology_distribution"],
            dict(
                Counter(
                    c["hard_evidence"]["selected_signature"]["topology"]
                    for c in self.report["cases"]
                )
            ),
        )
        reason_total = Counter()
        for case in self.report["cases"]:
            reason_total.update(case["hard_evidence"]["reason_code_distribution"])
        self.assertEqual(hard["reason_code_distribution"], dict(reason_total))
        self.assertIs(hard["all_repeated_signatures_stable"], True)
        self.assertEqual(hard["max_candidates_limit"], ADR_009_MAX_CANDIDATES)

    def test_soft_quality_is_fixed_point_and_separate_from_hard_evidence(self):
        for case_id, case in self.cases.items():
            hard = case["hard_evidence"]
            soft = case["soft_quality"]
            with self.subTest(case=case_id):
                # Separation: no quality component or ranking list leaks into hard
                # evidence (ADR-009 section 1: no soft proxy score may rescue a
                # hard-invalid candidate; section 4: only hard-valid candidates are ranked).
                self.assertFalse(SOFT_COMPONENTS & set(hard))
                self.assertFalse({"candidate_components", "selected_components"} & set(hard))
                # One quality tuple per admitted candidate.
                self.assertEqual(len(soft["candidate_components"]), hard["admitted_candidates"])
                for quality in [*soft["candidate_components"], soft["selected_components"]]:
                    self.assertEqual(set(quality), SOFT_COMPONENTS)
                    for name, value in quality.items():
                        # ADR-009 section 5: documented fixed-point integers.
                        self.assertIs(type(value), int, name)
                        self.assertTrue(0 <= value <= SCORE_SCALE, (name, value))
                # The selected candidate is one of the admitted candidates.
                self.assertIn(soft["selected_components"], soft["candidate_components"])


if __name__ == "__main__":
    unittest.main()
