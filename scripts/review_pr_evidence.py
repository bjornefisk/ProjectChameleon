"""Evidence publication and Markdown rendering for review capsules."""

from __future__ import annotations

import os
import re
import shutil
import stat
import tempfile
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Mapping

try:
    import fcntl
except ImportError:
    fcntl = None


@dataclass
class CheckResult:
    name: str
    status: str
    duration_seconds: float
    command: list[str]
    returncode: int | None = None
    log: str | None = None
    reason: str | None = None
    output: bytes | None = field(default=None, repr=False, compare=False)


def open_evidence_directory(path: Path) -> int:
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    flags |= getattr(os, "O_NOFOLLOW", 0)
    return os.open(path, flags)


def validate_publication_parent(path: Path) -> None:
    parent = os.stat(path, follow_symlinks=False)
    if not stat.S_ISDIR(parent.st_mode):
        raise ValueError(f"report parent is not a directory: {path}")
    if parent.st_mode & (stat.S_IWGRP | stat.S_IWOTH):
        raise ValueError(f"report parent must not be group/world writable: {path}")


def verify_evidence_directory(
    path: Path,
    descriptor: int,
    expected_names: Iterable[str] | None = None,
) -> None:
    expected = os.fstat(descriptor)
    actual = os.stat(path, follow_symlinks=False)
    if (actual.st_dev, actual.st_ino) != (expected.st_dev, expected.st_ino):
        raise ValueError("evidence directory changed during PR checks")
    if expected_names is None:
        return
    expected_entries = set(expected_names)
    actual_entries = set(os.listdir(descriptor))
    if actual_entries != expected_entries:
        raise ValueError(
            "evidence directory contains unexpected artifacts: "
            + ", ".join(sorted(actual_entries ^ expected_entries))
        )
    for name in expected_entries:
        entry = os.stat(name, dir_fd=descriptor, follow_symlinks=False)
        if not stat.S_ISREG(entry.st_mode):
            raise ValueError(f"evidence artifact is not a regular file: {name}")


def evidence_directory_entries(descriptor: int) -> list[str]:
    return sorted(os.listdir(descriptor))


def create_staging_directory(target: Path) -> Path:
    try:
        target_stat = os.lstat(target)
    except FileNotFoundError:
        target_stat = None
    if target_stat is not None:
        if stat.S_ISLNK(target_stat.st_mode):
            raise ValueError(f"report directory must not be a symlink: {target}")
        if not stat.S_ISDIR(target_stat.st_mode):
            raise ValueError(f"report path is not a directory: {target}")
        raise ValueError(f"report directory must not already exist: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    validate_publication_parent(target.parent)
    return Path(tempfile.mkdtemp(prefix=f".{target.name}.", dir=target.parent))


def publish_staging_directory(
    staging: Path,
    target: Path,
    directory_fd: int | None = None,
    expected_names: Iterable[str] | None = None,
) -> None:
    if staging.parent.absolute() != target.parent.absolute():
        raise ValueError("staging and target directories must share a parent")
    parent_fd: int | None = None
    target_fd: int | None = None
    lock_fd: int | None = None
    target_moved = False
    target_identity: os.stat_result | None = None
    expected_identity: os.stat_result | None = None
    staging_fd = directory_fd
    owns_staging_fd = False
    lock_acquired = False
    publication_succeeded = False
    lock_name = f".{target.name}.publish.lock"
    staging_name = staging.name
    target_name = target.name
    try:
        validate_publication_parent(target.parent)
        parent_fd = open_evidence_directory(target.parent)
        if fcntl is None:
            raise OSError("publication locks require POSIX advisory locking")
        lock_fd = os.open(
            lock_name,
            os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0),
            0o600,
            dir_fd=parent_fd,
        )
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise ValueError(
                f"report publication already in progress: {target}"
            ) from error
        lock_acquired = True
        if staging_fd is None:
            staging_fd = os.open(
                staging_name,
                os.O_RDONLY
                | getattr(os, "O_DIRECTORY", 0)
                | getattr(os, "O_NOFOLLOW", 0),
                dir_fd=parent_fd,
            )
            owns_staging_fd = True
        expected = os.fstat(staging_fd)
        expected_identity = expected
        actual = os.stat(
            staging_name,
            dir_fd=parent_fd,
            follow_symlinks=False,
        )
        if (actual.st_dev, actual.st_ino) != (expected.st_dev, expected.st_ino):
            raise ValueError("staging directory changed before publication")
        try:
            os.stat(target_name, dir_fd=parent_fd, follow_symlinks=False)
        except FileNotFoundError:
            pass
        else:
            raise ValueError(f"report directory appeared during checks: {target}")
        os.replace(
            staging_name,
            target_name,
            src_dir_fd=parent_fd,
            dst_dir_fd=parent_fd,
        )
        target_moved = True
        target_fd = os.open(
            target_name,
            os.O_RDONLY
            | getattr(os, "O_DIRECTORY", 0)
            | getattr(os, "O_NOFOLLOW", 0),
            dir_fd=parent_fd,
        )
        target_identity = os.fstat(target_fd)
        if (target_identity.st_dev, target_identity.st_ino) != (
            expected.st_dev,
            expected.st_ino,
        ):
            raise ValueError("published directory changed before validation")
        if expected_names is not None:
            expected_entries = set(expected_names)
            actual_entries = set(os.listdir(target_fd))
            if actual_entries != expected_entries:
                raise ValueError(
                    "published directory contains unexpected artifacts: "
                    + ", ".join(sorted(actual_entries ^ expected_entries))
                )
            for name in expected_entries:
                entry = os.stat(
                    name,
                    dir_fd=target_fd,
                    follow_symlinks=False,
                )
                if not stat.S_ISREG(entry.st_mode):
                    raise ValueError(
                        f"published artifact is not a regular file: {name}"
                    )
        publication_succeeded = True
    finally:
        if (
            target_moved
            and not publication_succeeded
            and expected_identity is not None
            and parent_fd is not None
        ):
            try:
                current_target = os.stat(
                    target_name,
                    dir_fd=parent_fd,
                    follow_symlinks=False,
                )
                if (
                    (current_target.st_dev, current_target.st_ino)
                    == (expected_identity.st_dev, expected_identity.st_ino)
                ):
                    if not shutil.rmtree.avoids_symlink_attacks:
                        raise OSError("safe publication rollback unavailable")
                    shutil.rmtree(target_name, dir_fd=parent_fd)
            except FileNotFoundError:
                pass
        if owns_staging_fd and staging_fd is not None:
            os.close(staging_fd)
        if target_fd is not None:
            os.close(target_fd)
        if lock_fd is not None:
            if lock_acquired:
                try:
                    fcntl.flock(lock_fd, fcntl.LOCK_UN)
                except OSError:
                    if not publication_succeeded:
                        raise
            os.close(lock_fd)
        if parent_fd is not None:
            os.close(parent_fd)


def discard_staging_directory(
    staging: Path,
    directory_fd: int | None = None,
) -> bool:
    parent_fd = open_evidence_directory(staging.parent)
    try:
        expected = os.fstat(directory_fd) if directory_fd is not None else None
        try:
            actual = os.stat(
                staging.name,
                dir_fd=parent_fd,
                follow_symlinks=False,
            )
        except FileNotFoundError:
            return True
        if expected is not None and (
            (actual.st_dev, actual.st_ino) != (expected.st_dev, expected.st_ino)
        ):
            return False
        if not stat.S_ISDIR(actual.st_mode):
            return False
        if not shutil.rmtree.avoids_symlink_attacks:
            raise OSError("safe staging cleanup unavailable")
        shutil.rmtree(staging.name, dir_fd=parent_fd)
        return True
    finally:
        os.close(parent_fd)


def _write_descriptor(descriptor: int, content: bytes) -> None:
    try:
        with os.fdopen(descriptor, "wb") as evidence:
            evidence.write(content)
            evidence.flush()
            os.fsync(evidence.fileno())
    except BaseException:
        try:
            os.close(descriptor)
        except OSError:
            pass
        raise


def write_evidence_bytes(
    path: Path,
    content: bytes,
    directory_fd: int | None = None,
) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    flags |= getattr(os, "O_NOFOLLOW", 0)
    temporary_path: Path | None = None
    temporary_name: str | None = None
    descriptor: int | None = None
    try:
        if directory_fd is None:
            descriptor, temporary_name = tempfile.mkstemp(
                prefix=f".{path.name}.",
                suffix=".tmp",
                dir=path.parent,
            )
            temporary_path = Path(temporary_name)
        else:
            temporary_name = f".{path.name}.{uuid.uuid4().hex}.tmp"
            descriptor = os.open(temporary_name, flags, 0o600, dir_fd=directory_fd)
        _write_descriptor(descriptor, content)
        descriptor = None
        if directory_fd is None:
            os.replace(temporary_path, path)
        else:
            os.replace(
                temporary_name,
                path.name,
                src_dir_fd=directory_fd,
                dst_dir_fd=directory_fd,
            )
    finally:
        if descriptor is not None:
            try:
                os.close(descriptor)
            except OSError:
                pass
        if directory_fd is None and temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
        elif directory_fd is not None and temporary_name is not None:
            try:
                os.unlink(temporary_name, dir_fd=directory_fd)
            except FileNotFoundError:
                pass


def write_text(
    path: Path,
    content: str,
    directory_fd: int | None = None,
) -> None:
    if not content.endswith("\n"):
        content += "\n"
    write_evidence_bytes(path, content.encode("utf-8"), directory_fd)


def flush_check_logs(
    checks: Iterable[CheckResult],
    directory_fd: int | None = None,
) -> None:
    for check in checks:
        if check.log is None or check.output is None:
            continue
        write_evidence_bytes(Path(check.log), check.output, directory_fd)
        check.output = None


def cleanup_evidence_files(directory_fd: int, names: Iterable[str]) -> None:
    for name in set(names):
        try:
            os.unlink(name, dir_fd=directory_fd)
        except FileNotFoundError:
            pass


def serialize_check(check: CheckResult) -> dict:
    value = asdict(check)
    value.pop("output", None)
    return value


def markdown_cell(value: object) -> str:
    return (
        str(value)
        .replace("&", "&amp;")
        .replace("\\", "\\\\")
        .replace("|", "\\|")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("\r", "\\r")
        .replace("\n", "\\n")
    )


def markdown_code(value: object) -> str:
    escaped = (
        str(value)
        .replace("\\", "\\\\")
        .replace("\r", "\\r")
        .replace("\n", "\\n")
        .replace("|", "\\|")
    )
    longest_backtick_run = max(
        (len(run) for run in re.findall(r"`+", escaped)),
        default=0,
    )
    fence = "`" * (longest_backtick_run + 1)
    return f"{fence}{escaped}{fence}"


def incomplete_checks(checks: Iterable[CheckResult]) -> list[str]:
    return [check.name for check in checks if check.status != "PASS"]


def next_owner(checks: Iterable[CheckResult], submit_mode: str) -> str:
    checks = list(checks)
    submission_succeeded = any(
        check.name == "submit-review" and check.status == "PASS" for check in checks
    )
    if submission_succeeded and submit_mode == "request-changes":
        return "PR author/maintainer"
    if any(check.status == "FAIL" for check in checks):
        return "PR author/maintainer (resolve failed checks)"
    if any(check.status == "SKIP" for check in checks):
        return "reviewer/maintainer (complete skipped evidence)"
    if submission_succeeded:
        return "PR author/maintainer"
    return "independent reviewer"


def submission_blocker(checks: Iterable[CheckResult]) -> str | None:
    incomplete = incomplete_checks(checks)
    if not incomplete:
        return None
    return "submission blocked; incomplete checks: " + ", ".join(incomplete)


def make_summary(
    report_dir: Path,
    metadata: dict,
    base_sha: str,
    head_sha: str,
    changed_files: list[str],
    checks: list[CheckResult],
    contract_sources: list[str],
    provenance: Mapping[str, str] | None = None,
    directory_fd: int | None = None,
) -> Path:
    if any(check.status == "FAIL" for check in checks):
        overall = "FAIL"
    elif any(check.status == "SKIP" for check in checks):
        overall = "INCOMPLETE"
    else:
        overall = "PASS"
    provenance = dict(provenance or {})
    lines = [
        "# PR review capsule",
        "",
        f"- Overall: **{overall}**",
        f"- PR: #{metadata['number']} ({markdown_code(metadata.get('url', 'unknown URL'))})",
        f"- Repository: {markdown_code(metadata['repository'])}",
        f"- Base: {markdown_code(base_sha)}",
        f"- Head: {markdown_code(head_sha)}",
        f"- Generated: {datetime.now(timezone.utc).isoformat()}",
        "",
        "## Provenance",
        "",
    ]
    for key in (
        "run_id",
        "capsule_revision",
        "role",
        "workflow",
        "gate",
        "environment",
        "validation",
        "contract_sources",
        "next_owner",
    ):
        value = provenance.get(key)
        if value:
            label = key.replace("_", " ").title()
            lines.append(f"- {label}: {markdown_code(value)}")
    lines.extend(
        [
            "",
            "## Evidence files",
            "",
            "- `diff.patch` — raw diff; inspect the complete diff before narrowing to affected paths.",
            "- `diff-stat.txt` — compact change-size summary.",
            "- `changed-files.txt` — review scope.",
            "- `commits.txt` — commit subjects.",
            "- `checks.json` and `*.log` — machine-readable statuses and bounded output.",
            "",
            "## Changed files",
            "",
        ]
    )
    lines.extend(f"- {markdown_code(path)}" for path in changed_files)
    lines.extend(["", "## Contract pointers", ""])
    lines.extend(f"- {markdown_code(source)}" for source in contract_sources)
    lines.extend(
        [
            "",
            "## Mechanical checks",
            "",
            "| Check | Status | Seconds | Log |",
            "| --- | --- | ---: | --- |",
        ]
    )
    for check in checks:
        if check.log:
            log_path = Path(check.log)
            try:
                log_path = log_path.relative_to(report_dir)
            except ValueError:
                pass
            log = markdown_code(log_path)
        else:
            log = "—"
        lines.append(
            f"| {markdown_code(check.name)} | **{markdown_cell(check.status)}** | "
            f"{check.duration_seconds:.3f} | {log} |"
        )
        if check.reason:
            lines.append(f"| reason | {markdown_code(check.reason)} |  |  |")
    lines.extend(
        [
            "",
            "## Manual review boundary",
            "",
            "Interpret contract, inspect diff, judge severity, and write review comments manually.",
            "Capsule does not approve, reject, or infer correctness.",
        ]
    )
    summary_path = report_dir / "summary.md"
    write_text(summary_path, "\n".join(lines), directory_fd)
    return summary_path
