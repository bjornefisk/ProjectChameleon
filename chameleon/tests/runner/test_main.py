import builtins
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).parents[3]
sys.path.insert(0, str(PROJECT_ROOT))

from chameleon.renderer.converter.wrap import MalformedTextError

from engine import main
from engine.errors import InfeasibleReasonCode


class RunnerPublicationTests(unittest.TestCase):
    def test_malformed_text_maps_to_malformed_input(self):
        with patch.object(main, "_MalformedTextError", MalformedTextError):
            self.assertEqual(
                main._failure_code(MalformedTextError("invalid style range")),
                InfeasibleReasonCode.MALFORMED_INPUT,
            )

    def test_publish_pair_commits_marker_with_both_hashes(self):
        output = {"canvas": {"width": 1, "height": 1}, "elements": []}
        with tempfile.TemporaryDirectory() as directory:
            output_dir = Path(directory)
            with patch.object(main, "OUTPUT_DIR", output_dir), patch.object(
                main,
                "render_to_png",
                side_effect=lambda _design, _assets, path: Path(path).write_bytes(b"png"),
            ):
                main._publish_pair(output, "task")

            json_path = output_dir / "task_output.json"
            png_path = output_dir / "task_output.png"
            commit_path = output_dir / ".task_output.commit"
            self.assertTrue(json_path.is_file())
            self.assertTrue(png_path.is_file())
            self.assertTrue(commit_path.is_file())
            commit = json.loads(commit_path.read_text(encoding="utf-8"))
            self.assertEqual(
                commit["json_sha256"], hashlib.sha256(json_path.read_bytes()).hexdigest()
            )
            self.assertEqual(
                commit["png_sha256"], hashlib.sha256(png_path.read_bytes()).hexdigest()
            )

    def test_failed_commit_removes_uncommitted_pair(self):
        output = {"canvas": {"width": 1, "height": 1}, "elements": []}
        with tempfile.TemporaryDirectory() as directory:
            output_dir = Path(directory)
            real_replace = main.os.replace

            def fail_commit_marker(source, destination):
                if Path(destination).name == ".task_output.commit":
                    raise OSError("commit marker failure")
                return real_replace(source, destination)

            with patch.object(main, "OUTPUT_DIR", output_dir), patch.object(
                main,
                "render_to_png",
                side_effect=lambda _design, _assets, path: Path(path).write_bytes(b"png"),
            ), patch.object(main.os, "replace", side_effect=fail_commit_marker):
                with self.assertRaises(OSError):
                    main._publish_pair(output, "task")

            self.assertEqual(list(output_dir.iterdir()), [])

    def test_missing_renderer_fails_instead_of_writing_placeholder(self):
        with tempfile.TemporaryDirectory() as directory:
            png_path = Path(directory) / "output.png"
            original_import = builtins.__import__

            def fail_renderer_import(name, *args, **kwargs):
                if name == "renderer.converter.convert":
                    raise ImportError("renderer unavailable")
                return original_import(name, *args, **kwargs)

            with patch.object(builtins, "__import__", side_effect=fail_renderer_import):
                with self.assertRaises(ImportError):
                    main.render_to_png(
                        {"canvas": {"width": 1, "height": 1}, "elements": []},
                        Path("assets"),
                        png_path,
                    )
            self.assertFalse(png_path.exists())


if __name__ == "__main__":
    unittest.main()
