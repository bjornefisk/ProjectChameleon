"""Unicode-safe text measurement and deterministic greedy wrapping."""

from dataclasses import dataclass
import unicodedata
from typing import Callable, List, Optional, Sequence, Set, Tuple

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

# These are the Unicode 17.0 Indic_Conjunct_Break values from
# DerivedCoreProperties.txt, used by UAX #29 GB9c. Keeping the versioned
# data local avoids adding a runtime Unicode dependency.
# Source: https://www.unicode.org/Public/17.0.0/ucd/DerivedCoreProperties.txt
_INCB_LINKERS = frozenset(
    {
        0x094D,
        0x09CD,
        0x0ACD,
        0x0B4D,
        0x0C4D,
        0x0D4D,
        0x1039,
        0x17D2,
        0x1A60,
        0x1B44,
        0x1BAB,
        0xA9C0,
        0xAAF6,
        0x10A3F,
        0x11133,
        0x113D0,
        0x1193E,
        0x11A47,
        0x11A99,
        0x11F42,
    }
)
_INCB_CONSONANT_RANGES = (
    (0x0915, 0x0939),
    (0x0958, 0x095F),
    (0x0978, 0x097F),
    (0x0995, 0x09A8),
    (0x09AA, 0x09B0),
    (0x09B2, 0x09B2),
    (0x09B6, 0x09B9),
    (0x09DC, 0x09DD),
    (0x09DF, 0x09DF),
    (0x09F0, 0x09F1),
    (0x0A95, 0x0AA8),
    (0x0AAA, 0x0AB0),
    (0x0AB2, 0x0AB3),
    (0x0AB5, 0x0AB9),
    (0x0AF9, 0x0AF9),
    (0x0B15, 0x0B28),
    (0x0B2A, 0x0B30),
    (0x0B32, 0x0B33),
    (0x0B35, 0x0B39),
    (0x0B5C, 0x0B5D),
    (0x0B5F, 0x0B5F),
    (0x0B71, 0x0B71),
    (0x0C15, 0x0C28),
    (0x0C2A, 0x0C39),
    (0x0C58, 0x0C5A),
    (0x0D15, 0x0D3A),
    (0x1000, 0x102A),
    (0x103F, 0x103F),
    (0x1050, 0x1055),
    (0x105A, 0x105D),
    (0x1061, 0x1061),
    (0x1065, 0x1066),
    (0x106E, 0x1070),
    (0x1075, 0x1081),
    (0x108E, 0x108E),
    (0x1780, 0x17B3),
    (0x1A20, 0x1A54),
    (0x1B0B, 0x1B0C),
    (0x1B13, 0x1B33),
    (0x1B45, 0x1B4C),
    (0x1B83, 0x1BA0),
    (0x1BAE, 0x1BAF),
    (0x1BBB, 0x1BBD),
    (0xA989, 0xA98B),
    (0xA98F, 0xA9B2),
    (0xA9E0, 0xA9E4),
    (0xA9E7, 0xA9EF),
    (0xA9FA, 0xA9FE),
    (0xAA60, 0xAA6F),
    (0xAA71, 0xAA73),
    (0xAA7A, 0xAA7A),
    (0xAA7E, 0xAA7F),
    (0xAAE0, 0xAAEA),
    (0xABC0, 0xABDA),
    (0x10A00, 0x10A00),
    (0x10A10, 0x10A13),
    (0x10A15, 0x10A17),
    (0x10A19, 0x10A35),
    (0x11103, 0x11126),
    (0x11144, 0x11144),
    (0x11147, 0x11147),
    (0x11380, 0x11389),
    (0x1138B, 0x1138B),
    (0x1138E, 0x1138E),
    (0x11390, 0x113B5),
    (0x11900, 0x11906),
    (0x11909, 0x11909),
    (0x1190C, 0x11913),
    (0x11915, 0x11916),
    (0x11918, 0x1192F),
    (0x11A00, 0x11A00),
    (0x11A0B, 0x11A32),
    (0x11A50, 0x11A50),
    (0x11A5C, 0x11A83),
    (0x11F04, 0x11F10),
    (0x11F12, 0x11F33),
)
_MANDATORY_BREAKS = frozenset("\n\v\f\x85\u2028\u2029")
_MANDATORY_BREAK_CHARS = _MANDATORY_BREAKS | {"\r"}


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
    return char in _MANDATORY_BREAK_CHARS or unicodedata.category(char) == "Cc"


def _is_extend(char: str) -> bool:
    codepoint = ord(char)
    return (
        unicodedata.category(char).startswith("M")
        or char == "\u200c"
        or 0xFE00 <= codepoint <= 0xFE0F
        or 0xE0100 <= codepoint <= 0xE01EF
        or 0x1F3FB <= codepoint <= 0x1F3FF
        or 0xE0020 <= codepoint <= 0xE007F
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


def _is_incb_linker(char: str) -> bool:
    return ord(char) in _INCB_LINKERS


def _is_incb_consonant(char: str) -> bool:
    codepoint = ord(char)
    return any(start <= codepoint <= end for start, end in _INCB_CONSONANT_RANGES)


def _is_incb_extend(char: str) -> bool:
    return _is_extend(char) and not _is_incb_linker(char)


def _joins_indic_conjunct(text: str, cluster_start: int, boundary: int) -> bool:
    """Apply UAX #29 Indic_Conjunct_Break data at one boundary."""
    current = text[boundary]
    if not _is_incb_consonant(current):
        return False

    index = boundary - 1
    while index >= cluster_start and _is_incb_extend(text[index]):
        index -= 1
    if index < cluster_start or not _is_incb_linker(text[index]):
        return False

    index -= 1
    while index >= cluster_start and _is_incb_extend(text[index]):
        index -= 1
    return index >= cluster_start and _is_incb_consonant(text[index])


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

    if _is_extend(current) or _is_spacing_mark(current) or _is_incb_linker(current):
        return True
    if _is_prepend(previous):
        return True

    if previous == "\u200d" and _is_extended_pictographic(current):
        return any(_is_extended_pictographic(char) for char in text[cluster_start : boundary - 1])

    if _joins_indic_conjunct(text, cluster_start, boundary):
        return True

    if _is_regional_indicator(previous) and _is_regional_indicator(current):
        regional_count = sum(
            _is_regional_indicator(char) for char in text[cluster_start:boundary]
        )
        return regional_count % 2 == 1

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


def _mandatory_break_ranges(text: str) -> List[Tuple[int, int]]:
    ranges: List[Tuple[int, int]] = []
    index = 0
    while index < len(text):
        char = text[index]
        if char == "\r":
            end = index + 2 if index + 1 < len(text) and text[index + 1] == "\n" else index + 1
        elif char in _MANDATORY_BREAKS:
            end = index + 1
        else:
            index += 1
            continue
        ranges.append((index, end))
        index = end
    return ranges


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
    glyph_count = sum(char not in _MANDATORY_BREAK_CHARS for char in text[start:end])
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
) -> List[int]:
    if start >= end:
        return []

    index_by_start = {cluster.start: index for index, cluster in enumerate(clusters)}
    index = index_by_start[start]
    line_start = start
    last_fitting_break: Optional[Tuple[int, int]] = None
    selected_breaks: List[int] = []

    while index < len(clusters) and clusters[index].end <= end:
        cluster = clusters[index]
        candidate_end = cluster.end
        candidate_width = measure(line_start, candidate_end)

        if candidate_end in boundaries:
            break_start = (
                cluster.start
                if _is_break_space(text[cluster.start : cluster.end])
                else candidate_end
            )
            if break_start > line_start and measure(line_start, break_start) <= max_width:
                last_fitting_break = (candidate_end, break_start)

        if candidate_width > max_width:
            if last_fitting_break is None:
                excerpt = text[line_start:candidate_end]
                raise UnbreakableTextError(
                    f"unbreakable text segment exceeds width {max_width}: {excerpt!r}"
                )
            break_at, line_break = last_fitting_break
            if line_break < break_at:
                for character_index in range(line_break, break_at):
                    chars[character_index] = "\n"
            selected_breaks.append(line_break)
            line_start = break_at
            index = index_by_start.get(line_start, len(clusters))
            last_fitting_break = None
            continue

        index += 1

    return selected_breaks


def _assign_segment_lines(
    line_indices: List[int],
    start: int,
    end: int,
    start_line: int,
    break_starts: Sequence[int],
) -> int:
    break_index = 0
    current_line = start_line
    for index in range(start, end):
        while break_index < len(break_starts) and break_starts[break_index] <= index:
            current_line = start_line + break_index + 1
            break_index += 1
        line_indices[index] = current_line
    return start_line + len(break_starts)


def wrap_text_with_line_map(
    text: str,
    widths: Sequence[float],
    max_width: float,
    *,
    letter_spacing: float = 0.0,
    measure: Optional[Callable[[int, int], float]] = None,
) -> Tuple[str, List[int], int]:
    """Return transient text, its upstream line map, and visual line count.

    The text keeps one code point per source code point. A breakable source
    space and a mandatory line separator may become ``"\\n"`` for the
    renderer, while non-space UAX #14 breaks stay in place and are represented
    only by the line map.
    """
    if not text:
        return text, [0], 1
    if measure is None:
        if len(widths) != len(text):
            raise ValueError("widths must contain one advance per text code point")
        measure = lambda start, end: _default_measure(
            widths, text, start, end, letter_spacing
        )

    clusters = _grapheme_clusters(text)
    boundaries = _break_boundaries(text, clusters)
    chars = list(text)
    line_indices = [0] * len(text)
    current_line = 0
    segment_start = 0

    for break_start, break_end in _mandatory_break_ranges(text):
        segment_breaks = _wrap_segment(
            text,
            chars,
            clusters,
            segment_start,
            break_start,
            max_width,
            measure,
            boundaries,
        )
        current_line = _assign_segment_lines(
            line_indices,
            segment_start,
            break_start,
            current_line,
            segment_breaks,
        )

        has_content_before_break = break_start > segment_start
        break_line = current_line + 1 if has_content_before_break else current_line
        for index in range(break_start, break_end):
            chars[index] = "\n"
            line_indices[index] = break_line
        current_line = break_line
        if not has_content_before_break:
            current_line += 1
        segment_start = break_end

    segment_breaks = _wrap_segment(
        text,
        chars,
        clusters,
        segment_start,
        len(text),
        max_width,
        measure,
        boundaries,
    )
    current_line = _assign_segment_lines(
        line_indices,
        segment_start,
        len(text),
        current_line,
        segment_breaks,
    )

    line_count = current_line + 1
    if line_indices and line_indices[-1] < line_count - 1:
        line_indices.append(line_count - 1)
    return "".join(chars), line_indices, line_count


def wrap_text(
    text: str,
    widths: Sequence[float],
    max_width: float,
    *,
    letter_spacing: float = 0.0,
    measure: Optional[Callable[[int, int], float]] = None,
) -> str:
    """Greedy wrapping at UAX-style opportunities and grapheme boundaries."""
    return wrap_text_with_line_map(
        text,
        widths,
        max_width,
        letter_spacing=letter_spacing,
        measure=measure,
    )[0]


def visual_line_count(text: str) -> int:
    """Count visual lines, treating CRLF as one mandatory break."""
    return len(_mandatory_break_ranges(text)) + 1


def enforce_text_limits(
    text: str,
    font_size: float,
    line_height: float,
    max_lines: Optional[int],
    element_height: float,
    line_count: Optional[int] = None,
) -> None:
    """Reject line-count and line-box overflow using renderer font semantics."""
    lines = visual_line_count(text) if line_count is None else line_count
    if max_lines is not None and lines > int(max_lines):
        raise TextOverflowError(f"text uses {lines} visual lines; max_lines is {max_lines}")

    rendered_font_size = int(font_size)
    line_box_height = lines * rendered_font_size * float(line_height)
    if line_box_height > float(element_height):
        raise TextOverflowError(
            f"text line boxes require {line_box_height:g}px; element height is {element_height:g}px"
        )
