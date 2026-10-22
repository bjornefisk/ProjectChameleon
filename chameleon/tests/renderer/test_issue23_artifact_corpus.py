"""Persisted renderer edge evidence for issue #23.

The corpus is intentionally small and source-derived: every expected PNG hash
is tied to the serialized input document, packaged asset bytes, fonts, pinned
renderer revision, Python 3.11, and direct Pillow/Skia versions. Assertions
exercise the real adapter rather than a mock or synthetic publication path.
"""

from __future__ import annotations

import hashlib
import io
import json
import platform
import sys
import tempfile
import unittest
from copy import deepcopy
from importlib.metadata import distribution, version
from pathlib import Path
from unittest.mock import patch

from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from renderer.converter.brand_fonts import load_brand_font_manager
    from renderer.converter.convert import convert_chameleon_to_crello, render_design_to_png
except ModuleNotFoundError:
    from chameleon.renderer.converter.brand_fonts import load_brand_font_manager
    from chameleon.renderer.converter.convert import (
        convert_chameleon_to_crello,
        render_design_to_png,
    )

ROOT = PROJECT_ROOT / "chameleon"
ASSETS = ROOT / "brand_kit" / "assets"
FONTS = ROOT / "brand_kit" / "fonts"
CORPUS = ROOT / "tests" / "fixtures" / "renderer_artifact_hashes.json"
PINNED_RENDERER_SHA = "a17e1fb9a732959dd6c21ae168d5ee09d74bd64f"
CANONICAL_PYTHON_MINOR = "3.11"


def _platform_hash_key() -> str:
    system = platform.system().strip().lower()
    machine = platform.machine().strip().lower().replace("-", "_")
    machine = {
        "amd64": "x86_64",
        "x64": "x86_64",
    }.get(machine, machine)
    return f"{system}-{machine}"

def _canonical_digest(value: object) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _font_tree_digest() -> str:
    digest = hashlib.sha256()
    for path in sorted(
        path
        for path in FONTS.rglob("*")
        if path.is_file() and path.suffix.lower() in {".otf", ".ttf"}
    ):
        digest.update(path.relative_to(FONTS).as_posix().encode("utf-8"))
        digest.update(path.read_bytes())
    return digest.hexdigest()


def _documents() -> dict[str, dict]:
    image_base = {
        "id": "asset",
        "type": "image",
        "x": 0,
        "y": 0,
        "width": 32,
        "height": 16,
        "asset_id": "solstice_bottle.png",
    }
    return {
        "contain": {
            "canvas": {"width": 32, "height": 16},
            "elements": [{**image_base, "fit": "contain"}],
        },
        "cover": {
            "canvas": {"width": 32, "height": 16},
            "elements": [{**image_base, "fit": "cover"}],
        },
        "fill": {
            "canvas": {"width": 32, "height": 16},
            "elements": [{**image_base, "fit": "fill"}],
        },
        "rotation": {
            "canvas": {"width": 40, "height": 40},
            "elements": [
                {
                    "id": "rotated",
                    "type": "shape",
                    "x": 10,
                    "y": 16,
                    "width": 20,
                    "height": 8,
                    "rotation": 90,
                    "shape_type": "rectangle",
                    "fill_color": "rgba(255,0,0,1)",
                }
            ],
        },
        "right_negative_spacing": {
            "canvas": {"width": 160, "height": 50},
            "elements": [
                {
                    "id": "copy",
                    "type": "text",
                    "x": 10,
                    "y": 5,
                    "width": 140,
                    "height": 40,
                    "content": "SOLSTICE ",
                    "font_family": "Solstice Sans",
                    "font_size": 20,
                    "color": "rgba(35,25,35,1)",
                    "text_align": "right",
                    "letter_spacing": -1,
                }
            ],
        },
        "missing_asset": {
            "canvas": {"width": 40, "height": 30},
            "elements": [
                {
                    "id": "missing",
                    "type": "image",
                    "x": 2,
                    "y": 2,
                    "width": 36,
                    "height": 26,
                    "asset_id": "missing-provenance.png",
                    "fit": "contain",
                }
            ],
        },
    }


def _render(document: dict, font_manager) -> tuple[bytes, list[str], tuple[int, int]]:
    with tempfile.TemporaryDirectory() as directory:
        output = Path(directory) / "artifact.png"
        warnings = render_design_to_png(
            document,
            ASSETS,
            output,
            fonts_dir=FONTS,
            max_size=2048,
            font_manager=font_manager,
        )
        payload = output.read_bytes()
    with Image.open(io.BytesIO(payload)) as image:
        image.load()
        size = image.size
    return payload, warnings, size


def _ink_bbox(payload: bytes) -> tuple[int, int, int, int] | None:
    with Image.open(io.BytesIO(payload)) as image:
        image.load()
        points = [
            (x, y)
            for y in range(image.height)
            for x in range(image.width)
            if image.getpixel((x, y))[:3] != (255, 255, 255)
        ]
    if not points:
        return None
    return (
        min(x for x, _ in points),
        min(y for _, y in points),
        max(x for x, _ in points) + 1,
        max(y for _, y in points) + 1,
    )


class RendererArtifactCorpusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.font_manager = load_brand_font_manager(str(FONTS))
        cls.manifest = json.loads(CORPUS.read_text(encoding="utf-8"))
        cls.documents = _documents()

    def test_persisted_hashes_bind_documents_assets_fonts_and_renderer(self):
        self.assertEqual(self.manifest["renderer_commit"], PINNED_RENDERER_SHA)
        self.assertEqual(self.manifest["python_minor_version"], CANONICAL_PYTHON_MINOR)
        self.assertEqual(
            f"{sys.version_info.major}.{sys.version_info.minor}",
            CANONICAL_PYTHON_MINOR,
            "renderer PNG hashes are bound to the project's Python 3.11 baseline",
        )
        for distribution_name, expected_version in self.manifest["dependencies"].items():
            self.assertEqual(expected_version, version(distribution_name), distribution_name)
        self.assertEqual(self.manifest["font_tree_sha256"], _font_tree_digest())
        direct_url = json.loads(distribution("cr-renderer").read_text("direct_url.json"))
        self.assertEqual(direct_url["vcs_info"]["commit_id"], PINNED_RENDERER_SHA)
        self.assertEqual(
            self.manifest["asset_sha256"],
            hashlib.sha256((ASSETS / "solstice_bottle.png").read_bytes()).hexdigest(),
        )

        for name, expected in self.manifest["cases"].items():
            document = self.documents[name]
            self.assertEqual(expected["document_sha256"], _canonical_digest(document), name)
            payload, warnings, size = _render(document, self.font_manager)
            expected_hashes = expected.get("png_sha256_by_platform", {})
            if expected_hashes:
                platform_key = _platform_hash_key()
                self.assertIn(platform_key, expected_hashes, name)
                expected_hash = expected_hashes[platform_key]
            else:
                expected_hash = expected["png_sha256"]
            self.assertEqual(expected_hash, hashlib.sha256(payload).hexdigest(), name)
            self.assertEqual(tuple(expected["size"]), size, name)
            self.assertEqual(expected["warnings"], warnings, name)

    def test_platform_aliases_select_persisted_hashes(self):
        with patch.object(platform, "system", return_value="Linux"), patch.object(
            platform, "machine", return_value="AMD64"
        ):
            self.assertEqual(_platform_hash_key(), "linux-x86_64")
        with patch.object(platform, "system", return_value="Linux"), patch.object(
            platform, "machine", return_value="aarch64"
        ):
            self.assertEqual(_platform_hash_key(), "linux-aarch64")
        with patch.object(platform, "system", return_value="Darwin"), patch.object(
            platform, "machine", return_value="arm64"
        ):
            self.assertEqual(_platform_hash_key(), "darwin-arm64")

    def test_fit_modes_have_distinct_rendered_provenance(self):
        payloads = {
            name: _render(self.documents[name], self.font_manager)[0]
            for name in ("contain", "cover", "fill")
        }
        self.assertEqual(len({hashlib.sha256(payload).digest() for payload in payloads.values()}), 3)
        contain_bbox = _ink_bbox(payloads["contain"])
        cover_bbox = _ink_bbox(payloads["cover"])
        fill_bbox = _ink_bbox(payloads["fill"])
        self.assertIsNotNone(contain_bbox)
        self.assertIsNotNone(cover_bbox)
        self.assertIsNotNone(fill_bbox)
        self.assertLess(contain_bbox[2] - contain_bbox[0], cover_bbox[2] - cover_bbox[0])
        self.assertLess(contain_bbox[2] - contain_bbox[0], fill_bbox[2] - fill_bbox[0])
        self.assertEqual(cover_bbox[3] - cover_bbox[1], 16)

    def test_rotation_changes_rendered_bounds_without_changing_canvas(self):
        rotated_payload, warnings, size = _render(self.documents["rotation"], self.font_manager)
        self.assertEqual(warnings, [])
        self.assertEqual(size, (40, 40))
        rotated_bbox = _ink_bbox(rotated_payload)
        self.assertIsNotNone(rotated_bbox)

        unrotated = deepcopy(self.documents["rotation"])
        unrotated["elements"][0]["rotation"] = 0
        unrotated_payload, warnings, _ = _render(unrotated, self.font_manager)
        self.assertEqual(warnings, [])
        unrotated_bbox = _ink_bbox(unrotated_payload)
        self.assertIsNotNone(unrotated_bbox)
        self.assertGreater(rotated_bbox[3] - rotated_bbox[1], unrotated_bbox[3] - unrotated_bbox[1])
        self.assertGreater(unrotated_bbox[2] - unrotated_bbox[0], rotated_bbox[2] - rotated_bbox[0])

    def test_right_alignment_and_negative_spacing_reach_renderer(self):
        document = self.documents["right_negative_spacing"]
        converted, warnings = convert_chameleon_to_crello(
            document,
            self.font_manager,
            str(ASSETS),
        )
        self.assertEqual(warnings, [])
        self.assertEqual(converted["text_align"], ["right"])
        self.assertEqual(converted["letter_spacing"], [-1.0])

        right_payload, warnings, _ = _render(document, self.font_manager)
        self.assertEqual(warnings, [])
        left_document = deepcopy(document)
        left_document["elements"][0]["text_align"] = "left"
        left_payload, warnings, _ = _render(left_document, self.font_manager)
        self.assertEqual(warnings, [])
        right_bbox = _ink_bbox(right_payload)
        left_bbox = _ink_bbox(left_payload)
        self.assertIsNotNone(right_bbox)
        self.assertIsNotNone(left_bbox)
        self.assertGreater(right_bbox[0], left_bbox[0])

    def test_missing_asset_warning_is_diagnostic_not_replacement(self):
        document = self.documents["missing_asset"]
        _converted, warnings = convert_chameleon_to_crello(
            document,
            self.font_manager,
            str(ASSETS),
        )
        self.assertEqual(
            warnings,
            ["Missing asset 'missing-provenance.png' for element 'missing' - rendered a placeholder."],
        )
        self.assertEqual(document["elements"][0]["asset_id"], "missing-provenance.png")
        payload, render_warnings, size = _render(document, self.font_manager)
        self.assertEqual(render_warnings, warnings)
        self.assertEqual(size, (40, 30))
        self.assertTrue(payload)


if __name__ == "__main__":
    unittest.main()
