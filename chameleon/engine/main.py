"""
Orchestrator for batch execution.

The development self-check remains warning-only and is not the semantic
contract validator. Task JSON and PNG files are staged privately and published
only after both the resize and render paths succeed.
"""

import hashlib
import json
import os
import sys
import time
from pathlib import Path

from engine.errors import InfeasibleLayoutError, InfeasibleReasonCode
from engine.resize import resize

try:
    from renderer.converter.wrap import (  # type: ignore
        MalformedTextError as _MalformedTextError,
        TextLayoutError as _TextLayoutError,
    )
except ImportError:
    _MalformedTextError = None
    _TextLayoutError = None

# Relative to the current working directory, which is /app both inside the
# Docker image (WORKDIR /app) and when run locally from this repo's root.
INPUT_DIR = Path("input")
OUTPUT_DIR = Path("output")
ASSETS_DIR = Path("brand_kit/assets")

REQUIRED_COMMON = ["id", "type", "x", "y", "width", "height"]
REQUIRED_BY_TYPE = {
    "text": ["content", "font_family", "font_size", "color"],
    "image": ["asset_id"],
    "shape": ["shape_type", "fill_color"],
}


class _MalformedInputError(ValueError):
    """Raised when JSON contains a non-standard non-finite number token."""


def _reject_json_constant(value: str) -> None:
    raise _MalformedInputError(f"non-finite JSON constant {value!r} is not allowed")


def self_check(source: dict, output: dict) -> list[str]:
    """Run the non-authoritative development sanity check."""
    problems = []

    if "canvas" not in output or "elements" not in output:
        return ["output is missing top-level 'canvas' or 'elements'"]

    src_ids = {el["id"] for el in source["elements"]}
    out_ids = {el.get("id") for el in output["elements"]}
    if src_ids != out_ids:
        problems.append(
            f"element id mismatch — missing {sorted(src_ids - out_ids)}, "
            f"unexpected {sorted(out_ids - src_ids)}"
        )

    cw, ch = output["canvas"].get("width"), output["canvas"].get("height")
    for el in output["elements"]:
        for field in REQUIRED_COMMON:
            if field not in el:
                problems.append(f"element '{el.get('id')}': missing '{field}'")
                continue
        for field in REQUIRED_BY_TYPE.get(el.get("type"), []):
            if field not in el:
                problems.append(
                    f"element '{el.get('id')}' (type={el.get('type')}): missing '{field}'"
                )
        if cw and ch and all(k in el for k in ("x", "y", "width", "height")):
            x1, y1 = el["x"] + el["width"], el["y"] + el["height"]
            if el["x"] < -0.5 or el["y"] < -0.5 or x1 > cw + 0.5 or y1 > ch + 0.5:
                problems.append(f"element '{el.get('id')}' is off-canvas ({cw}x{ch})")

    return problems


def render_to_png(design: dict, assets_dir: Path, png_path: Path) -> None:
    """Render with the pinned local adapter."""
    from renderer.converter.convert import render_design_to_png  # type: ignore

    render_design_to_png(design, assets_dir, str(png_path))


def _task_paths(stem: str) -> tuple[Path, Path, Path, Path, Path]:
    return (
        OUTPUT_DIR / f"{stem}_output.json",
        OUTPUT_DIR / f"{stem}_output.png",
        OUTPUT_DIR / f"{stem}_output.json.tmp",
        OUTPUT_DIR / f"{stem}_output.png.tmp",
        OUTPUT_DIR / f".{stem}_output.commit",
    )


def _cleanup_task_paths(stem: str) -> None:
    paths = _task_paths(stem)
    for path in (*paths, paths[-1].with_suffix(".commit.tmp")):
        path.unlink(missing_ok=True)


def _publish_pair(output: dict, stem: str) -> None:
    """Stage artifacts, then publish a pair with an atomic commit marker."""
    json_path, png_path, json_tmp, png_tmp, commit_path = _task_paths(stem)
    _cleanup_task_paths(stem)
    commit_tmp = commit_path.with_suffix(".commit.tmp")
    try:
        json_tmp.write_text(
            json.dumps(output, indent=2, allow_nan=False),
            encoding="utf-8",
        )
        render_to_png(output, ASSETS_DIR, png_tmp)
        if not png_tmp.is_file():
            raise OSError("renderer did not write staged PNG")
        commit_tmp.write_text(
            json.dumps(
                {
                    "json": json_path.name,
                    "png": png_path.name,
                    "json_sha256": hashlib.sha256(json_tmp.read_bytes()).hexdigest(),
                    "png_sha256": hashlib.sha256(png_tmp.read_bytes()).hexdigest(),
                },
                sort_keys=True,
            ),
            encoding="utf-8",
        )
        os.replace(json_tmp, json_path)
        os.replace(png_tmp, png_path)
        os.replace(commit_tmp, commit_path)
    except Exception:
        _cleanup_task_paths(stem)
        raise


def _failure_code(error: Exception) -> InfeasibleReasonCode:
    if isinstance(error, InfeasibleLayoutError):
        return error.reason_code
    if _MalformedTextError is not None and isinstance(error, _MalformedTextError):
        return InfeasibleReasonCode.MALFORMED_INPUT
    if _TextLayoutError is not None and isinstance(error, _TextLayoutError):
        return InfeasibleReasonCode.TEXT_OVERFLOW
    if isinstance(error, (_MalformedInputError, json.JSONDecodeError, KeyError, TypeError)):
        return InfeasibleReasonCode.MALFORMED_INPUT
    return InfeasibleReasonCode.RUNTIME_IO_FAILURE


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    task_files = sorted(INPUT_DIR.glob("*.json"))
    if not task_files:
        print(f"No task files found in {INPUT_DIR}", file=sys.stderr)
        return 1

    exit_code = 0
    for task_path in task_files:
        stem = task_path.stem
        _cleanup_task_paths(stem)
        try:
            task = json.loads(
                task_path.read_text(encoding="utf-8"),
                parse_constant=_reject_json_constant,
            )
            source, target_canvas = task["source"], task["target_canvas"]

            t0 = time.monotonic()
            output = resize(source, target_canvas)
            elapsed = time.monotonic() - t0
            problems = self_check(source, output)
            _publish_pair(output, stem)
        except Exception as error:
            exit_code = 1
            _cleanup_task_paths(stem)
            code = _failure_code(error)
            print(
                f"[{task_path.name}] {code.value}: {error}",
                file=sys.stderr,
            )
            continue

        status = "OK" if not problems else f"{len(problems)} self-check warning(s)"
        print(
            f"[{task_path.name}] {status} in {elapsed:.2f}s "
            f"-> {stem}_output.json, {stem}_output.png"
        )
        for problem in problems:
            print(f"    - {problem}")

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
