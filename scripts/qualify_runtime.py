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
import time
from pathlib import Path
from typing import Sequence


def _max_rss_unit() -> str:
    return "bytes" if sys.platform == "darwin" else "KiB"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    return parser


def _run(command: Sequence[str], report_path: Path) -> int:
    before = resource.getrusage(resource.RUSAGE_CHILDREN)
    started = time.perf_counter()
    completed = subprocess.run(command, check=False)
    elapsed = time.perf_counter() - started
    after = resource.getrusage(resource.RUSAGE_CHILDREN)

    report = {
        "command": list(command),
        "returncode": completed.returncode,
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
        "platform": {
            "machine": platform.machine(),
            "python": platform.python_version(),
            "system": platform.platform(),
        },
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return completed.returncode


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
