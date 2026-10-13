import hashlib
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).parents[3]
sys.path.insert(0, str(PROJECT_ROOT))

from scripts import inspect_layout
from scripts.inspect_layout import committed_json_files


class CommittedOutputTests(unittest.TestCase):
    def test_unmarked_partial_output_is_not_inspectable(self):
        with tempfile.TemporaryDirectory() as directory:
            output_dir = Path(directory)
            json_path = output_dir / "task_output.json"
            json_path.write_text("{}", encoding="utf-8")

            self.assertEqual(committed_json_files(output_dir), [])

    def test_direct_unmarked_output_is_not_inspectable(self):
        with tempfile.TemporaryDirectory() as directory:
            json_path = Path(directory) / "task_output.json"
            json_path.write_text("{}", encoding="utf-8")
            stderr = io.StringIO()
            with patch.object(
                inspect_layout.sys, "argv", ["inspect_layout.py", str(json_path)]
            ), redirect_stderr(stderr):
                result = inspect_layout.main()

            self.assertEqual(result, 1)
            self.assertIn("Uncommitted or invalid output pair", stderr.getvalue())

    def test_marker_without_both_final_files_is_not_inspectable(self):
        with tempfile.TemporaryDirectory() as directory:
            output_dir = Path(directory)
            json_path = output_dir / "task_output.json"
            marker_path = output_dir / ".task_output.commit"
            json_path.write_text("{}", encoding="utf-8")
            marker_path.write_text(
                json.dumps(
                    {
                        "json": json_path.name,
                        "png": "task_output.png",
                        "json_sha256": hashlib.sha256(json_path.read_bytes()).hexdigest(),
                        "png_sha256": "not-yet-installed",
                    }
                ),
                encoding="utf-8",
            )

            self.assertEqual(committed_json_files(output_dir), [])


    def test_marker_hashes_authorize_matching_pair_only(self):
        with tempfile.TemporaryDirectory() as directory:
            output_dir = Path(directory)
            json_path = output_dir / "task_output.json"
            png_path = output_dir / "task_output.png"
            marker_path = output_dir / ".task_output.commit"
            json_path.write_text("{}", encoding="utf-8")
            png_path.write_bytes(b"png")
            marker_path.write_text(
                json.dumps(
                    {
                        "json": json_path.name,
                        "png": png_path.name,
                        "json_sha256": hashlib.sha256(json_path.read_bytes()).hexdigest(),
                        "png_sha256": hashlib.sha256(png_path.read_bytes()).hexdigest(),
                    }
                ),
                encoding="utf-8",
            )

            self.assertEqual(committed_json_files(output_dir), [json_path])

            json_path.write_text("changed", encoding="utf-8")
            self.assertEqual(committed_json_files(output_dir), [])

            json_path.write_text("{}", encoding="utf-8")
            png_path.write_bytes(b"changed")
            self.assertEqual(committed_json_files(output_dir), [])

            marker_path.write_text("[]", encoding="utf-8")
            self.assertEqual(committed_json_files(output_dir), [])


if __name__ == "__main__":
    unittest.main()
