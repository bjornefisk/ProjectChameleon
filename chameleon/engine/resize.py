"""Public Stage 1 resize seam with bounded topology candidates."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .layout.search import search






def resize(
    source: Mapping[str, Any], target_canvas: Mapping[str, Any]
) -> dict[str, Any]:
    """Return the highest-ranked hard-valid rendered candidate.

    Candidate generation, serialized hard validation, renderer gating, and
    deterministic fixed-point ranking live in :mod:`engine.layout.search`.
    The public response remains the flat design document only.
    """

    result = search(source, target_canvas)
    return dict(result.response)
