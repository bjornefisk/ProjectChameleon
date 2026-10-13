import json
import os
import shutil
import sys
import tempfile
import time
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from scripts import review_pr


ROOT = Path(__file__).resolve().parents[1]


class ReviewCapsuleTests(unittest.TestCase):

    @staticmethod
    def _review_repository(directory: Path) -> tuple[Path, str, str]:
        repository = directory / "repository"
        repository.mkdir()

        def run_git(*args: str) -> None:
            review_pr.subprocess.run(
                ["git", *args],
                cwd=repository,
                stdout=review_pr.subprocess.PIPE,
                stderr=review_pr.subprocess.PIPE,
                check=True,
            )

        def git_output(*args: str) -> str:
            result = review_pr.subprocess.run(
                ["git", *args],
                cwd=repository,
                stdout=review_pr.subprocess.PIPE,
                stderr=review_pr.subprocess.PIPE,
                check=True,
            )
            return result.stdout.decode("utf-8").strip()

        run_git("init", "--quiet")
        run_git("config", "user.email", "test@example.invalid")
        run_git("config", "user.name", "Test")
        (repository / "README.md").write_text("base\n", encoding="utf-8")
        run_git("add", "README.md")
        run_git("commit", "--quiet", "-m", "base")
        run_git("branch", "base")
        base_sha = git_output("rev-parse", "HEAD")
        (repository / "changed.txt").write_text("head\n", encoding="utf-8")
        run_git("add", "changed.txt")
        run_git("commit", "--quiet", "-m", "head")
        run_git("branch", "pr-head")
        return repository, base_sha, git_output("rev-parse", "HEAD")

    def test_main_publishes_default_report_from_temp_repository(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repository, base_sha, head_sha = self._review_repository(root)
            metadata = {
                "baseRefName": "base",
                "baseRefOid": base_sha,
                "headRefOid": head_sha,
                "state": "OPEN",
                "url": "https://example.test/pr/1",
            }
            argv = [
                "review_pr.py",
                "--pr",
                "1",
                "--repo",
                "owner/repo",
            ]
            output = StringIO()
            with patch.object(review_pr, "ROOT", repository), patch.object(
                review_pr, "run_gh_json", return_value=metadata
            ), patch.object(
                review_pr,
                "fetch_pr_refs",
                return_value=("refs/heads/pr-head", "refs/heads/base"),
            ), patch.object(review_pr.sys, "argv", argv), redirect_stdout(output):
                result = review_pr.main()

            report_line = next(
                line for line in output.getvalue().splitlines() if line.startswith("report: ")
            )
            report_dir = Path(report_line.removeprefix("report: ")).parent
            try:
                self.assertEqual(result, 2)
                self.assertEqual(
                    {
                        path.name
                        for path in report_dir.iterdir()
                    },
                    {
                        "00-diff-check.log",
                        "changed-files.txt",
                        "checks.json",
                        "commits.txt",
                        "diff-stat.txt",
                        "diff.patch",
                        "summary.md",
                    },
                )
                checks = json.loads(
                    (report_dir / "checks.json").read_text(encoding="utf-8")
                )
                self.assertEqual(checks[0]["name"], "contract-sources")
                self.assertEqual(checks[0]["status"], "SKIP")
                self.assertEqual(Path(checks[1]["log"]).parent, report_dir)
                summary = (report_dir / "summary.md").read_text(encoding="utf-8")
                self.assertRegex(
                    summary,
                    r"- Run Id: `pr-1-[0-9a-f]{32}`",
                )
            finally:
                shutil.rmtree(report_dir.parent)

    def test_main_blocks_submission_when_checks_are_incomplete(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repository, base_sha, head_sha = self._review_repository(root)
            report_dir = root / "report"
            body_file = root / "review.md"
            body_file.write_text("review body\n", encoding="utf-8")
            metadata = {
                "baseRefName": "base",
                "baseRefOid": base_sha,
                "headRefOid": head_sha,
                "state": "OPEN",
                "url": "https://example.test/pr/1",
            }
            argv = [
                "review_pr.py",
                "--pr",
                "1",
                "--repo",
                "owner/repo",
                "--report-dir",
                str(report_dir),
                "--run-checks",
                "--submit",
                "comment",
                "--body-file",
                str(body_file),
            ]
            with patch.object(review_pr, "ROOT", repository), patch.object(
                review_pr, "run_gh_json", return_value=metadata
            ), patch.object(
                review_pr,
                "fetch_pr_refs",
                return_value=("refs/heads/pr-head", "refs/heads/base"),
            ), patch.object(
                review_pr, "resolve_runner_python", return_value=None
            ), patch.object(
                review_pr, "submit_review"
            ) as submit, patch.object(review_pr.sys, "argv", argv):
                result = review_pr.main()

            self.assertEqual(result, 2)
            submit.assert_not_called()
            checks = json.loads(
                (report_dir / "checks.json").read_text(encoding="utf-8")
            )
            submission = next(
                check for check in checks if check["name"] == "submit-review"
            )
            self.assertEqual(submission["status"], "SKIP")

    def test_main_rejects_nonempty_report_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            report_dir = Path(directory) / "report"
            report_dir.mkdir()
            stale = report_dir / "stale.txt"
            stale.write_text("old\n", encoding="utf-8")
            argv = [
                "review_pr.py",
                "--pr",
                "1",
                "--repo",
                "owner/repo",
                "--report-dir",
                str(report_dir),
            ]
            error_output = StringIO()
            with patch.object(review_pr.sys, "argv", argv), redirect_stderr(error_output):
                result = review_pr.main()

            self.assertEqual(result, 2)
            self.assertEqual(stale.read_text(encoding="utf-8"), "old\n")
            self.assertFalse((report_dir / "error.txt").exists())
            self.assertNotIn("report:", error_output.getvalue())

    def test_main_rejects_symlinked_report_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "target"
            target.mkdir()
            link = root / "report"
            link.symlink_to(target, target_is_directory=True)
            argv = [
                "review_pr.py",
                "--pr",
                "1",
                "--repo",
                "owner/repo",
                "--report-dir",
                str(link),
            ]
            with patch.object(review_pr.sys, "argv", argv):
                result = review_pr.main()

            self.assertEqual(result, 2)
            self.assertEqual(list(target.iterdir()), [])

    def test_main_publishes_typed_error_after_evidence_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repository, base_sha, head_sha = self._review_repository(root)
            report_dir = root / "report"
            metadata = {
                "baseRefName": "base",
                "baseRefOid": base_sha,
                "headRefOid": head_sha,
                "state": "OPEN",
                "url": "https://example.test/pr/1",
            }
            argv = [
                "review_pr.py",
                "--pr",
                "1",
                "--repo",
                "owner/repo",
                "--report-dir",
                str(report_dir),
            ]
            real_write = review_pr.write_evidence_bytes
            calls = 0

            def fail_on_second_write(path, content, directory_fd=None):
                nonlocal calls
                self.assertFalse(report_dir.exists())
                calls += 1
                if calls == 2:
                    raise OSError("simulated evidence failure")
                return real_write(path, content, directory_fd)

            with patch.object(review_pr, "ROOT", repository), patch.object(
                review_pr, "run_gh_json", return_value=metadata
            ), patch.object(
                review_pr,
                "fetch_pr_refs",
                return_value=("refs/heads/pr-head", "refs/heads/base"),
            ), patch.object(
                review_pr,
                "write_evidence_bytes",
                side_effect=fail_on_second_write,
            ), patch.object(review_pr.sys, "argv", argv):
                result = review_pr.main()

            self.assertEqual(result, 2)
            self.assertEqual(
                {path.name for path in report_dir.iterdir()},
                {"error.txt"},
            )
            error_record = json.loads(
                (report_dir / "error.txt").read_text(encoding="utf-8")
            )
            self.assertEqual(error_record["pull_request"], 1)
            self.assertIn("run_id", error_record)
            self.assertIn("capsule_revision", error_record)
            self.assertIn("environment", error_record)
            self.assertEqual(
                error_record["validation"],
                "capsule generation failed before complete evidence publication",
            )
            self.assertEqual(error_record["next_owner"], "reviewer/maintainer")

    def test_publish_staging_directory_rejects_target_collision(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            staging = root / "staging"
            target = root / "report"
            staging.mkdir()
            target.mkdir()

            with self.assertRaisesRegex(
                ValueError,
                "report directory appeared during checks",
            ):
                review_pr.publish_staging_directory(staging, target)

            self.assertTrue(staging.exists())

    def test_publish_staging_directory_rejects_publication_lock(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            staging = root / "staging"
            target = root / "report"
            staging.mkdir()
            lock = root / ".report.publish.lock"
            lock.touch()

            with self.assertRaisesRegex(
                ValueError,
                "report publication already in progress",
            ):
                review_pr.publish_staging_directory(staging, target)

            self.assertTrue(staging.exists())
            self.assertTrue(lock.exists())


    def test_contract_sources_are_canonical_and_present(self):
        self.assertNotIn("Docs/AGENTS/PR_REVIEW_AGENT.md", review_pr.CONTRACT_SOURCES)
        for source in review_pr.CONTRACT_SOURCES:
            self.assertTrue((ROOT / source).is_file(), source)
        for suffix in range(1, 10):
            self.assertIn(
                f"Docs/DECISIONS/ADR-{suffix:03d}-",
                "\n".join(review_pr.CONTRACT_SOURCES),
            )
        self.assertIn(".agents/policies/artifacts.md", review_pr.CONTRACT_SOURCES)

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
                base_sha="a" * 40,
            )

        self.assertEqual(head_ref, "refs/review-capsule/run-1/head")
        self.assertEqual(base_ref, "refs/review-capsule/run-1/base")
        commands = [call.args[0] for call in run.call_args_list]
        self.assertIn("refs/review-capsule/run-1/head", commands[0][-1])
        self.assertIn(
            f"+{'a' * 40}:refs/review-capsule/run-1/base",
            commands[1][-1],
        )

    def test_fetch_pr_refs_rejects_invalid_base_sha(self):
        with self.assertRaisesRegex(
            review_pr.ReviewError,
            "invalid base revision SHA",
        ):
            review_pr.fetch_pr_refs(
                8,
                "main",
                "owner/repo",
                base_sha="not-a-sha",
            )


    def test_delete_review_refs_surfaces_cleanup_failure(self):
        with patch.object(
            review_pr,
            "git_output",
            side_effect=review_pr.ReviewError("ref deletion failed"),
        ):
            with self.assertRaisesRegex(
                review_pr.ReviewError,
                "review ref cleanup failed.*refs/review-capsule/run-1/head",
            ):
                review_pr.delete_review_refs(
                    (
                        "refs/review-capsule/run-1/head",
                        "refs/review-capsule/run-1/base",
                    )
                )

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

    @unittest.skipUnless(os.name == "posix", "requires process groups")
    def test_run_bounded_command_kills_descendants_after_parent_exit(self):
        with tempfile.TemporaryDirectory() as directory:
            marker = Path(directory) / "child-alive"
            child_code = (
                "import pathlib, sys, time; "
                "time.sleep(0.4); pathlib.Path(sys.argv[1]).write_text('alive')"
            )
            parent_code = (
                "import subprocess, sys; "
                "subprocess.Popen([sys.executable, '-c', sys.argv[2], sys.argv[1]])"
            )
            result = review_pr.run_bounded_command(
                [
                    sys.executable,
                    "-c",
                    parent_code,
                    str(marker),
                    child_code,
                ],
                ROOT,
                10,
            )

            self.assertEqual(result.returncode, 0)
            time.sleep(0.7)
            self.assertFalse(marker.exists())

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
                        reason="![x](https://evil.test)|reason\nnext",
                    )
                ],
                list(review_pr.CONTRACT_SOURCES),
            )
            content = summary.read_text(encoding="utf-8")

        self.assertIn("``bad`\\|name\\nline``", content)
        self.assertIn("`![x](https://evil.test)\\|reason\\nnext`", content)
        self.assertIn("&lt;tag&gt;", review_pr.markdown_cell("<tag>"))

    def test_markdown_code_uses_fence_longer_than_embedded_backticks(self):
        self.assertEqual(review_pr.markdown_code("a``b"), "```a``b```")

    def test_run_process_closes_stdin_by_default(self):
        with tempfile.TemporaryDirectory() as directory:
            result = review_pr.run_process(
                [
                    sys.executable,
                    "-c",
                    "import sys; print('closed' if sys.stdin.read(1) == '' else 'open')",
                ],
                ROOT,
                Path(directory) / "check.log",
                10,
            )
            content = Path(result.log).read_text(encoding="utf-8")

        self.assertEqual(result.status, "PASS")
        self.assertEqual(content, "closed\n")


if __name__ == "__main__":
    unittest.main()
