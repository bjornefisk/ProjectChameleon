"""Public Stage 1 resize seam with bounded topology candidates."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .contract import validate_response, validate_source, validate_target_canvas
from .errors import InfeasibleLayoutError, InfeasibleReasonCode
from .layout.column_pivot import is_column_pivot_suitable, solve_column_pivot
from .layout.horizontal_ribbon import is_horizontal_ribbon_suitable, solve_horizontal_ribbon
from .layout.near_isomorphic import solve_near_isomorphic
from .layout.roles import infer_roles
from .layout.vertical_restack import is_vertical_restack_suitable, solve_vertical_restack



def _coerce_layout_error(error: Exception) -> InfeasibleLayoutError | None:
    if isinstance(error, InfeasibleLayoutError):
        return error
    reason_code = getattr(error, "reason_code", None)
    if reason_code is None:
        return None
    try:
        normalized = InfeasibleReasonCode(reason_code)
    except ValueError:
        return None
    return InfeasibleLayoutError(
        normalized,
        getattr(error, "message", str(error)),
        getattr(error, "details", {}),
    )



def resize(
    source: Mapping[str, Any], target_canvas: Mapping[str, Any]
) -> dict[str, Any]:
    """Return the first serialized, hard-validated bounded candidate.

    Topology suitability is source- and target-aware.  Every supported family
    remains available until its candidate is serialized and hard validated;
    no fixed aspect-ratio delta is used as the routing contract.
    """

    validate_source(source)
    validate_target_canvas(target_canvas)
    roles = infer_roles(source)
    candidates: list[tuple[str, Any]] = []
    if is_horizontal_ribbon_suitable(source, target_canvas):
        candidates.append(("horizontal_ribbon", solve_horizontal_ribbon))
    if is_vertical_restack_suitable(source, target_canvas):
        candidates.append(("vertical_restack", solve_vertical_restack))
    if is_column_pivot_suitable(source, target_canvas, roles):
        candidates.append(("column_pivot", solve_column_pivot))
    candidates.append(("near_isomorphic", solve_near_isomorphic))

    failures: dict[str, dict[str, Any]] = {}
    for name, solver in candidates:
        try:
            if name == "column_pivot":
                response = solver(source, target_canvas, roles=roles)
            else:
                response = solver(source, target_canvas)
        except Exception as raw_error:
            error = _coerce_layout_error(raw_error)
            if error is None:
                raise
            if error.reason_code not in {
                InfeasibleReasonCode.INCOMPLETE_SEARCH,
                InfeasibleReasonCode.NO_HARD_VALID_CANDIDATE,
            }:
                raise
            details = (
                dict(error.details)
                if isinstance(error.details, Mapping)
                else {}
            )
            details["search_exhausted"] = details.get("search_exhausted") is True
            failures[name] = {
                "reason_code": error.reason_code.value,
                "message": error.message,
                "details": details,
            }
            continue
        try:
            validate_response(source, target_canvas, response)
        except InfeasibleLayoutError as error:
            failures[name] = {
                "reason_code": InfeasibleReasonCode.NO_HARD_VALID_CANDIDATE.value,
                "message": "layout candidate failed serialized hard validation",
                "details": {
                    "reason_code": error.reason_code.value,
                    "reason": error.message,
                    "details": error.details,
                    "search_exhausted": False,
                },
            }
            continue
        return response

    all_exhausted = bool(failures) and all(
        failure["details"].get("search_exhausted") is True
        for failure in failures.values()
    )
    if failures:
        reason_code = (
            InfeasibleReasonCode.NO_HARD_VALID_CANDIDATE
            if all_exhausted
            else InfeasibleReasonCode.INCOMPLETE_SEARCH
        )
        raise InfeasibleLayoutError(
            reason_code,
            "bounded candidate families failed",
            {
                "candidate_failures": failures,
                "search_exhausted": all_exhausted,
            },
        )
    raise InfeasibleLayoutError(
        InfeasibleReasonCode.INCOMPLETE_SEARCH,
        "no bounded candidate family was suitable",
        {"candidate_failures": {}, "search_exhausted": False},
    )
