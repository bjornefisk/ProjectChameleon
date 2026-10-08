"""Typed failures shared by the Stage 1 contract and runner seams."""

from __future__ import annotations

from enum import Enum
from typing import Any, Mapping


class InfeasibleReasonCode(str, Enum):
    """Stable reason codes for hard validation and fail-closed outcomes."""

    INVALID_SOURCE = "INVALID_SOURCE"
    INVALID_TARGET = "INVALID_TARGET"
    MALFORMED_INPUT = "MALFORMED_INPUT"
    IMMUTABLE_FIELD_CHANGED = "IMMUTABLE_FIELD_CHANGED"
    CONTAINMENT_VIOLATION = "CONTAINMENT_VIOLATION"
    IMAGE_RATIO_VIOLATION = "IMAGE_RATIO_VIOLATION"
    GROUP_VIOLATION = "GROUP_VIOLATION"
    SOURCE_SEPARATION_VIOLATION = "SOURCE_SEPARATION_VIOLATION"
    TEXT_OVERFLOW = "TEXT_OVERFLOW"
    NO_HARD_VALID_CANDIDATE = "NO_HARD_VALID_CANDIDATE"
    INCOMPLETE_SEARCH = "INCOMPLETE_SEARCH"
    RUNTIME_IO_FAILURE = "RUNTIME_IO_FAILURE"


class InfeasibleLayoutError(ValueError):
    """A typed, fail-closed contract or layout failure.

    ``reason_code`` is kept as an enum for stable programmatic handling.  The
    string-valued ``code`` alias is convenient for runner logs and JSON-free
    diagnostics; neither field changes the public design response shape.
    """

    def __init__(
        self,
        reason_code: InfeasibleReasonCode | str,
        message: str | None = None,
        details: Mapping[str, Any] | None = None,
    ) -> None:
        self.reason_code = InfeasibleReasonCode(reason_code)
        self.details = dict(details or {})
        self.message = message or self.reason_code.value
        super().__init__(self.message)

    @property
    def code(self) -> str:
        """Return the wire/log spelling of :attr:`reason_code`."""

        return self.reason_code.value


__all__ = ["InfeasibleLayoutError", "InfeasibleReasonCode"]
