import os
import sys
import tempfile
import unittest
from contextlib import redirect_stderr
from io import StringIO
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

    def test_changed_authority_sources_require_trusted_comparison(self):
        sources = review_pr.changed_contract_sources([".agents/roles/reviewer.md"])

        self.assertIn("skills/chameleon-review/SKILL.md", sources)
        self.assertIn("chameleon/RULES.md", sources)
        self.assertEqual(
            review_pr.changed_authority_sources(
                [".agents/roles/reviewer.md"], sources
            ),
            [".agents/roles/reviewer.md"],
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

    def test_run_process_caps_output(self):
        with tempfile.TemporaryDirectory() as directory:
            log_path = Path(directory) / "check.log"
            with patch.object(review_pr, "MAX_LOG_BYTES", 32):
                result = review_pr.run_process(
                    [
                        sys.executable,
                        "-c",
                        "import sys; sys.stdout.write('x' * 256)",
                    ],
                    ROOT,
                    log_path,
                    10,
                )

            self.assertEqual(result.status, "PASS")
            content = log_path.read_bytes()
            self.assertIn(review_pr.LOG_TRUNCATION_MARKER, content)
            self.assertLessEqual(
                len(content),
                32 + len(review_pr.LOG_TRUNCATION_MARKER),
            )

    def test_resolve_runner_python_requires_executable_path(self):
        with tempfile.TemporaryDirectory() as directory:
            runner = Path(directory) / "bin" / "python"
            runner.parent.mkdir()
            runner.write_text("", encoding="utf-8")
            runner.chmod(0o755)

            self.assertEqual(
                review_pr.resolve_runner_python(runner),
                runner.absolute(),
            )
            self.assertIsNone(
                review_pr.resolve_runner_python(runner.parent / "missing")
            )

    def test_resolve_runner_python_preserves_venv_launcher(self):
        with tempfile.TemporaryDirectory() as directory:
            launcher = Path(directory) / "bin" / "python"
            launcher.parent.mkdir()
            launcher.symlink_to(sys.executable)

            self.assertEqual(
                review_pr.resolve_runner_python(launcher),
                launcher.absolute(),
            )


    def test_make_command_pins_runner_interpreter(self):
        python_path = Path("/trusted/.venv/bin/python")
        command = review_pr.make_command("verify", python_path)

        self.assertIn(f"PYTHON_BOOTSTRAP={python_path}", command)
        self.assertIn(f"PYTHON={python_path}", command)

    def test_isolated_environment_does_not_expose_reviewer_python(self):
        with tempfile.TemporaryDirectory() as directory:
            environment = review_pr.isolated_environment(Path(directory))

        self.assertNotIn(
            str(Path(sys.executable).parent),
            environment["PATH"].split(os.pathsep),
        )

    def test_submission_requires_complete_checks(self):
        checks = [
            review_pr.CheckResult("contract-sources", "PASS", 0.0, []),
            review_pr.CheckResult("test", "SKIP", 0.0, [], reason="not run"),
        ]

        self.assertEqual(
            review_pr.submission_blocker(checks),
            "submission blocked; incomplete checks: test",
        )
        self.assertEqual(
            review_pr.next_owner(checks, "request-changes"),
            "reviewer/maintainer (complete skipped evidence)",
        )
        self.assertEqual(
            review_pr.next_owner(
                [review_pr.CheckResult("submit-review", "PASS", 0.0, [])],
                "request-changes",
            ),
            "PR author/maintainer",
        )

    def test_parse_args_accepts_runner_interpreter(self):
        runner = Path("/trusted/.venv/bin/python")
        with patch.object(
            review_pr.sys,
            "argv",
            [
                "review_pr.py",
                "--pr",
                "8",
                "--run-checks",
                "--python-path",
                str(runner),
            ],
        ):
            args = review_pr.parse_args()

        self.assertEqual(args.python_path, runner)

    def test_submit_requires_run_checks(self):
        with patch.object(
            review_pr.sys,
            "argv",
            [
                "review_pr.py",
                "--pr",
                "8",
                "--submit",
                "comment",
                "--body-file",
                "review.md",
            ],
        ):
            with redirect_stderr(StringIO()):
                with self.assertRaises(SystemExit):
                    review_pr.parse_args()

    def test_summary_escapes_untrusted_markdown_fields(self):
        with tempfile.TemporaryDirectory() as directory:
            summary = review_pr.make_summary(
                Path(directory),
                {"number": 8, "repository": "owner/repo", "url": "https://example.test"},
                "base",
                "head",
                ["bad`|name\nline"],
                [
                    review_pr.CheckResult(
                        "check",
                        "SKIP",
                        0.0,
                        [],
                        reason="bad|reason\nnext",
                    )
                ],
                list(review_pr.CONTRACT_SOURCES),
            )
            content = summary.read_text(encoding="utf-8")

        self.assertIn("bad\\`\\|name\\nline", content)
        self.assertIn("bad\\|reason\\nnext", content)


if __name__ == "__main__":
    unittest.main()
