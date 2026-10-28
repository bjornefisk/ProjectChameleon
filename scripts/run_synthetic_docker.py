#!/usr/bin/env python3
"""Run and hard-validate the 18 production-image synthetic cases offline."""

from __future__ import annotations

import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
CHAMELEON_DIR = REPO_ROOT / "chameleon"
IMAGE = "chameleon-stage1"
EXPECTED_CASES = 18


def docker_value(*args: str) -> str:
    result = subprocess.run(
        ["docker", *args], check=True, capture_output=True, text=True
    )
    return result.stdout.strip()


def run() -> int:
    sys.path.insert(0, str(REPO_ROOT))
    from scripts.generate_synthetic_cases import generate_cases

    daemon_arch = docker_value("info", "--format", "{{.Architecture}}")
    image_arch = docker_value(
        "image", "inspect", "--format", "{{.Os}}/{{.Architecture}}", IMAGE
    )
    print(f"Docker daemon architecture: {daemon_arch}")
    print(f"Image architecture: {image_arch}")
    if image_arch != "linux/amd64":
        raise RuntimeError(f"expected {IMAGE} to be linux/amd64, got {image_arch}")

    workspace = Path(tempfile.mkdtemp(prefix="chameleon-synthetic-docker-"))
    input_dir = workspace / "input"
    output_dir = workspace / "output"
    output_dir.mkdir()
    cases = generate_cases(CHAMELEON_DIR / "input", input_dir)
    if len(cases) != EXPECTED_CASES:
        raise RuntimeError(f"expected {EXPECTED_CASES} generated cases, got {len(cases)}")

    command = [
        "docker", "run", "--rm", "--network", "none", "--platform", "linux/amd64",
        "-v", f"{input_dir}:/app/input:ro",
        "-v", f"{output_dir}:/app/output",
        IMAGE,
    ]
    total_started = time.monotonic()
    result = subprocess.run(command, capture_output=True, text=True)
    engine_elapsed = time.monotonic() - total_started
    print(f"Engine container wall time: {engine_elapsed:.3f}s")
    print(f"Engine Docker command: {' '.join(command)}")
    if result.stdout:
        print("Engine container stdout:")
        print(result.stdout, end="" if result.stdout.endswith("\n") else "\n")
    print("Engine container stderr (warnings/errors):")
    print(result.stderr if result.stderr else "(none)")

    audit_code = """\
import json
import sys
from decimal import Decimal
from pathlib import Path
from engine.contract import validate_response

input_dir = Path("/app/input")
output_dir = Path("/app/output")
tasks = {p.stem: p for p in input_dir.glob("*.json")}
json_paths = set(output_dir.glob("*_output.json"))
png_stems = {p.name.removesuffix("_output.png") for p in output_dir.glob("*_output.png")}
marker_stems = {p.name.removeprefix(".").removesuffix("_output.commit") for p in output_dir.glob(".*_output.commit")}
json_stems = {p.name.removesuffix("_output.json") for p in json_paths}
pairs = json_stems & png_stems & marker_stems
validated = 0
errors = []
for stem in sorted(json_stems & tasks.keys()):
    try:
        task = json.loads(tasks[stem].read_text(), parse_float=Decimal)
        response = json.loads((output_dir / f"{stem}_output.json").read_text(), parse_float=Decimal)
        validate_response(task["source"], task["target_canvas"], response)
        validated += 1
    except Exception as error:
        errors.append(f"{stem}: {error}")
print(f"AUDIT_PAIRS={len(pairs)}")
print(f"AUDIT_VALIDATED={validated}")
for error in errors:
    print(f"validation error: {error}", file=sys.stderr)
if set(tasks) != json_stems or set(tasks) != png_stems or set(tasks) != marker_stems or len(pairs) != 18 or validated != 18 or errors:
    raise SystemExit(1)
"""
    audit_command = [
        "docker", "run", "--rm", "--network", "none", "--platform", "linux/amd64",
        "-v", f"{input_dir}:/app/input:ro",
        "-v", f"{output_dir}:/app/output:ro",
        "--entrypoint", "python", IMAGE, "-c", audit_code,
    ]
    audit_started = time.monotonic()
    audit = subprocess.run(audit_command, capture_output=True, text=True)
    audit_elapsed = time.monotonic() - audit_started
    total_elapsed = time.monotonic() - total_started
    print(f"In-image audit wall time: {audit_elapsed:.3f}s")
    print(f"Audit Docker command: {' '.join(audit_command)}")
    if audit.stdout:
        print("In-image audit stdout:")
        print(audit.stdout, end="" if audit.stdout.endswith("\n") else "\n")
    print("In-image audit stderr (warnings/errors):")
    print(audit.stderr if audit.stderr else "(none)")
    print(f"Total container wall time: {total_elapsed:.3f}s")
    statuses = re.findall(
        r"\bstatus=([A-Z_]+)\b", result.stdout + "\n" + result.stderr
    )
    status_counts = {status: statuses.count(status) for status in sorted(set(statuses))}
    expected_stems = {case.stem for case in cases}
    json_paths = set(output_dir.glob("*_output.json"))
    png_paths = set(output_dir.glob("*_output.png"))
    marker_paths = set(output_dir.glob(".*_output.commit"))
    json_stems = {path.name.removesuffix("_output.json") for path in json_paths}
    png_stems = {path.name.removesuffix("_output.png") for path in png_paths}
    marker_stems = {
        path.name.removeprefix(".").removesuffix("_output.commit")
        for path in marker_paths
    }
    committed_stems = json_stems & png_stems & marker_stems
    audit_values = dict(
        re.findall(r"^AUDIT_(PAIRS|VALIDATED)=(\d+)$", audit.stdout, re.MULTILINE)
    )
    validated = int(audit_values.get("VALIDATED", "0"))
    audited_pairs = int(audit_values.get("PAIRS", "0"))

    successes = status_counts.get("SUCCESS", 0)
    print(f"Task statuses: {successes}/{EXPECTED_CASES} SUCCESS ({status_counts})")
    print(
        f"Committed JSON/PNG pairs: {len(committed_stems)}/{EXPECTED_CASES} "
        f"({len(json_paths)} JSON, {len(png_paths)} PNG, {len(marker_paths)} markers)"
    )
    print(f"In-image committed pairs: {audited_pairs}/{EXPECTED_CASES}")
    print(f"In-image serialized responses hard-validated: {validated}/{EXPECTED_CASES}")
    print(f"Preserved artifacts: {workspace}")
    problems = []
    if result.returncode != 0:
        problems.append(f"offline engine container exited with status {result.returncode}")
    if audit.returncode != 0:
        problems.append(f"offline validator container exited with status {audit.returncode}")
    if len(statuses) != EXPECTED_CASES or successes != EXPECTED_CASES:
        problems.append(
            f"expected {EXPECTED_CASES}/{EXPECTED_CASES} task SUCCESS statuses; "
            f"observed {successes}/{len(statuses)}"
        )
    if (
        json_stems != expected_stems
        or png_stems != expected_stems
        or marker_stems != expected_stems
        or len(committed_stems) != EXPECTED_CASES
        or audited_pairs != EXPECTED_CASES
    ):
        problems.append(
            f"expected 18 matching JSON/PNG/commit-marker triples; got "
            f"{len(json_paths)} JSON, {len(png_paths)} PNG, "
            f"{len(marker_paths)} markers, {len(committed_stems)} local and "
            f"{audited_pairs} in-image triples"
        )
    if validated != EXPECTED_CASES:
        problems.append(
            f"expected 18 in-image hard-valid serialized responses, validated {validated}"
        )
    if problems:
        raise RuntimeError("; ".join(problems))
    return 0


def main() -> int:
    try:
        return run()
    except Exception as error:
        print(f"synthetic Docker qualification failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
