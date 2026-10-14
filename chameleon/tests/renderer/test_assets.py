import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).parents[3]
sys.path.insert(0, str(PROJECT_ROOT))

from chameleon.renderer.converter.assets import asset_path


class AssetPathTests(unittest.TestCase):
    def test_asset_path_rejects_absolute_traversal_and_symlink_escape(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "assets"
            outside = Path(directory) / "outside.png"
            root.mkdir()
            outside.write_bytes(b"outside")
            (root / "inside.png").write_bytes(b"inside")
            (root / "link.png").symlink_to(outside)

            self.assertEqual(asset_path(str(root), "inside.png"), (root / "inside.png").resolve())
            self.assertIsNone(asset_path(str(root), str(outside)))
            self.assertIsNone(asset_path(str(root), "../outside.png"))
            self.assertIsNone(asset_path(str(root), "link.png"))

    def test_asset_path_rejects_non_string_identifiers(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.assertIsNone(asset_path(str(root), 42))


if __name__ == "__main__":
    unittest.main()
