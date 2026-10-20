"""End-to-end artifact gates at publication and candidate boundaries."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from .support import (
    BRAND_ASSETS,
    BRAND_FONTS,
    design_of,
    render_to_png,
    shape_element,
    text_element,
)

try:
    from engine.errors import InfeasibleLayoutError, InfeasibleReasonCode
    from engine import staging
    from engine.layout import near_isomorphic
except ModuleNotFoundError:
    from chameleon.engine.errors import InfeasibleLayoutError, InfeasibleReasonCode
    from chameleon.engine import staging
    from chameleon.engine.layout import near_isomorphic


class ArtifactBoundaryTests(unittest.TestCase):
    def test_publication_rejects_readable_semantically_wrong_png(self):
        source = design_of(24, 18, shape_element("box", 4, 3, 10, 8))
        target = dict(source["canvas"])

        def white_renderer(_design, _assets_dir, png_path):
            Image.new("RGBA", (24, 18), (255, 255, 255, 255)).save(
                png_path, format="PNG"
            )
            return []

        with tempfile.TemporaryDirectory() as directory:
            output_dir = Path(directory)
            with self.assertRaises(InfeasibleLayoutError) as raised:
                staging.publish_task(
                    output_dir=output_dir,
                    task_name="wrong_pixels",
                    source=source,
                    target_canvas=target,
                    response=source,
                    assets_dir=BRAND_ASSETS,
                    render_to_png=white_renderer,
                )

            error = raised.exception
            self.assertEqual(
                error.reason_code, InfeasibleReasonCode.RUNTIME_IO_FAILURE
            )
            self.assertEqual(error.details["artifact_check"], "shape_pixels")
            self.assertEqual(list(output_dir.iterdir()), [])

    def test_publication_rejects_readable_blank_text_png(self):
        source = design_of(
            160,
            80,
            text_element("label", 20, 15, 120, 45, content="Hello"),
        )
        target = dict(source["canvas"])

        def white_renderer(_design, _assets_dir, png_path):
            Image.new("RGBA", (160, 80), (255, 255, 255, 255)).save(
                png_path, format="PNG"
            )
            return []

        with tempfile.TemporaryDirectory() as directory:
            output_dir = Path(directory)
            with self.assertRaises(InfeasibleLayoutError) as raised:
                staging.publish_task(
                    output_dir=output_dir,
                    task_name="wrong_text_pixels",
                    source=source,
                    target_canvas=target,
                    response=source,
                    assets_dir=BRAND_ASSETS,
                    render_to_png=white_renderer,
                )

            error = raised.exception
            self.assertEqual(error.details["artifact_check"], "render_pixels")
            self.assertEqual(list(output_dir.iterdir()), [])

    def test_publication_commits_real_renderer_artifact(self):
        source = design_of(24, 18, shape_element("box", 4, 3, 10, 8))
        target = dict(source["canvas"])

        with tempfile.TemporaryDirectory() as directory:
            output_dir = Path(directory)
            paths = staging.publish_task(
                output_dir=output_dir,
                task_name="real_render",
                source=source,
                target_canvas=target,
                response=source,
                assets_dir=BRAND_ASSETS,
                render_to_png=render_to_png,
            )

            self.assertTrue(paths.json_final.is_file())
            self.assertTrue(paths.png_final.is_file())
            self.assertTrue(paths.commit_marker.is_file())

    def test_candidate_gate_rejects_readable_semantically_wrong_png(self):
        source = design_of(24, 18, shape_element("box", 4, 3, 10, 8))
        target = dict(source["canvas"])

        def white_renderer(design, _assets_dir, png_path, **_kwargs):
            Image.new(
                "RGBA",
                (design["canvas"]["width"], design["canvas"]["height"]),
                (255, 255, 255, 255),
            ).save(png_path, format="PNG")
            return []

        fake_components = (None, None, white_renderer, RuntimeError)
        with patch.object(
            near_isomorphic, "_renderer_components", return_value=fake_components
        ):
            with self.assertRaises(InfeasibleLayoutError) as raised:
                near_isomorphic.solve_near_isomorphic(
                    source,
                    target,
                    assets_dir=str(BRAND_ASSETS),
                    fonts_dir=str(BRAND_FONTS),
                )

        error = raised.exception
        self.assertEqual(error.reason_code, InfeasibleReasonCode.RUNTIME_IO_FAILURE)
        self.assertEqual(error.details["artifact_check"], "shape_pixels")


if __name__ == "__main__":
    unittest.main()
