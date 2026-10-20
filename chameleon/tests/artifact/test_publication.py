from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

try:
    from engine import staging
    from engine.errors import InfeasibleLayoutError, InfeasibleReasonCode
    from tests.artifact.support import shape_design, shape_render, save_png
except ModuleNotFoundError:
    from chameleon.engine import staging
    from chameleon.engine.errors import InfeasibleLayoutError, InfeasibleReasonCode
    from chameleon.tests.artifact.support import shape_design, shape_render, save_png


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


if __name__ == "__main__":
    unittest.main()
