"""Unicode-safe text measurement and deterministic greedy wrapping."""

from dataclasses import dataclass
import unicodedata
from typing import Callable, List, Optional, Sequence, Set

import skia  # type: ignore

from cr_renderer.fonts import FontManager


class TextLayoutError(ValueError):
    """Base class for deterministic renderer text-layout failures."""


class UnbreakableTextError(TextLayoutError):
    """Raised when a grapheme-safe segment cannot fit the element width."""


class TextOverflowError(TextLayoutError):
    """Raised when wrapped text exceeds a hard line or height limit."""


@dataclass(frozen=True)
class _Cluster:
    start: int
    end: int


_BREAK_AFTER = {
    "-",
    "\u058a",
    "\u05be",
    "\u1400",
    "\u1806",
    "\u2010",
    "\u2012",
    "\u2013",
    "\u2e17",
    "\u2e1a",
    "\u2e3a",
    "\u2e3b",
    "\u301c",
    "/",
    "\u2044",
}
_OPENING_PUNCTUATION = {
    "(",
    "[",
    "{",
    "\u2018",
    "\u201c",
    "\u3008",
    "\u300a",
    "\u300c",
    "\u300e",
}
_CLOSING_PUNCTUATION = {
    ")",
    "]",
    "}",
    "\u2019",
    "\u201d",
    "\u3009",
    "\u300b",
    "\u300d",
    "\u300f",
}


def char_widths(
    font_manager: FontManager, family: str, weight: str, style: str, size: float, text: str
) -> List[float]:
    """Return glyph advances using the pinned renderer's Skia path."""
    if not text:
        return []
    ttf_bytes = font_manager.lookup(family, weight, style)
    typeface = skia.Typeface.MakeFromData(ttf_bytes)
    font = skia.Font(typeface, int(size))
    glyphs = font.textToGlyphs(text)
    widths = list(font.getWidths(glyphs))
    if len(widths) < len(text):
        widths.extend([0.0] * (len(text) - len(widths)))
    return widths[: len(text)]


def _is_control(char: str) -> bool:
    return char in "\r\n" or unicodedata.category(char) == "Cc"


def _is_extend(char: str) -> bool:
    codepoint = ord(char)
    return (
        unicodedata.category(char).startswith("M")
        or char == "\u200c"
        or 0xFE00 <= codepoint <= 0xFE0F
        or 0xE0100 <= codepoint <= 0xE01EF
        or 0x1F3FB <= codepoint <= 0x1F3FF
    )


def _is_spacing_mark(char: str) -> bool:
    return unicodedata.category(char) == "Mc"


def _is_prepend(char: str) -> bool:
    codepoint = ord(char)
    return (
        0x0600 <= codepoint <= 0x0605
        or codepoint in {0x06DD, 0x070F, 0x0890, 0x0891, 0x08E2, 0x0D4E}
        or 0x110BD <= codepoint <= 0x110CD
    )


def _is_regional_indicator(char: str) -> bool:
    return 0x1F1E6 <= ord(char) <= 0x1F1FF


def _is_extended_pictographic(char: str) -> bool:
    codepoint = ord(char)
    return (
        0x1F000 <= codepoint <= 0x1FAFF
        or 0x2600 <= codepoint <= 0x27BF
        or 0x2300 <= codepoint <= 0x23FF
        or 0x2B00 <= codepoint <= 0x2BFF
    )


def _is_virama(char: str) -> bool:
    return ord(char) in {
        0x094D,
        0x09CD,
        0x0A4D,
        0x0ACD,
        0x0B4D,
        0x0BCD,
        0x0C4D,
        0x0CCD,
        0x0D3B,
        0x0D3C,
        0x0D4D,
        0x1039,
        0x103A,
        0x1714,
        0x1A60,
        0x1BAA,
        0xA806,
        0xA8C4,
        0xA953,
        0xAAF6,
    }


def _hangul_class(char: str) -> Optional[str]:
    codepoint = ord(char)
    if 0x1100 <= codepoint <= 0x115F or 0xA960 <= codepoint <= 0xA97C:
        return "L"
    if 0x1160 <= codepoint <= 0x11A7 or 0xD7B0 <= codepoint <= 0xD7C6:
        return "V"
    if 0x11A8 <= codepoint <= 0x11FF or 0xD7CB <= codepoint <= 0xD7FB:
        return "T"
    if 0xAC00 <= codepoint <= 0xD7A3:
        return "LV" if (codepoint - 0xAC00) % 28 == 0 else "LVT"
    return None


def _should_join(text: str, cluster_start: int, boundary: int) -> bool:
    previous = text[boundary - 1]
    current = text[boundary]

    if previous == "\r" and current == "\n":
        return True
    if _is_control(previous) or _is_control(current):
        return False

    previous_hangul = _hangul_class(previous)
    current_hangul = _hangul_class(current)
    if previous_hangul == "L" and current_hangul in {"L", "V", "LV", "LVT"}:
        return True
    if previous_hangul in {"LV", "V"} and current_hangul in {"V", "T"}:
        return True
    if previous_hangul in {"LVT", "T"} and current_hangul == "T":
        return True

    if _is_extend(current) or _is_spacing_mark(current) or current == "\u200d":
        return True
    if _is_prepend(previous):
        return True

    if previous == "\u200d" and _is_extended_pictographic(current):
        return any(_is_extended_pictographic(char) for char in text[cluster_start : boundary - 1])

    if (
        unicodedata.category(current).startswith("L")
        and any(_is_virama(char) for char in text[cluster_start:boundary])
    ):
        return True

    if _is_regional_indicator(previous) and _is_regional_indicator(current):
        regional_count = sum(
            _is_regional_indicator(char) for char in text[cluster_start:boundary]
        )
        return regional_count % 2 == 1

    if _is_virama(previous) and unicodedata.category(current).startswith("L"):
        return True
    return False


def _grapheme_clusters(text: str) -> List[_Cluster]:
    clusters: List[_Cluster] = []
    start = 0
    index = 0
    while index < len(text):
        index += 1
        while index < len(text) and _should_join(text, start, index):
            index += 1
        clusters.append(_Cluster(start, index))
        start = index
    return clusters


def _is_break_space(value: str) -> bool:
    return bool(value) and all(
        char.isspace() and char not in "\r\n\u00a0\u202f" for char in value
    )


def _is_ideographic(char: str) -> bool:
    codepoint = ord(char)
    return (
        0x2E80 <= codepoint <= 0x9FFF
        or 0xF900 <= codepoint <= 0xFAFF
        or 0x20000 <= codepoint <= 0x323AF
    )


def _line_break_allowed(previous: str, current: str) -> bool:
    if not previous or not current:
        return False
    previous_char = previous[-1]
    current_char = current[0]
    if (
        unicodedata.category(current_char) in {"Pe", "Pf"}
        or current_char in _CLOSING_PUNCTUATION
        or current_char in "!?;:,\u3001\u3002"
    ):
        return False
    if (
        unicodedata.category(previous_char) in {"Ps", "Pi"}
        or previous_char in _OPENING_PUNCTUATION
    ):
        return False
    if _is_break_space(previous):
        return True
    if previous_char in _BREAK_AFTER:
        return True
    if _is_ideographic(previous_char) or _is_ideographic(current_char):
        return True
    if previous_char == "\u200b":
        return True
    return False


def _break_boundaries(text: str, clusters: Sequence[_Cluster]) -> Set[int]:
    boundaries: Set[int] = set()
    for left, right in zip(clusters, clusters[1:]):
        previous = text[left.start : left.end]
        current = text[right.start : right.end]
        if _line_break_allowed(previous, current):
            boundaries.add(left.end)
    return boundaries


def _default_measure(
    widths: Sequence[float], text: str, start: int, end: int, letter_spacing: float
) -> float:
    glyph_count = sum(char not in "\r\n" for char in text[start:end])
    return sum(widths[start:end]) + letter_spacing * max(0, glyph_count - 1)


def _wrap_segment(
    text: str,
    chars: List[str],
    clusters: Sequence[_Cluster],
    start: int,
    end: int,
    max_width: float,
    measure: Callable[[int, int], float],
    boundaries: Set[int],
) -> None:
    if start >= end:
        return

    index_by_start = {cluster.start: index for index, cluster in enumerate(clusters)}
    index = index_by_start[start]
    line_start = start
    last_fitting_break: Optional[int] = None

    while index < len(clusters) and clusters[index].end <= end:
        cluster = clusters[index]
        candidate_end = cluster.end
        candidate_width = measure(line_start, candidate_end)

        if candidate_end in boundaries:
            break_end = (
                cluster.start
                if _is_break_space(text[cluster.start : cluster.end])
                else candidate_end
            )
            if measure(line_start, break_end) <= max_width:
                last_fitting_break = candidate_end

        if candidate_width > max_width:
            if last_fitting_break is None or last_fitting_break <= line_start:
                excerpt = text[line_start:candidate_end]
                raise UnbreakableTextError(
                    f"unbreakable text segment exceeds width {max_width}: {excerpt!r}"
                )
            break_at = last_fitting_break
            if _is_break_space(text[break_at - 1 : break_at]):
                chars[break_at - 1] = "\n"
            line_start = break_at
            index = index_by_start[line_start]
            last_fitting_break = None
            continue

        index += 1


def wrap_text(
    text: str,
    widths: Sequence[float],
    max_width: float,
    *,
    letter_spacing: float = 0.0,
    measure: Optional[Callable[[int, int], float]] = None,
) -> str:
    """Greedy wrapping at UAX-style opportunities and grapheme boundaries.

    The returned transient renderer text keeps code-point indices stable:
    only a breakable source whitespace character is replaced by ``"\\n"``.
    Public JSON content is never changed by this adapter.
    """
    if not text:
        return text
    if measure is None:
        if len(widths) != len(text):
            raise ValueError("widths must contain one advance per text code point")
        measure = lambda start, end: _default_measure(
            widths, text, start, end, letter_spacing
        )

    clusters = _grapheme_clusters(text)
    boundaries = _break_boundaries(text, clusters)
    chars = list(text)
    segment_start = 0

    for cluster in clusters:
        cluster_text = text[cluster.start : cluster.end]
        if "\n" not in cluster_text and "\r" not in cluster_text:
            continue
        _wrap_segment(
            text,
            chars,
            clusters,
            segment_start,
            cluster.start,
            max_width,
            measure,
            boundaries,
        )
        segment_start = cluster.end

    _wrap_segment(
        text,
        chars,
        clusters,
        segment_start,
        len(text),
        max_width,
        measure,
        boundaries,
    )
    return "".join(chars)


def visual_line_count(text: str) -> int:
    """Count visual lines, including forced empty and trailing lines."""
    return text.count("\n") + 1


def enforce_text_limits(
    text: str,
    font_size: float,
    line_height: float,
    max_lines: Optional[int],
    element_height: float,
) -> None:
    """Reject line-count and line-box overflow using renderer font semantics."""
    lines = visual_line_count(text)
    if max_lines is not None and lines > int(max_lines):
        raise TextOverflowError(f"text uses {lines} visual lines; max_lines is {max_lines}")

    rendered_font_size = int(font_size)
    line_box_height = lines * rendered_font_size * float(line_height)
    if line_box_height > float(element_height):
        raise TextOverflowError(
            f"text line boxes require {line_box_height:g}px; element height is {element_height:g}px"
        )
