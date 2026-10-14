"""Task-local staging and logical JSON/PNG publication.

A task is committed only after both its design document and render have been
validated and the final commit marker exists. Temporary paths and final files
without a matching marker are not submission artifacts.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_EVEN
from fractions import Fraction
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
    commit_marker: Path
    commit_marker_tmp: Path


def artifact_paths(output_dir: Path, task_name: str) -> TaskArtifactPaths:
    """Return the task-private temporary and final artifact paths."""

    return TaskArtifactPaths(
        json_final=output_dir / f"{task_name}_output.json",
        png_final=output_dir / f"{task_name}_output.png",
        json_tmp=output_dir / f"{task_name}_output.json.tmp",
        png_tmp=output_dir / f"{task_name}_output.png.tmp",
        commit_marker=output_dir / f".{task_name}_output.commit",
        commit_marker_tmp=output_dir / f".{task_name}_output.commit.tmp",
    )


def _staging_entries(output_dir: Path, task_name: str) -> list[Path]:
    prefix = f".{task_name}.stage-"
    try:
        return [path for path in output_dir.iterdir() if path.name.startswith(prefix)]
    except FileNotFoundError:
        return []


def _private_staging_paths(
    output_dir: Path, task_name: str, public_paths: TaskArtifactPaths
) -> tuple[Path, TaskArtifactPaths]:
    staging_dir = Path(
        tempfile.mkdtemp(prefix=f".{task_name}.stage-", dir=output_dir)
    )
    return staging_dir, TaskArtifactPaths(
        json_final=public_paths.json_final,
        png_final=public_paths.png_final,
        json_tmp=staging_dir / f"{task_name}_output.json.tmp",
        png_tmp=staging_dir / f"{task_name}_output.png.tmp",
        commit_marker=public_paths.commit_marker,
        commit_marker_tmp=staging_dir / f".{task_name}_output.commit.tmp",
    )


def cleanup_task_artifacts(output_dir: Path, task_name: str) -> None:
    """Remove all final and staged paths for ``task_name``.

    Missing paths are expected. Other filesystem errors are raised after all
    task paths have been attempted.
    """

    paths = artifact_paths(output_dir, task_name)
    errors: list[OSError] = []
    for path in (
        paths.commit_marker,
        paths.commit_marker_tmp,
        paths.json_final,
        paths.png_final,
        paths.json_tmp,
        paths.png_tmp,
    ):
        try:
            path.unlink()
        except FileNotFoundError:
            pass
        except OSError as error:
            errors.append(error)
    for path in _staging_entries(output_dir, task_name):
        try:
            if path.is_symlink() or not path.is_dir():
                path.unlink()
            else:
                shutil.rmtree(path)
        except FileNotFoundError:
            pass
        except OSError as error:
            errors.append(error)
    if errors:
        raise errors[0]


def quarantine_task_artifacts(output_dir: Path, task_name: str) -> None:
    """Move unremovable task paths out of the scorer-visible namespace."""

    quarantine_dir = Path(
        tempfile.mkdtemp(prefix=".chameleon-quarantine-", dir=output_dir)
    )
    moved = False
    errors: list[OSError] = []
    paths = artifact_paths(output_dir, task_name)
    candidates = [
        paths.commit_marker,
        paths.commit_marker_tmp,
        paths.json_final,
        paths.png_final,
        paths.json_tmp,
        paths.png_tmp,
        *_staging_entries(output_dir, task_name),
    ]
    for path in candidates:
        try:
            if not path.exists() and not path.is_symlink():
                continue
            os.replace(path, quarantine_dir / path.name)
            moved = True
        except FileNotFoundError:
            pass
        except OSError as error:
            errors.append(error)
    if errors:
        raise errors[0]
    if not moved:
        shutil.rmtree(quarantine_dir)


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


def _quantize_mutable(value: Any) -> int:
    if type(value) is int:
        return value
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise ValueError("non-finite Decimal cannot be serialized")
        return int(value.to_integral_value(rounding=ROUND_HALF_EVEN))
    if isinstance(value, Fraction):
        return round(value)
    if isinstance(value, float):
        raise ValueError(
            "binary-float mutable geometry cannot be serialized; use Decimal or Fraction"
        )
    raise TypeError(f"mutable geometry is not numeric: {type(value).__name__}")


def _write_commit_marker(paths: TaskArtifactPaths) -> None:
    marker = {
        "committed": True,
        "json": paths.json_final.name,
        "png": paths.png_final.name,
        "json_sha256": hashlib.sha256(paths.json_tmp.read_bytes()).hexdigest(),
        "png_sha256": hashlib.sha256(paths.png_tmp.read_bytes()).hexdigest(),
    }
    paths.commit_marker_tmp.write_text(
        json.dumps(marker, sort_keys=True),
        encoding="utf-8",
    )

def _verify_published_pair(paths: TaskArtifactPaths) -> None:
    """Require the final files to match the committed manifest."""

    marker = json.loads(paths.commit_marker.read_text(encoding="utf-8"))
    if (
        marker.get("committed") is not True
        or marker.get("json") != paths.json_final.name
        or marker.get("png") != paths.png_final.name
    ):
        raise ValueError("commit marker does not authorize this artifact pair")
    if (
        marker.get("json_sha256")
        != hashlib.sha256(paths.json_final.read_bytes()).hexdigest()
        or marker.get("png_sha256")
        != hashlib.sha256(paths.png_final.read_bytes()).hexdigest()
    ):
        raise ValueError("published artifact pair does not match commit marker")


def _canonicalize_response_mutables(response: Mapping[str, Any]) -> Mapping[str, Any]:
    """Round mutable values once using the contract's half-even rule.

    The parser intentionally retains Decimal values. Contract serialization
    emits only finite integers, while immutable source fields retain their
    exact Decimal representation.
    """

    result = dict(response)
    canvas = response.get("canvas")
    if isinstance(canvas, Mapping):
        result["canvas"] = dict(canvas)
        for field in ("width", "height"):
            if field in canvas:
                result["canvas"][field] = _quantize_mutable(canvas[field])
    elements = response.get("elements")
    if isinstance(elements, list):
        result["elements"] = []
        for element in elements:
            if not isinstance(element, Mapping):
                result["elements"].append(element)
                continue
            candidate = dict(element)
            for field in ("x", "y", "width", "height", "font_size"):
                if field in element:
                    candidate[field] = _quantize_mutable(element[field])
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
    with Image.open(path) as image:
        image.load()


def publish_task(
    *,
    output_dir: Path,
    task_name: str,
    source: Mapping[str, Any],
    target_canvas: Mapping[str, Any],
    response: Mapping[str, Any],
    assets_dir: Path,
    render_to_png: Callable[
        [Mapping[str, Any], Path, Path], list[str] | None
    ],
) -> TaskArtifactPaths:
    """Stage, validate, and marker-publish one JSON/PNG task pair."""

    output_dir.mkdir(parents=True, exist_ok=True)
    public_paths = artifact_paths(output_dir, task_name)
    cleanup_task_artifacts(output_dir, task_name)
    staging_dir, paths = _private_staging_paths(output_dir, task_name, public_paths)
    try:
        serialized = _publish_response_json(response, paths.json_tmp)
        validate_response(source, target_canvas, serialized)
        render_to_png(serialized, assets_dir, paths.png_tmp)
        validate_png(paths.png_tmp)
        _write_commit_marker(paths)

        # POSIX cannot rename two root files as one operation. The marker is
        # written last and is the sole committed-pair visibility gate.
        os.replace(paths.json_tmp, paths.json_final)
        os.replace(paths.png_tmp, paths.png_final)
        os.replace(paths.commit_marker_tmp, paths.commit_marker)
        _verify_published_pair(public_paths)
        return public_paths
    except BaseException as error:
        cleanup_error: OSError | None = None
        try:
            cleanup_task_artifacts(output_dir, task_name)
        except OSError as failure:
            cleanup_error = failure
            try:
                quarantine_task_artifacts(output_dir, task_name)
            except OSError as quarantine_failure:
                cleanup_error = OSError(
                    f"{failure}; quarantine failed: {quarantine_failure}"
                )
        if cleanup_error is not None and isinstance(error, Exception):
            raise RuntimeError(
                f"{type(error).__name__}: {error}; cleanup failed: {cleanup_error}"
            ) from error
        raise
    finally:
        shutil.rmtree(staging_dir, ignore_errors=True)


__all__ = [
    "TaskArtifactPaths",
    "artifact_paths",
    "cleanup_task_artifacts",
    "publish_task",
    "quarantine_task_artifacts",
    "validate_png",
]
