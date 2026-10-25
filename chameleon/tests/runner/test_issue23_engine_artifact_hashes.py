"""Persisted engine-level artifact evidence for issue #23 (F-07).

``test_issue23_artifact_corpus.py`` pins renderer-only documents.  This module
pins what the runner actually publishes: it runs ``python -m engine.main`` in
fresh interpreter processes, with different ``PYTHONHASHSEED`` values, over the
shipped Level 1 and Level 2 sample tasks and then checks the *published* files:

* the committed JSON/PNG pair is hard-valid under the independent contract
  validator, the PNG has the target canvas size, and no stray files remain;
* the published bytes do not depend on the process hash seed; and
* on every platform with persisted evidence, the JSON and PNG SHA-256 values
  equal the pins in ``fixtures/engine_artifact_hashes.json``, which are bound to
  task, schema, asset, font, renderer, Python 3.11, and direct dependency provenance.

Observed platform behavior (see the evidence record for the commands):

* the layout JSON depends on the operating system's Skia text backend: glyph
  advances are hinted integers on Linux and fractional on macOS, which moves the
  largest fitting font size in the Level 2 headline/subhead; and
* PNG bytes depend on the operating system and the CPU architecture.

Pins are keyed by ``<system>-<machine>`` and bind Python minor version 3.11.
A platform without pins skips only the pin comparison; the hard-validity and
determinism checks still run.

To refresh pins after an *intentional* behavior change, run the runner on each
recorded platform, copy the observed values from the failure message, and
explain every changed hash in the pull request.  Never refresh to silence an
unexplained difference.
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from decimal import Decimal
from importlib.metadata import distribution, version
from pathlib import Path

from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from engine.contract import validate_response
except ModuleNotFoundError:
    from chameleon.engine.contract import validate_response

CHAMELEON = PROJECT_ROOT / "chameleon"
FIXTURE = CHAMELEON / "tests" / "fixtures" / "engine_artifact_hashes.json"
INPUT_DIR = CHAMELEON / "input"
ASSETS = CHAMELEON / "brand_kit" / "assets"
FONTS = CHAMELEON / "brand_kit" / "fonts"
SCHEMA = CHAMELEON / "chameleon_design_schema_v0.9.json"
RENDERER_ARTIFACT = CHAMELEON / "renderer-artifact.json"

STEMS = ("chameleon_sample_level1_warmup", "chameleon_sample_level2_core")
HASH_SEEDS = ("0", "4242")
OFFICIAL_PLATFORM = "linux-x86_64"
CANONICAL_PYTHON_MINOR = "3.11"
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _tree_digest(directory: Path, suffixes: set[str]) -> str:
    digest = hashlib.sha256()
    for path in sorted(
        path
        for path in directory.rglob("*")
        if path.is_file() and path.suffix.lower() in suffixes
    ):
        digest.update(path.relative_to(directory).as_posix().encode("utf-8"))
        digest.update(path.read_bytes())
    return digest.hexdigest()


def _platform_key() -> str:
    machine = platform.machine().strip().lower()
    machine = {"amd64": "x86_64", "x64": "x86_64"}.get(machine, machine)
    return f"{platform.system().strip().lower()}-{machine}"


def _load_exact(path: Path) -> dict:
    """Decode JSON the way the runner does: exact integers and Decimal tokens."""

    return json.loads(
        path.read_text(encoding="utf-8"), parse_int=int, parse_float=Decimal
    )


def _run_engine(parent: Path, seed: str) -> tuple[Path, subprocess.CompletedProcess]:
    """Run the real runner in a fresh process inside an isolated working tree."""

    workdir = parent / f"seed-{seed}"
    (workdir / "input").mkdir(parents=True)
    for stem in STEMS:
        shutil.copyfile(INPUT_DIR / f"{stem}.json", workdir / "input" / f"{stem}.json")
    # The runner resolves brand_kit/assets and brand_kit/fonts relative to its
    # working directory (/app in the official image), so mirror that layout.
    shutil.copytree(CHAMELEON / "brand_kit", workdir / "brand_kit")
    environment = dict(os.environ)
    environment.update(
        {
            "PYTHONHASHSEED": seed,
            "PYTHONPATH": str(CHAMELEON),
            "PYTHONDONTWRITEBYTECODE": "1",
        }
    )
    result = subprocess.run(
        [sys.executable, "-m", "engine.main"],
        cwd=workdir,
        env=environment,
        capture_output=True,
        text=True,
        timeout=600,
        check=False,
    )
    return workdir, result


class EngineArtifactEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        scratch = tempfile.TemporaryDirectory(prefix="chameleon-engine-evidence-")
        cls.addClassCleanup(scratch.cleanup)
        cls.runs = {seed: _run_engine(Path(scratch.name), seed) for seed in HASH_SEEDS}
        cls.manifest = json.loads(FIXTURE.read_text(encoding="utf-8"))

    def _output_dir(self, seed: str) -> Path:
        return self.runs[seed][0] / "output"

    def test_runner_succeeds_in_every_process_and_publishes_only_committed_pairs(self):
        expected_names = {
            name
            for stem in STEMS
            for name in (f"{stem}_output.json", f"{stem}_output.png", f".{stem}_output.commit")
        }
        for seed, (_, result) in self.runs.items():
            diagnostics = f"seed={seed}\nstdout={result.stdout}\nstderr={result.stderr}"
            self.assertEqual(result.returncode, 0, diagnostics)
            for stem in STEMS:
                self.assertIn(f"[{stem}.json] status=SUCCESS", result.stdout, diagnostics)
            self.assertEqual(
                expected_names,
                {path.name for path in self._output_dir(seed).iterdir()},
                f"stray or missing output artifacts for seed={seed}",
            )

    def test_published_pairs_are_hard_valid_canvas_sized_and_match_their_commit_markers(self):
        output = self._output_dir(HASH_SEEDS[0])
        for stem in STEMS:
            task = _load_exact(INPUT_DIR / f"{stem}.json")
            json_path = output / f"{stem}_output.json"
            png_path = output / f"{stem}_output.png"

            # Authoritative contract validator, re-run on the bytes that were
            # actually published rather than on the engine's in-memory result.
            validate_response(task["source"], task["target_canvas"], _load_exact(json_path))

            with Image.open(png_path) as image:
                image.load()
                self.assertEqual(image.format, "PNG", stem)
                self.assertEqual(
                    image.size,
                    (task["target_canvas"]["width"], task["target_canvas"]["height"]),
                    stem,
                )

            marker = json.loads((output / f".{stem}_output.commit").read_text(encoding="utf-8"))
            self.assertIs(marker["committed"], True, stem)
            self.assertEqual(marker["json_sha256"], _sha256(json_path), stem)
            self.assertEqual(marker["png_sha256"], _sha256(png_path), stem)

    def test_published_bytes_are_identical_across_processes_and_hash_seeds(self):
        first, second = (self._output_dir(seed) for seed in HASH_SEEDS)
        names = sorted(path.name for path in first.iterdir())
        self.assertEqual(names, sorted(path.name for path in second.iterdir()))
        for name in names:
            self.assertEqual(
                _sha256(first / name),
                _sha256(second / name),
                f"{name} differs between PYTHONHASHSEED={HASH_SEEDS[0]} and {HASH_SEEDS[1]}",
            )

    def test_persisted_pins_bind_current_task_schema_asset_font_and_dependency_inputs(self):
        bound = self.manifest["bound_inputs"]
        refresh = "inputs changed: refresh engine_artifact_hashes.json on every recorded platform"
        self.assertEqual(bound["python_minor_version"], CANONICAL_PYTHON_MINOR, refresh)
        self.assertEqual(
            f"{sys.version_info.major}.{sys.version_info.minor}",
            CANONICAL_PYTHON_MINOR,
            "engine PNG hashes are bound to the project's Python 3.11 baseline",
        )

        renderer = json.loads(RENDERER_ARTIFACT.read_text(encoding="utf-8"))
        direct_url = json.loads(distribution("cr-renderer").read_text("direct_url.json"))
        archive_info = direct_url.get("archive_info", {})
        installed_wheel_sha256 = archive_info.get("hashes", {}).get("sha256")
        if installed_wheel_sha256 is None:
            installed_wheel_sha256 = archive_info.get("hash", "").removeprefix("sha256=")
        self.assertEqual(bound["renderer_commit"], renderer["source"]["commit"], refresh)
        self.assertEqual(renderer["wheel"]["version"], version("cr-renderer"), refresh)
        self.assertEqual(renderer["wheel"]["sha256"], installed_wheel_sha256, refresh)
        for distribution_name, expected_version in bound["dependencies"].items():
            self.assertEqual(expected_version, version(distribution_name), distribution_name)

        self.assertEqual(bound["schema_sha256"], _sha256(SCHEMA), refresh)
        self.assertEqual(bound["asset_tree_sha256"], _tree_digest(ASSETS, {".png"}), refresh)
        self.assertEqual(
            bound["font_tree_sha256"], _tree_digest(FONTS, {".otf", ".ttf"}), refresh
        )
        self.assertEqual(sorted(bound["task_sha256"]), sorted(STEMS))
        for stem in STEMS:
            self.assertEqual(
                bound["task_sha256"][stem], _sha256(INPUT_DIR / f"{stem}.json"), f"{stem}: {refresh}"
            )

    def test_official_linux_amd64_pins_remain_persisted_for_every_sample(self):
        """Guard the evidence itself: pins cannot be dropped to dodge a mismatch."""

        pins = self.manifest["platforms"][OFFICIAL_PLATFORM]["artifacts"]
        self.assertEqual(sorted(pins), sorted(STEMS))
        for stem in STEMS:
            for kind in ("json_sha256", "png_sha256"):
                self.assertRegex(pins[stem][kind], SHA256_PATTERN, f"{stem}.{kind}")

    def test_artifact_hashes_match_the_persisted_pins_for_this_platform(self):
        self.assertEqual(
            f"{sys.version_info.major}.{sys.version_info.minor}",
            CANONICAL_PYTHON_MINOR,
            "engine PNG hashes are bound to the project's Python 3.11 baseline",
        )
        key = _platform_key()
        platforms = self.manifest["platforms"]
        if key not in platforms:
            self.skipTest(
                f"no persisted engine artifact pins for {key!r}; recorded platforms: "
                f"{sorted(platforms)}. Hard-validity and determinism checks still ran."
            )
        pins = platforms[key]["artifacts"]
        self.assertEqual(sorted(pins), sorted(STEMS))
        output = self._output_dir(HASH_SEEDS[0])
        for stem in STEMS:
            observed = {
                "json_sha256": _sha256(output / f"{stem}_output.json"),
                "png_sha256": _sha256(output / f"{stem}_output.png"),
            }
            self.assertEqual(
                pins[stem],
                observed,
                f"{stem} on {key}: observed values above are what to persist if this "
                "change is intentional and explained",
            )


if __name__ == "__main__":
    unittest.main()
