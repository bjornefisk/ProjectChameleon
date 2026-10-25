"""Regression tests for dependency input preparation."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import prepare_dependency_inputs


class PrepareDependencyInputsTests(unittest.TestCase):
    def test_local_install_preserves_venv_python_symlink(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            python_path = Path(temporary_directory) / "venv" / "bin" / "python"
            python_path.parent.mkdir(parents=True)
            python_path.symlink_to(sys.executable)

            with (
                patch.object(
                    sys,
                    "argv",
                    [
                        str(prepare_dependency_inputs.__file__),
                        "--install-local-renderer",
                        "--python",
                        str(python_path),
                    ],
                ),
                patch.object(prepare_dependency_inputs, "install_local_renderer") as install,
            ):
                self.assertEqual(prepare_dependency_inputs.main(), 0)

            install.assert_called_once_with(python_path)


if __name__ == "__main__":
    unittest.main()
