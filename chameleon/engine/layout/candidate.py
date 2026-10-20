"""Private hand-off types shared by topology solvers and candidate search."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class RenderedCandidate:
    """A serialized topology response together with its verified render.

    Topology solvers render once while establishing renderer-dependent text and
    asset behavior.  The centralized search gate still validates ``response``
    before admission, while reusing these bytes for the unchanged base variant.
    """

    response: Mapping[str, Any]
    rendered_png: bytes
    warnings: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.response, Mapping):
            raise TypeError("rendered candidate response must be a mapping")
        if not isinstance(self.rendered_png, bytes):
            raise TypeError("rendered candidate PNG must be bytes")
        if not isinstance(self.warnings, tuple) or not all(
            isinstance(warning, str) for warning in self.warnings
        ):
            raise TypeError("rendered candidate warnings must be a string tuple")


__all__ = ["RenderedCandidate"]
