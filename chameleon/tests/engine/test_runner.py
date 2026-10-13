import json
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from engine import main
from engine.errors import InfeasibleLayoutError


def _test_renderer(design, assets_dir, png_path):
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

    def test_infeasible_task_cleans_stale_and_publishes_nothing(self):
        self.write_task("bad", self.task())
        for suffix in ("json", "png", "json.tmp", "png.tmp"):
            (self.output_dir / f"bad_output.{suffix}").write_text("stale")
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

        def resize_probe(source, target):
            seen["x"] = source["elements"][0]["x"]
            seen["target"] = target["width"]
            result = {"canvas": dict(target), "elements": [dict(source["elements"][0])]}
            result["elements"][0].update({"x": 10, "y": 2, "width": 10, "height": 10})
            return result

        with patch.object(main, "resize", side_effect=resize_probe):
            self.assertEqual(main.main(), 0)
        self.assertEqual(seen["x"], Decimal("12.5"))
        self.assertIs(type(seen["x"]), Decimal)
        self.assertIs(type(seen["target"]), int)

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

    def test_complete_batch_returns_zero_only_after_all_pairs_commit(self):
        self.write_task("first", self.task(100))
        self.write_task("second", self.task(100))
        self.assertEqual(main.main(), 0)
        for stem in ("first", "second"):
            self.assertTrue((self.output_dir / f"{stem}_output.json").is_file())
            self.assertTrue((self.output_dir / f"{stem}_output.png").is_file())


if __name__ == "__main__":
    unittest.main()
