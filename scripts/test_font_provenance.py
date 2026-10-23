import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from scripts.verify_font_provenance import verify_manifest


class FontProvenanceManifestTests(unittest.TestCase):
    @staticmethod
    def _write_manifest(root: Path, font_bytes: bytes = b"font", license_bytes: bytes = b"license") -> Path:
        fonts_directory = root / "chameleon" / "brand_kit" / "fonts"
        fonts_directory.mkdir(parents=True)
        font_path = fonts_directory / "Example-Regular.ttf"
        license_path = fonts_directory / "OFL-Example.txt"
        font_path.write_bytes(font_bytes)
        license_path.write_bytes(license_bytes)
        manifest_path = root / "Docs" / "font_provenance_manifest.json"
        manifest_path.parent.mkdir()
        manifest_path.write_text(
            json.dumps(
                {
                    "manifest_version": 1,
                    "font_directory": "chameleon/brand_kit/fonts",
                    "fonts": [
                        {
                            "path": "chameleon/brand_kit/fonts/Example-Regular.ttf",
                            "sha256": hashlib.sha256(font_bytes).hexdigest(),
                        }
                    ],
                    "licenses": [
                        {
                            "path": "chameleon/brand_kit/fonts/OFL-Example.txt",
                            "sha256": hashlib.sha256(license_bytes).hexdigest(),
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        return manifest_path

    def test_accepts_matching_font_and_license_inventory(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            manifest_path = self._write_manifest(root)

            self.assertEqual(verify_manifest(root, manifest_path), [])

    def test_rejects_hash_drift_and_unlisted_font(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            manifest_path = self._write_manifest(root)
            fonts_directory = root / "chameleon" / "brand_kit" / "fonts"
            (fonts_directory / "Example-Regular.ttf").write_bytes(b"changed")
            (fonts_directory / "Example-Bold.ttf").write_bytes(b"extra")

            errors = verify_manifest(root, manifest_path)

            self.assertTrue(any("hash mismatch" in error for error in errors))
            self.assertTrue(any("unexpected font file" in error for error in errors))

    def test_rejects_missing_license_file(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            manifest_path = self._write_manifest(root)
            (root / "chameleon" / "brand_kit" / "fonts" / "OFL-Example.txt").unlink()

            errors = verify_manifest(root, manifest_path)

            self.assertTrue(any("missing file" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
