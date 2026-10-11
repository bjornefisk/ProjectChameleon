#!/usr/bin/env python3
"""Build a compact, isolated evidence capsule for one GitHub pull request.

The script automates repository mechanics only. It never chooses a review
verdict and never mutates GitHub unless ``--submit`` is supplied explicitly.
PR-controlled checks require the explicit ``--run-checks`` opt-in.
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
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TIMEOUT = 300
GH_TIMEOUT = 60
CONTRACT_SOURCES = (
    "AGENTS.md",
    "Docs/PROJECT_CONTRACT.md",
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
    "Docs/DEPENDENCY_EVIDENCE.md",
    "Docs/STATUS.md",
    "Docs/IMPLEMENTATION_ROADMAP.md",
    ".agents/README.md",
    ".agents/OPERATING_CONTRACT.md",
    ".agents/PROJECT_PROFILE.md",
    ".agents/TOOLING.md",
    ".agents/policies/authority.md",
    ".agents/policies/evidence.md",
    ".agents/roles/reviewer.md",
    ".agents/workflows/06-review.md",
    ".agents/workflows/07-github-pr.md",
    ".agents/checklists/review.md",
    ".agents/templates/review.md",
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


def run_process(
    command: Sequence[str],
    cwd: Path,
    log_path: Path,
    timeout: int,
    env: Mapping[str, str] | None = None,
) -> CheckResult:
    started = time.monotonic()
    try:
        completed = subprocess.run(
            list(command),
            cwd=cwd,
            env=dict(env) if env is not None else None,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=timeout,
            check=False,
        )
        output = completed.stdout or ""
        status = "PASS" if completed.returncode == 0 else "FAIL"
        returncode = completed.returncode
        reason = None
    except subprocess.TimeoutExpired as error:
        partial_output = error.stdout or ""
        if isinstance(partial_output, bytes):
            partial_output = partial_output.decode(errors="replace")
        output = partial_output + f"\nTimed out after {timeout}s.\n"
        status = "FAIL"
        returncode = None
        reason = f"timeout after {timeout}s"
    except OSError as error:
        output = f"{type(error).__name__}: {error}\n"
        status = "FAIL"
        returncode = None
        reason = str(error)

    log_path.write_text(output, encoding="utf-8")
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

def missing_contract_sources(root: Path, sources: Iterable[str]) -> list[str]:
    missing = []
    for source in sources:
        path = source.split(" §", 1)[0]
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
        f"- PR: #{metadata['number']} ({metadata.get('url', 'unknown URL')})",
        f"- Repository: {metadata['repository']}",
        f"- Base: `{base_sha}`",
        f"- Head: `{head_sha}`",
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
            lines.append(f"- {label}: `{value}`")
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
    lines.extend(f"- `{path}`" for path in changed_files)
    lines.extend(["", "## Contract pointers", ""])
    lines.extend(f"- `{source}`" for source in contract_sources)
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
            log = f"`{log_path}`"
        else:
            log = "—"
        lines.append(
            f"| `{check.name}` | **{check.status}** | {check.duration_seconds:.3f} | {log} |"
        )
        if check.reason:
            lines.append(f"| reason | {check.reason} |  |  |")
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
        help="Execute PR-controlled repository checks in an isolated checkout",
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
        if missing_sources:
            checks.append(
                skipped(
                    "contract-sources",
                    ["canonical-contract-sources"],
                    "missing from PR checkout: " + ", ".join(missing_sources),
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
        provenance = {
            "run_id": report_dir.name,
            "capsule_revision": capsule_revision,
            "role": ".agents/roles/reviewer.md",
            "workflow": ".agents/workflows/06-review.md; .agents/workflows/07-github-pr.md",
            "gate": "Gate 1: renderer and validator qualification before solver",
            "environment": f"{platform.python_implementation()} {platform.python_version()} on {platform.platform()}",
            "validation": (
                "PR code execution requested; inspect check statuses"
                if args.run_checks
                else "PR code execution disabled by default"
            ),
            "contract_sources": (
                "complete" if not missing_sources else "incomplete"
            ),
            "next_owner": "independent reviewer",
        }

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
            python_path = ROOT / ".venv" / "bin" / "python"
            if not engine_available or not python_path.is_file():
                reason = "missing nested engine or host .venv; initialize prerequisites before runtime checks"
                checks.extend(
                    [
                        skipped("test", make_command("test", python_path if python_path.is_file() else None), reason),
                        skipped("run", make_command("run", python_path if python_path.is_file() else None), reason),
                        skipped("inspect", make_command("inspect", python_path if python_path.is_file() else None), reason),
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
            checks.append(submit_review(args.pr, repository, args.submit, body_file, report_dir, args.timeout))

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
