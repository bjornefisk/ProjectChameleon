"""Batch runner for independent fail-closed Stage 1 tasks."""

import json
import sys
import time
from decimal import Decimal
from pathlib import Path
from typing import Any, Mapping

from engine.contract import validate_source, validate_target_canvas
from engine.errors import InfeasibleLayoutError
from engine.resize import resize
from engine.staging import (
    cleanup_task_artifacts,
    publish_task,
    quarantine_task_artifacts,
)

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
    validate_target_canvas(target)
    return task


def _error_status(error: InfeasibleLayoutError) -> str:
    if error.code in _MALFORMED_CODES:
        return "MALFORMED_INPUT"
    if error.code == "INCOMPLETE_SEARCH":
        return "INCOMPLETE_SEARCH"
    if error.code == "RUNTIME_IO_FAILURE":
        return "RUNTIME_IO_FAILURE"
    if error.code == "NO_HARD_VALID_CANDIDATE":
        return "INFEASIBLE_LAYOUT"
    return "RUNTIME_IO_FAILURE"


def _cleanup_after_failure(stem: str) -> str | None:
    try:
        cleanup_task_artifacts(OUTPUT_DIR, stem)
    except Exception as error:
        quarantine_error = None
        try:
            quarantine_task_artifacts(OUTPUT_DIR, stem)
        except Exception as quarantine_failure:
            quarantine_error = (
                f"{type(quarantine_failure).__name__}: {quarantine_failure}"
            )
        message = f"{type(error).__name__}: {error}"
        if quarantine_error:
            message += f"; quarantine failed: {quarantine_error}"
        else:
            message += "; stale paths quarantined"
        return message
    return None


def _report_failure(
    task_name: str,
    status: str,
    reason: str,
    cleanup_error: str | None,
) -> None:
    if cleanup_error:
        status = "RUNTIME_IO_FAILURE"
        reason = f"{reason}; cleanup failed: {cleanup_error}"
    print(
        f"[{task_name}] status={status} reason={reason}",
        file=sys.stderr,
    )


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


def render_to_png(design: dict, assets_dir: Path, png_path: Path) -> list[str]:
    """Render with the pinned local adapter and return conversion warnings."""

    from renderer.converter.convert import render_design_to_png  # type: ignore

    warnings = render_design_to_png(design, assets_dir, str(png_path)) or []
    for warning in warnings:
        print(f"renderer warning: {warning}", file=sys.stderr)
    return warnings


def main() -> int:
    try:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        task_files = sorted(INPUT_DIR.glob("*.json"))
    except OSError as error:
        print(
            f"[runner] status=RUNTIME_IO_FAILURE "
            f"reason=RUNTIME_IO_FAILURE: {error}",
            file=sys.stderr,
        )
        return 1

    if not task_files:
        print(f"No task files found in {INPUT_DIR}", file=sys.stderr)
        return 1

    all_succeeded = True
    for task_path in task_files:
        stem = task_path.stem
        cleanup_error = _cleanup_after_failure(stem)
        if cleanup_error:
            all_succeeded = False
            _report_failure(
                task_path.name,
                "RUNTIME_IO_FAILURE",
                f"RUNTIME_IO_FAILURE: {cleanup_error}",
                None,
            )
            continue

        started = time.time()
        try:
            task = _load_task(task_path)
        except InfeasibleLayoutError as error:
            all_succeeded = False
            cleanup_error = _cleanup_after_failure(stem)
            _report_failure(
                task_path.name,
                _error_status(error),
                f"{error.code}: {error}",
                cleanup_error,
            )
            continue
        except OSError as error:
            all_succeeded = False
            cleanup_error = _cleanup_after_failure(stem)
            _report_failure(
                task_path.name,
                "RUNTIME_IO_FAILURE",
                f"RUNTIME_IO_FAILURE: {error}",
                cleanup_error,
            )
            continue
        except Exception as error:
            all_succeeded = False
            cleanup_error = _cleanup_after_failure(stem)
            _report_failure(
                task_path.name,
                "MALFORMED_INPUT",
                f"MALFORMED_INPUT: {error}",
                cleanup_error,
            )
            continue

        try:
            source, target_canvas = task["source"], task["target_canvas"]
            output = resize(source, target_canvas)
            for problem in self_check(source, output):
                print(f"self-check warning: {problem}", file=sys.stderr)
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
            cleanup_error = _cleanup_after_failure(stem)
            _report_failure(
                task_path.name,
                _error_status(error),
                f"{error.code}: {error}",
                cleanup_error,
            )
            continue
        except Exception as error:
            all_succeeded = False
            cleanup_error = _cleanup_after_failure(stem)
            _report_failure(
                task_path.name,
                "RUNTIME_IO_FAILURE",
                f"RUNTIME_IO_FAILURE: {error}",
                cleanup_error,
            )
            continue

        elapsed = time.time() - started
        print(
            f"[{task_path.name}] status=SUCCESS in {elapsed:.2f}s "
            f"-> {stem}_output.json, {stem}_output.png"
        )

    return 0 if all_succeeded else 1


if __name__ == "__main__":
    raise SystemExit(main())
