import hashlib
import importlib.util
import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from unittest.mock import patch

_SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "inspect_layout.py"
_SPEC = importlib.util.spec_from_file_location("inspect_layout", _SCRIPT)
assert _SPEC is not None and _SPEC.loader is not None
inspect_layout = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(inspect_layout)


class InspectLayoutTests(unittest.TestCase):
    def test_reports_any_positive_area_collision(self):
        elements = [
            {"id": "first", "type": "shape", "x": 0, "y": 0, "width": 1, "height": 1},
            {"id": "second", "type": "shape", "x": 0.5, "y": 0.5, "width": 1, "height": 1},
        ]

        warnings = inspect_layout.check_collisions(elements, set())

        self.assertEqual(len(warnings), 1)
        self.assertIn("0px²", warnings[0])

    def test_background_selection_uses_source_coverage_not_target_coverage(self):
        output_cover = {
            "id": "foreground-cover",
            "type": "image",
            "fit": "cover",
            "x": 0,
            "y": 0,
            "width": 200,
            "height": 200,
        }
        source = {
            "canvas": {"width": 100, "height": 100},
            "elements": [
                {
                    **output_cover,
                    "x": 10,
                    "y": 10,
                    "width": 20,
                    "height": 20,
                }
            ],
        }

        self.assertEqual(inspect_layout._background_ids(source), set())
        self.assertEqual(
            inspect_layout._background_ids(
                {
                    "canvas": {"width": 100, "height": 100},
                    "elements": [
                        {
                            **output_cover,
                            "x": 0,
                            "y": 0,
                            "width": 100,
                            "height": 100,
                        }
                    ],
                }
            ),
            {"foreground-cover"},
        )
        self.assertEqual(
            len(inspect_layout._foreground_elements([output_cover], set())),
            1,
        )

    def test_rejects_orphan_png_as_uncommitted(self):
        with tempfile.TemporaryDirectory() as tempdir:
            output_dir = Path(tempdir)
            orphan = output_dir / "orphan_output.png"
            orphan.write_bytes(b"not a committed pair")

            self.assertEqual(
                inspect_layout._uncommitted_artifacts(output_dir),
                [orphan],
            )

    def test_rejects_temporary_output_artifacts(self):
        with tempfile.TemporaryDirectory() as tempdir:
            output_dir = Path(tempdir)
            json_tmp = output_dir / "task_output.json.tmp"
            png_tmp = output_dir / "task_output.png.tmp"
            json_tmp.write_text("{}", encoding="utf-8")
            png_tmp.write_bytes(b"partial")

            self.assertEqual(
                inspect_layout._uncommitted_artifacts(output_dir),
                [json_tmp, png_tmp],
            )


class CommittedOutputTests(unittest.TestCase):
    def test_unmarked_partial_output_is_not_inspectable(self):
        with tempfile.TemporaryDirectory() as directory:
            output_dir = Path(directory)
            json_path = output_dir / "task_output.json"
            json_path.write_text("{}", encoding="utf-8")

            self.assertEqual(inspect_layout.committed_json_files(output_dir), [])

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

    def test_direct_temporary_output_is_not_inspectable(self):
        with tempfile.TemporaryDirectory() as directory:
            json_path = Path(directory) / "task_output.json.tmp"
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
                        "committed": True,
                        "json": json_path.name,
                        "png": "task_output.png",
                        "json_sha256": hashlib.sha256(json_path.read_bytes()).hexdigest(),
                        "png_sha256": "not-yet-installed",
                    }
                ),
                encoding="utf-8",
            )

            self.assertEqual(inspect_layout.committed_json_files(output_dir), [])

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
                        "committed": True,
                        "json": json_path.name,
                        "png": png_path.name,
                        "json_sha256": hashlib.sha256(json_path.read_bytes()).hexdigest(),
                        "png_sha256": hashlib.sha256(png_path.read_bytes()).hexdigest(),
                    }
                ),
                encoding="utf-8",
            )

            self.assertEqual(inspect_layout.committed_json_files(output_dir), [json_path])

            json_path.write_text("changed", encoding="utf-8")
            self.assertEqual(inspect_layout.committed_json_files(output_dir), [])

            json_path.write_text("{}", encoding="utf-8")
            png_path.write_bytes(b"changed")
            self.assertEqual(inspect_layout.committed_json_files(output_dir), [])

            marker_path.write_text("[]", encoding="utf-8")
            self.assertEqual(inspect_layout.committed_json_files(output_dir), [])

    def test_symlinked_final_artifact_is_not_inspectable(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output_dir = root / "output"
            output_dir.mkdir()
            outside_json = root / "outside.json"
            outside_json.write_text("{}", encoding="utf-8")
            json_path = output_dir / "task_output.json"
            png_path = output_dir / "task_output.png"
            marker_path = output_dir / ".task_output.commit"
            json_path.symlink_to(outside_json)
            png_path.write_bytes(b"png")
            marker_path.write_text(
                json.dumps(
                    {
                        "committed": True,
                        "json": json_path.name,
                        "png": png_path.name,
                        "json_sha256": hashlib.sha256(json_path.read_bytes()).hexdigest(),
                        "png_sha256": hashlib.sha256(png_path.read_bytes()).hexdigest(),
                    }
                ),
                encoding="utf-8",
            )

            self.assertEqual(inspect_layout.committed_json_files(output_dir), [])

    def test_symlinked_commit_marker_is_not_inspectable(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output_dir = root / "output"
            output_dir.mkdir()
            json_path = output_dir / "task_output.json"
            png_path = output_dir / "task_output.png"
            marker_path = output_dir / ".task_output.commit"
            outside_marker = root / "outside-marker.json"
            json_path.write_text("{}", encoding="utf-8")
            png_path.write_bytes(b"png")
            outside_marker.write_text(
                json.dumps(
                    {
                        "committed": True,
                        "json": json_path.name,
                        "png": png_path.name,
                        "json_sha256": hashlib.sha256(json_path.read_bytes()).hexdigest(),
                        "png_sha256": hashlib.sha256(png_path.read_bytes()).hexdigest(),
                    }
                ),
                encoding="utf-8",
            )
            marker_path.symlink_to(outside_marker)

            self.assertEqual(inspect_layout.committed_json_files(output_dir), [])


if __name__ == "__main__":
    unittest.main()
