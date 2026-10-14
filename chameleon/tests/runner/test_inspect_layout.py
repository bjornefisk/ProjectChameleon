import importlib.util
import tempfile
import unittest
from pathlib import Path

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


if __name__ == "__main__":
    unittest.main()
