import sys
import unittest
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


class HeldoutEvaluationTests(unittest.TestCase):
    def test_evaluator_repeats_search_at_observable_seam(self):
        report = evaluate_corpus(load_corpus(CORPUS), repeats=2)
        hard = report["hard_evidence"]

        self.assertEqual(hard["case_count"], 5)
        self.assertTrue(hard["all_repeated_signatures_stable"])
        self.assertLessEqual(hard["max_candidates_limit"], 12)
        self.assertGreaterEqual(hard["hard_valid_rate"], 0.0)
        self.assertLessEqual(hard["hard_valid_rate"], 1.0)
        self.assertTrue(REQUIRED_FAMILIES.issubset(set(hard["topology_coverage"])))
        self.assertIn("status_distribution", hard)
        self.assertIn("reason_code_distribution", hard)
        self.assertIn("selected_topology_distribution", hard)
        self.assertIn("candidate_counts", hard)

        for case in report["cases"]:
            case_hard = case["hard_evidence"]
            self.assertIn("status", case_hard)
            self.assertIn("candidate_count", case_hard)
            self.assertIn("evaluated_candidates", case_hard)
            self.assertIn("admitted_candidates", case_hard)
            self.assertIn("cutoff", case_hard)
            self.assertIn("runtime_ms", case_hard)
            self.assertIn("max_rss_bytes", case_hard)
            self.assertTrue(case_hard["source_unchanged"])
            self.assertTrue(case_hard["deterministic_repeated"])
            self.assertTrue(case_hard["png_bytes_stable"])
            self.assertLessEqual(case_hard["candidate_count"], 12)
            self.assertEqual(case_hard["hard_validation_errors"], [])
            self.assertIn("candidate_components", case["soft_quality"])
            self.assertIn("selected_components", case["soft_quality"])
            for quality in case["soft_quality"]["candidate_components"]:
                self.assertEqual(
                    set(quality), {"readability", "balance", "alignment", "hierarchy"}
                )
                self.assertTrue(all(isinstance(value, int) for value in quality.values()))


if __name__ == "__main__":
    unittest.main()
