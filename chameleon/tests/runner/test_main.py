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
    def _write_png(path, design=None):
        """Write a conformant test render for shape/text-only designs."""

        if design is not None and all(
            element.get("type") in {"shape", "text"}
            for element in design.get("elements", ())
        ):
            from chameleon.renderer.converter.convert import render_design_to_png

            root = PROJECT_ROOT / "chameleon" / "brand_kit"
            render_design_to_png(
                design,
                root / "assets",
                path,
                fonts_dir=root / "fonts",
            )
            return
        size = (
            (int(design["canvas"]["width"]), int(design["canvas"]["height"]))
            if design is not None
            else (1, 1)
        )
        Image.new("RGBA", size, (255, 255, 255, 255)).save(path, format="PNG")

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
        self.assertEqual(status, TaskStatus.RUNTIME_IO_FAILURE)
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
            with patch.object(main, "INPUT_DIR", task_path.parent):
                task = main._load_task(task_path)
            self.assertEqual(task["target_canvas"]["width"], Decimal("1.25e+3"))

            task_path.write_text(
                '{"source":{"canvas":{"width":1,"height":1},"elements":[]},'
                '"target_canvas":{"width":NaN,"height":2}}',
                encoding="utf-8",
            )
            with self.assertRaises(main._MalformedInputError):
                with patch.object(main, "INPUT_DIR", task_path.parent):
                    main._load_task(task_path)

            for constant in ("Infinity", "-Infinity"):
                task_path.write_text(
                    '{"source":{"canvas":{"width":1,"height":1},"elements":[]},'
                    f'"target_canvas":{{"width":{constant},"height":2}}}}',
                    encoding="utf-8",
                )
                with self.assertRaises(main._MalformedInputError):
                    with patch.object(main, "INPUT_DIR", task_path.parent):
                        main._load_task(task_path)

    def test_publish_renders_the_reparsed_private_staged_design(self):
        source = {
            "canvas": {"width": 20, "height": 20},
            "elements": [
                {
                    "id": "shape",
                    "type": "shape",
                    "x": 0,
                    "y": 0,
                    "width": 10,
                    "height": 10,
                    "opacity": Decimal("0.1234567890123456789"),
                    "shape_type": "rectangle",
                    "fill_color": "rgba(0,0,0,1)",
                }
            ],
        }
        target = {"width": 20, "height": 20}
        response = {
            "canvas": dict(target),
            "elements": [
                {
                    **source["elements"][0],
                    "x": Decimal("10.5"),
                }
            ],
        }
        rendered = {}

        def renderer(design, _assets_dir, png_path):
            rendered["design"] = design
            rendered["png_path"] = Path(png_path)
            self._write_png(png_path, design)

        with tempfile.TemporaryDirectory() as directory:
            output_dir = Path(directory)
            with patch.object(main, "OUTPUT_DIR", output_dir):
                staging.publish_task(
                    output_dir=output_dir,
                    task_name="task",
                    source=source,
                    target_canvas=target,
                    response=response,
                    assets_dir=Path(directory) / "assets",
                    render_to_png=renderer,
                )

            self.assertEqual(rendered["design"]["elements"][0]["x"], 10)
            self.assertIs(type(rendered["design"]["elements"][0]["x"]), int)
            self.assertEqual(
                rendered["design"]["elements"][0]["opacity"],
                source["elements"][0]["opacity"],
            )
            self.assertIsInstance(rendered["design"]["elements"][0]["opacity"], Decimal)
            self.assertNotEqual(rendered["png_path"].parent, output_dir)
            self.assertTrue(rendered["png_path"].parent.name.startswith(".task.stage-"))

    def test_half_even_serialization_applies_to_text_font_size(self):
        source = {
            "canvas": {"width": 80, "height": 20},
            "elements": [
                {
                    "id": "label",
                    "type": "text",
                    "x": 2,
                    "y": 0,
                    "width": 70,
                    "height": 20,
                    "content": "",
                    "font_family": "Solstice Sans",
                    "font_size": 10,
                    "color": "rgba(0,0,0,1)",
                }
            ],
        }
        target = {"width": 80, "height": 20}
        response = {
            "canvas": dict(target),
            "elements": [{**source["elements"][0], "font_size": Decimal("10.5")}],
        }
        with tempfile.TemporaryDirectory() as directory:
            output_dir = Path(directory)
            with patch.object(main, "OUTPUT_DIR", output_dir), patch.object(
                main,
                "render_to_png",
                side_effect=lambda _design, _assets, path: self._write_png(path, _design),
            ):
                self._publish_pair(source, target, response, "text")

            published = json.loads(
                (output_dir / "text_output.json").read_text(encoding="utf-8")
            )
            self.assertEqual(published["elements"][0]["font_size"], 10)

    def test_nontext_font_size_remains_immutable_during_serialization(self):
        source = {
            "canvas": {"width": 20, "height": 20},
            "elements": [
                {
                    "id": "shape",
                    "type": "shape",
                    "x": 0,
                    "y": 0,
                    "width": 20,
                    "height": 20,
                    "font_size": Decimal("10.5"),
                    "shape_type": "rectangle",
                    "fill_color": "rgba(0,0,0,1)",
                }
            ],
        }
        target = {"width": 20, "height": 20}
        rendered = {}

        def renderer(design, _assets_dir, png_path):
            rendered["design"] = design
            self._write_png(png_path, design)

        with tempfile.TemporaryDirectory() as directory:
            output_dir = Path(directory)
            staging.publish_task(
                output_dir=output_dir,
                task_name="shape",
                source=source,
                target_canvas=target,
                response={"canvas": dict(target), "elements": [dict(source["elements"][0])]},
                assets_dir=output_dir / "assets",
                render_to_png=renderer,
            )

            published = json.loads(
                (output_dir / "shape_output.json").read_text(encoding="utf-8"),
                parse_float=Decimal,
            )

        self.assertEqual(published["elements"][0]["font_size"], Decimal("10.5"))
        self.assertEqual(rendered["design"]["elements"][0]["font_size"], Decimal("10.5"))

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
                side_effect=lambda _design, _assets, path: self._write_png(path, _design),
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


    def test_task_name_traversal_is_rejected_at_staging_boundary(self):
        source, target = self._empty_request()
        output = {"canvas": target, "elements": []}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output_dir = root / "output"
            escaped_json = root / "escape_output.json"
            escaped_png = root / "escape_output.png"
            with patch.object(main, "OUTPUT_DIR", output_dir), patch.object(
                main,
                "render_to_png",
                side_effect=lambda _design, _assets, path: self._write_png(path, _design),
            ):
                with self.assertRaises(ValueError):
                    self._publish_pair(source, target, output, "../escape")

            self.assertFalse(escaped_json.exists())
            self.assertFalse(escaped_png.exists())
            self.assertFalse((output_dir / ".escape_output.commit").exists())

    def test_task_name_control_characters_are_rejected_at_staging_boundary(self):
        with self.assertRaises(ValueError):
            staging.validate_task_name("odd\nname")

    def test_symlinked_final_artifact_is_rejected_by_publication(self):
        source, target = self._empty_request()
        output = {"canvas": target, "elements": []}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output_dir = root / "output"
            outside = root / "outside.json"

            real_replace = staging.os.replace

            def symlink_json(source_path, destination):
                real_replace(source_path, destination)
                if Path(destination).name == "task_output.json":
                    outside.write_bytes(Path(destination).read_bytes())
                    Path(destination).unlink()
                    Path(destination).symlink_to(outside)

            with patch.object(main, "OUTPUT_DIR", output_dir), patch.object(
                main,
                "render_to_png",
                side_effect=lambda _design, _assets, path: self._write_png(path, _design),
            ), patch.object(staging.os, "replace", side_effect=symlink_json):
                with self.assertRaises((OSError, ValueError)):
                    self._publish_pair(source, target, output, "task")

            self.assertTrue(outside.is_file())
            self.assertFalse((output_dir / "task_output.json").exists())
            self.assertFalse((output_dir / "task_output.json").is_symlink())

    def test_symlinked_commit_marker_is_rejected_by_publication(self):
        source, target = self._empty_request()
        output = {"canvas": target, "elements": []}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output_dir = root / "output"
            outside = root / "outside-marker.json"

            real_replace = staging.os.replace

            def symlink_marker(source_path, destination):
                real_replace(source_path, destination)
                if Path(destination).name == ".task_output.commit":
                    outside.write_bytes(Path(destination).read_bytes())
                    Path(destination).unlink()
                    Path(destination).symlink_to(outside)

            with patch.object(main, "OUTPUT_DIR", output_dir), patch.object(
                main,
                "render_to_png",
                side_effect=lambda _design, _assets, path: self._write_png(path, _design),
            ), patch.object(staging.os, "replace", side_effect=symlink_marker):
                with self.assertRaises((OSError, ValueError)):
                    self._publish_pair(source, target, output, "task")

            self.assertTrue(outside.is_file())
            self.assertFalse((output_dir / ".task_output.commit").exists())
            self.assertFalse((output_dir / ".task_output.commit").is_symlink())


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
                side_effect=lambda _design, _assets, path: self._write_png(path, _design),
            ), patch.object(staging.os, "replace", side_effect=record_replace):
                self._publish_pair(source, target, output, "task")

        self.assertEqual(
            replace_destinations,
            ["task_output.json", "task_output.png", ".task_output.commit"],
        )

    def test_tampered_commit_marker_removes_pair(self):
        source, target = self._empty_request()
        output = {"canvas": target, "elements": []}
        with tempfile.TemporaryDirectory() as directory:
            output_dir = Path(directory)
            real_replace = staging.os.replace

            def tamper_marker(source_path, destination):
                real_replace(source_path, destination)
                if Path(destination).name == ".task_output.commit":
                    Path(destination).write_text("{}", encoding="utf-8")

            with patch.object(main, "OUTPUT_DIR", output_dir), patch.object(
                main,
                "render_to_png",
                side_effect=lambda _design, _assets, path: self._write_png(path, _design),
            ), patch.object(staging.os, "replace", side_effect=tamper_marker):
                with self.assertRaises((ValueError, KeyError)):
                    self._publish_pair(source, target, output, "task")

            self.assertFalse((output_dir / "task_output.json").exists())
            self.assertFalse((output_dir / "task_output.png").exists())
            self.assertFalse((output_dir / ".task_output.commit").exists())

    def test_initial_stale_cleanup_failure_is_quarantined(self):
        source, target = self._empty_request()
        output = {"canvas": target, "elements": []}
        with tempfile.TemporaryDirectory() as directory:
            output_dir = Path(directory)
            stale_json = output_dir / "task_output.json"
            stale_json.mkdir()
            with patch.object(main, "OUTPUT_DIR", output_dir), patch.object(
                main,
                "render_to_png",
                side_effect=lambda _design, _assets, path: self._write_png(path, _design),
            ):
                with self.assertRaises(OSError):
                    self._publish_pair(source, target, output, "task")

            self.assertFalse(stale_json.exists())
            self.assertTrue(
                any(
                    path.name.startswith(".chameleon-quarantine-")
                    for path in output_dir.iterdir()
                )
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
                side_effect=lambda _design, _assets, path: self._write_png(path, _design),
            ):
                self._publish_pair(source, target, output, "task")

            wire = json.loads(
                (output_dir / "task_output.json").read_text(encoding="utf-8"),
                parse_float=Decimal,
            )
            self.assertEqual(wire["elements"][0]["opacity"], opacity)

    def test_integral_exponent_decimal_token_survives_pair_serialization(self):
        opacity = Decimal("1e0")
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
        with tempfile.TemporaryDirectory() as directory:
            output_dir = Path(directory)
            with patch.object(main, "OUTPUT_DIR", output_dir), patch.object(
                main,
                "render_to_png",
                side_effect=lambda _design, _assets, path: self._write_png(path, _design),
            ):
                self._publish_pair(
                    source,
                    target,
                    {"canvas": target, "elements": [dict(source["elements"][0])]},
                    "task",
                )

            wire = json.loads(
                (output_dir / "task_output.json").read_text(encoding="utf-8"),
                parse_float=Decimal,
            )
            self.assertEqual(wire["elements"][0]["opacity"], opacity)

    def test_publish_rejects_symlinked_output_root(self):
        source, target = self._empty_request()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            outside = root / "outside"
            outside.mkdir()
            output_dir = root / "output"
            output_dir.symlink_to(outside, target_is_directory=True)

            with self.assertRaisesRegex(OSError, "symlink"):
                staging.publish_task(
                    output_dir=output_dir,
                    task_name="task",
                    source=source,
                    target_canvas=target,
                    response={"canvas": target, "elements": []},
                    assets_dir=root / "assets",
                    render_to_png=lambda _design, _assets, path: self._write_png(path, _design),
                )

            self.assertEqual(list(outside.iterdir()), [])

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

            def write_invalid_png(_design, _assets, path):
                Path(path).write_bytes(b"not-a-png")
                return []

            with patch.object(main, "OUTPUT_DIR", output_dir), patch.object(
                main,
                "render_to_png",
                side_effect=write_invalid_png,
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
                side_effect=lambda _design, _assets, path: self._write_png(path, _design),
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
                side_effect=lambda _design, _assets, path: self._write_png(path, _design),
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
                side_effect=lambda _design, _assets, path: self._write_png(path, _design),
            ):
                result = main.main()

            self.assertEqual(result, 1)
            self.assertTrue((output_dir / "second_output.json").is_file())
            self.assertTrue((output_dir / "second_output.png").is_file())
            self.assertTrue((output_dir / ".second_output.commit").is_file())


    def test_startup_warmup_reuses_renderer_font_manager(self):
        from chameleon.renderer.converter.brand_fonts import warm_brand_font_manager
        from chameleon.renderer.converter.convert import _get_renderer

        fonts_dir = PROJECT_ROOT / "chameleon" / "brand_kit" / "fonts"
        warmed = warm_brand_font_manager(str(fonts_dir))
        renderer = _get_renderer(str(fonts_dir.resolve()))

        self.assertIs(renderer.font_manager, warmed)
        self.assertIsNotNone(warmed._skia_warmup)

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
