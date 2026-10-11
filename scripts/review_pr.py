#!/usr/bin/env python3
"""Build a compact evidence capsule for one GitHub pull request.

The script automates repository mechanics only. The extracted checkout is not
a security sandbox. It never chooses a review verdict and never mutates GitHub
unless ``--submit`` is supplied explicitly; submission requires complete
passing checks.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import shlex
import shutil
import signal
import subprocess
import sys
import tarfile
import tempfile
import threading
import time
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TIMEOUT = 300
GH_TIMEOUT = 60
MAX_LOG_BYTES = 4 * 1024 * 1024
LOG_TRUNCATION_MARKER = b"\n[output truncated]\n"
CONTRACT_SOURCES = (
    "AGENTS.md",
    "Docs/README.md",
    "Docs/PROJECT_CONTRACT.md",
    "Docs/DECISION_REGISTER.md",
    "Docs/DECISIONS/ADR-001-source-of-truth-hierarchy.md",
    "Docs/DECISIONS/ADR-002-stage-1-schema-renderer.md",
    "Docs/DECISIONS/ADR-003-hard-constraints-and-fallback.md",
    "Docs/DECISIONS/ADR-004-stage-1-runtime.md",
    "Docs/DECISIONS/ADR-005-separate-stage-1-from-finale.md",
    "Docs/DECISIONS/ADR-006-failure-protocol-and-search-status.md",
    "Docs/DECISIONS/ADR-007-numeric-and-geometry-semantics.md",
    "Docs/DECISIONS/ADR-008-typography-and-renderer-edge-semantics.md",
    "Docs/DECISIONS/ADR-009-initial-search-strategy.md",
    "Docs/FINAL_ARCHITECTURE.md",
    "chameleon/chameleon_design_schema_v0.9.json",
    "chameleon/RULES.md",
    "Docs/CHAMELEONCHALLENGE.md",
    "Docs/DEPENDENCY_EVIDENCE.md",
    "Docs/STATUS.md",
    "Docs/IMPLEMENTATION_ROADMAP.md",
    ".agents/README.md",
    ".agents/OPERATING_CONTRACT.md",
    ".agents/PROJECT_PROFILE.md",
    ".agents/TOOLING.md",
    ".agents/policies/authority.md",
    ".agents/policies/evidence.md",
    ".agents/policies/security.md",
    ".agents/roles/reviewer.md",
    ".agents/roles/security-reviewer.md",
    ".agents/workflows/06-review.md",
    ".agents/workflows/07-github-pr.md",
    ".agents/checklists/review.md",
    ".agents/templates/review.md",
    "skills/chameleon-contract/SKILL.md",
    "skills/chameleon-review/SKILL.md",
    "skills/chameleon-testing/SKILL.md",
)


class ReviewError(RuntimeError):
    """Raised when review capsule setup cannot continue safely."""


@dataclass
class CheckResult:
    name: str
    status: str
    duration_seconds: float
    command: list[str]
    returncode: int | None = None
    log: str | None = None
    reason: str | None = None


def terminate_process(process: subprocess.Popen) -> None:
    if process.poll() is not None:
        return
    try:
        if os.name == "posix":
            os.killpg(process.pid, signal.SIGTERM)
        else:
            process.terminate()
        process.wait(timeout=5)
        return
    except (OSError, subprocess.TimeoutExpired):
        pass
    try:
        if os.name == "posix":
            os.killpg(process.pid, signal.SIGKILL)
        else:
            process.kill()
    except OSError:
        pass
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        pass


def run_process(
    command: Sequence[str],
    cwd: Path,
    log_path: Path,
    timeout: int,
    env: Mapping[str, str] | None = None,
) -> CheckResult:
    started = time.monotonic()
    try:
        process = subprocess.Popen(
            list(command),
            cwd=cwd,
            env=dict(env) if env is not None else None,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            start_new_session=os.name == "posix",
        )
    except OSError as error:
        log_path.write_text(f"{type(error).__name__}: {error}\n", encoding="utf-8")
        return CheckResult(
            name=log_path.stem,
            status="FAIL",
            duration_seconds=round(time.monotonic() - started, 3),
            command=list(command),
            reason=str(error),
            log=str(log_path),
        )

    written = 0
    output_truncated = False
    reader_error: OSError | None = None

    with log_path.open("wb") as log:
        def drain_output() -> None:
            nonlocal output_truncated, reader_error, written
            stream = process.stdout
            if stream is None:
                return
            try:
                while True:
                    chunk = stream.read(65536)
                    if not chunk:
                        return
                    remaining = MAX_LOG_BYTES - written
                    if remaining > 0:
                        log.write(chunk[:remaining])
                        written += min(len(chunk), remaining)
                    if len(chunk) > remaining:
                        output_truncated = True
            except OSError as error:
                reader_error = error

        reader = threading.Thread(target=drain_output, daemon=True)
        reader.start()
        timed_out = False
        try:
            returncode = process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            terminate_process(process)
            returncode = process.returncode
        reader.join(timeout=5)
        if reader.is_alive():
            output_truncated = True
            if process.stdout is not None:
                process.stdout.close()
            reader.join(timeout=1)
        if process.stdout is not None:
            process.stdout.close()
        if reader_error is not None:
            log.write(f"\nOutput capture failed: {reader_error}\n".encode())
        if output_truncated:
            log.write(LOG_TRUNCATION_MARKER)

    if timed_out:
        status = "FAIL"
        returncode = None
        reason = f"timeout after {timeout}s"
    else:
        status = "PASS" if returncode == 0 else "FAIL"
        reason = None
    return CheckResult(
        name=log_path.stem,
        status=status,
        duration_seconds=round(time.monotonic() - started, 3),
        command=list(command),
        returncode=returncode,
        log=str(log_path),
        reason=reason,
    )


def skipped(name: str, command: Sequence[str], reason: str) -> CheckResult:
    return CheckResult(
        name=name,
        status="SKIP",
        duration_seconds=0.0,
        command=list(command),
        reason=reason,
    )


def run_check(
    name: str,
    command: Sequence[str],
    cwd: Path,
    report_dir: Path,
    timeout: int,
    env: Mapping[str, str] | None = None,
) -> CheckResult:
    log_path = report_dir / f"{len(list(report_dir.glob('*.log'))):02d}-{name}.log"
    result = run_process(command, cwd, log_path, timeout, env)
    result.name = name
    return result


def run_gh_json(
    command: Sequence[str], cwd: Path = ROOT, timeout: int = GH_TIMEOUT
) -> dict:
    try:
        completed = subprocess.run(
            list(command),
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as error:
        raise ReviewError(f"timed out after {timeout}s: {shlex.join(command)}") from error
    except OSError as error:
        raise ReviewError(f"cannot run {shlex.join(command)}: {error}") from error
    if completed.returncode != 0:
        raise ReviewError(completed.stderr.strip() or shlex.join(command))
    try:
        value = json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        raise ReviewError(f"invalid JSON from {shlex.join(command)}: {error}") from error
    if not isinstance(value, dict):
        raise ReviewError(f"expected object from {shlex.join(command)}")
    return value


def git_output(*args: str, cwd: Path = ROOT, strip: bool = True) -> str:
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
    except OSError as error:
        raise ReviewError(f"cannot run git {shlex.join(args)}: {error}") from error
    if completed.returncode != 0:
        raise ReviewError(completed.stderr.strip() or shlex.join(["git", *args]))
    return completed.stdout.strip() if strip else completed.stdout


def ensure_file(path: Path) -> None:
    if not path.is_file():
        raise SystemExit(f"--body-file must be a file: {path}")


def changed_contract_sources(changed_files: Iterable[str]) -> list[str]:
    changed = set(changed_files)
    sources = list(CONTRACT_SOURCES)
    if any(path.startswith("chameleon/renderer/") for path in changed):
        sources.extend(
            [
                "Docs/PROJECT_CONTRACT.md §6",
                "Docs/DECISIONS/ADR-008-typography-and-renderer-edge-semantics.md",
                "skills/chameleon-review/SKILL.md",
                "skills/chameleon-testing/SKILL.md",
            ]
        )
    if any(path.startswith("chameleon/engine/") for path in changed):
        sources.extend(
            [
                "Docs/PROJECT_CONTRACT.md §8",
                "Docs/DECISIONS/ADR-006-failure-protocol-and-search-status.md",
                "skills/chameleon-contract/SKILL.md",
            ]
        )
    if "chameleon/Dockerfile" in changed or "chameleon/requirements.txt" in changed:
        sources.extend(
            [
                "Docs/PROJECT_CONTRACT.md §9",
                "Docs/DECISIONS/ADR-004-stage-1-runtime.md",
            ]
        )
    return list(dict.fromkeys(sources))

def source_path(source: str) -> str:
    return source.split(" §", 1)[0]


def changed_authority_sources(
    changed_files: Iterable[str],
    sources: Iterable[str] = CONTRACT_SOURCES,
) -> list[str]:
    changed = set(changed_files)
    return sorted({source_path(source) for source in sources if source_path(source) in changed})


def missing_contract_sources(root: Path, sources: Iterable[str]) -> list[str]:
    missing = []
    for source in sources:
        path = source_path(source)
        if not (root / path).is_file():
            missing.append(source)
    return missing


def write_text(path: Path, content: str) -> None:
    if not content.endswith("\n"):
        content += "\n"
    path.write_text(content, encoding="utf-8")


def create_checkout(head_sha: str, checkout: Path) -> None:
    """Extract PR files into an isolated local Git repository."""
    if checkout.exists():
        raise ReviewError(f"checkout path already exists: {checkout}")
    checkout.mkdir(parents=True)
    archive_path = checkout.parent / "source.tar"
    try:
        try:
            with archive_path.open("wb") as archive_file:
                subprocess.run(
                    ["git", "archive", "--format=tar", head_sha],
                    cwd=ROOT,
                    stdout=archive_file,
                    stderr=subprocess.PIPE,
                    check=True,
                )
            with tarfile.open(archive_path, mode="r") as archive:
                for member in archive.getmembers():
                    if member.issym() or member.islnk():
                        raise ReviewError(f"refusing link in PR archive: {member.name}")
                    target = (checkout / member.name).resolve()
                    if target != checkout and checkout not in target.parents:
                        raise ReviewError(f"unsafe archive path: {member.name}")
                    archive.extract(member, checkout)
        except subprocess.CalledProcessError as error:
            raise ReviewError(f"cannot archive PR head {head_sha}: {error}") from error
        finally:
            archive_path.unlink(missing_ok=True)
        subprocess.run(
            ["git", "init", "--quiet"],
            cwd=checkout,
            env={"GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull},
            check=True,
        )
    except BaseException:
        shutil.rmtree(checkout, ignore_errors=True)
        raise


def isolated_environment(report_dir: Path) -> dict[str, str]:
    sandbox_home = report_dir / "sandbox-home"
    sandbox_tmp = report_dir / "sandbox-tmp"
    sandbox_config = report_dir / "sandbox-config"
    sandbox_home.mkdir(parents=True, exist_ok=True)
    sandbox_tmp.mkdir(parents=True, exist_ok=True)
    sandbox_config.mkdir(parents=True, exist_ok=True)
    path_parts = {"/usr/bin", "/bin", "/usr/sbin", "/sbin", str(Path(sys.executable).parent)}
    for command in ("git", "make", "docker"):
        resolved = shutil.which(command)
        if resolved:
            path_parts.add(str(Path(resolved).parent))
    environment = {
        "PATH": os.pathsep.join(sorted(path_parts)),
        "HOME": str(sandbox_home),
        "TMPDIR": str(sandbox_tmp),
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_TERMINAL_PROMPT": "0",
        "GH_PROMPT_DISABLED": "1",
        "GH_CONFIG_DIR": str(sandbox_config),
        "DOCKER_CONFIG": str(sandbox_config),
        "PYTHONNOUSERSITE": "1",
    }
    for name in ("LANG", "LC_ALL", "TERM", "CI", "NO_COLOR"):
        if name in os.environ:
            environment[name] = os.environ[name]
    return environment


def make_command(target: str, python_path: Path | None) -> list[str]:
    command = ["make"]
    if python_path is not None:
        venv = python_path.parent.parent
        command.extend(
            [
                f"VENV_DIR={venv}",
                f"PYTHON={python_path}",
                f"PIP={venv / 'bin' / 'pip'}",
            ]
        )
    command.append(target)
    return command
def markdown_cell(value: object) -> str:
    return (
        str(value)
        .replace("\\", "\\\\")
        .replace("|", "\\|")
        .replace("\r", "\\r")
        .replace("\n", "\\n")
    )


def markdown_code(value: object) -> str:
    escaped = markdown_cell(value).replace("`", "\\`")
    return f"`{escaped}`"


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


def checkout_python(checkout: Path) -> Path | None:
    candidate = checkout / ".venv" / "bin" / "python"
    return candidate if candidate.is_file() else None

def make_summary(
    report_dir: Path,
    metadata: dict,
    base_sha: str,
    head_sha: str,
    changed_files: list[str],
    checks: list[CheckResult],
    contract_sources: list[str],
    provenance: Mapping[str, str] | None = None,
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
            "- `diff.patch` — raw diff; inspect affected paths only.",
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
            lines.append(f"| reason | {markdown_cell(check.reason)} |  |  |")
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
    write_text(summary_path, "\n".join(lines))
    return summary_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pr", type=int, required=True, help="GitHub pull-request number")
    parser.add_argument("--repo", help="GitHub repository in OWNER/REPO form")
    parser.add_argument(
        "--report-dir",
        type=Path,
        help="Directory for the capsule; defaults to a temporary directory",
    )
    parser.add_argument(
        "--run-checks",
        action="store_true",
        help="Execute PR-controlled checks in an extracted checkout; this is not a sandbox",
    )
    parser.add_argument(
        "--submit",
        choices=("none", "comment", "request-changes"),
        default="none",
        help="Explicitly submit a GitHub review after checks",
    )
    parser.add_argument("--body-file", type=Path, help="Review body used with --submit")
    parser.add_argument(
        "--docker",
        action="store_true",
        help="Run Docker build and offline container checks when available",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT,
        help=f"Per-check timeout in seconds (default: {DEFAULT_TIMEOUT})",
    )
    args = parser.parse_args()
    if args.timeout < 1:
        parser.error("--timeout must be positive")
    if args.submit != "none" and args.body_file is None:
        parser.error("--body-file is required with --submit")
    if args.submit != "none" and not args.run_checks:
        parser.error("--submit requires --run-checks")
    if args.docker and not args.run_checks:
        parser.error("--docker requires --run-checks")
    return args


def resolve_repository(repo: str | None) -> str:
    if repo:
        return repo
    command = [
        "gh",
        "repo",
        "view",
        "--json",
        "name,owner",
        "--jq",
        ".owner.login + \"/\" + .name",
    ]
    environment = os.environ.copy()
    environment["GH_PROMPT_DISABLED"] = "1"
    try:
        completed = subprocess.run(
            command,
            cwd=ROOT,
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=GH_TIMEOUT,
            check=False,
        )
    except subprocess.TimeoutExpired as error:
        raise ReviewError(f"timed out after {GH_TIMEOUT}s: {shlex.join(command)}") from error
    except OSError as error:
        raise ReviewError(f"cannot run {shlex.join(command)}: {error}") from error
    if completed.returncode != 0 or not completed.stdout.strip():
        raise ReviewError(completed.stderr.strip() or "cannot resolve GitHub repository")
    return completed.stdout.strip()


def fetch_pr_refs(
    pr: int,
    base_ref_name: str,
    repository: str,
    namespace: str | None = None,
) -> tuple[str, str]:
    remote_url = f"https://github.com/{repository}.git"
    namespace = namespace or f"pr-{pr}-{uuid.uuid4().hex}"
    head_ref = f"refs/review-capsule/{namespace}/head"
    base_ref = f"refs/review-capsule/{namespace}/base"
    commands = (
        [
            "git",
            "fetch",
            "--no-tags",
            remote_url,
            f"+refs/pull/{pr}/head:{head_ref}",
        ],
        [
            "git",
            "fetch",
            "--no-tags",
            remote_url,
            f"+refs/heads/{base_ref_name}:{base_ref}",
        ],
    )
    environment = os.environ.copy()
    environment["GIT_TERMINAL_PROMPT"] = "0"
    try:
        for command in commands:
            try:
                completed = subprocess.run(
                    command,
                    cwd=ROOT,
                    env=environment,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=GH_TIMEOUT,
                    check=False,
                )
            except subprocess.TimeoutExpired as error:
                raise ReviewError(
                    f"timed out after {GH_TIMEOUT}s: {shlex.join(command)}"
                ) from error
            except OSError as error:
                raise ReviewError(
                    f"cannot run {shlex.join(command)}: {error}"
                ) from error
            if completed.returncode != 0:
                raise ReviewError(completed.stderr.strip() or shlex.join(command))
    except ReviewError:
        delete_review_refs((head_ref, base_ref))
        raise
    return head_ref, base_ref


def delete_review_refs(refs: Iterable[str]) -> None:
    for ref in refs:
        try:
            git_output("update-ref", "-d", ref)
        except ReviewError:
            continue


def submit_review(
    pr: int,
    repo: str,
    mode: str,
    body_file: Path,
    report_dir: Path,
    timeout: int,
) -> CheckResult:
    flag = "--request-changes" if mode == "request-changes" else "--comment"
    command = [
        "gh",
        "pr",
        "review",
        str(pr),
        "--repo",
        repo,
        flag,
        "--body-file",
        str(body_file),
    ]
    expected = "CHANGES_REQUESTED" if mode == "request-changes" else None
    result = run_check("submit-review", command, ROOT, report_dir, timeout)
    if result.status != "PASS":
        if result.reason and "timeout" in result.reason.lower():
            result.reason = (
                f"{result.reason}; submission outcome indeterminate; "
                "inspect GitHub before retrying"
            )
        else:
            result.reason = (
                f"{result.reason or 'submission failed'}; "
                "submission not confirmed; inspect GitHub before retrying"
            )
        return result

    try:
        verification = run_gh_json(
            ["gh", "pr", "view", str(pr), "--repo", repo, "--json", "reviewDecision"],
            timeout=timeout,
        )
    except ReviewError as error:
        result.status = "FAIL"
        result.reason = f"review submitted; verification failed: {error}; do not retry"
        return result
    actual = verification.get("reviewDecision")
    if expected and actual != expected:
        result.status = "FAIL"
        result.reason = f"expected reviewDecision={expected}, got {actual!r}"
    return result


def main() -> int:
    args = parse_args()
    body_file = args.body_file.resolve() if args.body_file else None
    if body_file is not None:
        ensure_file(body_file)

    report_dir = args.report_dir.resolve() if args.report_dir else Path(
        tempfile.mkdtemp(prefix=f"chameleon-pr-{args.pr}-")
    )
    report_dir.mkdir(parents=True, exist_ok=True)
    checks: list[CheckResult] = []
    checkout = report_dir / "checkout"
    checkout_created = False
    review_refs: tuple[str, ...] = ()
    metadata: dict

    try:
        repository = resolve_repository(args.repo)
        metadata = run_gh_json(
            [
                "gh",
                "pr",
                "view",
                str(args.pr),
                "--repo",
                repository,
                "--json",
                "baseRefName,baseRefOid,headRefOid,state,url",
            ]
        )
        metadata["number"] = args.pr
        metadata["repository"] = repository
        base_sha = str(metadata["baseRefOid"])
        head_sha = str(metadata["headRefOid"])
        head_ref, base_ref = fetch_pr_refs(args.pr, str(metadata["baseRefName"]), repository)
        review_refs = (head_ref, base_ref)
        if git_output("rev-parse", head_ref) != head_sha:
            raise ReviewError("fetched PR head does not match GitHub head SHA")
        if git_output("rev-parse", base_ref) != base_sha:
            raise ReviewError("fetched PR base does not match GitHub base SHA")

        diff_range = f"{base_sha}...{head_sha}"
        write_text(
            report_dir / "diff.patch",
            git_output("diff", "--no-ext-diff", diff_range, strip=False),
        )
        write_text(report_dir / "diff-stat.txt", git_output("diff", "--stat", diff_range))
        write_text(report_dir / "changed-files.txt", git_output("diff", "--name-only", diff_range))
        write_text(report_dir / "commits.txt", git_output("log", "--oneline", f"{base_sha}..{head_sha}"))
        changed_files = [
            line
            for line in (report_dir / "changed-files.txt").read_text(encoding="utf-8").splitlines()
            if line
        ]
        contract_sources = changed_contract_sources(changed_files)
        capsule_revision = git_output("rev-parse", "HEAD")
        create_checkout(head_sha, checkout)
        checkout_created = True
        missing_sources = missing_contract_sources(checkout, contract_sources)
        changed_sources = changed_authority_sources(changed_files, contract_sources)
        contract_issues = []
        if missing_sources:
            contract_issues.append(
                "missing from PR checkout: " + ", ".join(missing_sources)
            )
        if changed_sources:
            contract_issues.append(
                "changed in PR; compare with trusted base: "
                + ", ".join(changed_sources)
            )
        if contract_issues:
            checks.append(
                skipped(
                    "contract-sources",
                    ["canonical-contract-sources"],
                    "; ".join(contract_issues),
                )
            )
        else:
            checks.append(
                CheckResult(
                    "contract-sources",
                    "PASS",
                    0.0,
                    ["canonical-contract-sources"],
                    returncode=0,
                )
            )

        if not args.run_checks:
            reason = "not requested; PR code execution is disabled by default"
            checks.append(
                run_check("diff-check", ["git", "diff", "--check", diff_range], ROOT, report_dir, args.timeout)
            )
            checks.extend(
                [
                    skipped("verify", ["make", "verify"], reason),
                    skipped("test", ["make", "test"], reason),
                    skipped("run", ["make", "run"], reason),
                    skipped("inspect", ["make", "inspect"], reason),
                ]
            )
        else:
            check_env = isolated_environment(report_dir)
            checks.append(
                run_check("diff-check", ["git", "diff", "--check", diff_range], ROOT, report_dir, args.timeout)
            )
            checks.append(run_check("verify", ["make", "verify"], checkout, report_dir, args.timeout, check_env))
            engine_available = (checkout / "chameleon" / "engine").is_dir()
            python_path = checkout_python(checkout)
            if not engine_available or python_path is None:
                missing_runtime = []
                if not engine_available:
                    missing_runtime.append("nested engine unavailable")
                if python_path is None:
                    missing_runtime.append(
                        "PR checkout has no pre-provisioned .venv; host environments are not used"
                    )
                reason = "; ".join(missing_runtime)
                checks.extend(
                    [
                        skipped("test", make_command("test", python_path), reason),
                        skipped("run", make_command("run", python_path), reason),
                        skipped("inspect", make_command("inspect", python_path), reason),
                    ]
                )
            else:
                checks.append(run_check("test", make_command("test", python_path), checkout, report_dir, args.timeout, check_env))
                run_result = run_check("run", make_command("run", python_path), checkout, report_dir, args.timeout, check_env)
                checks.append(run_result)
                if run_result.status == "PASS":
                    checks.append(run_check("inspect", make_command("inspect", python_path), checkout, report_dir, args.timeout, check_env))
                else:
                    checks.append(skipped("inspect", make_command("inspect", python_path), "sample render failed"))

            if args.docker:
                if shutil.which("docker") is None:
                    checks.extend(
                        [
                            skipped("docker-build", ["make", "docker-build"], "docker executable unavailable"),
                            skipped("docker-test", ["make", "docker-test"], "docker executable unavailable"),
                        ]
                    )
                elif not engine_available:
                    reason = "nested engine unavailable"
                    checks.extend(
                        [
                            skipped("docker-build", ["make", "docker-build"], reason),
                            skipped("docker-test", ["make", "docker-test"], reason),
                        ]
                    )
                else:
                    docker_build = run_check("docker-build", ["make", "docker-build"], checkout, report_dir, args.timeout, check_env)
                    checks.append(docker_build)
                    if docker_build.status == "PASS":
                        checks.append(run_check("docker-test", ["make", "docker-test"], checkout, report_dir, args.timeout, check_env))
                    else:
                        checks.append(skipped("docker-test", ["make", "docker-test"], "docker build failed"))

        if args.submit != "none":
            blocker = submission_blocker(checks)
            if blocker:
                checks.append(
                    skipped(
                        "submit-review",
                        ["gh", "pr", "review", str(args.pr)],
                        blocker,
                    )
                )
            else:
                checks.append(
                    submit_review(
                        args.pr,
                        repository,
                        args.submit,
                        body_file,
                        report_dir,
                        args.timeout,
                    )
                )

        provenance = {
            "run_id": report_dir.name,
            "capsule_revision": capsule_revision,
            "role": ".agents/roles/reviewer.md",
            "workflow": ".agents/workflows/06-review.md; .agents/workflows/07-github-pr.md",
            "gate": "Gate 1: renderer and validator qualification before solver",
            "environment": f"{platform.python_implementation()} {platform.python_version()} on {platform.platform()}",
            "validation": (
                "PR-controlled checks requested; inspect statuses; execution is not sandboxed"
                if args.run_checks
                else "PR code execution disabled by default"
            ),
            "contract_sources": (
                "complete" if not contract_issues else "incomplete"
            ),
            "next_owner": next_owner(checks, args.submit),
        }
        write_text(
            report_dir / "checks.json",
            json.dumps([asdict(check) for check in checks], indent=2),
        )
        summary_path = make_summary(
            report_dir,
            metadata,
            base_sha,
            head_sha,
            changed_files,
            checks,
            contract_sources,
            provenance,
        )
        print(f"report: {summary_path}")
        for check in checks:
            print(f"{check.status:4} {check.name}")
        if any(check.status == "FAIL" for check in checks):
            return 1
        if any(check.status == "SKIP" for check in checks):
            return 2
        return 0
    except (ReviewError, OSError, subprocess.CalledProcessError) as error:
        write_text(report_dir / "error.txt", str(error))
        print(f"error: {error}", file=sys.stderr)
        print(f"report: {report_dir}", file=sys.stderr)
        return 2
    finally:
        delete_review_refs(review_refs)
        if checkout_created:
            shutil.rmtree(checkout, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
