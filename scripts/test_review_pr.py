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
        completed = review_pr.CommandResult(
            0,
            b"diff line  \n\n",
            b"",
        )
        with patch.object(review_pr, "run_bounded_command", return_value=completed):
            output = review_pr.git_output("diff", strip=False)

        self.assertEqual(output, "diff line  \n\n")

    def test_repository_resolution_wraps_missing_gh(self):
        with patch.object(
            review_pr,
            "run_bounded_command",
            side_effect=review_pr.ReviewError("cannot run gh"),
        ):
            with self.assertRaises(review_pr.ReviewError):
                review_pr.resolve_repository(None)

    def test_fetch_pr_refs_uses_private_noncolliding_namespace(self):
        completed = review_pr.CommandResult(0, b"", b"")
        with patch.object(
            review_pr,
            "run_bounded_command",
            return_value=completed,
        ) as run:
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
        with tempfile.TemporaryDirectory() as directory:
            body_file = Path(directory) / "review.md"
            body_file.write_text("body\n", encoding="utf-8")
            timed_out = review_pr.CheckResult(
                name="submit-review",
                status="FAIL",
                duration_seconds=1.0,
                command=["gh"],
                returncode=None,
                reason="timeout after 60s",
            )
            with patch.object(
                review_pr,
                "run_check",
                return_value=timed_out,
            ), patch.object(
                review_pr,
                "run_gh_json",
                side_effect=[{"login": "reviewer"}, {"reviews": []}],
            ) as verify:
                result = review_pr.submit_review(
                    8,
                    "owner/repo",
                    "request-changes",
                    body_file.read_bytes(),
                    Path(directory),
                    60,
                )

        self.assertEqual(result.status, "FAIL")
        self.assertIn("indeterminate", result.reason)
        self.assertEqual(verify.call_count, 2)

    def test_submission_accepts_new_matching_review(self):
        with tempfile.TemporaryDirectory() as directory:
            body_file = Path(directory) / "review.md"
            body_file.write_text("body\n", encoding="utf-8")
            before = {
                "id": "old",
                "author": {"login": "reviewer"},
                "state": "COMMENTED",
                "body": "older",
            }
            after = {
                **before,
                "id": "new",
                "state": "CHANGES_REQUESTED",
                "body": "body",
            }
            passed = review_pr.CheckResult(
                "submit-review",
                "PASS",
                0.1,
                ["gh", "pr", "review"],
            )
            with patch.object(
                review_pr,
                "run_gh_json",
                side_effect=[
                    {"login": "reviewer"},
                    {"reviews": [before]},
                    {"reviews": [before, after]},
                ],
            ), patch.object(
                review_pr,
                "run_check",
                return_value=passed,
            ) as execute:
                result = review_pr.submit_review(
                    8,
                    "owner/repo",
                    "request-changes",
                    body_file.read_bytes(),
                    Path(directory),
                    60,
                )

        self.assertEqual(result.status, "PASS")
        self.assertEqual(execute.call_args.args[1][-2:], ["--body-file", "-"])
        self.assertEqual(execute.call_args.kwargs["input_bytes"], b"body\n")

    def test_submission_rejects_preexisting_matching_review(self):
        with tempfile.TemporaryDirectory() as directory:
            body_file = Path(directory) / "review.md"
            body_file.write_text("body\n", encoding="utf-8")
            existing = {
                "id": "old",
                "author": {"login": "reviewer"},
                "state": "CHANGES_REQUESTED",
                "body": "body",
            }
            passed = review_pr.CheckResult(
                "submit-review",
                "PASS",
                0.1,
                ["gh", "pr", "review"],
            )
            with patch.object(
                review_pr,
                "run_gh_json",
                side_effect=[
                    {"login": "reviewer"},
                    {"reviews": [existing]},
                    {"reviews": [existing]},
                ],
            ), patch.object(review_pr, "run_check", return_value=passed):
                result = review_pr.submit_review(
                    8,
                    "owner/repo",
                    "request-changes",
                    body_file.read_bytes(),
                    Path(directory),
                    60,
                )

        self.assertEqual(result.status, "FAIL")
        self.assertIn("no new matching review", result.reason)


    def test_missing_gh_is_a_review_error(self):
        with patch.object(
            review_pr,
            "run_bounded_command",
            side_effect=review_pr.ReviewError("cannot run gh"),
        ):
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

    def test_run_check_defers_report_log_until_flush(self):
        with tempfile.TemporaryDirectory() as directory:
            report_dir = Path(directory)
            result = review_pr.run_check(
                "check",
                [sys.executable, "-c", "print('captured')"],
                ROOT,
                report_dir,
                10,
            )

            log_path = Path(result.log)
            self.assertFalse(log_path.exists())
            self.assertIn(b"captured", result.output)
            review_pr.flush_check_logs([result])

            self.assertEqual(log_path.read_text(encoding="utf-8"), "captured\n")

    def test_run_process_passes_review_body_on_stdin(self):
        with tempfile.TemporaryDirectory() as directory:
            log_path = Path(directory) / "check.log"
            result = review_pr.run_process(
                [
                    sys.executable,
                    "-c",
                    "import sys; sys.stdout.write(sys.stdin.read())",
                ],
                ROOT,
                log_path,
                10,
                input_bytes=b"body\n",
            )

            self.assertEqual(result.status, "PASS")
            self.assertEqual(log_path.read_bytes(), b"body\n")

    def test_bounded_command_rejects_excessive_output(self):
        result = review_pr.run_bounded_command(
            [
                sys.executable,
                "-c",
                "import sys; sys.stdout.write('x' * 256)",
            ],
            ROOT,
            10,
            max_output_bytes=32,
        )

        self.assertTrue(result.output_limited)
        self.assertLessEqual(len(result.stdout), 32)

    def test_create_checkout_rejects_export_ignored_file(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory) / "repo"
            repo.mkdir()
            run_git = lambda *args: review_pr.subprocess.run(
                ["git", *args],
                cwd=repo,
                stdout=review_pr.subprocess.PIPE,
                stderr=review_pr.subprocess.PIPE,
                check=True,
            )
            run_git("init", "--quiet")
            run_git("config", "user.email", "test@example.invalid")
            run_git("config", "user.name", "Test")
            (repo / ".gitattributes").write_text(
                "hidden.txt export-ignore\n",
                encoding="utf-8",
            )
            (repo / "hidden.txt").write_text("hidden\n", encoding="utf-8")
            (repo / "visible.txt").write_text("visible\n", encoding="utf-8")
            run_git("add", ".")
            run_git("commit", "--quiet", "-m", "test")
            checkout = Path(directory) / "checkout"

            with patch.object(review_pr, "ROOT", repo):
                with self.assertRaisesRegex(
                    review_pr.ReviewError,
                    "archive manifest mismatch",
                ):
                    review_pr.create_checkout("HEAD", checkout)

        self.assertFalse(checkout.exists())

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
