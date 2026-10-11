"""
Orchestrator for batch execution.

The development self-check remains warning-only and is not the semantic
contract validator. Task JSON and PNG files are staged privately and published
only after both the resize and render paths succeed.
"""

import json
import os
import sys
import time
from pathlib import Path

from engine.errors import InfeasibleLayoutError, InfeasibleReasonCode
from engine.resize import resize

try:
    from renderer.converter.wrap import TextLayoutError as _TextLayoutError
except ImportError:
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
    """Render with the integrated adapter, using the dev fallback only if it is unavailable."""
    try:
        from renderer.converter.convert import render_design_to_png  # type: ignore
    except ImportError:
        _fallback_render(design, png_path)
        return
    render_design_to_png(design, assets_dir, str(png_path))


def _fallback_render(design: dict, png_path: Path) -> None:
    """Development-only labeled-box preview."""
    from PIL import Image, ImageDraw

    w, h = design["canvas"]["width"], design["canvas"]["height"]
    img = Image.new("RGB", (w, h), "#EDE7DD")
    draw = ImageDraw.Draw(img)
    palette = {"text": "#2B6CB0", "image": "#B7791F", "shape": "#2F855A"}
    for el in sorted(design["elements"], key=lambda e: e.get("z_index", 0)):
        x0, y0 = el["x"], el["y"]
        x1, y1 = x0 + el["width"], y0 + el["height"]
        color = palette.get(el["type"], "#555555")
        draw.rectangle([x0, y0, x1, y1], outline=color, width=3)
        draw.text((x0 + 4, y0 + 4), el["id"], fill=color)
    img.save(png_path, format="PNG")


def _task_paths(stem: str) -> tuple[Path, Path, Path, Path]:
    return (
        OUTPUT_DIR / f"{stem}_output.json",
        OUTPUT_DIR / f"{stem}_output.png",
        OUTPUT_DIR / f"{stem}_output.json.tmp",
        OUTPUT_DIR / f"{stem}_output.png.tmp",
    )


def _cleanup_task_paths(stem: str) -> None:
    for path in _task_paths(stem):
        path.unlink(missing_ok=True)


def _publish_pair(output: dict, stem: str) -> None:
    """Stage both artifacts, then publish them as one task-level result."""
    json_path, png_path, json_tmp, png_tmp = _task_paths(stem)
    _cleanup_task_paths(stem)
    try:
        json_tmp.write_text(
            json.dumps(output, indent=2, allow_nan=False),
            encoding="utf-8",
        )
        render_to_png(output, ASSETS_DIR, png_tmp)
        os.replace(json_tmp, json_path)
        os.replace(png_tmp, png_path)
    except Exception:
        _cleanup_task_paths(stem)
        raise


def _failure_code(error: Exception) -> InfeasibleReasonCode:
    if isinstance(error, InfeasibleLayoutError):
        return error.reason_code
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
