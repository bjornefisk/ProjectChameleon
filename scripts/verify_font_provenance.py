#!/usr/bin/env python3
"""Verify packaged font and license files against the release manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "Docs" / "font_provenance_manifest.json"
_FONT_EXTENSIONS = {".ttf", ".otf"}
_LICENSE_PATTERN = "OFL-*.txt"
_SHA256_LENGTH = 64


def _resolve_manifest_path(root: Path, raw_path: Any) -> Path | None:
    if not isinstance(raw_path, str):
        return None
    relative = Path(raw_path)
    if relative.is_absolute() or ".." in relative.parts:
        return None
    resolved_root = root.resolve()
    resolved = (resolved_root / relative).resolve()
    try:
        resolved.relative_to(resolved_root)
    except ValueError:
        return None
    return resolved


def _valid_hash(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == _SHA256_LENGTH
        and all(character in "0123456789abcdef" for character in value)
    )


def _file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _check_inventory(
    root: Path,
    fonts_directory: Path,
    entries: Any,
    actual_paths: set[Path],
    label: str,
) -> list[str]:
    errors: list[str] = []
    expected_paths: set[Path] = set()
    if not isinstance(entries, list):
        return [f"manifest field {label!r} must be a list"]

    for entry in entries:
        if not isinstance(entry, dict):
            errors.append(f"manifest {label} entry must be an object")
            continue
        path = _resolve_manifest_path(root, entry.get("path"))
        relative_path = entry.get("path")
        if path is None:
            errors.append(f"manifest {label} entry has an invalid path: {relative_path!r}")
            continue
        if path.parent != fonts_directory:
            errors.append(f"manifest {label} path is outside the font directory: {relative_path}")
        if path in expected_paths:
            errors.append(f"manifest {label} contains duplicate path: {relative_path}")
            continue
        expected_paths.add(path)
        expected_hash = entry.get("sha256")
        if not _valid_hash(expected_hash):
            errors.append(f"manifest {label} has an invalid SHA-256: {relative_path}")
            continue
        if not path.is_file():
            errors.append(f"missing file: {relative_path}")
            continue
        actual_hash = _file_hash(path)
        if actual_hash != expected_hash:
            errors.append(
                f"hash mismatch: {relative_path} expected {expected_hash} got {actual_hash}"
            )

    for path in sorted(actual_paths - expected_paths):
        errors.append(f"unexpected {label[:-1]} file: {path.relative_to(root)}")
    return errors


def verify_manifest(root: Path = ROOT, manifest_path: Path = DEFAULT_MANIFEST) -> list[str]:
    """Return all packaged-font manifest violations without changing repository files."""
    root = root.resolve()
    manifest_path = manifest_path.resolve()
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        return [f"cannot read font provenance manifest: {error}"]
    if not isinstance(data, dict):
        return ["font provenance manifest must contain an object"]
    if data.get("manifest_version") != 1:
        return ["font provenance manifest must use manifest_version 1"]

    fonts_directory = _resolve_manifest_path(root, data.get("font_directory"))
    if fonts_directory is None:
        return ["manifest font_directory is invalid"]
    if not fonts_directory.is_dir():
        return [f"missing font directory: {data.get('font_directory')}"]

    actual_fonts = {
        path for path in fonts_directory.iterdir() if path.is_file() and path.suffix.lower() in _FONT_EXTENSIONS
    }
    actual_licenses = {
        path for path in fonts_directory.glob(_LICENSE_PATTERN) if path.is_file()
    }
    errors = _check_inventory(root, fonts_directory, data.get("fonts"), actual_fonts, "fonts")
    errors.extend(
        _check_inventory(root, fonts_directory, data.get("licenses"), actual_licenses, "licenses")
    )
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    args = parser.parse_args()
    root = args.root.resolve()
    manifest = args.manifest if args.manifest.is_absolute() else root / args.manifest
    errors = verify_manifest(root, manifest)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(f"Font provenance manifest verified: {manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
