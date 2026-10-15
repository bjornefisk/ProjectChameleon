"""Public Stage 1 resize seam backed by the Level 1 near-isomorphic solver."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .contract import validate_response, validate_source, validate_target_canvas
from .errors import InfeasibleLayoutError, InfeasibleReasonCode
from .layout.near_isomorphic import solve_near_isomorphic


def resize(
    source: Mapping[str, Any], target_canvas: Mapping[str, Any]
) -> dict[str, Any]:
    """Return a serialized, hard-validated near-isomorphic target design.

    Ticket 05 intentionally exposes one finite Level 1 candidate rather than
    pretending that the later topology families or ranker already exist.
    Candidate generation and final validation both use the contract's exact
    numeric and geometry rules; a failed candidate never becomes best-effort
    output.
    """

    validate_source(source)
    validate_target_canvas(target_canvas)
    response = solve_near_isomorphic(source, target_canvas)
    try:
        validate_response(source, target_canvas, response)
    except InfeasibleLayoutError as error:
        raise InfeasibleLayoutError(
            InfeasibleReasonCode.NO_HARD_VALID_CANDIDATE,
            "near-isomorphic candidate failed serialized hard validation",
            {
                "reason_code": error.reason_code.value,
                "reason": error.message,
                "details": error.details,
            },
        ) from error
    return response
