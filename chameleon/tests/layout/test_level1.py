import copy
import hashlib
import json
import sys
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT))

from chameleon.renderer.converter.convert import render_design_to_png

try:
    from engine.contract import validate_response
    from engine.geometry.ratios import preserves_source_ratio
    from engine.resize import resize
except ModuleNotFoundError:
    from chameleon.engine.contract import validate_response
    from chameleon.engine.geometry.ratios import preserves_source_ratio
    from chameleon.engine.resize import resize


ROOT = Path(__file__).resolve().parents[2]
LEVEL1 = ROOT / "input" / "chameleon_sample_level1_warmup.json"
ASSETS = ROOT / "brand_kit" / "assets"


class Level1IntegrationTests(unittest.TestCase):
    def _load_task(self):
        return json.loads(
            LEVEL1.read_text(encoding="utf-8"),
            parse_int=int,
            parse_float=Decimal,
        )

    def test_warmup_resizes_validates_and_renders_without_distortion(self):
        task = self._load_task()
        source = task["source"]
        target_canvas = task["target_canvas"]
        before = copy.deepcopy(source)

        response = resize(source, target_canvas)
        validate_response(source, target_canvas, response)

        self.assertEqual(source, before)
        self.assertEqual(response["canvas"], target_canvas)
        self.assertEqual(
            [element["id"] for element in response["elements"]],
            [element["id"] for element in source["elements"]],
        )

        background, logo, headline, cta = response["elements"]
        self.assertEqual(
            (background["x"], background["y"], background["width"], background["height"]),
            (0, 0, 1080, 1350),
        )
        self.assertTrue(
            preserves_source_ratio(
                logo["width"],
                logo["height"],
                source["elements"][1]["width"],
                source["elements"][1]["height"],
            )
        )
        for element in (headline, cta):
            self.assertIs(type(element["font_size"]), int)
            self.assertGreaterEqual(element["font_size"], 1)

        with tempfile.TemporaryDirectory() as directory:
            png_path = Path(directory) / "level1.png"
            repeat_path = Path(directory) / "level1-repeat.png"
            warnings = render_design_to_png(response, ASSETS, png_path)
            repeat_warnings = render_design_to_png(response, ASSETS, repeat_path)
            self.assertEqual(warnings, [])
            self.assertEqual(repeat_warnings, [])
            self.assertEqual(
                hashlib.sha256(png_path.read_bytes()).digest(),
                hashlib.sha256(repeat_path.read_bytes()).digest(),
            )
            with Image.open(png_path) as image:
                self.assertEqual(image.format, "PNG")
                self.assertEqual(image.size, (1080, 1350))

if __name__ == "__main__":
    unittest.main()
