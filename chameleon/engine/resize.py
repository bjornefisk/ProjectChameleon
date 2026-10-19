"""Public Stage 1 resize seam with bounded topology candidates."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .contract import validate_response, validate_source, validate_target_canvas
from .errors import InfeasibleLayoutError, InfeasibleReasonCode
from .layout.column_pivot import is_column_pivot_suitable, solve_column_pivot
from .layout.near_isomorphic import solve_near_isomorphic
from .layout.roles import infer_roles


def resize(
    source: Mapping[str, Any], target_canvas: Mapping[str, Any]
) -> dict[str, Any]:
    """Return the first serialized, hard-validated bounded candidate.

    A source/target-aware column pivot is attempted when role and proportion
    evidence supports it.  Near-isomorphic remains available as the bounded
    fallback family; no fixed aspect-ratio delta is exposed as the routing
    contract.
    """

    validate_source(source)
    validate_target_canvas(target_canvas)
    roles = infer_roles(source)

    response: dict[str, Any]
    if is_column_pivot_suitable(source, target_canvas, roles):
        try:
            response = solve_column_pivot(source, target_canvas, roles=roles)
        except InfeasibleLayoutError as column_error:
            if column_error.reason_code not in {
                InfeasibleReasonCode.INCOMPLETE_SEARCH,
                InfeasibleReasonCode.NO_HARD_VALID_CANDIDATE,
            }:
                raise
            response = solve_near_isomorphic(source, target_canvas)
    else:
        response = solve_near_isomorphic(source, target_canvas)

    try:
        validate_response(source, target_canvas, response)
    except InfeasibleLayoutError as error:
        raise InfeasibleLayoutError(
            InfeasibleReasonCode.NO_HARD_VALID_CANDIDATE,
            "layout candidate failed serialized hard validation",
            {
                "reason_code": error.reason_code.value,
                "reason": error.message,
                "details": error.details,
            },
        ) from error
    return response
