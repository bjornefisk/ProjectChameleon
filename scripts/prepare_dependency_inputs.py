#!/usr/bin/env python3
"""Prepare the hash-verified linux/amd64 wheelhouse or a local dev install."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CHAMELEON = ROOT / "chameleon"
WHEELHOUSE = CHAMELEON / ".wheelhouse"
DOCKERFILE = CHAMELEON / "Dockerfile"
REQUIREMENTS_LOCK = CHAMELEON / "requirements.lock"
BUILD_LOCK = CHAMELEON / "renderer-build.lock"
RENDERER_MANIFEST = CHAMELEON / "renderer-artifact.json"
DOCKERFILE_BASE = re.compile(r"^ARG PYTHON_BASE=(\S+)$", re.MULTILINE)
CHUNK_SIZE = 1024 * 1024


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(CHUNK_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_inputs() -> tuple[str, dict[str, Any]]:
    dockerfile = DOCKERFILE.read_text(encoding="utf-8")
    base_match = DOCKERFILE_BASE.search(dockerfile)
    if base_match is None:
        raise ValueError("Dockerfile must declare one pinned ARG PYTHON_BASE")
    base_image = base_match.group(1)
    renderer = json.loads(RENDERER_MANIFEST.read_text(encoding="utf-8"))
    if renderer["build"]["base_image"] != base_image:
        raise ValueError("Dockerfile base image differs from renderer-artifact.json")
    return base_image, renderer


def input_digests() -> dict[str, str]:
    return {
        "requirements.lock": sha256(REQUIREMENTS_LOCK),
        "renderer-build.lock": sha256(BUILD_LOCK),
        "renderer-artifact.json": sha256(RENDERER_MANIFEST),
    }


def wheel_records(directory: Path) -> list[dict[str, Any]]:
    return [
        {"filename": path.name, "sha256": sha256(path), "size_bytes": path.stat().st_size}
        for path in sorted(directory.glob("*.whl"))
    ]


def verify_wheelhouse(directory: Path) -> dict[str, Any]:
    """Reject stale, incomplete, modified, or unexpected generated wheelhouses."""
    manifest_path = directory / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    base_image, renderer = read_inputs()
    expected = {
        "format": 1,
        "target": "linux/amd64",
        "python": renderer["build"]["python"],
        "base_image": base_image,
        "inputs": input_digests(),
    }
    for key, value in expected.items():
        if manifest.get(key) != value:
            raise ValueError(f"wheelhouse manifest {key} does not match current inputs")

    declared = manifest.get("wheels")
    if not isinstance(declared, list) or not declared:
        raise ValueError("wheelhouse manifest contains no wheels")
    actual = wheel_records(directory)
    if actual != declared:
        raise ValueError("wheelhouse files differ from their recorded names, sizes, or hashes")
    files = {path.name for path in directory.iterdir()}
    expected_files = {"manifest.json", *(record["filename"] for record in declared)}
    if files != expected_files:
        raise ValueError("wheelhouse contains missing or unexpected files")
    renderer_wheel = renderer["wheel"]
    if not any(
        record["filename"] == renderer_wheel["filename"]
        and record["sha256"] == renderer_wheel["sha256"]
        and record["size_bytes"] == renderer_wheel["size_bytes"]
        for record in declared
    ):
        raise ValueError("wheelhouse renderer wheel differs from renderer-artifact.json")
    return manifest


def download_verified_renderer(destination: Path, renderer: dict[str, Any]) -> None:
    source = renderer["source"]
    request = urllib.request.Request(
        source["archive_url"], headers={"User-Agent": "ProjectChameleon-dependency-prep"}
    )
    digest = hashlib.sha256()
    with urllib.request.urlopen(request, timeout=60) as response, destination.open("wb") as target:
        while chunk := response.read(CHUNK_SIZE):
            target.write(chunk)
            digest.update(chunk)
    actual = digest.hexdigest()
    if actual != source["archive_sha256"]:
        raise ValueError(
            f"renderer source archive hash mismatch: expected {source['archive_sha256']}, got {actual}"
        )
    if destination.stat().st_size != source["archive_size_bytes"]:
        raise ValueError("renderer source archive size differs from renderer-artifact.json")


def pinned_base_command(source_archive: Path, destination: Path, base_image: str) -> None:
    destination.mkdir()
    script = """set -eu
python -c 'import sys; sys.version_info[:3] == (3, 11, 11) or sys.exit(sys.version)'
python -m pip download --disable-pip-version-check --no-cache-dir \\
  --require-hashes --only-binary=:all: --dest /wheelhouse \\
  -r /inputs/requirements.lock -r /inputs/renderer-build.lock
python -m pip install --disable-pip-version-check --no-cache-dir --no-index \\
  --find-links=/wheelhouse --require-hashes --only-binary=:all: \\
  -r /inputs/renderer-build.lock
mkdir -p /tmp/renderer-src
tar -xzf /tmp/renderer.tar.gz --strip-components=1 -C /tmp/renderer-src
SOURCE_DATE_EPOCH="$SOURCE_DATE_EPOCH" python -m pip wheel --disable-pip-version-check \\
  --no-deps --no-build-isolation --no-cache-dir --no-index \\
  --wheel-dir=/wheelhouse /tmp/renderer-src
"""
    subprocess.run(
        [
            "docker",
            "run",
            "--rm",
            "--platform",
            "linux/amd64",
            "-e",
            f"SOURCE_DATE_EPOCH={json.loads(RENDERER_MANIFEST.read_text(encoding='utf-8'))['build']['source_date_epoch']}",
            "--mount",
            f"type=bind,source={CHAMELEON},target=/inputs,readonly",
            "--mount",
            f"type=bind,source={source_archive},target=/tmp/renderer.tar.gz,readonly",
            "--mount",
            f"type=bind,source={destination},target=/wheelhouse",
            "--entrypoint",
            "sh",
            base_image,
            "-c",
            script,
        ],
        check=True,
    )


def prepare_wheelhouse() -> None:
    base_image, renderer = read_inputs()
    if WHEELHOUSE.exists():
        verify_wheelhouse(WHEELHOUSE)
        print(f"Verified existing wheelhouse: {WHEELHOUSE}")
        return

    scratch = Path(tempfile.mkdtemp(prefix=".wheelhouse.tmp-", dir=CHAMELEON))
    try:
        source_archive = scratch / "renderer.tar.gz"
        download_verified_renderer(source_archive, renderer)
        wheel_directory = scratch / "wheels"
        pinned_base_command(source_archive, wheel_directory, base_image)
        records = wheel_records(wheel_directory)
        expected_renderer = renderer["wheel"]
        if not any(
            record["filename"] == expected_renderer["filename"]
            and record["sha256"] == expected_renderer["sha256"]
            and record["size_bytes"] == expected_renderer["size_bytes"]
            for record in records
        ):
            raise ValueError("reproducible renderer wheel differs from renderer-artifact.json")
        manifest = {
            "format": 1,
            "target": "linux/amd64",
            "python": renderer["build"]["python"],
            "base_image": base_image,
            "inputs": input_digests(),
            "wheels": records,
        }
        (wheel_directory / "manifest.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        verify_wheelhouse(wheel_directory)
        os.replace(wheel_directory, WHEELHOUSE)
        print(f"Prepared and verified {len(records)} wheels in {WHEELHOUSE}")
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def install_local_renderer(target_python: Path) -> None:
    base_image, renderer = read_inputs()
    subprocess.run(
        [
            str(target_python),
            "-m",
            "pip",
            "install",
            "--disable-pip-version-check",
            "--no-cache-dir",
            "--require-hashes",
            "--only-binary=:all:",
            "-r",
            str(REQUIREMENTS_LOCK),
        ],
        check=True,
    )
    scratch = Path(tempfile.mkdtemp(prefix="chameleon-renderer-build-"))
    try:
        source_archive = scratch / "renderer.tar.gz"
        download_verified_renderer(source_archive, renderer)
        build_environment = scratch / "build-env"
        subprocess.run([str(target_python), "-m", "venv", str(build_environment)], check=True)
        build_python = build_environment / "bin" / "python"
        subprocess.run(
            [
                str(build_python),
                "-m",
                "pip",
                "install",
                "--disable-pip-version-check",
                "--no-cache-dir",
                "--require-hashes",
                "--only-binary=:all:",
                "-r",
                str(BUILD_LOCK),
            ],
            check=True,
        )
        source_directory = scratch / "renderer-src"
        source_directory.mkdir()
        subprocess.run(
            ["tar", "-xzf", str(source_archive), "--strip-components=1", "-C", str(source_directory)],
            check=True,
        )
        wheel_directory = scratch / "wheels"
        wheel_directory.mkdir()
        environment = os.environ.copy()
        environment["SOURCE_DATE_EPOCH"] = str(renderer["build"]["source_date_epoch"])
        subprocess.run(
            [
                str(build_python),
                "-m",
                "pip",
                "wheel",
                "--disable-pip-version-check",
                "--no-deps",
                "--no-build-isolation",
                "--no-cache-dir",
                "--no-index",
                f"--wheel-dir={wheel_directory}",
                str(source_directory),
            ],
            check=True,
            env=environment,
        )
        expected = renderer["wheel"]
        wheel = wheel_directory / expected["filename"]
        if not wheel.is_file() or sha256(wheel) != expected["sha256"]:
            raise ValueError("local renderer build differs from renderer-artifact.json")
        if wheel.stat().st_size != expected["size_bytes"]:
            raise ValueError("local renderer wheel size differs from renderer-artifact.json")
        subprocess.run(
            [
                str(target_python),
                "-m",
                "pip",
                "install",
                "--disable-pip-version-check",
                "--no-cache-dir",
                "--no-index",
                "--no-deps",
                str(wheel),
            ],
            check=True,
        )
        verify_installed_renderer(target_python, expected["sha256"])
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def verify_installed_renderer(target_python: Path, expected_sha256: str) -> None:
    check = (
        "import json; from importlib.metadata import distribution; "
        "data=json.loads(distribution('cr-renderer').read_text('direct_url.json')); "
        "archive=data.get('archive_info', {}); "
        "actual=archive.get('hashes', {}).get('sha256') or "
        "archive.get('hash', '').removeprefix('sha256='); "
        "actual == __import__('sys').argv[1] or "
        "__import__('sys').exit(f'renderer direct_url hash mismatch: {actual!r}')"
    )
    subprocess.run([str(target_python), "-c", check, expected_sha256], check=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_mutually_exclusive_group(required=True)
    actions.add_argument("--prepare-wheelhouse", action="store_true")
    actions.add_argument("--install-local-renderer", action="store_true")
    parser.add_argument("--python", type=Path, default=Path(sys.executable))
    arguments = parser.parse_args()
    try:
        if arguments.prepare_wheelhouse:
            prepare_wheelhouse()
        else:
            install_local_renderer(arguments.python)
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        print(f"dependency preparation failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
