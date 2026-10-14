"""Task-local staging and logical JSON/PNG publication.

A task is committed only after both its design document and render have been
validated and the final commit marker exists. Temporary paths and final files
without a matching marker are not submission artifacts.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import stat
import tempfile
import unicodedata
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any, Callable, Mapping

from PIL import Image

from .contract import validate_response
from .geometry.math_util import quantize_to_int


_OUTPUT_FILE_RE = re.compile(
    r"(?P<stem>.+)_output\.(?:json|png)(?:\.tmp)?\Z", re.DOTALL
)
_COMMIT_FILE_RE = re.compile(
    r"\.(?P<stem>.+)_output\.commit(?:\.tmp)?\Z", re.DOTALL
)
_STAGING_DIR_RE = re.compile(r"\.(?P<stem>.+)\.stage-.+\Z", re.DOTALL)


@dataclass(frozen=True)
class TaskArtifactPaths:
    """Final and private staging paths for one task."""

    json_final: Path
    png_final: Path
    json_tmp: Path
    png_tmp: Path
    commit_marker: Path
    commit_marker_tmp: Path


def validate_task_name(task_name: str) -> None:
    """Reject names that could escape the output directory or create ambiguity."""

    if not isinstance(task_name, str) or not task_name:
        raise ValueError("task name must be a non-empty basename")
    if task_name in {".", ".."} or "\x00" in task_name:
        raise ValueError("task name must not be '.' or '..'")
    if any(unicodedata.category(character) == "Cc" for character in task_name):
        raise ValueError("task name must not contain control characters")
    if "/" in task_name or "\\" in task_name or Path(task_name).is_absolute():
        raise ValueError(f"task name is not a basename: {task_name!r}")
    if Path(task_name).name != task_name:
        raise ValueError(f"task name is not a basename: {task_name!r}")


def _open_regular_file(path: Path):
    """Open a regular file without following a final symlink."""

    initial = path.lstat()
    if stat.S_ISLNK(initial.st_mode):
        raise OSError(f"refusing symlink artifact: {path}")
    if not stat.S_ISREG(initial.st_mode):
        raise OSError(f"refusing non-regular artifact: {path}")
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0)
    nofollow = getattr(os, "O_NOFOLLOW", 0)
    if nofollow:
        flags |= nofollow
    fd = os.open(path, flags)
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise OSError(f"refusing non-regular artifact: {path}")
        return os.fdopen(fd, "rb")
    except BaseException:
        os.close(fd)
        raise


def _read_regular_bytes(path: Path) -> bytes:
    with _open_regular_file(path) as stream:
        return stream.read()


def _read_regular_text(path: Path) -> str:
    return _read_regular_bytes(path).decode("utf-8")


def _sha256_regular_file(path: Path) -> str:
    return hashlib.sha256(_read_regular_bytes(path)).hexdigest()


def _generated_stem(name: str) -> str | None:
    for pattern in (_OUTPUT_FILE_RE, _COMMIT_FILE_RE, _STAGING_DIR_RE):
        match = pattern.fullmatch(name)
        if match:
            return match.group("stem")
    return None


def reconcile_output_artifacts(
    output_dir: Path, current_task_names: set[str] | frozenset[str]
) -> None:
    """Remove stale generated artifacts while preserving unrelated output files."""

    current = set(current_task_names)
    for task_name in current:
        validate_task_name(task_name)
    try:
        entries = list(output_dir.iterdir())
    except FileNotFoundError:
        return

    stale_names = {
        stem
        for path in entries
        if (stem := _generated_stem(path.name)) is not None and stem not in current
    }
    failures: list[str] = []
    for task_name in sorted(stale_names):
        try:
            cleanup_task_artifacts(output_dir, task_name)
        except BaseException as error:
            try:
                quarantine_task_artifacts(output_dir, task_name)
            except BaseException as quarantine_error:
                failures.append(
                    f"{task_name!r}: {type(error).__name__}: {error}; "
                    f"quarantine failed: {type(quarantine_error).__name__}: "
                    f"{quarantine_error}"
                )
            else:
                failures.append(
                    f"{task_name!r}: {type(error).__name__}: {error}; "
                    "stale paths quarantined"
                )
    if failures:
        raise RuntimeError("output reconciliation failed: " + "; ".join(failures))


def _validate_artifact_stem(task_name: str) -> None:
    """Reject stems that could escape the output directory."""

    if not isinstance(task_name, str) or not task_name:
        raise ValueError("artifact stem must be a non-empty basename")
    if task_name in {".", ".."} or "\x00" in task_name:
        raise ValueError("artifact stem must not be '.' or '..'")
    if "/" in task_name or "\\" in task_name or Path(task_name).is_absolute():
        raise ValueError(f"artifact stem is not a basename: {task_name!r}")
    if Path(task_name).name != task_name:
        raise ValueError(f"artifact stem is not a basename: {task_name!r}")


def _artifact_paths(output_dir: Path, task_name: str) -> TaskArtifactPaths:
    _validate_artifact_stem(task_name)
    return TaskArtifactPaths(
        json_final=output_dir / f"{task_name}_output.json",
        png_final=output_dir / f"{task_name}_output.png",
        json_tmp=output_dir / f"{task_name}_output.json.tmp",
        png_tmp=output_dir / f"{task_name}_output.png.tmp",
        commit_marker=output_dir / f".{task_name}_output.commit",
        commit_marker_tmp=output_dir / f".{task_name}_output.commit.tmp",
    )


def artifact_paths(output_dir: Path, task_name: str) -> TaskArtifactPaths:
    """Return the task-private temporary and final artifact paths."""

    validate_task_name(task_name)
    return _artifact_paths(output_dir, task_name)


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

    paths = _artifact_paths(output_dir, task_name)
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
    paths = _artifact_paths(output_dir, task_name)
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
        _read_regular_text(path),
        parse_int=int,
        parse_float=Decimal,
        parse_constant=_reject_constant,
    )


def _quantize_mutable(value: Any) -> int:
    """Round one mutable value with the contract's centralized rule."""

    return quantize_to_int(value)


def _write_commit_marker(paths: TaskArtifactPaths) -> None:
    marker = {
        "committed": True,
        "json": paths.json_final.name,
        "png": paths.png_final.name,
        "json_sha256": _sha256_regular_file(paths.json_tmp),
        "png_sha256": _sha256_regular_file(paths.png_tmp),
    }
    paths.commit_marker_tmp.write_text(
        json.dumps(marker, sort_keys=True),
        encoding="utf-8",
    )

def _verify_published_pair(paths: TaskArtifactPaths) -> None:
    """Require the final files to match the committed manifest."""

    marker = json.loads(_read_regular_text(paths.commit_marker))
    if (
        not isinstance(marker, Mapping)
        or marker.get("committed") is not True
        or marker.get("json") != paths.json_final.name
        or marker.get("png") != paths.png_final.name
    ):
        raise ValueError("commit marker does not authorize this artifact pair")
    if (
        marker.get("json_sha256") != _sha256_regular_file(paths.json_final)
        or marker.get("png_sha256") != _sha256_regular_file(paths.png_final)
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
            for field in ("x", "y", "width", "height"):
                if field in element:
                    candidate[field] = _quantize_mutable(element[field])
            if element.get("type") == "text" and "font_size" in element:
                candidate["font_size"] = _quantize_mutable(element["font_size"])
            result["elements"].append(candidate)
    return result


def _publish_response_json(response: Mapping[str, Any], path: Path) -> Mapping[str, Any]:
    canonical = _canonicalize_response_mutables(response)
    path.write_text(_serialize_json(canonical), encoding="utf-8")
    return _read_serialized_design(path)


def validate_png(path: Path) -> None:
    """Ensure a staged file is a readable, non-empty PNG image."""

    with _open_regular_file(path) as stream:
        if os.fstat(stream.fileno()).st_size == 0:
            raise ValueError(f"renderer did not produce a PNG: {path}")
        with Image.open(stream) as image:
            if image.format != "PNG":
                raise ValueError(f"renderer produced {image.format!r}, not PNG")
            image.verify()
    with _open_regular_file(path) as stream:
        with Image.open(stream) as image:
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
    try:
        cleanup_task_artifacts(output_dir, task_name)
    except BaseException as error:
        try:
            quarantine_task_artifacts(output_dir, task_name)
        except BaseException as quarantine_error:
            raise RuntimeError(
                f"{type(error).__name__}: {error}; quarantine failed: "
                f"{type(quarantine_error).__name__}: {quarantine_error}"
            ) from error
        raise
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
    "reconcile_output_artifacts",
    "validate_png",
    "validate_task_name",
]
