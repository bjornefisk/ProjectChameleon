"""Batch runner for independent fail-closed Stage 1 tasks."""

from __future__ import annotations

import json
import sys
import time
from decimal import Decimal
from pathlib import Path
from typing import Any, Mapping

from engine.contract import validate_source, validate_target_canvas
from engine.errors import InfeasibleLayoutError, InfeasibleReasonCode, TaskStatus
from engine.resize import resize
from engine.staging import (
    cleanup_task_artifacts,
    publish_task,
    quarantine_task_artifacts,
)

try:
    from renderer.converter.wrap import (  # type: ignore
        MalformedTextError as _MalformedTextError,
        TextLayoutError as _TextLayoutError,
    )
except ImportError:
    _MalformedTextError = None
    _TextLayoutError = None

# Relative to the current working directory, which is /app inside Docker and
# the chameleon project directory for local execution.
INPUT_DIR = Path("input")
OUTPUT_DIR = Path("output")
ASSETS_DIR = Path("brand_kit/assets")


class _MalformedInputError(ValueError):
    """Raised when JSON contains a non-standard or non-finite number."""


def _reject_json_constant(value: str) -> None:
    raise _MalformedInputError(f"non-finite JSON constant {value!r} is not allowed")


def _load_task(task_path: Path) -> Mapping[str, Any]:
    """Decode and validate a task envelope without binary-float ingress."""
    task = json.loads(
        task_path.read_text(encoding="utf-8"),
        parse_int=int,
        parse_float=Decimal,
        parse_constant=_reject_json_constant,
    )
    if not isinstance(task, Mapping):
        raise _MalformedInputError("task envelope must be a JSON object")
    if "source" not in task or "target_canvas" not in task:
        raise _MalformedInputError("task envelope requires source and target_canvas")
    source, target_canvas = task["source"], task["target_canvas"]
    if not isinstance(source, Mapping) or not isinstance(target_canvas, Mapping):
        raise _MalformedInputError("source and target_canvas must be JSON objects")
    validate_source(source)
    validate_target_canvas(target_canvas)
    return task


def _failure_reason(error: Exception, phase: str) -> str:
    if isinstance(error, InfeasibleLayoutError):
        return error.reason_code.value
    if _MalformedTextError is not None and isinstance(error, _MalformedTextError):
        return InfeasibleReasonCode.MALFORMED_INPUT.value
    if _TextLayoutError is not None and isinstance(error, _TextLayoutError):
        return InfeasibleReasonCode.TEXT_OVERFLOW.value
    if phase == "input" and isinstance(
        error, (_MalformedInputError, json.JSONDecodeError, KeyError, TypeError, ValueError)
    ):
        return InfeasibleReasonCode.MALFORMED_INPUT.value
    return type(error).__name__


def _classify_failure(
    error: Exception, phase: str
) -> tuple[TaskStatus, str]:
    """Map a failure to an accepted task status and stable diagnostic reason."""
    reason = _failure_reason(error, phase)

    if isinstance(error, InfeasibleLayoutError):
        code = error.reason_code
        if code in {
            InfeasibleReasonCode.INVALID_SOURCE,
            InfeasibleReasonCode.INVALID_TARGET,
            InfeasibleReasonCode.MALFORMED_INPUT,
        }:
            return TaskStatus.MALFORMED_INPUT, reason
        if code == InfeasibleReasonCode.INCOMPLETE_SEARCH:
            return TaskStatus.INCOMPLETE_SEARCH, reason
        if code == InfeasibleReasonCode.RUNTIME_IO_FAILURE:
            return TaskStatus.RUNTIME_IO_FAILURE, reason
        if code == InfeasibleReasonCode.NO_HARD_VALID_CANDIDATE:
            return TaskStatus.INFEASIBLE_LAYOUT, reason
        # A response validator rejection means the engine produced an invalid
        # candidate; it is a runtime failure, not proof of infeasibility.
        return TaskStatus.RUNTIME_IO_FAILURE, reason

    if phase == "input":
        if isinstance(
            error, (_MalformedInputError, json.JSONDecodeError, KeyError, TypeError, ValueError)
        ):
            return TaskStatus.MALFORMED_INPUT, reason
        return TaskStatus.RUNTIME_IO_FAILURE, reason

    if _MalformedTextError is not None and isinstance(error, _MalformedTextError):
        return TaskStatus.MALFORMED_INPUT, reason
    if _TextLayoutError is not None and isinstance(error, _TextLayoutError):
        return TaskStatus.INFEASIBLE_LAYOUT, reason
    return TaskStatus.RUNTIME_IO_FAILURE, reason


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
    status: TaskStatus | str,
    reason: str,
    cleanup_error: str | None,
) -> None:
    status_value = status.value if isinstance(status, TaskStatus) else status
    if cleanup_error:
        status_value = TaskStatus.RUNTIME_IO_FAILURE.value
        reason = f"{reason}; cleanup failed: {cleanup_error}"
    print(
        f"[{task_name}] status={status_value} reason={reason}",
        file=sys.stderr,
    )


REQUIRED_COMMON = ["id", "type", "x", "y", "width", "height"]
REQUIRED_BY_TYPE = {
    "text": ["content", "font_family", "font_size", "color"],
    "image": ["asset_id"],
    "shape": ["shape_type", "fill_color"],
}


def self_check(source: Mapping[str, Any], output: Mapping[str, Any]) -> list[str]:
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

    canvas = output["canvas"]
    cw, ch = canvas.get("width"), canvas.get("height")
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


def render_to_png(
    design: Mapping[str, Any], assets_dir: Path, png_path: Path
) -> list[str]:
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
            "[runner] status=RUNTIME_IO_FAILURE "
            f"reason=RUNTIME_IO_FAILURE: {error}",
            file=sys.stderr,
        )
        return 1

    if not task_files:
        print(
            "[runner] status=RUNTIME_IO_FAILURE "
            f"reason=RUNTIME_IO_FAILURE: no task files found in {INPUT_DIR}",
            file=sys.stderr,
        )
        return 1

    all_succeeded = True
    for task_path in task_files:
        stem = task_path.stem
        cleanup_error = _cleanup_after_failure(stem)
        if cleanup_error:
            all_succeeded = False
            _report_failure(
                task_path.name,
                TaskStatus.RUNTIME_IO_FAILURE,
                f"RUNTIME_IO_FAILURE: {cleanup_error}",
                None,
            )
            continue

        started = time.monotonic()
        phase = "input"
        try:
            task = _load_task(task_path)
            source, target_canvas = task["source"], task["target_canvas"]
            phase = "resize"
            output = resize(source, target_canvas)
            for problem in self_check(source, output):
                print(f"self-check warning: {problem}", file=sys.stderr)
            phase = "publish"
            publish_task(
                output_dir=OUTPUT_DIR,
                task_name=stem,
                source=source,
                target_canvas=target_canvas,
                response=output,
                assets_dir=ASSETS_DIR,
                render_to_png=render_to_png,
            )
        except Exception as error:
            all_succeeded = False
            cleanup_error = _cleanup_after_failure(stem)
            status, reason = _classify_failure(error, phase)
            _report_failure(
                task_path.name,
                status,
                f"{reason}: {error}",
                cleanup_error,
            )
            continue

        elapsed = time.monotonic() - started
        print(
            f"[{task_path.name}] status=SUCCESS in {elapsed:.2f}s "
            f"-> {stem}_output.json, {stem}_output.png"
        )

    return 0 if all_succeeded else 1


if __name__ == "__main__":
    raise SystemExit(main())
