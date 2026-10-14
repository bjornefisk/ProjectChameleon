import builtins
import io
import hashlib
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

from PIL import Image

PROJECT_ROOT = Path(__file__).parents[3]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "chameleon"))

from chameleon.renderer.converter.wrap import (
    MalformedTextError,
    TextLayoutError,
    TextOverflowError,
)

from engine import main, staging
from engine.errors import InfeasibleLayoutError, InfeasibleReasonCode, TaskStatus


class RunnerPublicationTests(unittest.TestCase):
    @staticmethod
    def _publish_pair(source, target, output, stem):
        return staging.publish_task(
            output_dir=main.OUTPUT_DIR,
            task_name=stem,
            source=source,
            target_canvas=target,
            response=output,
            assets_dir=main.ASSETS_DIR,
            render_to_png=main.render_to_png,
        )
    @staticmethod
    def _empty_request():
        source = {"canvas": {"width": 1, "height": 1}, "elements": []}
        target = {"width": 1, "height": 1}
        return source, target

    @staticmethod
    def _write_png(path):
        Image.new("RGBA", (1, 1), (0, 0, 0, 0)).save(path, format="PNG")

    @staticmethod
    def _classify(error, phase):
        with patch.object(main, "_MalformedTextError", MalformedTextError), patch.object(
            main, "_TextLayoutError", TextLayoutError
        ):
            return main._classify_failure(error, phase)


    def test_malformed_text_maps_to_malformed_input(self):
        status, reason = self._classify(
            MalformedTextError("invalid style range"), "publish"
        )
        self.assertEqual(status, TaskStatus.MALFORMED_INPUT)
        self.assertEqual(reason, InfeasibleReasonCode.MALFORMED_INPUT.value)

    def test_layout_and_runtime_failures_use_accepted_statuses(self):
        status, reason = self._classify(
            InfeasibleLayoutError(
                InfeasibleReasonCode.IMMUTABLE_FIELD_CHANGED, "candidate changed"
            ),
            "publish",
        )
        self.assertEqual(status, TaskStatus.RUNTIME_IO_FAILURE)
        self.assertEqual(reason, InfeasibleReasonCode.IMMUTABLE_FIELD_CHANGED.value)

        status, reason = self._classify(
            TextOverflowError("text overflow"), "publish"
        )
        self.assertEqual(status, TaskStatus.INFEASIBLE_LAYOUT)
        self.assertEqual(reason, InfeasibleReasonCode.TEXT_OVERFLOW.value)

        for error in (TypeError("renderer failure"), KeyError("renderer field")):
            status, reason = self._classify(error, "publish")
            self.assertEqual(status, TaskStatus.RUNTIME_IO_FAILURE)
            self.assertEqual(reason, type(error).__name__)

        status, reason = self._classify(
            InfeasibleLayoutError(InfeasibleReasonCode.INVALID_SOURCE, "bad source"),
            "input",
        )
        self.assertEqual(status, TaskStatus.MALFORMED_INPUT)
        self.assertEqual(reason, InfeasibleReasonCode.INVALID_SOURCE.value)
        status, reason = self._classify(
            InfeasibleLayoutError(
                InfeasibleReasonCode.MALFORMED_INPUT, "serialized input is invalid"
            ),
            "publish",
        )
        self.assertEqual(status, TaskStatus.MALFORMED_INPUT)
        self.assertEqual(reason, InfeasibleReasonCode.MALFORMED_INPUT.value)


    def test_task_decoder_preserves_exponents_and_rejects_nonfinite_numbers(self):
        with tempfile.TemporaryDirectory() as directory:
            task_path = Path(directory) / "task.json"
            task_path.write_text(
                '{"source":{"canvas":{"width":1,"height":1},"elements":[]},'
                '"target_canvas":{"width":1.25e+3,"height":2}}',
                encoding="utf-8",
            )
            task = main._load_task(task_path)
            self.assertEqual(task["target_canvas"]["width"], Decimal("1.25e+3"))

            task_path.write_text(
                '{"source":{"canvas":{"width":1,"height":1},"elements":[]},'
                '"target_canvas":{"width":NaN,"height":2}}',
                encoding="utf-8",
            )
            with self.assertRaises(main._MalformedInputError):
                main._load_task(task_path)

    def test_main_reports_malformed_source_status(self):
        element = {
            "id": "same",
            "type": "shape",
            "x": 0,
            "y": 0,
            "width": 1,
            "height": 1,
            "shape_type": "rectangle",
            "fill_color": "rgba(0,0,0,1)",
        }
        task = {
            "source": {"canvas": {"width": 1, "height": 1}, "elements": [element, dict(element)]},
            "target_canvas": {"width": 1, "height": 1},
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            input_dir = root / "input"
            output_dir = root / "output"
            input_dir.mkdir()
            output_dir.mkdir()
            (input_dir / "task.json").write_text(json.dumps(task), encoding="utf-8")
            stderr = io.StringIO()

            with patch.object(main, "INPUT_DIR", input_dir), patch.object(
                main, "OUTPUT_DIR", output_dir
            ), redirect_stderr(stderr):
                result = main.main()

            self.assertEqual(result, 1)
            self.assertIn(
                "[task.json] status=MALFORMED_INPUT reason=INVALID_SOURCE",
                stderr.getvalue(),
            )
            self.assertEqual(list(output_dir.iterdir()), [])

    def test_main_reports_renderer_type_error_as_runtime_failure(self):
        task = {
            "source": {"canvas": {"width": 1, "height": 1}, "elements": []},
            "target_canvas": {"width": 1, "height": 1},
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            input_dir = root / "input"
            output_dir = root / "output"
            input_dir.mkdir()
            output_dir.mkdir()
            (input_dir / "task.json").write_text(json.dumps(task), encoding="utf-8")
            stderr = io.StringIO()
            with patch.object(main, "INPUT_DIR", input_dir), patch.object(
                main, "OUTPUT_DIR", output_dir
            ), patch.object(
                main,
                "resize",
                return_value={"canvas": task["target_canvas"], "elements": []},
            ), patch.object(
                main, "render_to_png", side_effect=TypeError("renderer failure")
            ), redirect_stderr(stderr):
                result = main.main()

            self.assertEqual(result, 1)
            self.assertIn(
                "[task.json] status=RUNTIME_IO_FAILURE reason=TypeError",
                stderr.getvalue(),
            )
            self.assertEqual(list(output_dir.iterdir()), [])

    def test_main_reports_output_setup_failure_as_runtime_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            output_path = Path(directory) / "output"
            output_path.write_text("not a directory", encoding="utf-8")
            stderr = io.StringIO()
            with patch.object(main, "OUTPUT_DIR", output_path), redirect_stderr(stderr):
                result = main.main()

            self.assertEqual(result, 1)
            self.assertIn("status=RUNTIME_IO_FAILURE reason=RUNTIME_IO_FAILURE", stderr.getvalue())


    def test_publish_pair_commits_marker_with_both_hashes(self):
        source, target = self._empty_request()
        output = {"canvas": target, "elements": []}
        with tempfile.TemporaryDirectory() as directory:
            output_dir = Path(directory)
            with patch.object(main, "OUTPUT_DIR", output_dir), patch.object(
                main,
                "render_to_png",
                side_effect=lambda _design, _assets, path: self._write_png(path),
            ):
                self._publish_pair(source, target, output, "task")

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


    def test_publish_pair_installs_marker_after_both_artifacts(self):
        source, target = self._empty_request()
        output = {"canvas": target, "elements": []}
        replace_destinations = []
        real_replace = staging.os.replace

        def record_replace(source_path, destination):
            replace_destinations.append(Path(destination).name)
            return real_replace(source_path, destination)

        with tempfile.TemporaryDirectory() as directory:
            output_dir = Path(directory)
            with patch.object(main, "OUTPUT_DIR", output_dir), patch.object(
                main,
                "render_to_png",
                side_effect=lambda _design, _assets, path: self._write_png(path),
            ), patch.object(staging.os, "replace", side_effect=record_replace):
                self._publish_pair(source, target, output, "task")

        self.assertEqual(
            replace_destinations,
            ["task_output.json", "task_output.png", ".task_output.commit"],
        )


    def test_decimal_immutable_tokens_survive_pair_serialization(self):
        opacity = Decimal("0.1234567890123456789")
        source = {
            "canvas": {"width": 1, "height": 1},
            "elements": [
                {
                    "id": "shape",
                    "type": "shape",
                    "x": 0,
                    "y": 0,
                    "width": 1,
                    "height": 1,
                    "opacity": opacity,
                    "shape_type": "rectangle",
                    "fill_color": "rgba(0,0,0,1)",
                }
            ],
        }
        target = {"width": 1, "height": 1}
        output = {"canvas": target, "elements": [dict(source["elements"][0])]}
        with tempfile.TemporaryDirectory() as directory:
            output_dir = Path(directory)
            with patch.object(main, "OUTPUT_DIR", output_dir), patch.object(
                main,
                "render_to_png",
                side_effect=lambda _design, _assets, path: self._write_png(path),
            ):
                self._publish_pair(source, target, output, "task")

            wire = json.loads(
                (output_dir / "task_output.json").read_text(encoding="utf-8"),
                parse_float=Decimal,
            )
            self.assertEqual(wire["elements"][0]["opacity"], opacity)

    def test_invalid_design_is_not_committed_or_rendered(self):
        source, target = self._empty_request()
        output = {
            "canvas": target,
            "elements": [
                {
                    "id": "unexpected",
                    "type": "shape",
                    "x": 0,
                    "y": 0,
                    "width": 1,
                    "height": 1,
                    "shape_type": "rectangle",
                    "fill_color": "rgba(0,0,0,1)",
                }
            ],
        }
        with tempfile.TemporaryDirectory() as directory:
            output_dir = Path(directory)
            with patch.object(main, "OUTPUT_DIR", output_dir), patch.object(
                main, "render_to_png"
            ) as render:
                with self.assertRaises(InfeasibleLayoutError):
                    self._publish_pair(source, target, output, "task")
                render.assert_not_called()
            self.assertEqual(list(output_dir.iterdir()), [])

    def test_invalid_png_is_not_committed(self):
        source, target = self._empty_request()
        output = {"canvas": target, "elements": []}
        with tempfile.TemporaryDirectory() as directory:
            output_dir = Path(directory)
            with patch.object(main, "OUTPUT_DIR", output_dir), patch.object(
                main,
                "render_to_png",
                side_effect=lambda _design, _assets, path: Path(path).write_bytes(
                    b"not-a-png"
                ),
            ):
                with self.assertRaises(OSError):
                    self._publish_pair(source, target, output, "task")
            self.assertEqual(list(output_dir.iterdir()), [])

    def test_failed_commit_removes_uncommitted_pair(self):
        source, target = self._empty_request()
        output = {"canvas": target, "elements": []}
        with tempfile.TemporaryDirectory() as directory:
            output_dir = Path(directory)
            real_replace = staging.os.replace

            def fail_commit_marker(source_path, destination):
                if Path(destination).name == ".task_output.commit":
                    raise OSError("commit marker failure")
                return real_replace(source_path, destination)

            with patch.object(main, "OUTPUT_DIR", output_dir), patch.object(
                main,
                "render_to_png",
                side_effect=lambda _design, _assets, path: self._write_png(path),
            ), patch.object(staging.os, "replace", side_effect=fail_commit_marker):
                with self.assertRaises(OSError):
                    self._publish_pair(source, target, output, "task")

            self.assertEqual(list(output_dir.iterdir()), [])

    def test_interrupt_after_first_rename_removes_uncommitted_pair(self):
        source, target = self._empty_request()
        output = {"canvas": target, "elements": []}
        with tempfile.TemporaryDirectory() as directory:
            output_dir = Path(directory)
            real_replace = staging.os.replace
            def interrupt_after_json(source_path, destination):
                real_replace(source_path, destination)
                if Path(destination).name == "task_output.json":
                    raise KeyboardInterrupt("simulated interruption")

            with patch.object(main, "OUTPUT_DIR", output_dir), patch.object(
                main,
                "render_to_png",
                side_effect=lambda _design, _assets, path: self._write_png(path),
            ), patch.object(staging.os, "replace", side_effect=interrupt_after_json):
                with self.assertRaises(KeyboardInterrupt):
                    self._publish_pair(source, target, output, "task")

            self.assertEqual(list(output_dir.iterdir()), [])

    def test_cleanup_failure_does_not_stop_later_tasks(self):
        task = {
            "source": {"canvas": {"width": 1, "height": 1}, "elements": []},
            "target_canvas": {"width": 1, "height": 1},
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            input_dir = root / "input"
            output_dir = root / "output"
            input_dir.mkdir()
            output_dir.mkdir()
            (input_dir / "first.json").write_text(json.dumps(task), encoding="utf-8")
            (input_dir / "second.json").write_text(json.dumps(task), encoding="utf-8")
            (output_dir / "first_output.json").mkdir()

            with patch.object(main, "INPUT_DIR", input_dir), patch.object(
                main, "OUTPUT_DIR", output_dir
            ), patch.object(
                main,
                "resize",
                return_value={"canvas": {"width": 1, "height": 1}, "elements": []},
            ), patch.object(
                main,
                "render_to_png",
                side_effect=lambda _design, _assets, path: self._write_png(path),
            ):
                result = main.main()

            self.assertEqual(result, 1)
            self.assertTrue((output_dir / "second_output.json").is_file())
            self.assertTrue((output_dir / "second_output.png").is_file())
            self.assertTrue((output_dir / ".second_output.commit").is_file())

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
