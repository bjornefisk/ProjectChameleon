import hashlib
import json
import sys
import unittest
from unittest.mock import patch
from collections import Counter
from decimal import Decimal
from pathlib import Path

from jsonschema import Draft202012Validator

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.evaluate_heldout_search import _case_report, evaluate_corpus, load_corpus
from engine.geometry.groups import has_common_transform
from renderer.converter.brand_fonts import load_brand_font_manager
from renderer.converter.convert import convert_chameleon_to_crello


CORPUS = PROJECT_ROOT / "chameleon" / "tests" / "fixtures" / "heldout_search_cases.json"
V1_CORPUS = PROJECT_ROOT / "chameleon" / "tests" / "fixtures" / "heldout_search_cases_v1.json"
SCHEMA = PROJECT_ROOT / "chameleon" / "chameleon_design_schema_v0.9.json"
ASSETS = PROJECT_ROOT / "chameleon" / "brand_kit" / "assets"
FONTS = PROJECT_ROOT / "chameleon" / "brand_kit" / "fonts"
REQUIRED_FAMILIES = {
    "near_isomorphic",
    "column_pivot",
    "horizontal_ribbon",
    "vertical_restack",
}
REQUIRED_COVERAGE = {
    "canvas:extreme-wide-4-to-1",
    "canvas:extreme-tall-1-to-8",
    "canvas:extreme-wide-target-728x90",
    "background:full-canvas-cover-image",
    "group:rigid",
    "overlap:grouped-source-intent",
    "rotation:non-right-angle",
    "image:foreground-ratio",
    "image:foreground-ratio-lattice",
    "text:wrapping",
    "text:style-runs",
    "text:italic-glyph-bounds",
    "source-bleed:left",
    "asset:missing-preservation",
}
# Each authored case was designed to exercise one family's route.
# STATUS.md records current corpus provenance and coverage boundaries. ADR-009
# section 3 only describes the regime each family serves; the per-case pairing is
# corpus design intent, so a failure below means the corpus no longer exercises
# that route and the corpus or solver change must be reviewed, not that the ADR
# mandates the pairing.
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


def _signature_json_default(value):
    if isinstance(value, Decimal):
        return {"__decimal__": format(value, "f")}
    raise TypeError(f"cannot encode {type(value).__name__}")


class HeldoutEvaluationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # The real search is slow; run the evaluator exactly once for the class.
        cls.corpus = load_corpus(CORPUS)
        cls.report = evaluate_corpus(cls.corpus, repeats=2)
        cls.v1_corpus = load_corpus(V1_CORPUS)
        cls.v1_report = evaluate_corpus(cls.v1_corpus, repeats=2)
        cls.cases = {case["id"]: case for case in cls.report["cases"]}
        cls.source_cases = {case["id"]: case for case in cls.corpus["cases"]}

    def test_report_covers_declared_cases_and_all_required_contract_dimensions(self):
        self.assertEqual(self.report["hard_evidence"]["case_count"], len(self.corpus["cases"]))
        actual_coverage = {
            dimension
            for case in self.corpus["cases"]
            for dimension in case["coverage"]
        }
        self.assertLessEqual(REQUIRED_COVERAGE, actual_coverage)
        for case in self.report["cases"]:
            with self.subTest(case=case["id"]):
                self.assertIs(case["expected_outcome"]["matched"], True)
                self.assertEqual(
                    case["coverage"],
                    self.source_cases[case["id"]]["coverage"],
                )

    def test_historical_v1_fixture_remains_separate_from_expanded_corpus(self):
        v1 = self.v1_corpus
        self.assertEqual(v1["corpus"], "stage1-heldout-search-v1")
        self.assertTrue(self.v1_report["outcome_expectations"]["all_match"])
        self.assertEqual(
            self.v1_report["hard_evidence"]["status_distribution"],
            {"SUCCESS": 5},
        )
        self.assertIs(
            self.v1_report["hard_evidence"]["all_repeated_task_outcomes_stable"],
            True,
        )
        self.assertIs(
            self.v1_report["hard_evidence"]["all_repeated_signatures_stable"],
            True,
        )
        for case in self.v1_report["cases"]:
            with self.subTest(v1_case=case["id"]):
                self.assertIs(case["hard_evidence"]["source_unchanged"], True)
                self.assertIs(case["hard_evidence"]["deterministic_repeated"], True)
                self.assertIs(case["hard_evidence"]["response_signature_stable"], True)
                self.assertIs(case["hard_evidence"]["png_signature_stable"], True)
        self.assertEqual(len(v1["cases"]), 5)
        self.assertEqual(
            [case["id"] for case in v1["cases"]],
            [
                "isomorphic-gallery",
                "column-pivot-catalog",
                "horizontal-ribbon-journal",
                "vertical-restack-studio",
                "missing-asset-diagnostic",
            ],
        )
        self.assertEqual(len(self.corpus["cases"]), 7)
        self.assertEqual(
            [
                (case["id"], case["source"], case["target_canvas"])
                for case in v1["cases"]
            ],
            [
                (case["id"], case["source"], case["target_canvas"])
                for case in self.corpus["cases"][:5]
            ],
        )

    def test_every_source_and_target_is_valid_under_the_ratified_schema(self):
        schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
        source_validator = Draft202012Validator(schema)
        canvas_validator = Draft202012Validator(schema["$defs"]["canvas"])
        for case in self.corpus["cases"]:
            with self.subTest(case=case["id"]):
                source_errors = list(source_validator.iter_errors(case["source"]))
                self.assertEqual(
                    source_errors,
                    [],
                    "; ".join(error.message for error in source_errors),
                )
                target_errors = list(canvas_validator.iter_errors(case["target_canvas"]))
                self.assertEqual(
                    target_errors,
                    [],
                    "; ".join(error.message for error in target_errors),
                )
                self.assertIn(
                    case["expected_status"],
                    {
                        "SUCCESS",
                        "MALFORMED_INPUT",
                        "INFEASIBLE_LAYOUT",
                        "INCOMPLETE_SEARCH",
                        "RUNTIME_IO_FAILURE",
                    },
                )

    def test_success_cases_pass_serialized_hard_validation_and_candidate_bound(self):
        for case_id, case in self.cases.items():
            if case["expected_outcome"]["status"] != "SUCCESS":
                continue
            hard = case["hard_evidence"]
            with self.subTest(case=case_id):
                self.assertEqual(hard["status"], "SUCCESS")
                self.assertEqual(hard["hard_validation_errors"], [])
                self.assertIs(hard["source_unchanged"], True)
                self.assertIs(hard["deterministic_repeated"], True)
                self.assertIs(hard["cutoff"], False)
                self.assertLessEqual(hard["candidate_count"], ADR_009_MAX_CANDIDATES)
                self.assertEqual(hard["evaluated_candidates"], hard["candidate_count"])
                self.assertGreater(hard["admitted_candidates"], 0)
                self.assertEqual(hard["hard_valid_admissions"], hard["admitted_candidates"])
                self.assertEqual(
                    sum(hard["candidate_rejection_reason_distribution"].values()),
                    hard["evaluated_candidates"] - hard["admitted_candidates"],
                )

    def test_intended_families_are_admitted_not_only_enumerated(self):
        for case_id, family in INTENDED_FAMILY.items():
            with self.subTest(case=case_id, family=family):
                admitted = self.cases[case_id]["hard_evidence"]["admitted_topology_coverage"]
                self.assertIn(family, admitted)

    def test_successful_admissions_cover_all_four_topologies(self):
        admitted_union = set()
        for case in self.report["cases"]:
            admitted_union.update(case["hard_evidence"]["admitted_topology_coverage"])
        self.assertEqual(admitted_union, REQUIRED_FAMILIES)

    def test_work_set_coverage_is_not_reported_as_hard_admission(self):
        for case_id, case in self.cases.items():
            with self.subTest(case=case_id):
                hard = case["hard_evidence"]
                self.assertEqual(set(hard["work_set_topology_coverage"]), REQUIRED_FAMILIES)
                self.assertLessEqual(set(hard["admitted_topology_coverage"]), REQUIRED_FAMILIES)

    def test_rejections_remain_observable_and_separate_from_task_failures(self):
        cases = [case["hard_evidence"] for case in self.report["cases"]]
        rejected = sum(
            case["evaluated_candidates"] - case["admitted_candidates"]
            for case in cases
        )
        self.assertGreater(rejected, 0)
        self.assertTrue(
            any(set(case["admitted_topology_coverage"]) < REQUIRED_FAMILIES for case in cases)
        )
        incomplete = self.cases["extreme-ratio-incomplete"]["hard_evidence"]
        self.assertEqual(incomplete["task_reason_code"], "INCOMPLETE_SEARCH")
        self.assertEqual(
            sum(incomplete["candidate_rejection_reason_distribution"].values()),
            incomplete["evaluated_candidates"],
        )
        self.assertEqual(
            self.report["hard_evidence"]["task_reason_code_distribution"],
            {"INCOMPLETE_SEARCH": 1},
        )

    def test_expected_outcome_requires_every_repeat_to_match(self):
        def run(status, reason_code):
            return {
                "status": status,
                "reason_code": reason_code,
                "message": None,
                "diagnostics": {},
                "failures": [],
                "candidate_count": 0,
                "evaluated_candidates": 0,
                "admitted_candidates": 0,
                "hard_valid_candidates": 0,
                "cutoff": False,
                "candidate_signatures": [],
                "selected_signature": None,
                "quality": [],
                "selected_quality": None,
                "hard_validation_errors": [],
                "source_unchanged": True,
                "runtime_ms": 0,
                "max_rss_bytes": 0,
            }

        case = {
            "id": "repeat-mismatch",
            "coverage": ["test:repeat-mismatch"],
            "expected_status": "SUCCESS",
        }
        with patch(
            "scripts.evaluate_heldout_search._run_once",
            side_effect=[
                run("SUCCESS", None),
                run("INCOMPLETE_SEARCH", "INCOMPLETE_SEARCH"),
            ],
        ):
            report = _case_report(case, repeats=2)

        self.assertIs(report["expected_outcome"]["matched"], False)
        self.assertIs(report["hard_evidence"]["task_outcome_stable"], False)
        self.assertEqual(
            report["expected_outcome"]["observed_repeats"],
            [
                {"status": "SUCCESS", "reason_code": None},
                {"status": "INCOMPLETE_SEARCH", "reason_code": "INCOMPLETE_SEARCH"},
            ],
        )

    def test_interaction_case_exercises_group_rotation_ratio_text_and_bleed(self):
        case = self.source_cases["contract-interactions"]
        hard = self.cases["contract-interactions"]["hard_evidence"]
        self.assertEqual(hard["status"], "SUCCESS")
        self.assertIn(hard["selected_topology"], REQUIRED_FAMILIES)
        source_by_id = {element["id"]: element for element in case["source"]["elements"]}
        output_by_id = {
            element["id"]: element
            for element in hard["selected_signature"]["response"]["elements"]
        }

        panel = source_by_id["group_panel"]
        label = source_by_id["group_label"]
        self.assertEqual(panel["group_id"], label["group_id"])
        self.assertGreater(
            min(panel["x"] + panel["width"], label["x"] + label["width"])
            - max(panel["x"], label["x"]),
            0,
        )
        self.assertGreater(
            min(panel["y"] + panel["height"], label["y"] + label["height"])
            - max(panel["y"], label["y"]),
            0,
        )
        self.assertTrue(
            has_common_transform(
                [panel, label],
                [output_by_id["group_panel"], output_by_id["group_label"]],
            )
        )

        image = source_by_id["gallery_vessel"]
        output_image = output_by_id["gallery_vessel"]
        self.assertEqual(image["rotation"], 11)
        self.assertEqual(image["fit"], "contain")
        self.assertEqual(
            output_image["width"] * image["height"],
            output_image["height"] * image["width"],
        )
        title = output_by_id["gallery_title"]
        converted, warnings = convert_chameleon_to_crello(
            {"canvas": case["target_canvas"], "elements": [title]},
            load_brand_font_manager(str(FONTS)),
            str(ASSETS),
        )
        wrapped_text = converted["text"][0]
        line_map = converted["text_line"][0]
        self.assertEqual(wrapped_text.count("\n") + 1, 2)
        self.assertEqual(len(set(line_map)), 2)
        self.assertTrue(all(converted["font_italic"][0]))
        self.assertEqual(warnings, [])
        self.assertEqual(source_by_id["gallery_title"]["font_style"], "italic")
        self.assertTrue(source_by_id["gallery_title"]["style_runs"])
        self.assertEqual(source_by_id["gallery_title"]["max_lines"], 2)
        self.assertLess(source_by_id["bleed_ellipse"]["x"], 0)
        self.assertLess(output_by_id["bleed_ellipse"]["x"], 0)

    def test_missing_asset_reference_is_preserved_in_success_response(self):
        source_case = self.source_cases["missing-asset-diagnostic"]
        hard = self.cases["missing-asset-diagnostic"]["hard_evidence"]
        self.assertEqual(hard["status"], "SUCCESS")
        self.assertEqual(
            hard["selected_signature"]["warnings"],
            [
                "Missing asset 'heldout_asset_not_packaged.png' "
                "for element 'unpackaged_asset' - rendered a placeholder."
            ],
        )

        response = hard["selected_signature"]["response"]
        source_elements = source_case["source"]["elements"]
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

    def test_extreme_ratio_case_remains_typed_incomplete_without_candidate_or_artifact(self):
        case = self.cases["extreme-ratio-incomplete"]
        hard = case["hard_evidence"]
        self.assertEqual(case["expected_outcome"]["status"], "INCOMPLETE_SEARCH")
        self.assertIs(case["expected_outcome"]["matched"], True)
        self.assertEqual(hard["status"], "INCOMPLETE_SEARCH")
        self.assertEqual(hard["task_reason_code"], "INCOMPLETE_SEARCH")
        self.assertIs(hard["source_unchanged"], True)
        self.assertFalse(hard["finite_work_exhausted"])
        self.assertEqual(hard["hard_valid_admissions"], 0)
        self.assertIsNone(hard["selected_topology"])
        self.assertIsNone(hard["selected_signature"])
        self.assertIsNone(hard["selected_response_sha256"])
        self.assertIsNone(hard["selected_png_sha256"])
        self.assertIsNone(hard["response_signature_stable"])
        self.assertIsNone(hard["png_signature_stable"])
        self.assertEqual(case["soft_quality"]["candidate_components"], [])
        self.assertIsNone(case["soft_quality"]["selected_components"])

    def test_aggregate_metrics_recompute_from_separate_case_fields(self):
        hard = self.report["hard_evidence"]
        evaluated = sum(case["hard_evidence"]["evaluated_candidates"] for case in self.report["cases"])
        hard_valid = sum(case["hard_evidence"]["hard_valid_admissions"] for case in self.report["cases"])
        self.assertGreater(evaluated, 0)
        self.assertEqual(hard["hard_valid_rate"], hard_valid / evaluated)
        self.assertEqual(
            hard["status_distribution"],
            dict(Counter(case["hard_evidence"]["status"] for case in self.report["cases"])),
        )
        self.assertEqual(
            hard["selected_topology_distribution"],
            dict(
                Counter(
                    case["hard_evidence"]["selected_topology"]
                    for case in self.report["cases"]
                    if case["hard_evidence"]["selected_topology"]
                )
            ),
        )
        rejection_total = Counter()
        task_reasons = Counter()
        for case in self.report["cases"]:
            rejection_total.update(
                case["hard_evidence"]["candidate_rejection_reason_distribution"]
            )
            reason = case["hard_evidence"]["task_reason_code"]
            if reason:
                task_reasons[reason] += 1
        self.assertEqual(hard["candidate_rejection_reason_distribution"], dict(rejection_total))
        self.assertEqual(hard["task_reason_code_distribution"], dict(task_reasons))
        self.assertIs(hard["all_repeated_task_outcomes_stable"], True)
        self.assertIs(hard["all_repeated_signatures_stable"], True)
        self.assertIs(hard["all_success_response_signatures_stable"], True)
        self.assertIs(hard["all_success_png_signatures_stable"], True)
        self.assertIs(self.report["outcome_expectations"]["all_match"], True)
        self.assertEqual(self.report["outcome_expectations"]["mismatches"], [])

    def test_report_separates_hard_quality_and_runtime_evidence(self):
        for case_id, case in self.cases.items():
            hard = case["hard_evidence"]
            with self.subTest(case=case_id):
                self.assertNotIn("runtime_observations", hard)
                self.assertNotIn("wall_time_ms", hard)
                self.assertNotIn("process_max_rss_bytes", hard)
                self.assertIn("wall_time_ms", case["runtime_observations"])
                self.assertIn("process_max_rss_bytes", case["runtime_observations"])
                self.assertFalse(SOFT_COMPONENTS & set(hard))
                soft = case["soft_quality"]
                if hard["selected_topology"] is None:
                    self.assertEqual(soft["candidate_components"], [])
                    self.assertIsNone(soft["selected_components"])
                    continue
                self.assertEqual(len(soft["candidate_components"]), hard["admitted_candidates"])
                for quality in [*soft["candidate_components"], soft["selected_components"]]:
                    self.assertEqual(set(quality), SOFT_COMPONENTS)
                    for name, value in quality.items():
                        self.assertIs(type(value), int, name)
                        self.assertTrue(0 <= value <= SCORE_SCALE, (name, value))
                self.assertIn(soft["selected_components"], soft["candidate_components"])

    def test_case_response_and_png_signatures_are_valid_and_repeatable(self):
        for case_id, case in self.cases.items():
            hard = case["hard_evidence"]
            with self.subTest(case=case_id):
                self.assertIs(hard["task_outcome_stable"], True)
                self.assertIs(hard["deterministic_repeated"], True)
                signature = hard["selected_signature"]
                if hard["status"] != "SUCCESS":
                    self.assertIsNone(signature)
                    self.assertIsNone(hard["response_signature_stable"])
                    self.assertIsNone(hard["png_signature_stable"])
                    continue

                response_json = json.dumps(
                    signature["response"],
                    sort_keys=True,
                    separators=(",", ":"),
                    ensure_ascii=False,
                    default=_signature_json_default,
                )
                response_digest = hashlib.sha256(response_json.encode("utf-8")).hexdigest()
                self.assertEqual(signature["response_sha256"], response_digest)
                self.assertRegex(signature["response_sha256"], r"^[0-9a-f]{64}$")
                self.assertRegex(signature["png_sha256"], r"^[0-9a-f]{64}$")
                self.assertIs(signature["png_header_valid"], True)
                self.assertIs(hard["response_signature_stable"], True)
                self.assertIs(hard["png_signature_stable"], True)


if __name__ == "__main__":
    unittest.main()
