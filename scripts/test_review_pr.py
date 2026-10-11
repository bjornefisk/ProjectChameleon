import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import review_pr


ROOT = Path(__file__).resolve().parents[1]


class ReviewCapsuleTests(unittest.TestCase):
    def test_contract_sources_are_canonical_and_present(self):
        self.assertNotIn("Docs/AGENTS/PR_REVIEW_AGENT.md", review_pr.CONTRACT_SOURCES)
        for source in review_pr.CONTRACT_SOURCES:
            self.assertTrue((ROOT / source).is_file(), source)
        for suffix in range(1, 10):
            self.assertIn(
                f"Docs/DECISIONS/ADR-{suffix:03d}-",
                "\n".join(review_pr.CONTRACT_SOURCES),
            )

    def test_write_text_preserves_diff_trailing_whitespace(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "diff.patch"
            review_pr.write_text(path, "+trailing spaces   \n")
            self.assertEqual(path.read_text(encoding="utf-8"), "+trailing spaces   \n")

    def test_git_output_raw_mode_preserves_trailing_whitespace(self):
        completed = review_pr.subprocess.CompletedProcess(
            ["git"], 0, "diff line  \n\n", ""
        )
        with patch.object(review_pr.subprocess, "run", return_value=completed):
            output = review_pr.git_output("diff", strip=False)

        self.assertEqual(output, "diff line  \n\n")

    def test_repository_resolution_wraps_missing_gh(self):
        with patch.object(review_pr.subprocess, "run", side_effect=FileNotFoundError("gh")):
            with self.assertRaises(review_pr.ReviewError):
                review_pr.resolve_repository(None)

    def test_fetch_pr_refs_uses_private_noncolliding_namespace(self):
        completed = review_pr.subprocess.CompletedProcess([], 0, "", "")
        with patch.object(review_pr.subprocess, "run", return_value=completed) as run:
            head_ref, base_ref = review_pr.fetch_pr_refs(
                8,
                "pr/8",
                "owner/repo",
                namespace="run-1",
            )

        self.assertEqual(head_ref, "refs/review-capsule/run-1/head")
        self.assertEqual(base_ref, "refs/review-capsule/run-1/base")
        commands = [call.args[0] for call in run.call_args_list]
        self.assertIn("refs/review-capsule/run-1/head", commands[0][-1])
        self.assertIn("refs/review-capsule/run-1/base", commands[1][-1])

    def test_timeout_submission_stays_failed_and_indeterminate(self):
        timed_out = review_pr.CheckResult(
            name="submit-review",
            status="FAIL",
            duration_seconds=1.0,
            command=["gh"],
            returncode=None,
            reason="timeout after 60s",
        )
        with patch.object(review_pr, "run_check", return_value=timed_out), patch.object(
            review_pr, "run_gh_json"
        ) as verify:
            result = review_pr.submit_review(
                8,
                "owner/repo",
                "request-changes",
                Path("review.md"),
                Path("."),
                60,
            )

        self.assertEqual(result.status, "FAIL")
        self.assertIn("indeterminate", result.reason)
        verify.assert_not_called()

    def test_missing_gh_is_a_review_error(self):
        with patch.object(review_pr.subprocess, "run", side_effect=FileNotFoundError("gh")):
            with self.assertRaises(review_pr.ReviewError):
                review_pr.run_gh_json(["gh", "pr", "view"])

    def test_summary_records_provenance_and_evidence_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            report_dir = Path(directory)
            summary = review_pr.make_summary(
                report_dir,
                {"number": 8, "repository": "owner/repo", "url": "https://example.test/pr/8"},
                "base",
                "head",
                ["scripts/review_pr.py"],
                [],
                list(review_pr.CONTRACT_SOURCES),
                {
                    "run_id": "capsule-8",
                    "capsule_revision": "revision",
                    "role": "reviewer",
                    "workflow": ".agents/workflows/06-review.md",
                    "gate": "Review",
                    "environment": "python3",
                    "validation": "manual verdict pending",
                    "next_owner": "independent reviewer",
                },
            )
            content = summary.read_text(encoding="utf-8")

        self.assertIn("capsule-8", content)
        self.assertIn("python3", content)
        self.assertIn("independent reviewer", content)
        self.assertIn("diff.patch", content)


if __name__ == "__main__":
    unittest.main()
