from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

try:
    from engine import staging
    from engine.errors import InfeasibleLayoutError, InfeasibleReasonCode
    from tests.artifact.support import (
        load_artifact_fixture,
        save_png,
        shape_design,
        shape_render,
        write_readable_blank_png,
    )
except ModuleNotFoundError:
    from chameleon.engine import staging
    from chameleon.engine.errors import InfeasibleLayoutError, InfeasibleReasonCode
    from chameleon.tests.artifact.support import (
        load_artifact_fixture,
        save_png,
        shape_design,
        shape_render,
        write_readable_blank_png,
    )


class PublicationArtifactTests(unittest.TestCase):
    def test_validate_png_runs_hard_artifact_gate(self):
        design = shape_design()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "render.png"
            save_png(shape_render(design), path)
            staging.validate_png(path, design=design, assets_dir=Path(directory))

    def test_validate_png_legacy_syntax_only_call_remains_supported(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "render.png"
            save_png(shape_render(shape_design()), path)
            staging.validate_png(path)

    def test_callback_runs_after_default_gate(self):
        design = shape_design()
        seen = []
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "render.png"
            save_png(shape_render(design), path)
            staging.validate_png(
                path,
                design=design,
                assets_dir=Path(directory),
                artifact_gate=lambda *_args: seen.append(True),
            )
        self.assertEqual(seen, [True])

    def test_artifact_mismatch_is_runtime_io_failure(self):
        design = shape_design()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "render.png"
            image = shape_render(design)
            image.putpixel((2, 2), (0, 0, 0, 255))
            save_png(image, path)
            with self.assertRaises(InfeasibleLayoutError) as context:
                staging.validate_png(path, design=design, assets_dir=Path(directory))
        self.assertEqual(context.exception.reason_code, InfeasibleReasonCode.RUNTIME_IO_FAILURE)

    def test_readable_wrong_fixture_is_rejected_at_validation_seam(self):
        design = load_artifact_fixture("shape.json")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "readable-but-wrong.png"
            write_readable_blank_png(design, path)
            with Image.open(path) as image:
                self.assertEqual(image.format, "PNG")
                image.verify()

            with self.assertRaises(InfeasibleLayoutError) as context:
                staging.validate_png(
                    path,
                    design=design,
                    assets_dir=Path(directory),
                )

        self.assertEqual(
            context.exception.reason_code,
            InfeasibleReasonCode.RUNTIME_IO_FAILURE,
        )
        self.assertEqual(context.exception.details["artifact_check"], "shape_pixels")

    def test_readable_wrong_fixture_is_not_published_as_a_pair(self):
        design = load_artifact_fixture("shape.json")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output_dir = root / "output"
            output_dir.mkdir()
            assets_dir = root / "assets"
            assets_dir.mkdir()

            def white_renderer(_design, _assets_dir, png_path):
                write_readable_blank_png(design, png_path)
                return []

            with self.assertRaises(InfeasibleLayoutError) as context:
                staging.publish_task(
                    output_dir=output_dir,
                    task_name="readable-wrong",
                    source=design,
                    target_canvas=dict(design["canvas"]),
                    response=design,
                    assets_dir=assets_dir,
                    render_to_png=white_renderer,
                )

            self.assertEqual(list(output_dir.iterdir()), [])

        self.assertEqual(
            context.exception.reason_code,
            InfeasibleReasonCode.RUNTIME_IO_FAILURE,
        )
        self.assertEqual(context.exception.details["artifact_check"], "shape_pixels")

    def test_readable_wrong_fixture_is_rejected_at_candidate_seam(self):
        design = load_artifact_fixture("shape.json")

        def white_renderer(_design, _assets_dir, png_path, **_kwargs):
            write_readable_blank_png(design, Path(png_path))
            return []

        from engine.layout import near_isomorphic

        with patch.object(
            near_isomorphic,
            "_renderer_components",
            return_value=(None, None, white_renderer, None),
        ):
            with self.assertRaises(InfeasibleLayoutError) as context:
                near_isomorphic._render_candidate(
                    design,
                    str(Path(__file__).resolve().parents[2] / "brand_kit" / "assets"),
                    None,
                    None,
                )

        self.assertEqual(
            context.exception.reason_code,
            InfeasibleReasonCode.RUNTIME_IO_FAILURE,
        )
        self.assertEqual(context.exception.details["artifact_check"], "shape_pixels")



if __name__ == "__main__":
    unittest.main()
