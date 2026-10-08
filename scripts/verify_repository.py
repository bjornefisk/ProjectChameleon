#!/usr/bin/env python3
"""Verify repository-level Chameleon governance and implementation wiring."""

from __future__ import annotations

import argparse
import re
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
REQUIRED_AGENT_FILES = (
    ".agents/README.md",
    ".agents/OPERATING_CONTRACT.md",
    ".agents/PROJECT_PROFILE.md",
    ".agents/PRODUCTION_STANDARD.md",
    ".agents/TOOLING.md",
    ".agents/tool-policy.yml",
    ".agents/roles/README.md",
    ".agents/roles/lead-orchestrator.md",
    ".agents/roles/researcher.md",
    ".agents/workflows/00-intake.md",
    ".agents/workflows/01-research.md",
    ".agents/workflows/03-implement.md",
    ".agents/workflows/05-verify.md",
    ".agents/workflows/12-incident-response.md",
    ".agents/research/web-search.md",
    ".agents/research/prompt-lineage.md",
    ".agents/policies/README.md",
    ".agents/checklists/web-research.md",
    ".agents/templates/task-brief.md",
    ".agents/templates/agent-run.md",
    ".agents/templates/handoff.md",
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



ROLE_HEADINGS = (
    "## Mission",
    "## Authority",
    "## Required inputs",
    "## Allowed tools",
    "## Quality gates",
    "## Failure and stop behavior",
    "## Security",
    "## Evidence and handoff",
)
MARKDOWN_LINK = re.compile(r"\[[^\]]*\]\(([^)]+)\)")


def check_agent_contract(errors: list[str]) -> None:
    agent_root = ROOT / ".agents"
    role_files = sorted(path for path in (agent_root / "roles").glob("*.md") if path.name != "README.md")
    for path in role_files:
        text = path.read_text(encoding="utf-8")
        missing = [heading for heading in ROLE_HEADINGS if heading not in text]
        if missing:
            errors.append(
                f"incomplete role contract {path.relative_to(ROOT)}: {', '.join(missing)}"
            )

    researcher = agent_root / "roles" / "researcher.md"
    if researcher.exists() and "web_search: required" not in researcher.read_text(encoding="utf-8"):
        errors.append("researcher role must require web_search")

    for path in sorted(agent_root.rglob("*.md")):
        text = path.read_text(encoding="utf-8")
        for raw_target in MARKDOWN_LINK.findall(text):
            target = raw_target.strip().split()[0].strip("<>")
            if target.startswith(("http://", "https://", "mailto:", "#")):
                continue
            target = target.split("#", 1)[0]
            if target and not (path.parent / target).resolve().exists():
                errors.append(
                    f"broken .agents link {path.relative_to(ROOT)} -> {target}"
                )

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
    check_paths(
        REQUIRED_ROOT_FILES
        + REQUIRED_AGENT_FILES
        + REQUIRED_SKILLS
        + REQUIRED_TICKETS,
        errors,
    )
    check_agent_contract(errors)

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
