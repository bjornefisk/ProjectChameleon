"""Task-local staging and logical JSON/PNG publication.

A task is observable only after both its design document and render have been
validated.  Temporary paths are deliberately task-specific and are never used
as submission artifacts.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any, Callable, Mapping

from PIL import Image

from .contract import validate_response


@dataclass(frozen=True)
class TaskArtifactPaths:
    """Final and private staging paths for one task."""

    json_final: Path
    png_final: Path
    json_tmp: Path
    png_tmp: Path


def artifact_paths(output_dir: Path, task_name: str) -> TaskArtifactPaths:
    """Return the task-private temporary and final artifact paths."""

    return TaskArtifactPaths(
        json_final=output_dir / f"{task_name}_output.json",
        png_final=output_dir / f"{task_name}_output.png",
        json_tmp=output_dir / f"{task_name}_output.json.tmp",
        png_tmp=output_dir / f"{task_name}_output.png.tmp",
    )


def cleanup_task_artifacts(output_dir: Path, task_name: str) -> None:
    """Remove all final and staged paths for ``task_name``.

    Missing paths are expected.  Other filesystem errors are allowed to reach
    the runner as runtime failures rather than being silently ignored.
    """

    paths = artifact_paths(output_dir, task_name)
    for path in (paths.json_final, paths.png_final, paths.json_tmp, paths.png_tmp):
        try:
            path.unlink()
        except FileNotFoundError:
            pass


def _reject_constant(value: str) -> None:
    raise ValueError(f"non-finite JSON constant is not allowed: {value}")


def _json_number(value: Any) -> str:
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise ValueError("non-finite Decimal cannot be serialized")
        return str(value)
    if isinstance(value, float):
        if value != value or value in (float("inf"), float("-inf")):
            raise ValueError("non-finite float cannot be serialized")
        return repr(value)
    return str(value)


def _serialize_json(value: Any) -> str:
    """Serialize JSON values while retaining Decimal as a JSON number.

    ``json.dumps`` has no Decimal hook that emits an unquoted number.  This
    small encoder is intentionally limited to JSON value types and is used
    only for the already validated public design document.
    """

    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, (int, Decimal, float)):
        return _json_number(value)
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    if isinstance(value, Mapping):
        parts: list[str] = []
        for key, child in value.items():
            if not isinstance(key, str):
                raise TypeError("JSON object keys must be strings")
            parts.append(
                json.dumps(key, ensure_ascii=False, separators=(",", ":"))
                + ":"
                + _serialize_json(child)
            )
        return "{" + ",".join(parts) + "}"
    if isinstance(value, (list, tuple)):
        return "[" + ",".join(_serialize_json(child) for child in value) + "]"
    raise TypeError(f"value is not JSON serializable: {type(value).__name__}")


def _read_serialized_design(path: Path) -> Any:
    return json.loads(
        path.read_text(encoding="utf-8"),
        parse_int=int,
        parse_float=Decimal,
        parse_constant=_reject_constant,
    )


def _canonicalize_response_mutables(response: Mapping[str, Any]) -> Mapping[str, Any]:
    """Convert integral Decimal mutables to serialized integers.

    The parser intentionally retains Decimal values.  Contract serialization
    permits only integer canvas and geometry values, while immutable source
    fields must retain their exact Decimal representation.
    """

    result = dict(response)
    canvas = response.get("canvas")
    if isinstance(canvas, Mapping):
        result["canvas"] = dict(canvas)
        for field in ("width", "height"):
            value = canvas.get(field)
            if isinstance(value, Decimal) and value.is_finite() and value == value.to_integral_value():
                result["canvas"][field] = int(value)
    elements = response.get("elements")
    if isinstance(elements, list):
        result["elements"] = []
        for element in elements:
            if not isinstance(element, Mapping):
                result["elements"].append(element)
                continue
            candidate = dict(element)
            for field in ("x", "y", "width", "height", "font_size"):
                value = element.get(field)
                if isinstance(value, Decimal) and value.is_finite() and value == value.to_integral_value():
                    candidate[field] = int(value)
            result["elements"].append(candidate)
    return result


def _publish_response_json(response: Mapping[str, Any], path: Path) -> Mapping[str, Any]:
    canonical = _canonicalize_response_mutables(response)
    path.write_text(_serialize_json(canonical), encoding="utf-8")
    return _read_serialized_design(path)


def validate_png(path: Path) -> None:
    """Ensure a staged file is a readable, non-empty PNG image."""

    if not path.is_file() or path.stat().st_size == 0:
        raise ValueError(f"renderer did not produce a PNG: {path}")
    with Image.open(path) as image:
        if image.format != "PNG":
            raise ValueError(f"renderer produced {image.format!r}, not PNG")
        image.verify()


def publish_task(
    *,
    output_dir: Path,
    task_name: str,
    source: Mapping[str, Any],
    target_canvas: Mapping[str, Any],
    response: Mapping[str, Any],
    assets_dir: Path,
    render_to_png: Callable[[Mapping[str, Any], Path, Path], None],
) -> TaskArtifactPaths:
    """Stage, validate, and logically publish one JSON/PNG task pair.

    Any exception removes both staged and final paths.  Individual ``os.replace``
    calls provide atomic visibility for each file; rollback on the second
    replacement failure preserves the task-level all-or-nothing contract.
    """

    output_dir.mkdir(parents=True, exist_ok=True)
    paths = artifact_paths(output_dir, task_name)
    cleanup_task_artifacts(output_dir, task_name)
    try:
        serialized = _publish_response_json(response, paths.json_tmp)
        validate_response(source, target_canvas, serialized)
        render_to_png(serialized, assets_dir, paths.png_tmp)
        validate_png(paths.png_tmp)

        os.replace(paths.json_tmp, paths.json_final)
        try:
            os.replace(paths.png_tmp, paths.png_final)
        except BaseException:
            # A failed second commit must not expose the first artifact.
            cleanup_task_artifacts(output_dir, task_name)
            raise
        return paths
    except BaseException:
        cleanup_task_artifacts(output_dir, task_name)
        raise


__all__ = [
    "TaskArtifactPaths",
    "artifact_paths",
    "cleanup_task_artifacts",
    "publish_task",
    "validate_png",
]
