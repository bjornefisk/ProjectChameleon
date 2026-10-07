#!/usr/bin/env python3
"""Verify repository-level Chameleon governance and implementation wiring."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REQUIRED_ROOT_FILES = (
    "AGENTS.md",
    "Makefile",
    "Docs/PROJECT_CONTRACT.md",
    "Docs/STATUS.md",
    "Docs/IMPLEMENTATION/README.md",
    "Docs/IMPLEMENTATION/SPEC.md",
)
REQUIRED_SKILLS = (
    "skills/chameleon-contract/SKILL.md",
    "skills/chameleon-testing/SKILL.md",
    "skills/chameleon-review/SKILL.md",
)
REQUIRED_TICKETS = tuple(
    f"Docs/IMPLEMENTATION/tickets/{number:02d}-{slug}.md"
    for number, slug in (
        (1, "contract-errors-and-validator"),
        (2, "renderer-conformance-and-wrapping"),
        (3, "atomic-runner-and-fail-closed"),
        (4, "exact-geometry-and-group-transforms"),
        (5, "level-1-safe-geometry-solver"),
        (6, "column-pivot-and-level-2-solver"),
        (7, "horizontal-ribbon-and-level-3-solver"),
        (8, "candidate-search-ranking-and-offline-docker"),
    )
)


def run_git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


def check_paths(paths: tuple[str, ...], errors: list[str]) -> None:
    for relative in paths:
        if not (ROOT / relative).exists():
            errors.append(f"missing required file: {relative}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--require-engine",
        action="store_true",
        help="fail when the nested chameleon gitlink is unavailable",
    )
    args = parser.parse_args()

    errors: list[str] = []
    warnings: list[str] = []
    check_paths(REQUIRED_ROOT_FILES + REQUIRED_SKILLS + REQUIRED_TICKETS, errors)

    engine_path = ROOT / "chameleon"
    if not engine_path.is_dir():
        message = (
            "nested engine directory is unavailable; initialize the chameleon "
            "gitlink before running software tests"
        )
        (errors if args.require_engine else warnings).append(message)
    elif not any(engine_path.iterdir()):
        message = (
            "nested engine directory is empty; restore gitlink commit "
            "af48d3f5e5420d0cc3d3eb4c39ff9a773616a432 before running software tests"
        )
        (errors if args.require_engine else warnings).append(message)

    try:
        status = run_git("status", "--porcelain")
    except subprocess.CalledProcessError as exc:
        errors.append(f"unable to inspect git status: {exc}")
    else:
        generated = (
            line
            for line in status.splitlines()
            if "chameleon/output/" in line or "__pycache__" in line or ".pyc" in line
        )
        errors.extend(f"generated artifact is tracked or pending: {line}" for line in generated)

    for warning in warnings:
        print(f"WARNING: {warning}")
    for error in errors:
        print(f"ERROR: {error}", file=sys.stderr)

    if errors:
        return 1
    print("Repository governance and implementation wiring are consistent.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
