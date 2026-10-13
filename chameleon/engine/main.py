"""Batch runner for independent fail-closed Stage 1 tasks."""

import json
import sys
import time
from decimal import Decimal
from pathlib import Path
from typing import Any, Mapping

from engine.contract import validate_source
from engine.errors import InfeasibleLayoutError
from engine.resize import resize
from engine.staging import cleanup_task_artifacts, publish_task

# Relative to the current working directory, which is /app inside Docker and
# the chameleon project directory for local execution.
INPUT_DIR = Path("input")
OUTPUT_DIR = Path("output")
ASSETS_DIR = Path("brand_kit/assets")

_MALFORMED_CODES = {"INVALID_SOURCE", "INVALID_TARGET", "MALFORMED_INPUT"}


def _reject_constant(value: str) -> None:
    raise ValueError(f"non-finite JSON constant is not allowed: {value}")


def _load_task(path: Path) -> Mapping[str, Any]:
    task = json.loads(
        path.read_text(encoding="utf-8"),
        parse_int=int,
        parse_float=Decimal,
        parse_constant=_reject_constant,
    )
    if not isinstance(task, Mapping):
        raise ValueError("task envelope must be a JSON object")
    if "source" not in task or "target_canvas" not in task:
        raise ValueError("task envelope requires source and target_canvas")
    source, target = task["source"], task["target_canvas"]
    if not isinstance(source, Mapping) or not isinstance(target, Mapping):
        raise ValueError("source and target_canvas must be JSON objects")
    validate_source(source)
    for field in ("width", "height"):
        value = target.get(field)
        if isinstance(value, bool) or not isinstance(value, (int, Decimal)):
            raise ValueError(f"target_canvas.{field} must be an integer")
        if isinstance(value, Decimal) and (
            not value.is_finite() or value != value.to_integral_value()
        ):
            raise ValueError(f"target_canvas.{field} must be an integer")
        if value <= 0:
            raise ValueError(f"target_canvas.{field} must be positive")
    return task


def _error_status(error: InfeasibleLayoutError) -> str:
    if error.code in _MALFORMED_CODES:
        return "MALFORMED_INPUT"
    if error.code == "INCOMPLETE_SEARCH":
        return "INCOMPLETE_SEARCH"
    if error.code == "RUNTIME_IO_FAILURE":
        return "RUNTIME_IO_FAILURE"
    return "INFEASIBLE_LAYOUT"

REQUIRED_COMMON = ["id", "type", "x", "y", "width", "height"]
REQUIRED_BY_TYPE = {
    "text": ["content", "font_family", "font_size", "color"],
    "image": ["asset_id"],
    "shape": ["shape_type", "fill_color"],
}


def self_check(source: dict, output: dict) -> list[str]:
    """Quick, non-authoritative sanity check so obvious mistakes are caught
    locally before you submit. This is NOT the official scorer — see
    RULES.md for what actually gates and grades your submission."""
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
                problems.append(f"element '{el.get('id')}' (type={el.get('type')}): missing '{field}'")
        if cw and ch and all(k in el for k in ("x", "y", "width", "height")):
            x1, y1 = el["x"] + el["width"], el["y"] + el["height"]
            if el["x"] < -0.5 or el["y"] < -0.5 or x1 > cw + 0.5 or y1 > ch + 0.5:
                problems.append(f"element '{el.get('id')}' is off-canvas ({cw}x{ch})")

    return problems


def render_to_png(design: dict, assets_dir: Path, png_path: Path) -> None:
    """Renders `design` to a PNG. Prefers the real renderer
    (transformer-convertor, wrapping cr-renderer) if it's vendored into
    ./renderer; falls back to a plain box-and-label preview otherwise so
    this repo is runnable before that's wired in. Swap the fallback out
    once ./renderer is populated — don't ship the fallback's output as a
    real preview."""
    try:
        from renderer.converter.convert import render_design_to_png  # type: ignore
        render_design_to_png(design, assets_dir, str(png_path))
        return
    except ImportError:
        pass

    _fallback_render(design, png_path)


def _fallback_render(design: dict, png_path: Path) -> None:
    """Placeholder only — labeled boxes, not real text/asset rendering.
    Confirms the pipeline runs end-to-end; do not use this to judge your
    actual layout quality. Use transformer-convertor (RULES.md / FAQ Q3)
    for a real preview."""
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


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    task_files = sorted(INPUT_DIR.glob("*.json"))
    if not task_files:
        print(f"No task files found in {INPUT_DIR}", file=sys.stderr)
        return 1

    all_succeeded = True
    for task_path in task_files:
        stem = task_path.stem
        try:
            cleanup_task_artifacts(OUTPUT_DIR, stem)
        except Exception as error:
            all_succeeded = False
            print(
                f"[{task_path.name}] status=RUNTIME_IO_FAILURE "
                f"reason=RUNTIME_IO_FAILURE: {error}",
                file=sys.stderr,
            )
            continue
        started = time.time()
        try:
            task = _load_task(task_path)
        except InfeasibleLayoutError as error:
            all_succeeded = False
            print(
                f"[{task_path.name}] status={_error_status(error)} "
                f"reason={error.code}: {error}",
                file=sys.stderr,
            )
            cleanup_task_artifacts(OUTPUT_DIR, stem)
            continue
        except Exception as error:
            all_succeeded = False
            print(
                f"[{task_path.name}] status=MALFORMED_INPUT "
                f"reason=MALFORMED_INPUT: {error}",
                file=sys.stderr,
            )
            cleanup_task_artifacts(OUTPUT_DIR, stem)
            continue

        try:
            source, target_canvas = task["source"], task["target_canvas"]
            output = resize(source, target_canvas)
            publish_task(
                output_dir=OUTPUT_DIR,
                task_name=stem,
                source=source,
                target_canvas=target_canvas,
                response=output,
                assets_dir=ASSETS_DIR,
                render_to_png=render_to_png,
            )
        except InfeasibleLayoutError as error:
            all_succeeded = False
            print(
                f"[{task_path.name}] status={_error_status(error)} "
                f"reason={error.code}: {error}",
                file=sys.stderr,
            )
            cleanup_task_artifacts(OUTPUT_DIR, stem)
            continue
        except Exception as error:
            all_succeeded = False
            print(
                f"[{task_path.name}] status=RUNTIME_IO_FAILURE "
                f"reason=RUNTIME_IO_FAILURE: {error}",
                file=sys.stderr,
            )
            cleanup_task_artifacts(OUTPUT_DIR, stem)
            continue

        elapsed = time.time() - started
        print(
            f"[{task_path.name}] status=SUCCESS in {elapsed:.2f}s "
            f"-> {stem}_output.json, {stem}_output.png"
        )

    return 0 if all_succeeded else 1


if __name__ == "__main__":
    raise SystemExit(main())
