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
from decimal import Decimal
from pathlib import Path

from PIL import Image

from engine.contract import validate_response, validate_source
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
    """Raised when JSON contains a non-standard or non-finite number."""


def _reject_json_constant(value: str) -> None:
    raise _MalformedInputError(f"non-finite JSON constant {value!r} is not allowed")


def _load_task(task_path: Path) -> dict:
    """Decode a task without converting decimal JSON tokens to binary floats."""
    return json.loads(
        task_path.read_text(encoding="utf-8"),
        parse_int=int,
        parse_float=Decimal,
        parse_constant=_reject_json_constant,
    )


def _serialize_json(value: object) -> str:
    """Serialize JSON while preserving Decimal tokens without binary floats."""
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise _MalformedInputError("non-finite Decimal cannot be serialized")
        return str(value)
    if isinstance(value, float):
        try:
            return json.dumps(value, allow_nan=False)
        except ValueError as error:
            raise _MalformedInputError("non-finite float cannot be serialized") from error
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    if isinstance(value, dict):
        fields = [
            f"{_serialize_json(str(key))}:{_serialize_json(child)}"
            for key, child in value.items()
        ]
        return "{" + ",".join(fields) + "}"
    if isinstance(value, (list, tuple)):
        return "[" + ",".join(_serialize_json(child) for child in value) + "]"
    raise TypeError(f"value of type {type(value).__name__} is not JSON serializable")


def _serialized_output(
    source: dict, target_canvas: dict, output: dict
) -> tuple[str, dict]:
    """Return JSON text and validate the exact values that will be rendered."""
    serialized = _serialize_json(output)
    wire_output = json.loads(
        serialized,
        parse_int=int,
        parse_float=Decimal,
        parse_constant=_reject_json_constant,
    )
    validate_response(source, target_canvas, wire_output)
    return serialized, wire_output


def _validate_staged_png(png_path: Path) -> None:
    """Require a decodable PNG before it becomes a committed artifact."""
    if not png_path.is_file():
        raise OSError("renderer did not write staged PNG")
    try:
        with Image.open(png_path) as image:
            if image.format != "PNG":
                raise OSError(f"renderer wrote {image.format or 'unknown'} instead of PNG")
            image.verify()
        with Image.open(png_path) as image:
            image.load()
    except Exception as error:
        raise OSError(f"staged PNG is not a valid decodable PNG: {error}") from error


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


def _publish_pair(
    source: dict, target_canvas: dict, output: dict, stem: str
) -> None:
    """Stage and validate a logical JSON/PNG pair before committing it."""
    json_path, png_path, json_tmp, png_tmp, commit_path = _task_paths(stem)
    commit_tmp = commit_path.with_suffix(".commit.tmp")
    try:
        _cleanup_task_paths(stem)
        serialized, serialized_output = _serialized_output(
            source, target_canvas, output
        )
        json_tmp.write_text(serialized, encoding="utf-8")
        render_to_png(serialized_output, ASSETS_DIR, png_tmp)
        _validate_staged_png(png_tmp)
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
    except BaseException:
        try:
            _cleanup_task_paths(stem)
        except Exception:
            pass
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
        try:
            _cleanup_task_paths(stem)
            task = _load_task(task_path)
            source, target_canvas = task["source"], task["target_canvas"]
            validate_source(source)

            t0 = time.monotonic()
            output = resize(source, target_canvas)
            elapsed = time.monotonic() - t0
            problems = self_check(source, output)
            _publish_pair(source, target_canvas, output, stem)
        except Exception as error:
            exit_code = 1
            cleanup_error = None
            try:
                _cleanup_task_paths(stem)
            except Exception as cleanup_exception:
                cleanup_error = cleanup_exception
            if cleanup_error is not None:
                print(
                    f"[{task_path.name}] {InfeasibleReasonCode.RUNTIME_IO_FAILURE.value}: "
                    f"{error}; cleanup failed: {cleanup_error}",
                    file=sys.stderr,
                )
            else:
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
