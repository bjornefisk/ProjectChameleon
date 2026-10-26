import contextlib
import io
import json
import sys
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parents[3]
CHAMELEON_ROOT = PROJECT_ROOT / "chameleon"
if str(CHAMELEON_ROOT) not in sys.path:
    sys.path.insert(0, str(CHAMELEON_ROOT))

from engine import main as runner_main
from engine.contract import validate_response
from engine.layout.horizontal_ribbon import is_horizontal_ribbon_suitable
from engine.layout.vertical_restack import is_vertical_restack_suitable

SYNTHETIC_ROOT = CHAMELEON_ROOT / "input_synthetic"
ASSETS = CHAMELEON_ROOT / "brand_kit" / "assets"
FONTS = CHAMELEON_ROOT / "brand_kit" / "fonts"
ISSUE_81_CASES = (
    "chameleon_sample_level2_core_skyscraper",
    "chameleon_sample_level2_core_compact_square",
    "chameleon_sample_level3_advanced_skyscraper",
    "chameleon_sample_level3_advanced_medium_rectangle",
    "chameleon_sample_level3_advanced_compact_square",
)
EXPECTED_SUCCESS_CASES = frozenset(
    {
        "chameleon_sample_level2_core_skyscraper",
        "chameleon_sample_level2_core_compact_square",
        "chameleon_sample_level3_advanced_compact_square",
    }
)
VERTICAL_CASES = frozenset(
    {
        "chameleon_sample_level2_core_skyscraper",
        "chameleon_sample_level2_core_compact_square",
        "chameleon_sample_level3_advanced_skyscraper",
        "chameleon_sample_level3_advanced_compact_square",
    }
)
HORIZONTAL_CASES = frozenset(
    {
        "chameleon_sample_level2_core_compact_square",
        "chameleon_sample_level3_advanced_medium_rectangle",
        "chameleon_sample_level3_advanced_compact_square",
    }
)


class SyntheticRestackFallbackTests(unittest.TestCase):
    def _load_task(self, stem):
        return json.loads(
            (SYNTHETIC_ROOT / f"{stem}.json").read_text(encoding="utf-8"),
            parse_float=Decimal,
        )

    def test_issue_81_targets_admit_directional_restack_fallbacks(self):
        for stem in ISSUE_81_CASES:
            with self.subTest(case=stem):
                task = self._load_task(stem)
                source = task["source"]
                target = task["target_canvas"]
                if stem in VERTICAL_CASES:
                    self.assertTrue(is_vertical_restack_suitable(source, target))
                if stem in HORIZONTAL_CASES:
                    self.assertTrue(is_horizontal_ribbon_suitable(source, target))

    def test_issue_81_cases_publish_valid_pairs_or_fail_closed(self):
        with tempfile.TemporaryDirectory(prefix="chameleon-issue-81-") as directory:
            root = Path(directory)
            input_dir = root / "input"
            output_dir = root / "output"
            input_dir.mkdir()
            output_dir.mkdir()
            for stem in ISSUE_81_CASES:
                (input_dir / f"{stem}.json").write_bytes(
                    (SYNTHETIC_ROOT / f"{stem}.json").read_bytes()
                )

            stdout = io.StringIO()
            stderr = io.StringIO()
            with patch.multiple(
                runner_main,
                INPUT_DIR=input_dir,
                OUTPUT_DIR=output_dir,
                ASSETS_DIR=ASSETS,
            ), contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                exit_code = runner_main.main()

            self.assertEqual(exit_code, 1, stderr.getvalue())
            expected_names = set()
            for stem in ISSUE_81_CASES:
                task = self._load_task(stem)
                target = task["target_canvas"]
                response_path = output_dir / f"{stem}_output.json"
                png_path = output_dir / f"{stem}_output.png"
                commit_path = output_dir / f".{stem}_output.commit"
                if stem in EXPECTED_SUCCESS_CASES:
                    expected_names.update(
                        {
                            response_path.name,
                            png_path.name,
                            commit_path.name,
                        }
                    )
                    self.assertTrue(response_path.is_file())
                    self.assertTrue(png_path.is_file())
                    self.assertTrue(commit_path.is_file())
                    self.assertIn(f"[{stem}.json] status=SUCCESS", stdout.getvalue())
                    response = json.loads(
                        response_path.read_text(encoding="utf-8"),
                        parse_float=Decimal,
                    )
                    validate_response(
                        task["source"], target, response, fonts_dir=FONTS
                    )
                    with Image.open(png_path) as artifact:
                        artifact.verify()
                    with Image.open(png_path) as artifact:
                        self.assertEqual(
                            artifact.size, (target["width"], target["height"])
                        )
                else:
                    self.assertIn(
                        f"[{stem}.json] status=INCOMPLETE_SEARCH",
                        stderr.getvalue(),
                    )
                    self.assertFalse(response_path.exists())
                    self.assertFalse(png_path.exists())
                    self.assertFalse(commit_path.exists())

            self.assertEqual(
                {path.name for path in output_dir.iterdir()}, expected_names
            )


if __name__ == "__main__":
    unittest.main()
