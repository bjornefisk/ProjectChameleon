import builtins
import contextlib
import hashlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "chameleon"))
from unittest.mock import Mock, patch

from PIL import Image

from engine import main, staging
from engine.errors import InfeasibleLayoutError, InfeasibleReasonCode
from chameleon.renderer.converter.assets import asset_path
from chameleon.renderer.converter.wrap import TextOverflowError


def _test_renderer(design, assets_dir, png_path):
    if design.get("elements") and all(
        element.get("type") == "shape" for element in design["elements"]
    ):
        from chameleon.renderer.converter.convert import render_design_to_png

        root = PROJECT_ROOT / "chameleon" / "brand_kit"
        render_design_to_png(
            design,
            root / "assets",
            png_path,
            fonts_dir=root / "fonts",
        )
        return
    Image.new(
        "RGB", (design["canvas"]["width"], design["canvas"]["height"]), "white"
    ).save(png_path, format="PNG")

class RunnerIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        root = Path(self.tempdir.name)
        self.input_dir = root / "input"
        self.output_dir = root / "output"
        self.input_dir.mkdir()
        self.output_dir.mkdir()
        self.assets_dir = root / "assets"
        self.assets_dir.mkdir()
        self.constants = patch.multiple(
            main,
            INPUT_DIR=self.input_dir,
            OUTPUT_DIR=self.output_dir,
            ASSETS_DIR=self.assets_dir,
        )
        self.constants.start()
        self.renderer = patch.object(main, "render_to_png", side_effect=_test_renderer)
        self.renderer.start()

    def tearDown(self):
        self.renderer.stop()
        self.constants.stop()
        self.tempdir.cleanup()

    @staticmethod
    def task(canvas_width=100):
        return {
            "source": {"canvas": {"width": canvas_width, "height": 100}, "elements": []},
            "target_canvas": {"width": 100, "height": 100},
        }

    def write_task(self, name, task, raw=False):
        path = self.input_dir / f"{name}.json"
        if raw:
            path.write_text(task, encoding="utf-8")
        else:
            path.write_text(json.dumps(task), encoding="utf-8")

    def test_success_publishes_valid_pair(self):
        self.write_task("good", self.task())
        self.assertEqual(main.main(), 0)
        json_path = self.output_dir / "good_output.json"
        png_path = self.output_dir / "good_output.png"
        self.assertTrue(json_path.is_file())
        self.assertTrue(png_path.is_file())
        self.assertEqual(json.loads(json_path.read_text()), {"canvas": {"width": 100, "height": 100}, "elements": []})

    def test_input_symlink_is_rejected_without_publishing_pair(self):
        outside = Path(self.tempdir.name) / "outside-task.json"
        outside.write_text(json.dumps(self.task()), encoding="utf-8")
        (self.input_dir / "linked.json").symlink_to(outside)

        with contextlib.redirect_stderr(io.StringIO()):
            self.assertNotEqual(main.main(), 0)

        self.assertFalse((self.output_dir / "linked_output.json").exists())
        self.assertFalse((self.output_dir / "linked_output.png").exists())
        self.assertFalse((self.output_dir / ".linked_output.commit").exists())


    def test_output_root_symlink_is_rejected_without_external_publication(self):
        outside_output = Path(self.tempdir.name) / "outside-output"
        outside_output.mkdir()
        preserved = outside_output / "preserved.txt"
        preserved.write_text("keep", encoding="utf-8")
        self.output_dir.rmdir()
        self.output_dir.symlink_to(outside_output, target_is_directory=True)
        self.write_task("good", self.task())

        with contextlib.redirect_stderr(io.StringIO()):
            self.assertNotEqual(main.main(), 0)

        self.assertTrue(preserved.is_file())
        self.assertFalse((outside_output / "good_output.json").exists())
        self.assertFalse((outside_output / "good_output.png").exists())

    def test_invalid_task_name_does_not_block_valid_task(self):
        self.write_task("bad\nname", self.task())
        self.write_task("good", self.task())
        stderr = io.StringIO()

        with contextlib.redirect_stderr(stderr):
            self.assertEqual(main.main(), 1)

        self.assertIn(
            r"[bad\nname.json] status=MALFORMED_INPUT",
            stderr.getvalue(),
        )
        self.assertTrue((self.output_dir / "good_output.json").is_file())
        self.assertTrue((self.output_dir / "good_output.png").is_file())
        self.assertFalse((self.output_dir / "bad\nname_output.json").exists())

    def test_invalid_stale_stem_is_reconciled_before_valid_task(self):
        stale_stem = "bad\nname"
        for suffix in ("json", "png", "json.tmp", "png.tmp"):
            (self.output_dir / f"{stale_stem}_output.{suffix}").write_text(
                "stale",
                encoding="utf-8",
            )
        (self.output_dir / f".{stale_stem}_output.commit").write_text(
            "stale",
            encoding="utf-8",
        )
        (self.output_dir / f".{stale_stem}.stage-old").mkdir()
        self.write_task("good", self.task())

        self.assertEqual(main.main(), 0)

        self.assertTrue((self.output_dir / "good_output.json").is_file())
        self.assertTrue((self.output_dir / "good_output.png").is_file())
        self.assertFalse((self.output_dir / f"{stale_stem}_output.json").exists())
        self.assertFalse((self.output_dir / f".{stale_stem}_output.commit").exists())
        self.assertFalse((self.output_dir / f".{stale_stem}.stage-old").exists())

    def test_removed_task_pair_is_reconciled_on_next_no_task_run(self):
        self.write_task("removed", self.task())
        self.assertEqual(main.main(), 0)
        self.assertTrue((self.output_dir / "removed_output.json").is_file())
        self.assertTrue((self.output_dir / "removed_output.png").is_file())

        (self.input_dir / "removed.json").unlink()
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertNotEqual(main.main(), 0)

        self.assertFalse((self.output_dir / "removed_output.json").exists())
        self.assertFalse((self.output_dir / "removed_output.png").exists())
        self.assertFalse((self.output_dir / ".removed_output.commit").exists())



    def test_task_and_element_control_characters_are_not_raw_diagnostics(self):
        task_name = "task"
        element_id = "element\x1b[32m\x07\x08\n"
        task = self.task()
        element = {
            "id": element_id,
            "type": "shape",
            "x": 0,
            "y": 0,
            "width": 1,
            "height": 1,
            "shape_type": "rectangle",
            "fill_color": "rgba(0,0,0,1)",
        }
        task["source"]["elements"] = [element, dict(element)]
        self.write_task(task_name, task)

        stdout = io.StringIO()
        stderr = io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            self.assertNotEqual(main.main(), 0)

        diagnostics = stdout.getvalue() + stderr.getvalue()
        for control in ("\x00", "\x01", "\x07", "\x08", "\x09", "\x0b", "\x0c", "\x0d", "\x1b", "\x7f"):
            self.assertNotIn(control, diagnostics)

    def test_infeasible_task_cleans_stale_and_publishes_nothing(self):
        self.write_task("bad", self.task())
        for suffix in ("json", "png", "json.tmp", "png.tmp"):
            (self.output_dir / f"bad_output.{suffix}").write_text("stale")
        for name in (".bad_output.commit", ".bad_output.commit.tmp"):
            (self.output_dir / name).write_text("stale")
        stale_stage = self.output_dir / ".bad.stage-old"
        stale_stage.mkdir()
        (stale_stage / "bad_output.json.tmp").write_text("stale")
        with patch.object(main, "resize", side_effect=InfeasibleLayoutError("NO_HARD_VALID_CANDIDATE")):
            self.assertNotEqual(main.main(), 0)
        self.assertEqual(list(self.output_dir.iterdir()), [])

    def test_malformed_and_nonfinite_input_fail_closed(self):
        self.write_task("nan", '{"source": {"canvas": {"width": NaN, "height": 1}, "elements": []}, "target_canvas": {"width": 1, "height": 1}}', raw=True)
        self.assertNotEqual(main.main(), 0)
        self.assertEqual(list(self.output_dir.iterdir()), [])

    def test_decimal_and_exponent_ingress_reaches_resize_exactly(self):
        task = self.task()
        task["source"]["elements"] = [{
            "id": "box", "type": "shape", "x": 1.25e1, "y": 2,
            "width": 10, "height": 10, "shape_type": "rectangle",
            "fill_color": "rgba(0,0,0,1)",
        }]
        self.write_task("numeric", json.dumps(task).replace("12.5", "1.25e1"), raw=True)
        seen = {}
        real_resize = main.resize

        def resize_probe(source, target):
            seen["x"] = source["elements"][0]["x"]
            seen["target"] = target["width"]
            return real_resize(source, target)

        with patch.object(main, "resize", side_effect=resize_probe):
            self.assertEqual(main.main(), 0)
        self.assertEqual(seen["x"], Decimal("12.5"))
        self.assertIs(type(seen["x"]), Decimal)
        self.assertIs(type(seen["target"]), int)
        published = json.loads(
            (self.output_dir / "numeric_output.json").read_text(encoding="utf-8")
        )
        self.assertEqual(published["elements"][0]["x"], 12)

    def test_mutable_decimal_output_uses_half_even_quantization(self):
        task = self.task()
        element = {
            "id": "box", "type": "shape", "x": 0, "y": 0,
            "width": 10, "height": 10, "shape_type": "rectangle",
            "fill_color": "rgba(0,0,0,1)",
        }
        task["source"]["elements"] = [element]
        self.write_task("rounded", task)
        response_element = dict(element)
        response_element.update({
            "x": Decimal("10.5"),
            "y": Decimal("11.5"),
            "width": Decimal("10.5"),
            "height": Decimal("10.5"),
        })
        response = {
            "canvas": {"width": 100, "height": 100},
            "elements": [response_element],
        }
        with patch.object(main, "resize", return_value=response):
            self.assertEqual(main.main(), 0)
        published = json.loads(
            (self.output_dir / "rounded_output.json").read_text(encoding="utf-8")
        )
        self.assertEqual(
            published["elements"][0],
            {
                **element,
                "x": 10,
                "y": 12,
                "width": 10,
                "height": 10,
            },
        )

    def test_invalid_candidate_is_runtime_failure_not_infeasibility(self):
        task = self.task()
        element = {
            "id": "box", "type": "shape", "x": 10, "y": 10,
            "width": 10, "height": 10, "shape_type": "rectangle",
            "fill_color": "rgba(0,0,0,1)",
        }
        task["source"]["elements"] = [element]
        self.write_task("invalid_candidate", task)
        response_element = dict(element)
        response_element["x"] = -10
        stderr = io.StringIO()
        with patch.object(
            main,
            "resize",
            return_value={
                "canvas": {"width": 100, "height": 100},
                "elements": [response_element],
            },
        ):
            with contextlib.redirect_stderr(stderr):
                self.assertNotEqual(main.main(), 0)
        self.assertIn("status=RUNTIME_IO_FAILURE", stderr.getvalue())
        self.assertNotIn("status=INFEASIBLE_LAYOUT", stderr.getvalue())


    def test_single_candidate_text_rejection_is_runtime_failure(self):
        self.write_task("text_rejection", self.task())
        stderr = io.StringIO()
        with patch.object(
            main,
            "resize",
            return_value={"canvas": {"width": 100, "height": 100}, "elements": []},
        ), patch.object(
            main, "render_to_png", side_effect=TextOverflowError("text overflow")
        ), patch.object(main, "_TextOverflowError", TextOverflowError):
            with contextlib.redirect_stderr(stderr):
                result = main.main()

        self.assertEqual(result, 1)
        self.assertIn(
            "[text_rejection.json] status=RUNTIME_IO_FAILURE reason=TEXT_OVERFLOW",
            stderr.getvalue(),
        )
        self.assertFalse((self.output_dir / "text_rejection_output.json").exists())
        self.assertFalse((self.output_dir / "text_rejection_output.png").exists())
    def test_asset_references_cannot_escape_asset_root(self):
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            assets_dir = root / "assets"
            assets_dir.mkdir()
            inside = assets_dir / "inside.png"
            outside = root / "outside.png"
            inside.write_bytes(b"inside")
            outside.write_bytes(b"outside")
            link = assets_dir / "link.png"
            link.symlink_to(outside)

            self.assertEqual(asset_path(str(assets_dir), "inside.png"), inside.resolve())
            self.assertIsNone(asset_path(str(assets_dir), "../outside.png"))
            self.assertIsNone(asset_path(str(assets_dir), str(outside)))
            self.assertIsNone(asset_path(str(assets_dir), "link.png"))

    def test_cleanup_failure_quarantines_stale_paths(self):
        self.write_task("stale", self.task())
        (self.output_dir / "stale_output.json").write_text("stale", encoding="utf-8")
        (self.output_dir / "stale_output.png").write_bytes(b"stale")
        (self.output_dir / ".stale_output.commit").mkdir()

        self.assertNotEqual(main.main(), 0)
        self.assertFalse((self.output_dir / "stale_output.json").exists())
        self.assertFalse((self.output_dir / "stale_output.png").exists())
        self.assertTrue(
            any(
                path.name.startswith(".chameleon-quarantine-")
                for path in self.output_dir.iterdir()
            )
        )

    def test_reconciliation_quarantine_does_not_block_current_tasks(self):
        self.write_task("good", self.task())
        (self.output_dir / "stale_output.json").write_text("stale", encoding="utf-8")
        (self.output_dir / "stale_output.png").write_bytes(b"stale")
        (self.output_dir / ".stale_output.commit").mkdir()

        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            result = main.main()

        self.assertEqual(result, 1)
        self.assertTrue((self.output_dir / "good_output.json").is_file())
        self.assertTrue((self.output_dir / "good_output.png").is_file())
        self.assertFalse((self.output_dir / "stale_output.json").exists())
        self.assertIn("stale paths quarantined", stderr.getvalue())
        self.assertTrue(
            any(
                path.name.startswith(".chameleon-quarantine-")
                for path in self.output_dir.iterdir()
            )
        )

    def test_inspector_rejects_uncommitted_json_in_directory(self):
        self.write_task("committed", self.task())
        self.assertEqual(main.main(), 0)
        (self.output_dir / "uncommitted_output.json").write_text(
            json.dumps({"canvas": {"width": 100, "height": 100}, "elements": []}),
            encoding="utf-8",
        )
        inspector = Path(__file__).resolve().parents[3] / "scripts" / "inspect_layout.py"
        result = subprocess.run(
            [sys.executable, str(inspector), str(self.output_dir)],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Uncommitted or invalid output pair", result.stderr)

    def test_staging_cleanup_failure_is_reported(self):
        self.write_task("cleanup_failure", self.task())
        original_cleanup = staging.cleanup_task_artifacts
        cleanup_calls = [0]

        def fail_on_rollback(output_dir, task_name):
            cleanup_calls[0] += 1
            if cleanup_calls[0] == 2:
                raise OSError("rollback failed")
            original_cleanup(output_dir, task_name)

        stderr = io.StringIO()
        with patch.object(
            staging,
            "cleanup_task_artifacts",
            side_effect=fail_on_rollback,
        ):
            with patch.object(
                main,
                "render_to_png",
                side_effect=OSError("renderer failed"),
            ):
                with contextlib.redirect_stderr(stderr):
                    self.assertNotEqual(main.main(), 0)
        self.assertIn("rollback failed", stderr.getvalue())
        visible = [path for path in self.output_dir.iterdir() if not path.name.startswith(".chameleon-quarantine-")]
        self.assertEqual(visible, [])
        self.assertTrue(any(path.name.startswith(".chameleon-quarantine-") for path in self.output_dir.iterdir()))

    def test_render_failure_cleans_staged_and_final_pair(self):
        self.write_task("render_failure", self.task())
        for suffix in ("json", "png", "json.tmp", "png.tmp"):
            (self.output_dir / f"render_failure_output.{suffix}").write_text("stale")

        def failing_renderer(design, assets_dir, png_path):
            png_path.write_bytes(b"partial")
            raise OSError("renderer failed")

        with patch.object(main, "render_to_png", side_effect=failing_renderer):
            self.assertNotEqual(main.main(), 0)
        self.assertEqual(list(self.output_dir.iterdir()), [])

    def test_mixed_batch_continues_and_returns_partial_failure(self):
        self.write_task("good", self.task(100))
        self.write_task("bad", self.task(101))

        def resize_mixed(source, target):
            if source["canvas"]["width"] == 101:
                raise InfeasibleLayoutError("NO_HARD_VALID_CANDIDATE")
            return {"canvas": dict(target), "elements": []}

        with patch.object(main, "resize", side_effect=resize_mixed):
            self.assertNotEqual(main.main(), 0)
        self.assertTrue((self.output_dir / "good_output.json").is_file())
        self.assertTrue((self.output_dir / "good_output.png").is_file())
        self.assertFalse((self.output_dir / "bad_output.json").exists())
        self.assertFalse((self.output_dir / "bad_output.png").exists())


    def test_typed_search_failures_continue_and_leave_only_successful_pair(self):
        self.write_task("good", self.task(100))
        self.write_task("infeasible", self.task(101))
        self.write_task("cutoff", self.task(102))

        def resize_mixed(source, target):
            width = source["canvas"]["width"]
            if width == 101:
                raise InfeasibleLayoutError(
                    InfeasibleReasonCode.NO_HARD_VALID_CANDIDATE
                )
            if width == 102:
                raise InfeasibleLayoutError(InfeasibleReasonCode.INCOMPLETE_SEARCH)
            return {"canvas": dict(target), "elements": []}

        stderr = io.StringIO()
        with patch.object(main, "resize", side_effect=resize_mixed):
            with contextlib.redirect_stderr(stderr):
                result = main.main()

        self.assertEqual(result, 1)
        diagnostics = stderr.getvalue()
        self.assertIn(
            "[cutoff.json] status=INCOMPLETE_SEARCH reason=INCOMPLETE_SEARCH",
            diagnostics,
        )
        self.assertIn(
            "[infeasible.json] status=INFEASIBLE_LAYOUT reason=NO_HARD_VALID_CANDIDATE",
            diagnostics,
        )
        self.assertTrue((self.output_dir / "good_output.json").is_file())
        self.assertTrue((self.output_dir / "good_output.png").is_file())
        for stem in ("infeasible", "cutoff"):
            self.assertFalse((self.output_dir / f"{stem}_output.json").exists())
            self.assertFalse((self.output_dir / f"{stem}_output.png").exists())
    def test_real_incomplete_search_publishes_no_artifacts(self):
        evaluation = json.loads(
            (
                PROJECT_ROOT
                / "chameleon"
                / "tests"
                / "fixtures"
                / "heldout_search_cases.json"
            ).read_text(encoding="utf-8")
        )
        case = next(
            item
            for item in evaluation["cases"]
            if item["id"] == "extreme-ratio-incomplete"
        )
        self.write_task(
            "incomplete",
            {"source": case["source"], "target_canvas": case["target_canvas"]},
        )

        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            result = main.main()

        self.assertEqual(result, 1)
        self.assertIn(
            "[incomplete.json] status=INCOMPLETE_SEARCH",
            stderr.getvalue(),
        )
        self.assertEqual(list(self.output_dir.iterdir()), [])

    def test_complete_batch_returns_zero_only_after_all_pairs_commit(self):
        self.write_task("first", self.task(100))
        self.write_task("second", self.task(100))
        self.assertEqual(main.main(), 0)
        for stem in ("first", "second"):
            self.assertTrue((self.output_dir / f"{stem}_output.json").is_file())
            self.assertTrue((self.output_dir / f"{stem}_output.png").is_file())



    def test_success_publishes_commit_marker_after_both_final_files(self):
        self.write_task("committed", self.task())
        paths = staging.artifact_paths(self.output_dir, "committed")
        observed_json_commit = []
        observed_marker_commit = []
        real_replace = staging.os.replace

        def observe_replace(source, destination):
            real_replace(source, destination)
            if destination == paths.json_final:
                observed_json_commit.append(
                    (paths.commit_marker.exists(), paths.png_final.exists())
                )
            if destination == paths.commit_marker:
                observed_marker_commit.append(
                    (paths.json_final.exists(), paths.png_final.exists())
                )

        with patch.object(staging.os, "replace", side_effect=observe_replace):
            self.assertEqual(main.main(), 0)

        marker = json.loads(paths.commit_marker.read_text(encoding="utf-8"))
        self.assertEqual(observed_json_commit, [(False, False)])
        self.assertEqual(observed_marker_commit, [(True, True)])
        self.assertEqual(marker["json"], paths.json_final.name)
        self.assertEqual(marker["png"], paths.png_final.name)
        self.assertEqual(
            marker["json_sha256"],
            hashlib.sha256(paths.json_final.read_bytes()).hexdigest(),
        )
        self.assertEqual(
            marker["png_sha256"],
            hashlib.sha256(paths.png_final.read_bytes()).hexdigest(),
        )

    def test_manifest_mismatch_after_publish_rolls_back_pair(self):
        self.write_task("tampered", self.task())
        paths = staging.artifact_paths(self.output_dir, "tampered")
        real_replace = staging.os.replace

        def tamper_json(source, destination):
            real_replace(source, destination)
            if destination == paths.json_final:
                paths.json_final.write_text("{}", encoding="utf-8")

        with patch.object(staging.os, "replace", side_effect=tamper_json):
            self.assertNotEqual(main.main(), 0)
        self.assertFalse(paths.json_final.exists())
        self.assertFalse(paths.png_final.exists())
        self.assertFalse(paths.commit_marker.exists())


    def test_interrupted_commit_cleans_pair(self):
        self.write_task("interrupted", self.task())
        paths = staging.artifact_paths(self.output_dir, "interrupted")
        real_replace = staging.os.replace

        def interrupt_after_json(source, destination):
            real_replace(source, destination)
            if destination == paths.json_final:
                raise KeyboardInterrupt

        with patch.object(staging.os, "replace", side_effect=interrupt_after_json):
            with self.assertRaises(KeyboardInterrupt):
                main.main()
        self.assertEqual(list(self.output_dir.iterdir()), [])

    def test_commit_failure_cleans_marker_and_pair(self):
        self.write_task("commit_failure", self.task())
        paths = staging.artifact_paths(self.output_dir, "commit_failure")
        real_replace = staging.os.replace

        def fail_marker_commit(source, destination):
            if destination == paths.commit_marker:
                raise OSError("marker commit failed")
            return real_replace(source, destination)

        with patch.object(staging.os, "replace", side_effect=fail_marker_commit):
            self.assertNotEqual(main.main(), 0)
        self.assertEqual(list(self.output_dir.iterdir()), [])


    def test_renderer_import_failure_does_not_use_placeholder(self):
        self.write_task("missing_renderer", self.task())
        self.renderer.stop()
        original_import = builtins.__import__

        def reject_renderer_import(name, *args, **kwargs):
            if name == "renderer.converter.convert":
                raise ImportError("renderer unavailable")
            return original_import(name, *args, **kwargs)

        stderr = io.StringIO()
        try:
            with patch("builtins.__import__", side_effect=reject_renderer_import):
                with contextlib.redirect_stderr(stderr):
                    self.assertNotEqual(main.main(), 0)
        finally:
            self.renderer.start()
        self.assertIn("status=RUNTIME_IO_FAILURE", stderr.getvalue())
        self.assertEqual(list(self.output_dir.iterdir()), [])

    def test_input_io_failure_reports_runtime_status(self):
        self.write_task("unreadable", self.task())
        stderr = io.StringIO()
        with patch.object(main, "_load_task", side_effect=OSError("read failed")):
            with contextlib.redirect_stderr(stderr):
                self.assertNotEqual(main.main(), 0)
        self.assertIn("status=RUNTIME_IO_FAILURE", stderr.getvalue())

    def test_cleanup_failure_does_not_stop_later_tasks(self):
        self.write_task("first", self.task())
        self.write_task("second", self.task())
        cleanup_calls = [0]
        original_cleanup = main.cleanup_task_artifacts

        def fail_second_cleanup(output_dir, task_name):
            cleanup_calls[0] += 1
            if cleanup_calls[0] == 2:
                raise OSError("cleanup failed")
            original_cleanup(output_dir, task_name)

        with patch.object(
            main,
            "cleanup_task_artifacts",
            side_effect=fail_second_cleanup,
        ):
            with patch.object(
                main,
                "resize",
                side_effect=[
                    InfeasibleLayoutError("NO_HARD_VALID_CANDIDATE"),
                    {"canvas": {"width": 100, "height": 100}, "elements": []},
                ],
            ):
                self.assertNotEqual(main.main(), 0)
        self.assertTrue((self.output_dir / "second_output.json").is_file())
        self.assertTrue((self.output_dir / "second_output.png").is_file())

    def test_invalid_target_schema_is_rejected_before_resize(self):
        task = self.task()
        task["target_canvas"]["unexpected"] = "invalid"
        self.write_task("invalid_target", task)
        resize_probe = Mock()
        with patch.object(main, "resize", resize_probe):
            self.assertNotEqual(main.main(), 0)
        resize_probe.assert_not_called()

    def test_renderer_writing_invalid_png_publishes_nothing(self):
        self.write_task("invalid_png", self.task())

        def invalid_renderer(design, assets_dir, png_path):
            png_path.write_bytes(b"not a png")

        with patch.object(main, "render_to_png", side_effect=invalid_renderer):
            self.assertNotEqual(main.main(), 0)
        self.assertEqual(list(self.output_dir.iterdir()), [])

    def test_inspector_rejects_uncommitted_json(self):
        json_path = self.output_dir / "uncommitted_output.json"
        json_path.write_text(
            json.dumps({"canvas": {"width": 100, "height": 100}, "elements": []}),
            encoding="utf-8",
        )
        inspector = Path(__file__).resolve().parents[3] / "scripts" / "inspect_layout.py"
        result = subprocess.run(
            [sys.executable, str(inspector), str(json_path)],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Uncommitted or invalid output pair", result.stderr)

if __name__ == "__main__":
    unittest.main()
