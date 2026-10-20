#!/usr/bin/env python3
"""Measure one child runtime without imposing unverified resource limits."""

from __future__ import annotations

import argparse
import json
import os
import platform
import resource
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Sequence


_THREAD_SAMPLE_INTERVAL_SECONDS = 0.01


def _max_rss_unit() -> str:
    return "bytes" if sys.platform == "darwin" else "KiB"


def _thread_count(pid: int) -> int | None:
    if sys.platform != "linux":
        return None
    try:
        status = Path(f"/proc/{pid}/status").read_text(encoding="utf-8")
    except (FileNotFoundError, OSError):
        return None
    for line in status.splitlines():
        if not line.startswith("Threads:"):
            continue
        try:
            return int(line.split()[1])
        except (IndexError, ValueError):
            return None
    return None


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    return parser


def _write_report(report_path: Path, report: dict) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    if report_path.is_symlink():
        raise RuntimeError(f"report path must not be a symlink: {report_path}")

    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=report_path.parent,
            prefix=f".{report_path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary_file:
            temporary_path = Path(temporary_file.name)
            json.dump(report, temporary_file, indent=2, sort_keys=True)
            temporary_file.write("\n")
            temporary_file.flush()
            os.fsync(temporary_file.fileno())
        os.replace(temporary_path, report_path)
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def _run(command: Sequence[str], report_path: Path) -> int:
    before = resource.getrusage(resource.RUSAGE_CHILDREN)
    started = time.perf_counter()
    child = subprocess.Popen(command)
    peak_threads: int | None = None
    while True:
        observed_threads = _thread_count(child.pid)
        if observed_threads is not None:
            peak_threads = (
                observed_threads
                if peak_threads is None
                else max(peak_threads, observed_threads)
            )
        if child.poll() is not None:
            break
        time.sleep(_THREAD_SAMPLE_INTERVAL_SECONDS)
    returncode = child.wait()
    elapsed = time.perf_counter() - started
    after = resource.getrusage(resource.RUSAGE_CHILDREN)

    report = {
        "command": list(command),
        "returncode": returncode,
        "elapsed_seconds": elapsed,
        "cpu_seconds": {
            "user": after.ru_utime - before.ru_utime,
            "system": after.ru_stime - before.ru_stime,
        },
        "max_rss": {
            "value": after.ru_maxrss,
            "unit": _max_rss_unit(),
        },
        "available_cpu_count": os.cpu_count(),
        "thread_count": {
            "peak": peak_threads,
            "source": "procfs" if peak_threads is not None else None,
            "unit": "threads",
        },
        "platform": {
            "machine": platform.machine(),
            "python": platform.python_version(),
            "system": platform.platform(),
        },
    }
    _write_report(report_path, report)
    return returncode


def main() -> int:
    args = _parser().parse_args()
    command = list(args.command)
    if command[:1] == ["--"]:
        command = command[1:]
    if not command:
        _parser().error("a child command is required after --")
    return _run(command, args.report)


if __name__ == "__main__":
    raise SystemExit(main())
