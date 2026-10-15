"""Public Stage 1 resize seam backed by the Level 1 near-isomorphic solver."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .contract import validate_response, validate_source, validate_target_canvas
from .errors import InfeasibleLayoutError, InfeasibleReasonCode
from .layout.near_isomorphic import solve_near_isomorphic


class _RenderedResponse(dict[str, Any]):
    """Keep the gated PNG private while preserving the response schema."""

    def __init__(self, response: Mapping[str, Any], rendered_png: bytes):
        super().__init__(response)
        self._rendered_png = rendered_png


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

    response, rendered_png = resize_with_render(source, target_canvas)
    return _RenderedResponse(response, rendered_png)


def resize_with_render(
    source: Mapping[str, Any], target_canvas: Mapping[str, Any]
) -> tuple[dict[str, Any], bytes]:
    """Return a hard-validated design and its already-gated PNG bytes."""

    validate_source(source)
    validate_target_canvas(target_canvas)
    rendered_png: list[bytes] = []
    response = solve_near_isomorphic(
        source,
        target_canvas,
        _rendered_png=rendered_png,
    )
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
    if len(rendered_png) != 1:
        raise RuntimeError("near-isomorphic renderer gate returned no PNG")
    return response, rendered_png[0]
