#!/usr/bin/env python3
"""Evaluate the checked-in Stage 1 search corpus without changing responses.

This is an evidence collector, not a second layout implementation.  It calls the
observable ``layout.search.search`` seam, validates the candidates admitted by
that seam, and keeps hard contract evidence separate from soft ranking quality.
The corpus is intentionally local and is not an official qualification set.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
try:
    import resource
except ImportError:  # pragma: no cover - Windows does not expose resource
    resource = None  # type: ignore[assignment]
import sys
import time
from collections import Counter
from decimal import Decimal
from pathlib import Path
from typing import Any, Mapping, Sequence

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CHAMELEON_ROOT = PROJECT_ROOT / "chameleon"
DEFAULT_CORPUS = CHAMELEON_ROOT / "tests" / "fixtures" / "heldout_search_cases.json"
ASSETS_DIR = CHAMELEON_ROOT / "brand_kit" / "assets"
FONTS_DIR = CHAMELEON_ROOT / "brand_kit" / "fonts"
if str(CHAMELEON_ROOT) not in sys.path:
    sys.path.insert(0, str(CHAMELEON_ROOT))

try:
    from engine.contract import validate_response
    from engine.errors import InfeasibleLayoutError, TaskStatus
    from engine.layout.search import MAX_CANDIDATES, search
except ModuleNotFoundError:  # pragma: no cover - package-style invocation
    from chameleon.engine.contract import validate_response
    from chameleon.engine.errors import InfeasibleLayoutError, TaskStatus
    from chameleon.engine.layout.search import MAX_CANDIDATES, search


class _ExactJSONError(ValueError):
    pass


def _reject_constant(value: str) -> None:
    raise _ExactJSONError(f"non-finite JSON number is not allowed: {value}")


def load_corpus(path: str | Path = DEFAULT_CORPUS) -> dict[str, Any]:
    """Load corpus numbers exactly (integers as int, decimals as Decimal)."""

    corpus_path = Path(path)
    with corpus_path.open("r", encoding="utf-8") as stream:
        value = json.load(
            stream,
            parse_int=int,
            parse_float=Decimal,
            parse_constant=_reject_constant,
        )
    if not isinstance(value, dict) or not isinstance(value.get("cases"), list):
        raise ValueError("held-out corpus must contain a cases array")
    return value


def _json_default(value: Any) -> Any:
    if isinstance(value, Decimal):
        # Decimal is retained while loading and running the engine.  This string
        # encoding is used only for canonical evidence/signature serialization.
        return {"__decimal__": format(value, "f")}
    if isinstance(value, bytes):
        return {"__bytes_sha256__": hashlib.sha256(value).hexdigest()}
    raise TypeError(f"cannot encode {type(value).__name__} in evidence JSON")


def _canonical(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=_json_default,
    )


def _rss_bytes() -> int | None:
    if resource is None:
        return None
    try:
        value = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    except (AttributeError, OSError, ValueError):
        return None
    if value < 0:
        return None
    # Darwin reports bytes; Linux and the BSDs conventionally report KiB.
    return value if sys.platform == "darwin" else value * 1024


def _quality_dict(candidate: Any) -> dict[str, int]:
    quality = candidate.quality
    return {
        "readability": int(quality.readability),
        "balance": int(quality.balance),
        "alignment": int(quality.alignment),
        "hierarchy": int(quality.hierarchy),
    }


def _candidate_signature(candidate: Any) -> dict[str, Any]:
    png = bytes(candidate.rendered_png)
    response = copy.deepcopy(dict(candidate.response))
    response_sha256 = hashlib.sha256(_canonical(response).encode("utf-8")).hexdigest()
    return {
        "topology": candidate.topology,
        "variant": candidate.variant,
        "candidate_index": int(candidate.candidate_index),
        "response": response,
        "response_sha256": response_sha256,
        "png_sha256": hashlib.sha256(png).hexdigest(),
        "png_size": len(png),
        "png_header_valid": png.startswith(b"\x89PNG\r\n\x1a\n"),
    }


def _error_status(error: InfeasibleLayoutError) -> str:
    details = error.details
    status = details.get("status") if isinstance(details, Mapping) else None
    if isinstance(status, str):
        return status
    if error.reason_code.value == "INCOMPLETE_SEARCH":
        return TaskStatus.INCOMPLETE_SEARCH.value
    if error.reason_code.value in {"INVALID_SOURCE", "INVALID_TARGET", "MALFORMED_INPUT"}:
        return TaskStatus.MALFORMED_INPUT.value
    if error.reason_code.value == "RUNTIME_IO_FAILURE":
        return TaskStatus.RUNTIME_IO_FAILURE.value
    return TaskStatus.INFEASIBLE_LAYOUT.value


def _run_once(case: Mapping[str, Any]) -> dict[str, Any]:
    source = case["source"]
    target = case["target_canvas"]
    source_before = copy.deepcopy(source)
    started = time.perf_counter_ns()
    try:
        result = search(
            source,
            target,
            max_candidates=MAX_CANDIDATES,
            assets_dir=ASSETS_DIR,
            fonts_dir=FONTS_DIR,
        )
    except InfeasibleLayoutError as error:
        elapsed_ns = time.perf_counter_ns() - started
        details = copy.deepcopy(error.details)
        failures = details.get("failures", []) if isinstance(details, Mapping) else []
        return {
            "status": _error_status(error),
            "reason_code": error.reason_code.value,
            "message": error.message,
            "diagnostics": details,
            "failures": failures if isinstance(failures, list) else [],
            "candidate_count": int(details.get("candidate_count", 0)) if isinstance(details, Mapping) else 0,
            "evaluated_candidates": int(details.get("evaluated_candidates", 0)) if isinstance(details, Mapping) else 0,
            "admitted_candidates": 0,
            "hard_valid_candidates": 0,
            "cutoff": bool(details.get("cutoff", False)) if isinstance(details, Mapping) else False,
            "candidate_signatures": [],
            "selected_signature": None,
            "quality": [],
            "selected_quality": None,
            "hard_validation_errors": [],
            "source_unchanged": source == source_before,
            "runtime_ms": elapsed_ns / 1_000_000,
            "max_rss_bytes": _rss_bytes(),
        }
    except Exception as error:  # Keep an evidence record for unexpected runtime failures.
        elapsed_ns = time.perf_counter_ns() - started
        return {
            "status": TaskStatus.RUNTIME_IO_FAILURE.value,
            "reason_code": "RUNTIME_IO_FAILURE",
            "message": f"{type(error).__name__}: {error}",
            "diagnostics": {},
            "failures": [],
            "candidate_count": 0,
            "evaluated_candidates": 0,
            "admitted_candidates": 0,
            "hard_valid_candidates": 0,
            "cutoff": False,
            "candidate_signatures": [],
            "selected_signature": None,
            "quality": [],
            "selected_quality": None,
            "hard_validation_errors": [f"{type(error).__name__}: {error}"],
            "source_unchanged": source == source_before,
            "runtime_ms": elapsed_ns / 1_000_000,
            "max_rss_bytes": _rss_bytes(),
        }

    hard_validation_errors: list[str] = []
    candidate_validation_errors = 0
    candidate_signatures: list[dict[str, Any]] = []
    for candidate in result.candidates:
        try:
            validate_response(source, target, candidate.response)
        except Exception as error:
            candidate_validation_errors += 1
            hard_validation_errors.append(
                f"candidate {candidate.candidate_index}: {type(error).__name__}: {error}"
            )
        candidate_signatures.append(_candidate_signature(candidate))
    try:
        validate_response(source, target, result.response)
    except Exception as error:
        hard_validation_errors.append(f"selected response: {type(error).__name__}: {error}")

    elapsed_ns = time.perf_counter_ns() - started
    diagnostics = dict(result.diagnostics)
    failures = list(diagnostics.get("failures", ()))
    return {
        "status": str(diagnostics.get("status", TaskStatus.SUCCESS.value)),
        "reason_code": None,
        "message": None,
        "diagnostics": copy.deepcopy(diagnostics),
        "failures": copy.deepcopy(failures),
        "candidate_count": int(diagnostics.get("candidate_count", len(result.candidates))),
        "evaluated_candidates": int(
            diagnostics.get("evaluated_candidates", len(result.candidates))
        ),
        "admitted_candidates": len(result.candidates),
        "hard_valid_candidates": len(result.candidates) - candidate_validation_errors,
        "cutoff": bool(diagnostics.get("cutoff", False)),
        "candidate_signatures": candidate_signatures,
        "selected_signature": _candidate_signature(result.selected),
        "quality": [_quality_dict(candidate) for candidate in result.candidates],
        "selected_quality": _quality_dict(result.selected),
        "hard_validation_errors": hard_validation_errors,
        "source_unchanged": source == source_before,
        "runtime_ms": elapsed_ns / 1_000_000,
        "max_rss_bytes": _rss_bytes(),
    }


def _stable_signature(run: Mapping[str, Any]) -> str:
    """Exclude measurements while retaining responses and exact PNG digests."""

    stable = {
        key: run[key]
        for key in (
            "status",
            "reason_code",
            "message",
            "candidate_count",
            "evaluated_candidates",
            "admitted_candidates",
            "cutoff",
            "candidate_signatures",
            "selected_signature",
            "quality",
            "selected_quality",
            "failures",
            "hard_validation_errors",
            "source_unchanged",
        )
    }
    return _canonical(stable)


def _repeat_signature_stability(values: Sequence[str | None]) -> bool | None:
    if all(value is None for value in values):
        return None
    return all(value is not None for value in values) and len(set(values)) == 1


def _case_report(case: Mapping[str, Any], repeats: int) -> dict[str, Any]:
    runs = [_run_once(case) for _ in range(repeats)]
    stable_signatures = [_stable_signature(run) for run in runs]
    first = runs[0]
    deterministic = all(signature == stable_signatures[0] for signature in stable_signatures[1:])
    topology_counts = Counter(
        item["topology"]
        for item in first["candidate_signatures"]
        if isinstance(item, Mapping) and isinstance(item.get("topology"), str)
    )
    diagnostics = first.get("diagnostics", {})
    work_set_topologies = {
        str(topology)
        for topology in (
            diagnostics.get("work_set_topologies", ())
            if isinstance(diagnostics, Mapping)
            else ()
        )
        if isinstance(topology, str)
    }
    topology_coverage = set(topology_counts) | work_set_topologies
    rejection_counts = Counter(
        str(failure["reason_code"])
        for failure in first["failures"]
        if isinstance(failure, Mapping) and failure.get("reason_code")
    )
    hard_valid = max(0, int(first["hard_valid_candidates"]))
    evaluated = int(first["evaluated_candidates"])
    selected_signatures = [run["selected_signature"] for run in runs]
    selected_response_hashes = [
        signature.get("response_sha256") if isinstance(signature, Mapping) else None
        for signature in selected_signatures
    ]
    selected_png_hashes = [
        signature.get("png_sha256") if isinstance(signature, Mapping) else None
        for signature in selected_signatures
    ]
    selected = first["selected_signature"]
    selected_topology = selected.get("topology") if isinstance(selected, Mapping) else None
    expected_status = case["expected_status"]
    expected_reason_code = case.get("expected_reason_code")
    expectation_met = first["status"] == expected_status and (
        expected_reason_code is None or first["reason_code"] == expected_reason_code
    )
    return {
        "id": case["id"],
        "coverage": list(case["coverage"]),
        "expected_outcome": {
            "status": expected_status,
            "reason_code": expected_reason_code,
            "matched": expectation_met,
        },
        "hard_evidence": {
            "status": first["status"],
            "task_reason_code": first["reason_code"],
            "candidate_rejection_reason_distribution": dict(sorted(rejection_counts.items())),
            "candidate_count": first["candidate_count"],
            "evaluated_candidates": evaluated,
            "admitted_candidates": first["admitted_candidates"],
            "hard_valid_admissions": hard_valid,
            "hard_valid_candidates": hard_valid,
            "hard_valid_rate": (hard_valid / evaluated) if evaluated else 0.0,
            "cutoff": first["cutoff"],
            "finite_work_exhausted": bool(
                diagnostics.get(
                    "finite_work_exhausted",
                    diagnostics.get("search_exhausted", False),
                )
            ),
            # Work-set coverage proves every family was considered; admitted
            # coverage remains separate hard-validation evidence.
            "topology_coverage": sorted(topology_coverage),
            "work_set_topology_coverage": sorted(work_set_topologies),
            "admitted_topology_coverage": sorted(topology_counts),
            "selected_topology": selected_topology,
            "selected_response_sha256": selected.get("response_sha256")
            if isinstance(selected, Mapping)
            else None,
            "selected_png_sha256": selected.get("png_sha256")
            if isinstance(selected, Mapping)
            else None,
            "selected_signature": selected,
            "response_signature_stable": _repeat_signature_stability(
                selected_response_hashes
            ),
            "png_signature_stable": _repeat_signature_stability(selected_png_hashes),
            "task_outcome_stable": len({run["status"] for run in runs}) == 1
            and len({run["reason_code"] for run in runs}) == 1,
            "hard_validation_errors": first["hard_validation_errors"],
            "source_unchanged": first["source_unchanged"],
            "deterministic_repeated": deterministic,
            "repeat_count": repeats,
        },
        "soft_quality": {
            "candidate_components": first["quality"],
            "selected_components": first["selected_quality"],
        },
        "runtime_observations": {
            "wall_time_ms": [run["runtime_ms"] for run in runs],
            "process_max_rss_bytes": [run["max_rss_bytes"] for run in runs],
        },
    }


def evaluate_corpus(corpus: Mapping[str, Any], repeats: int = 2) -> dict[str, Any]:
    if isinstance(repeats, bool) or not isinstance(repeats, int) or repeats < 2:
        raise ValueError("repeats must be an integer >= 2")
    cases = corpus.get("cases")
    if not isinstance(cases, list) or not cases:
        raise ValueError("corpus cases must be a non-empty list")
    allowed_statuses = {status.value for status in TaskStatus}
    case_ids: list[str] = []
    for case in cases:
        if not isinstance(case, Mapping):
            raise ValueError("each corpus case must be an object")
        case_id = case.get("id")
        if not isinstance(case_id, str) or not case_id:
            raise ValueError("each corpus case requires a non-empty id")
        if case_id in case_ids:
            raise ValueError(f"duplicate corpus case id: {case_id}")
        case_ids.append(case_id)
        if case.get("expected_status") not in allowed_statuses:
            raise ValueError(f"case {case_id} requires a valid expected_status")
        coverage = case.get("coverage")
        if not isinstance(coverage, list) or not coverage or any(
            not isinstance(item, str) or not item for item in coverage
        ):
            raise ValueError(f"case {case_id} requires non-empty string coverage labels")
        expected_reason_code = case.get("expected_reason_code")
        if expected_reason_code is not None and not isinstance(expected_reason_code, str):
            raise ValueError(f"case {case_id} expected_reason_code must be a string")

    case_reports = [_case_report(case, repeats) for case in cases]
    statuses = Counter(report["hard_evidence"]["status"] for report in case_reports)
    task_reasons = Counter(
        report["hard_evidence"]["task_reason_code"]
        for report in case_reports
        if report["hard_evidence"]["task_reason_code"]
    )
    rejection_reasons = Counter()
    selected_topologies = Counter()
    topology_coverage: set[str] = set()
    total_evaluated = total_hard_valid = 0
    for report in case_reports:
        hard = report["hard_evidence"]
        rejection_reasons.update(hard["candidate_rejection_reason_distribution"])
        if hard["selected_topology"]:
            selected_topologies[str(hard["selected_topology"])] += 1
        topology_coverage.update(hard["topology_coverage"])
        total_evaluated += hard["evaluated_candidates"]
        total_hard_valid += hard["hard_valid_admissions"]

    mismatches = [
        {
            "case_id": report["id"],
            "expected_status": report["expected_outcome"]["status"],
            "actual_status": report["hard_evidence"]["status"],
            "expected_reason_code": report["expected_outcome"]["reason_code"],
            "actual_reason_code": report["hard_evidence"]["task_reason_code"],
        }
        for report in case_reports
        if not report["expected_outcome"]["matched"]
    ]
    successful_cases = [
        report for report in case_reports if report["hard_evidence"]["selected_topology"]
    ]
    all_repeated_stable = all(
        report["hard_evidence"]["deterministic_repeated"] for report in case_reports
    )
    return {
        "evaluator": "stage1-heldout-search-v2",
        "corpus": corpus.get("corpus", "unknown"),
        "corpus_provenance": corpus.get("provenance"),
        "outcome_expectations": {
            "all_match": not mismatches,
            "mismatches": mismatches,
        },
        "hard_evidence": {
            "case_count": len(case_reports),
            "status_distribution": dict(sorted(statuses.items())),
            "task_reason_code_distribution": dict(sorted(task_reasons.items())),
            "candidate_rejection_reason_distribution": dict(sorted(rejection_reasons.items())),
            "candidate_counts": {
                report["id"]: {
                    "candidate_count": report["hard_evidence"]["candidate_count"],
                    "evaluated_candidates": report["hard_evidence"]["evaluated_candidates"],
                    "admitted_candidates": report["hard_evidence"]["admitted_candidates"],
                    "hard_valid_admissions": report["hard_evidence"]["hard_valid_admissions"],
                    "cutoff": report["hard_evidence"]["cutoff"],
                }
                for report in case_reports
            },
            "hard_valid_rate": (total_hard_valid / total_evaluated) if total_evaluated else 0.0,
            "selected_topology_distribution": dict(sorted(selected_topologies.items())),
            "topology_coverage": sorted(topology_coverage),
            "all_repeated_task_outcomes_stable": all(
                report["hard_evidence"]["task_outcome_stable"] for report in case_reports
            ),
            "all_repeated_signatures_stable": all_repeated_stable,
            "all_success_response_signatures_stable": all(
                report["hard_evidence"]["response_signature_stable"] is True
                for report in successful_cases
            )
            if successful_cases
            else None,
            "all_success_png_signatures_stable": all(
                report["hard_evidence"]["png_signature_stable"] is True
                for report in successful_cases
            )
            if successful_cases
            else None,
            "max_candidates_limit": MAX_CANDIDATES,
        },
        "soft_quality": {
            "fixed_point_quality_components": {
                report["id"]: report["soft_quality"] for report in case_reports
            },
        },
        "runtime_observations": {
            "wall_time_ms": {
                report["id"]: report["runtime_observations"]["wall_time_ms"]
                for report in case_reports
            },
            "process_max_rss_bytes": {
                report["id"]: report["runtime_observations"]["process_max_rss_bytes"]
                for report in case_reports
            },
        },
        "cases": case_reports,
        "limitations": {
            "offline_local_corpus_only": True,
            "official_heldout_qualification": False,
            "native_amd64_qualification": False,
            "organizer_controlled_limits": False,
        },
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS)
    parser.add_argument("--repeats", type=int, default=2)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args(argv)
    report = evaluate_corpus(load_corpus(args.corpus), repeats=args.repeats)
    encoded = json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False, default=_json_default)
    if args.output is None:
        print(encoded)
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded + "\n", encoding="utf-8")
    return 0 if report["outcome_expectations"]["all_match"] else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
