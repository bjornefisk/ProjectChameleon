import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

import skia

PROJECT_ROOT = Path(__file__).parents[3]
FONT_DIR = PROJECT_ROOT / "chameleon" / "brand_kit" / "fonts"
sys.path.insert(0, str(PROJECT_ROOT))

from chameleon.renderer.converter.brand_fonts import (
    MissingFontError,
    load_brand_font_manager,
    lookup_exact_font,
)


class FontLoaderProvenanceTests(unittest.TestCase):
    def test_rejects_unknown_filename_weight_suffix(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            temporary_fonts = Path(temporary_directory)
            shutil.copyfile(
                FONT_DIR / "SolsticeSans-Bold.ttf",
                temporary_fonts / "SolsticeSans-Condensed.ttf",
            )

            with self.assertRaises(MissingFontError):
                load_brand_font_manager(str(temporary_fonts))

    def test_rejects_duplicate_face_mapping(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            temporary_fonts = Path(temporary_directory)
            shutil.copyfile(
                FONT_DIR / "SolsticeSans-BoldItalic.ttf",
                temporary_fonts / "SolsticeSans-BoldItalic.ttf",
            )
            shutil.copyfile(
                FONT_DIR / "SolsticeSans-BoldItalic.ttf",
                temporary_fonts / "SolsticeSans-ItalicBold.ttf",
            )

            with self.assertRaises(MissingFontError):
                load_brand_font_manager(str(temporary_fonts))

    def test_rejects_embedded_metadata_mismatch(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            temporary_fonts = Path(temporary_directory)
            shutil.copyfile(
                FONT_DIR / "SolsticeSans-Bold.ttf",
                temporary_fonts / "SolsticeSans-Regular.ttf",
            )

            with self.assertRaises(MissingFontError):
                load_brand_font_manager(str(temporary_fonts))

    def test_checked_samples_have_glyphs_for_exact_faces(self):
        codepoints = {}
        input_directory = PROJECT_ROOT / "chameleon" / "input"
        for sample_path in sorted(input_directory.glob("chameleon_sample_*.json")):
            document = json.loads(sample_path.read_text(encoding="utf-8"))
            for element in document["source"]["elements"]:
                if element["type"] != "text":
                    continue
                weight = "bold" if element.get("font_weight") == "bold" else "regular"
                style = (
                    "bold"
                    if weight == "bold" and element.get("font_style") != "italic"
                    else "italic"
                    if element.get("font_style") == "italic"
                    else "regular"
                )
                face = (element["font_family"], weight, style)
                codepoints.setdefault(face, set()).update(element["content"])

        self.assertEqual(
            {face: len(values) for face, values in codepoints.items()},
            {
                ("Solstice Serif", "bold", "bold"): 35,
                ("Solstice Sans", "regular", "regular"): 35,
                ("Solstice Sans", "bold", "bold"): 33,
            },
        )
        manager = load_brand_font_manager(str(FONT_DIR))
        for face, values in codepoints.items():
            family, weight, style = face
            typeface = skia.Typeface.MakeFromData(
                lookup_exact_font(manager, family, weight, style)
            )
            glyphs = skia.Font(typeface, 24).textToGlyphs("".join(sorted(values)))
            self.assertEqual(len(glyphs), len(values), face)
            self.assertTrue(all(int(glyph) != 0 for glyph in glyphs), face)


if __name__ == "__main__":
    unittest.main()
