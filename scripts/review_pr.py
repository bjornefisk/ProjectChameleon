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
import subprocess
import sys
import tarfile
import tempfile
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping, Sequence

try:
    from .review_pr_process import execute_process
except ImportError:
    from review_pr_process import execute_process

try:
    from .review_pr_evidence import (
        CheckResult,
        create_staging_directory,
        publish_staging_directory,
        cleanup_evidence_files,
        evidence_directory_entries,
        flush_check_logs,
        incomplete_checks,
        make_summary,
        markdown_cell,
        markdown_code,
        next_owner,
        open_evidence_directory,
        serialize_check,
        submission_blocker,
        verify_evidence_directory,
        write_evidence_bytes,
        write_text,
    )
except ImportError:
    from review_pr_evidence import (
        CheckResult,
        create_staging_directory,
        publish_staging_directory,
        cleanup_evidence_files,
        evidence_directory_entries,
        flush_check_logs,
        incomplete_checks,
        make_summary,
        markdown_cell,
        markdown_code,
        next_owner,
        open_evidence_directory,
        serialize_check,
        submission_blocker,
        verify_evidence_directory,
        write_evidence_bytes,
        write_text,
    )


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TIMEOUT = 300
GH_TIMEOUT = 60
COMMAND_TIMEOUT = 60
MAX_COMMAND_OUTPUT_BYTES = 16 * 1024 * 1024
MAX_DIFF_BYTES = 64 * 1024 * 1024
MAX_ARCHIVE_BYTES = 256 * 1024 * 1024
MAX_ARCHIVE_MEMBERS = 100_000
MAX_ARCHIVE_MEMBER_BYTES = 128 * 1024 * 1024
MAX_EXTRACTED_BYTES = 512 * 1024 * 1024
MAX_BODY_BYTES = 1 * 1024 * 1024
MAX_LOG_BYTES = 4 * 1024 * 1024
LOG_TRUNCATION_MARKER = b"\n[output truncated]\n"
EVIDENCE_FILE_NAMES = frozenset(
    {
        "diff.patch",
        "diff-stat.txt",
        "changed-files.txt",
        "commits.txt",
        "checks.json",
        "summary.md",
        "error.txt",
    }
)
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
    ".agents/policies/artifacts.md",
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



@dataclass(frozen=True)
class CommandResult:
    returncode: int | None
    stdout: bytes
    stderr: bytes
    timed_out: bool = False
    output_limited: bool = False


def run_bounded_command(
    command: Sequence[str],
    cwd: Path,
    timeout: int,
    max_output_bytes: int = MAX_COMMAND_OUTPUT_BYTES,
    env: Mapping[str, str] | None = None,
    stdout_path: Path | None = None,
) -> CommandResult:
    """Run a command with bounded output, timeout, and process cleanup."""
    try:
        result = execute_process(
            command,
            cwd,
            timeout,
            max_output_bytes,
            env=env,
            stdout_path=stdout_path,
            terminate_on_output_limit=True,
        )
    except OSError as error:
        raise ReviewError(f"cannot run {shlex.join(command)}: {error}") from error
    if result.reader_error and not result.timed_out and not result.output_limited:
        raise ReviewError(f"command output capture failed: {result.reader_error}")
    return CommandResult(
        returncode=result.returncode,
        stdout=result.stdout,
        stderr=result.stderr,
        timed_out=result.timed_out,
        output_limited=result.output_limited,
    )


def require_command_success(
    command: Sequence[str],
    result: CommandResult,
    timeout: int,
    max_output_bytes: int,
) -> CommandResult:
    if result.timed_out:
        raise ReviewError(f"timed out after {timeout}s: {shlex.join(command)}")
    if result.output_limited:
        raise ReviewError(
            f"output exceeded {max_output_bytes} bytes: {shlex.join(command)}"
        )
    if result.returncode != 0:
        error = result.stderr.decode("utf-8", errors="replace").strip()
        raise ReviewError(error or shlex.join(command))
    return result


def decode_output(value: bytes) -> str:
    return value.decode("utf-8", errors="replace")


def run_process(
    command: Sequence[str],
    cwd: Path,
    log_path: Path,
    timeout: int,
    env: Mapping[str, str] | None = None,
    defer_log: bool = False,
    input_bytes: bytes | None = None,
) -> CheckResult:
    started = time.monotonic()
    try:
        result = execute_process(
            command,
            cwd,
            timeout,
            MAX_LOG_BYTES,
            env=env,
            stdin_bytes=input_bytes,
            merge_stderr=True,
            terminate_on_output_limit=False,
        )
    except OSError as error:
        content = f"{type(error).__name__}: {error}\n".encode()
        if not defer_log:
            log_path.write_bytes(content)
        return CheckResult(
            name=log_path.stem,
            status="FAIL",
            duration_seconds=round(time.monotonic() - started, 3),
            command=list(command),
            reason=str(error),
            log=str(log_path),
            output=content if defer_log else None,
        )

    content = result.stdout
    output_truncated = result.output_limited or result.capture_incomplete
    if result.reader_error is not None and not output_truncated:
        content += f"\nOutput capture failed: {result.reader_error}\n".encode()
    if output_truncated:
        content += LOG_TRUNCATION_MARKER
    if not defer_log:
        log_path.write_bytes(content)

    if result.timed_out:
        status = "FAIL"
        returncode = None
        reason = f"timeout after {timeout}s"
    else:
        status = "PASS" if result.returncode == 0 else "FAIL"
        returncode = result.returncode
        reason = None
    return CheckResult(
        name=log_path.stem,
        status=status,
        duration_seconds=round(time.monotonic() - started, 3),
        command=list(command),
        returncode=returncode,
        log=str(log_path),
        reason=reason,
        output=content if defer_log else None,
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
    input_bytes: bytes | None = None,
) -> CheckResult:
    log_path = report_dir / f"{len(list(report_dir.glob('*.log'))):02d}-{name}.log"
    result = run_process(
        command,
        cwd,
        log_path,
        timeout,
        env,
        input_bytes=input_bytes,
        defer_log=True,
    )
    result.name = name
    return result



def run_gh_json(
    command: Sequence[str], cwd: Path | None = None, timeout: int = GH_TIMEOUT
) -> dict:
    cwd = cwd or ROOT
    result = require_command_success(
        command,
        run_bounded_command(
            command,
            cwd,
            timeout,
            max_output_bytes=MAX_COMMAND_OUTPUT_BYTES,
        ),
        timeout,
        MAX_COMMAND_OUTPUT_BYTES,
    )
    try:
        value = json.loads(decode_output(result.stdout))
    except json.JSONDecodeError as error:
        raise ReviewError(f"invalid JSON from {shlex.join(command)}: {error}") from error
    if not isinstance(value, dict):
        raise ReviewError(f"expected object from {shlex.join(command)}")
    return value


def git_output_bytes(
    *args: str,
    cwd: Path | None = None,
    strip: bool = True,
    timeout: int = COMMAND_TIMEOUT,
    max_output_bytes: int = MAX_COMMAND_OUTPUT_BYTES,
) -> bytes:
    cwd = cwd or ROOT
    command = ["git", *args]
    result = require_command_success(
        command,
        run_bounded_command(
            command,
            cwd,
            timeout,
            max_output_bytes=max_output_bytes,
        ),
        timeout,
        max_output_bytes,
    )
    return result.stdout.strip() if strip else result.stdout


def git_output(*args: str, cwd: Path | None = None, strip: bool = True) -> str:
    return decode_output(git_output_bytes(*args, cwd=cwd, strip=strip))


def ensure_file(path: Path) -> None:
    if not path.is_file():
        raise SystemExit(f"--body-file must be a file: {path}")


def snapshot_file(source: Path, max_bytes: int = MAX_BODY_BYTES) -> bytes:
    size = source.stat().st_size
    if size > max_bytes:
        raise ReviewError(f"file exceeds {max_bytes} bytes: {source}")
    content = source.read_bytes()
    if len(content) > max_bytes:
        raise ReviewError(f"file exceeds {max_bytes} bytes: {source}")
    return content


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




def create_checkout(head_sha: str, checkout: Path) -> None:
    """Extract the complete PR tree into an isolated local Git repository."""
    if checkout.exists():
        raise ReviewError(f"checkout path already exists: {checkout}")
    checkout.mkdir(parents=True)
    archive_fd, archive_name = tempfile.mkstemp(
        prefix=".source-",
        suffix=".tar",
        dir=checkout.parent,
    )
    os.close(archive_fd)
    archive_path = Path(archive_name)
    checkout_root = checkout.resolve()
    try:
        expected_paths = {
            os.fsdecode(path)
            for path in git_output_bytes(
                "ls-tree",
                "-r",
                "--name-only",
                "-z",
                head_sha,
                strip=False,
            ).split(b"\0")
            if path
        }
        archive_command = ["git", "archive", "--format=tar", head_sha]
        archive_result = run_bounded_command(
            archive_command,
            ROOT,
            COMMAND_TIMEOUT,
            max_output_bytes=MAX_ARCHIVE_BYTES,
            stdout_path=archive_path,
        )
        require_command_success(
            archive_command,
            archive_result,
            COMMAND_TIMEOUT,
            MAX_ARCHIVE_BYTES,
        )
        if archive_path.stat().st_size > MAX_ARCHIVE_BYTES:
            raise ReviewError(f"archive exceeds {MAX_ARCHIVE_BYTES} bytes")

        with tarfile.open(archive_path, mode="r") as archive:
            members = []
            archive_paths = set()
            extracted_bytes = 0
            for index, member in enumerate(archive, start=1):
                if index > MAX_ARCHIVE_MEMBERS:
                    raise ReviewError(
                        f"archive exceeds {MAX_ARCHIVE_MEMBERS} members"
                    )
                if member.issym() or member.islnk():
                    raise ReviewError(f"refusing link in PR archive: {member.name}")
                if not member.isdir() and not member.isfile():
                    raise ReviewError(f"refusing special file in PR archive: {member.name}")
                target = (checkout_root / member.name).resolve()
                if target != checkout_root and checkout_root not in target.parents:
                    raise ReviewError(f"unsafe archive path: {member.name}")
                if member.isfile():
                    if member.size > MAX_ARCHIVE_MEMBER_BYTES:
                        raise ReviewError(
                            f"archive member exceeds {MAX_ARCHIVE_MEMBER_BYTES} bytes: "
                            f"{member.name}"
                        )
                    extracted_bytes += member.size
                    if extracted_bytes > MAX_EXTRACTED_BYTES:
                        raise ReviewError(
                            f"archive contents exceed {MAX_EXTRACTED_BYTES} bytes"
                        )
                    archive_paths.add(member.name)
                members.append(member)

            if archive_paths != expected_paths:
                missing = sorted(expected_paths - archive_paths)[:5]
                extra = sorted(archive_paths - expected_paths)[:5]
                raise ReviewError(
                    "PR archive manifest mismatch; "
                    f"missing={missing!r}, extra={extra!r}"
                )

            for member in members:
                if sys.version_info >= (3, 12):
                    archive.extract(member, checkout, filter="data")
                else:
                    archive.extract(member, checkout)
    except BaseException:
        shutil.rmtree(checkout, ignore_errors=True)
        raise
    finally:
        archive_path.unlink(missing_ok=True)

    try:
        init_command = ["git", "init", "--quiet"]
        init_result = run_bounded_command(
            init_command,
            checkout,
            COMMAND_TIMEOUT,
            env={"GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull},
        )
        require_command_success(
            init_command,
            init_result,
            COMMAND_TIMEOUT,
            MAX_COMMAND_OUTPUT_BYTES,
        )
    except BaseException:
        shutil.rmtree(checkout, ignore_errors=True)
        raise


def resolve_runner_python(configured: Path | None) -> Path | None:
    candidate = configured if configured is not None else ROOT / ".venv" / "bin" / "python"
    candidate = candidate.expanduser().absolute()
    if candidate.is_file() and os.access(candidate, os.X_OK):
        return candidate
    return None


def isolated_environment(report_dir: Path) -> dict[str, str]:
    sandbox_home = report_dir / "sandbox-home"
    sandbox_tmp = report_dir / "sandbox-tmp"
    sandbox_config = report_dir / "sandbox-config"
    sandbox_home.mkdir(parents=True, exist_ok=True)
    sandbox_tmp.mkdir(parents=True, exist_ok=True)
    sandbox_config.mkdir(parents=True, exist_ok=True)
    path_parts = {"/usr/bin", "/bin", "/usr/sbin", "/sbin"}
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
                f"PYTHON_BOOTSTRAP={python_path}",
            ]
        )
    command.append(target)
    return command


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pr", type=int, required=True, help="GitHub pull-request number")
    parser.add_argument("--repo", help="GitHub repository in OWNER/REPO form")
    parser.add_argument(
        "--report-dir",
        type=Path,
        help="New directory for the capsule; defaults to a temporary directory",
    )
    parser.add_argument(
        "--run-checks",
        action="store_true",
        help="Execute PR-controlled checks in an extracted checkout; this is not a sandbox",
    )
    parser.add_argument(
        "--python-path",
        type=Path,
        help="Trusted pre-provisioned runner interpreter; defaults to ROOT/.venv/bin/python",
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
    result = require_command_success(
        command,
        run_bounded_command(
            command,
            ROOT,
            GH_TIMEOUT,
            max_output_bytes=1024,
            env=environment,
        ),
        GH_TIMEOUT,
        1024,
    )
    repository = decode_output(result.stdout).strip()
    if not repository:
        raise ReviewError("cannot resolve GitHub repository")
    return repository


def fetch_pr_refs(
    pr: int,
    base_ref_name: str,
    repository: str,
    namespace: str | None = None,
    base_sha: str | None = None,
) -> tuple[str, str]:
    remote_url = f"https://github.com/{repository}.git"
    namespace = namespace or f"pr-{pr}-{uuid.uuid4().hex}"
    head_ref = f"refs/review-capsule/{namespace}/head"
    base_ref = f"refs/review-capsule/{namespace}/base"
    base_source = base_sha or f"refs/heads/{base_ref_name}"
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
            f"+{base_source}:{base_ref}",
        ],
    )
    environment = os.environ.copy()
    environment["GIT_TERMINAL_PROMPT"] = "0"
    try:
        for command in commands:
            result = require_command_success(
                command,
                run_bounded_command(
                    command,
                    ROOT,
                    GH_TIMEOUT,
                    max_output_bytes=MAX_COMMAND_OUTPUT_BYTES,
                    env=environment,
                ),
                GH_TIMEOUT,
                MAX_COMMAND_OUTPUT_BYTES,
            )
    except ReviewError as error:
        try:
            delete_review_refs((head_ref, base_ref))
        except ReviewError as cleanup_error:
            raise ReviewError(f"{error}; {cleanup_error}") from error
        raise
    return head_ref, base_ref


def delete_review_refs(refs: Iterable[str]) -> None:
    failures = []
    for ref in refs:
        try:
            git_output("update-ref", "-d", ref)
        except ReviewError as error:
            failures.append(f"{ref}: {error}")
    if failures:
        raise ReviewError("review ref cleanup failed: " + "; ".join(failures))


def review_entries(payload: Mapping[str, object]) -> list[Mapping[str, object]]:
    raw_reviews = payload.get("reviews")
    if not isinstance(raw_reviews, list):
        raise ReviewError("GitHub response did not contain a reviews list")
    reviews = []
    for review in raw_reviews:
        if not isinstance(review, dict):
            raise ReviewError("GitHub response contained a malformed review")
        reviews.append(review)
    return reviews


def review_login(review: Mapping[str, object]) -> str | None:
    author = review.get("author")
    if not isinstance(author, dict):
        return None
    login = author.get("login")
    return str(login) if login is not None else None


def review_id(review: Mapping[str, object]) -> str | None:
    value = review.get("id")
    return str(value) if value is not None else None


def review_body(review: Mapping[str, object]) -> str | None:
    value = review.get("body")
    return str(value).strip() if value is not None else None


def submit_review(
    pr: int,
    repo: str,
    mode: str,
    body_content: bytes,
    report_dir: Path,
    timeout: int,
) -> CheckResult:
    flag = "--request-changes" if mode == "request-changes" else "--comment"
    expected_state = "CHANGES_REQUESTED" if mode == "request-changes" else "COMMENTED"
    command = [
        "gh",
        "pr",
        "review",
        str(pr),
        "--repo",
        repo,
        flag,
        "--body-file",
        "-",
    ]
    try:
        if len(body_content) > MAX_BODY_BYTES:
            raise ReviewError(f"review body exceeds {MAX_BODY_BYTES} bytes")
        expected_body = body_content.decode("utf-8").strip()

        try:
            actor_payload = run_gh_json(["gh", "api", "user"], timeout=timeout)
            actor = actor_payload.get("login")
            if not isinstance(actor, str) or not actor:
                raise ReviewError("authenticated GitHub actor was not returned")
            reviews_command = [
                "gh",
                "pr",
                "view",
                str(pr),
                "--repo",
                repo,
                "--json",
                "reviews",
            ]
            before_reviews = review_entries(
                run_gh_json(reviews_command, timeout=timeout)
            )
            before_ids = {
                identifier
                for review in before_reviews
                if (identifier := review_id(review)) is not None
            }
        except (OSError, ReviewError, UnicodeError) as error:
            return CheckResult(
                name="submit-review",
                status="FAIL",
                duration_seconds=0.0,
                command=command,
                reason=(
                    "pre-submission verification failed: "
                    f"{error}; submission not attempted"
                ),
            )

        result = run_check(
            "submit-review",
            command,
            ROOT,
            report_dir,
            timeout,
            input_bytes=body_content,
        )
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
            after_reviews = review_entries(
                run_gh_json(reviews_command, timeout=timeout)
            )
        except ReviewError as error:
            result.status = "FAIL"
            result.reason = (
                f"review submitted; verification failed: {error}; "
                "inspect GitHub before retrying"
            )
            return result

        matching_review = next(
            (
                review
                for review in after_reviews
                if review_id(review) is not None
                and review_id(review) not in before_ids
                and review_login(review) == actor
                and review.get("state") == expected_state
                and review_body(review) == expected_body
            ),
            None,
        )
        if matching_review is None:
            result.status = "FAIL"
            result.reason = (
                "review submitted; no new matching review was observed "
                f"for actor {actor!r} with state {expected_state!r}; "
                "submission outcome indeterminate; inspect GitHub before retrying"
            )
        return result
    except (OSError, ReviewError, UnicodeError) as error:
        return CheckResult(
            name="submit-review",
            status="FAIL",
            duration_seconds=0.0,
            command=command,
            reason=f"pre-submission verification failed: {error}; submission not attempted",
        )


def main() -> int:
    args = parse_args()
    body_source = args.body_file.resolve() if args.body_file else None
    if body_source is not None:
        ensure_file(body_source)

    run_id = f"pr-{args.pr}-{uuid.uuid4().hex}"
    environment = (
        f"{platform.python_implementation()} {platform.python_version()} "
        f"on {platform.platform()}"
    )
    target_report_dir = args.report_dir.absolute() if args.report_dir else (
        Path(tempfile.mkdtemp(prefix=f"chameleon-pr-{args.pr}-")) / "report"
    )
    report_dir: Path | None = None
    checks: list[CheckResult] = []
    checkout: Path | None = None
    execution_dir: Path | None = None
    body_content: bytes | None = None
    report_fd: int | None = None
    report_directory_validated = False
    review_refs: tuple[str, ...] = ()
    metadata: dict
    repository = args.repo or "unresolved"
    capsule_revision = "unavailable"
    contract_issues: list[str] = []
    summary_path: Path | None = None
    publish_ready = False
    published = False
    try:
        report_dir = create_staging_directory(target_report_dir)
        report_fd = open_evidence_directory(report_dir)
        existing_entries = evidence_directory_entries(report_fd)
        if existing_entries:
            raise ReviewError(
                "staging directory must be empty: " + ", ".join(existing_entries[:5])
            )
        report_directory_validated = True
        publish_ready = True
        if body_source is not None:
            body_content = snapshot_file(body_source)

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
        head_ref, base_ref = fetch_pr_refs(
            args.pr,
            str(metadata["baseRefName"]),
            repository,
            base_sha=base_sha,
        )
        review_refs = (head_ref, base_ref)
        if git_output("rev-parse", head_ref) != head_sha:
            raise ReviewError("fetched PR head does not match GitHub head SHA")
        if git_output("rev-parse", base_ref) != base_sha:
            raise ReviewError("fetched PR base does not match GitHub base SHA")

        diff_range = f"{base_sha}...{head_sha}"
        diff_patch = git_output_bytes(
            "diff",
            "--no-ext-diff",
            diff_range,
            strip=False,
            max_output_bytes=MAX_DIFF_BYTES,
        )
        diff_stat = git_output_bytes("diff", "--stat", diff_range, strip=False)
        changed_files_blob = git_output_bytes(
            "diff",
            "--name-only",
            diff_range,
            strip=False,
        )
        commits_blob = git_output_bytes(
            "log",
            "--oneline",
            f"{base_sha}..{head_sha}",
            strip=False,
        )
        changed_files = [
            line
            for line in decode_output(changed_files_blob).splitlines()
            if line
        ]
        contract_sources = changed_contract_sources(changed_files)
        capsule_revision = git_output("rev-parse", "HEAD")
        execution_dir = Path(
            tempfile.mkdtemp(prefix=f"chameleon-pr-{args.pr}-checks-")
        )
        checkout = execution_dir / "checkout"
        create_checkout(head_sha, checkout)
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
            if execution_dir is None:
                raise ReviewError("check execution directory was not created")
            check_env = isolated_environment(execution_dir)
            checks.append(
                run_check("diff-check", ["git", "diff", "--check", diff_range], ROOT, report_dir, args.timeout)
            )
            engine_available = (checkout / "chameleon" / "engine").is_dir()
            python_path = resolve_runner_python(args.python_path)
            if python_path is None:
                reason = (
                    "no trusted runner interpreter; pass --python-path or provision "
                    f"{ROOT / '.venv' / 'bin' / 'python'}"
                )
                checks.extend(
                    [
                        skipped("verify", make_command("verify", None), reason),
                        skipped("test", make_command("test", None), reason),
                        skipped("run", make_command("run", None), reason),
                        skipped("inspect", make_command("inspect", None), reason),
                    ]
                )
            else:
                checks.append(
                    run_check(
                        "verify",
                        make_command("verify", python_path),
                        checkout,
                        report_dir,
                        args.timeout,
                        check_env,
                    )
                )
                if not engine_available:
                    reason = "nested engine unavailable"
                    checks.extend(
                        [
                            skipped("test", make_command("test", python_path), reason),
                            skipped("run", make_command("run", python_path), reason),
                            skipped("inspect", make_command("inspect", python_path), reason),
                        ]
                    )
                else:
                    checks.append(
                        run_check(
                            "test",
                            make_command("test", python_path),
                            checkout,
                            report_dir,
                            args.timeout,
                            check_env,
                        )
                    )
                    run_result = run_check(
                        "run",
                        make_command("run", python_path),
                        checkout,
                        report_dir,
                        args.timeout,
                        check_env,
                    )
                    checks.append(run_result)
                    if run_result.status == "PASS":
                        checks.append(
                            run_check(
                                "inspect",
                                make_command("inspect", python_path),
                                checkout,
                                report_dir,
                                args.timeout,
                                check_env,
                            )
                        )
                    else:
                        checks.append(
                            skipped(
                                "inspect",
                                make_command("inspect", python_path),
                                "sample render failed",
                            )
                        )

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
                if body_content is None:
                    raise ReviewError("review body snapshot is unavailable")
                checks.append(
                    submit_review(
                        args.pr,
                        repository,
                        args.submit,
                        body_content,
                        report_dir,
                        args.timeout,
                    )
                )
        delete_review_refs(review_refs)
        review_refs = ()
        if report_fd is None:
            raise ReviewError("evidence directory is not open")
        verify_evidence_directory(report_dir, report_fd)
        write_evidence_bytes(report_dir / "diff.patch", diff_patch, report_fd)
        write_evidence_bytes(report_dir / "diff-stat.txt", diff_stat, report_fd)
        write_evidence_bytes(
            report_dir / "changed-files.txt",
            changed_files_blob,
            report_fd,
        )
        write_evidence_bytes(report_dir / "commits.txt", commits_blob, report_fd)
        flush_check_logs(checks, report_fd)
        for check in checks:
            if check.log is not None:
                check.log = str(target_report_dir / Path(check.log).name)

        provenance = {
            "run_id": run_id,
            "capsule_revision": capsule_revision,
            "role": ".agents/roles/reviewer.md",
            "workflow": ".agents/workflows/06-review.md; .agents/workflows/07-github-pr.md",
            "gate": "Gate 1: renderer and validator qualification before solver",
            "environment": environment,
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
            target_report_dir / "checks.json",
            json.dumps([serialize_check(check) for check in checks], indent=2),
            report_fd,
        )
        summary_path = make_summary(
            target_report_dir,
            metadata,
            base_sha,
            head_sha,
            changed_files,
            checks,
            contract_sources,
            provenance,
            directory_fd=report_fd,
        )
        if any(check.status == "FAIL" for check in checks):
            exit_code = 1
        elif any(check.status == "SKIP" for check in checks):
            exit_code = 2
        else:
            exit_code = 0
    except (
        ReviewError,
        OSError,
        ValueError,
        subprocess.CalledProcessError,
        tarfile.TarError,
    ) as error:
        if report_directory_validated and report_fd is not None:
            names = set(EVIDENCE_FILE_NAMES)
            names.update(
                Path(check.log).name for check in checks if check.log is not None
            )
            try:
                cleanup_evidence_files(report_fd, names)
            except OSError:
                pass
            error_checks = []
            for check in checks:
                serialized = serialize_check(check)
                if check.log is not None:
                    serialized["log"] = str(
                        target_report_dir / Path(check.log).name
                    )
                error_checks.append(serialized)
            error_record = {
                "error": str(error),
                "pull_request": args.pr,
                "repository": repository,
                "run_id": run_id,
                "capsule_revision": capsule_revision,
                "environment": environment,
                "validation": (
                    "capsule generation failed before complete evidence publication"
                ),
                "next_owner": "reviewer/maintainer",
                "checks": error_checks,
            }
            try:
                write_text(
                    report_dir / "error.txt",
                    json.dumps(error_record, indent=2),
                    report_fd,
                )
            except OSError:
                pass
        print(f"error: {error}", file=sys.stderr)
        exit_code = 2
    finally:
        try:
            delete_review_refs(review_refs)
        except ReviewError as cleanup_error:
            print(f"error: {cleanup_error}", file=sys.stderr)
            exit_code = 2
        if execution_dir is not None:
            shutil.rmtree(execution_dir, ignore_errors=True)
        if report_fd is not None:
            os.close(report_fd)
    if report_dir is not None:
        if not publish_ready:
            shutil.rmtree(report_dir, ignore_errors=True)
        else:
            try:
                publish_staging_directory(report_dir, target_report_dir)
            except (OSError, ValueError) as publication_error:
                shutil.rmtree(report_dir, ignore_errors=True)
                print(
                    f"error: report publication failed: {publication_error}",
                    file=sys.stderr,
                )
                exit_code = 2
            else:
                published = True
    if published:
        if summary_path is not None:
            print(f"report: {target_report_dir / 'summary.md'}")
            for check in checks:
                print(f"{check.status:4} {check.name}")
        else:
            print(f"report: {target_report_dir}", file=sys.stderr)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
