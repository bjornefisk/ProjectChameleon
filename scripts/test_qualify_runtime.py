"""Regression tests for the runtime qualification harness."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path
import unittest


SCRIPT = Path(__file__).with_name("qualify_runtime.py")


class QualifyRuntimeTests(unittest.TestCase):
    def _run_child(self, code: str) -> tuple[subprocess.CompletedProcess[str], dict]:
        with tempfile.TemporaryDirectory() as temporary_directory:
            report_path = Path(temporary_directory) / "runtime.json"
            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--report",
                    str(report_path),
                    "--",
                    sys.executable,
                    "-c",
                    code,
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            report = json.loads(report_path.read_text(encoding="utf-8"))
        return completed, report

    def test_records_runtime_measurements_and_thread_count(self) -> None:
        completed, report = self._run_child(
            "import threading, time; worker = threading.Thread(target=time.sleep, args=(0.1,)); worker.start(); worker.join()"
        )

        self.assertEqual(completed.returncode, 0)
        self.assertEqual(report["returncode"], 0)
        self.assertGreaterEqual(report["elapsed_seconds"], 0)
        self.assertGreaterEqual(report["cpu_seconds"]["user"], 0)
        self.assertGreaterEqual(report["cpu_seconds"]["system"], 0)
        self.assertIn(report["max_rss"]["unit"], {"KiB", "bytes"})
        self.assertGreater(report["max_rss"]["value"], 0)
        self.assertGreater(report["available_cpu_count"], 0)

        thread_count = report["thread_count"]
        self.assertIn(thread_count["peak"], (None, *range(1, 1025)))
        if thread_count["peak"] is not None:
            self.assertEqual(thread_count["unit"], "threads")
            self.assertEqual(thread_count["source"], "procfs")

    def test_rejects_symlinked_report_path(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            target_path = directory / "target.json"
            report_path = directory / "runtime.json"
            target_path.write_text("sentinel\n", encoding="utf-8")
            report_path.symlink_to(target_path)

            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--report",
                    str(report_path),
                    "--",
                    sys.executable,
                    "-c",
                    "pass",
                ],
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertNotEqual(completed.returncode, 0)
            self.assertEqual(target_path.read_text(encoding="utf-8"), "sentinel\n")

    def test_propagates_child_status_in_report(self) -> None:
        completed, report = self._run_child("import sys; sys.exit(7)")

        self.assertEqual(completed.returncode, 7)
        self.assertEqual(report["returncode"], 7)


if __name__ == "__main__":
    unittest.main()
