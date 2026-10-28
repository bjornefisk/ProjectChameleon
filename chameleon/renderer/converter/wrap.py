"""Unicode-safe text measurement and deterministic greedy wrapping."""

from dataclasses import dataclass
from functools import lru_cache
from typing import Callable, FrozenSet, List, Optional, Sequence, Set, Tuple

import skia  # type: ignore

from cr_renderer.fonts import FontManager
from .brand_fonts import lookup_exact_font
from .unicode_data import (
    EAST_ASIAN_WIDTH_RANGES,
    EXTENDED_PICTOGRAPHIC_RANGES,
    GENERAL_CATEGORY_RANGES,
    GRAPHEME_BREAK_RANGES,
    INDIC_CONJUNCT_BREAK_RANGES,
    LINE_BREAK_RANGES,
    property_for,
)


class TextLayoutError(ValueError):
    """Base class for deterministic renderer text-layout failures."""


class MalformedTextError(TextLayoutError):
    """Raised when text metadata violates the renderer input contract."""


class UnbreakableTextError(TextLayoutError):
    """Raised when a grapheme-safe segment cannot fit the element width."""


class TextOverflowError(TextLayoutError):
    """Raised when wrapped text exceeds a hard line or height limit."""


@dataclass(frozen=True)
class _Cluster:
    start: int
    end: int


def _collapse_crlf(text: str) -> tuple[str, List[int]]:
    """Return one transient line-feed code point for each CRLF pair.

    CRLF is one UAX #14 mandatory break.  The renderer receives transient
    text, so collapsing the pair prevents the upstream explicit-line path
    from rendering an extra empty line.  The returned source indices let the
    converter project style maps back onto the shortened transient string.
    """
    if "\r\n" not in text:
        return text, list(range(len(text)))

    chars: List[str] = []
    source_indices: List[int] = []
    index = 0
    while index < len(text):
        if text[index] == "\r" and index + 1 < len(text) and text[index + 1] == "\n":
            chars.append("\n")
            source_indices.append(index)
            index += 2
            continue
        chars.append(text[index])
        source_indices.append(index)
        index += 1
    return "".join(chars), source_indices



@lru_cache(maxsize=512)
def _cached_char_widths(
    ttf_bytes: bytes, size: int, text: str
) -> Tuple[float, ...]:
    typeface = skia.Typeface.MakeFromData(ttf_bytes)
    font = skia.Font(typeface, size)
    glyphs = font.textToGlyphs(text)
    widths = list(font.getWidths(glyphs))
    if len(widths) < len(text):
        widths.extend([0.0] * (len(text) - len(widths)))
    return tuple(widths[: len(text)])


def char_widths(
    font_manager: FontManager, family: str, weight: str, style: str, size: float, text: str
) -> List[float]:
    """Return glyph advances using the pinned renderer's Skia path."""
    if not text:
        return []
    ttf_bytes = lookup_exact_font(font_manager, family, weight, style)
    return list(_cached_char_widths(ttf_bytes, int(size), text))


def _grapheme_break_property(char: str) -> str:
    return property_for(ord(char), GRAPHEME_BREAK_RANGES, "Other")


def _is_control(char: str) -> bool:
    return _grapheme_break_property(char) in {"Control", "CR", "LF"}


def _is_extend(char: str) -> bool:
    return _grapheme_break_property(char) == "Extend"


def _is_spacing_mark(char: str) -> bool:
    return _grapheme_break_property(char) == "SpacingMark"


def _is_prepend(char: str) -> bool:
    return _grapheme_break_property(char) == "Prepend"


def _is_regional_indicator(char: str) -> bool:
    return _grapheme_break_property(char) == "Regional_Indicator"


def _is_extended_pictographic(char: str) -> bool:
    return property_for(ord(char), EXTENDED_PICTOGRAPHIC_RANGES, "No") == "Extended_Pictographic"


def _indic_conjunct_break_property(char: str) -> str:
    return property_for(ord(char), INDIC_CONJUNCT_BREAK_RANGES, "None")


def _is_incb_linker(char: str) -> bool:
    return _indic_conjunct_break_property(char) == "Linker"


def _is_incb_consonant(char: str) -> bool:
    return _indic_conjunct_break_property(char) == "Consonant"


def _is_incb_extend(char: str) -> bool:
    return _indic_conjunct_break_property(char) == "Extend"


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
        index = boundary - 2
        while index >= cluster_start and _is_extend(text[index]):
            index -= 1
        return index >= cluster_start and _is_extended_pictographic(text[index])

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


def _line_break_property(char: str) -> str:
    return property_for(ord(char), LINE_BREAK_RANGES, "XX")


def _general_category(char: str) -> str:
    return property_for(ord(char), GENERAL_CATEGORY_RANGES, "Cn")


def _east_asian_width(char: str) -> str:
    return property_for(ord(char), EAST_ASIAN_WIDTH_RANGES, "N")


def _resolved_line_break_class(char: str) -> str:
    value = _line_break_property(char)
    if value in {"AI", "SG", "XX"}:
        return "AL"
    if value == "SA":
        return "CM" if _general_category(char) in {"Mn", "Mc"} else "AL"
    if value == "CJ":
        return "NS"
    return value


def _cluster_line_break_class(value: str) -> str:
    for index, char in enumerate(value):
        line_class = _resolved_line_break_class(char)
        if index and line_class in {"CM", "ZWJ"}:
            previous_class = _resolved_line_break_class(value[index - 1])
            if previous_class not in {"BK", "CR", "LF", "NL", "SP", "ZW"}:
                continue
        if line_class not in {"CM", "ZWJ"}:
            return line_class
    return "AL"


def _mandatory_break_ranges(text: str) -> List[Tuple[int, int]]:
    ranges: List[Tuple[int, int]] = []
    index = 0
    while index < len(text):
        line_class = _line_break_property(text[index])
        if line_class == "CR":
            end = index + 2 if index + 1 < len(text) and _line_break_property(text[index + 1]) == "LF" else index + 1
        elif line_class in {"BK", "LF", "NL"}:
            end = index + 1
        else:
            index += 1
            continue
        ranges.append((index, end))
        index = end
    return ranges


def _is_break_space(value: str) -> bool:
    return bool(value) and all(_line_break_property(char) == "SP" for char in value)


def _cluster_has_property(value: str, line_class: str) -> bool:
    return any(_line_break_property(char) == line_class for char in value)


def _is_east_asian(value: str) -> bool:
    return any(_east_asian_width(char) in {"F", "W", "H"} for char in value)


def _previous_non_space(classes: Sequence[str], index: int) -> Optional[int]:
    index -= 1
    while index >= 0 and classes[index] == "SP":
        index -= 1
    return index if index >= 0 else None


def _next_non_space(classes: Sequence[str], index: int) -> Optional[int]:
    index += 1
    while index < len(classes) and classes[index] == "SP":
        index += 1
    return index if index < len(classes) else None


def _line_break_allowed(
    classes: Sequence[str], cluster_texts: Sequence[str], boundary: int
) -> bool:
    previous_class = classes[boundary - 1]
    current_class = classes[boundary]
    previous = cluster_texts[boundary - 1]
    current = cluster_texts[boundary]

    if current_class in {"BK", "CR", "LF", "NL", "SP", "ZW"}:
        return False
    if previous_class in {"BK", "CR", "LF", "NL"}:
        return False
    if previous_class == "WJ" or current_class == "WJ":
        return False
    if _cluster_has_property(previous, "ZWJ") or _cluster_has_property(current, "ZWJ"):
        return False
    if previous_class == "GL":
        return False
    if current_class == "GL" and previous_class not in {"SP", "BA", "HY", "HH"}:
        return False

    previous_non_space = _previous_non_space(classes, boundary)
    next_non_space = _next_non_space(classes, boundary - 1)

    if current_class in {"CL", "CP", "EX", "SY"}:
        return False
    if previous_class == "OP":
        return False
    if previous_class == "SP" and previous_non_space is not None:
        if classes[previous_non_space] == "OP":
            return False
    if current_class == "IS":
        if previous_class == "SP" and next_non_space is not None and classes[next_non_space] == "NU":
            return True
        return False
    if current_class == "NS" and previous_non_space is not None:
        if classes[previous_non_space] in {"CL", "CP"}:
            return False
    if current_class == "B2" and previous_non_space is not None:
        if classes[previous_non_space] == "B2":
            return False
    if previous_class == "QU" or current_class == "QU":
        return False
    if previous_class == "CB" or current_class == "CB":
        return True
    if previous_class == "SP":
        return True

    before_previous = (
        classes[previous_non_space - 1]
        if previous_non_space is not None and previous_non_space > 0
        else None
    )
    if (
        previous_class in {"HY", "HH"}
        and current_class in {"AL", "HL"}
        and before_previous in {None, "BK", "CR", "LF", "NL", "SP", "ZW", "CB", "GL"}
    ):
        return False
    if current_class in {"BA", "HH", "HY", "NS"} or previous_class == "BB":
        return False
    if previous_class == "SY" and current_class == "HL":
        return False
    if previous_class == "HL" and current_class in {"HY", "HH"}:
        following = next_non_space
        if following is None or classes[following] != "HL":
            return False
    if current_class == "IN":
        return False

    if (
        previous_class in {"AL", "HL"} and current_class == "NU"
        or previous_class == "NU" and current_class in {"AL", "HL"}
    ):
        return False
    if (
        previous_class in {"PR", "PO"} and current_class in {"AL", "HL", "NU", "OP"}
        or previous_class in {"AL", "HL"} and current_class in {"PR", "PO"}
        or previous_class == "NU" and current_class in {"PR", "PO", "CL", "CP"}
        or previous_class in {"PR", "PO"} and current_class == "NU"
        or previous_class in {"HY", "IS", "SY"} and current_class == "NU"
        or previous_class == "NU" and current_class == "NU"
    ):
        return False
    if (
        previous_class in {"PR", "PO"} and current_class in {"ID", "EB", "EM"}
        or previous_class in {"ID", "EB", "EM"} and current_class == "PO"
    ):
        return False

    if (
        previous_class == "JL" and current_class in {"JL", "JV", "H2", "H3"}
        or previous_class in {"JV", "H2"} and current_class in {"JV", "JT"}
        or previous_class in {"JT", "H3"} and current_class == "JT"
    ):
        return False
    if (
        previous_class in {"JL", "JV", "JT", "H2", "H3"} and current_class == "PO"
        or previous_class == "PR" and current_class in {"JL", "JV", "JT", "H2", "H3"}
    ):
        return False
    if previous_class in {"AL", "HL"} and current_class in {"AL", "HL"}:
        return False
    if previous_class == "IS" and current_class in {"AL", "HL"}:
        return False

    if current_class == "OP" and previous_class in {"AL", "HL", "NU"}:
        if not _is_east_asian(current):
            return False
    if previous_class == "CP" and current_class in {"AL", "HL", "NU"}:
        if not _is_east_asian(previous):
            return False
    if previous_class == "RI" and current_class == "RI":
        regional_count = 0
        index = boundary - 1
        while index >= 0 and classes[index] == "RI":
            regional_count += sum(
                _is_regional_indicator(char) for char in cluster_texts[index]
            )
            index -= 1
        return regional_count % 2 == 0
    if current_class == "EM" and (
        previous_class == "EB" or _is_extended_pictographic(previous[0])
    ):
        return False
    return True


def _break_boundaries(text: str, clusters: Sequence[_Cluster]) -> Set[int]:
    boundaries: Set[int] = set()
    cluster_texts = [text[cluster.start : cluster.end] for cluster in clusters]
    classes = [_cluster_line_break_class(value) for value in cluster_texts]
    for index, left in enumerate(clusters[:-1]):
        if _line_break_allowed(classes, cluster_texts, index + 1):
            boundaries.add(left.end)
    return boundaries


@lru_cache(maxsize=128)
def _line_break_data(text: str) -> Tuple[Tuple[_Cluster, ...], FrozenSet[int]]:
    """Reuse content-only Unicode segmentation across width and font probes."""
    clusters = tuple(_grapheme_clusters(text))
    return clusters, frozenset(_break_boundaries(text, clusters))


def _default_measure(
    widths: Sequence[float], text: str, start: int, end: int, letter_spacing: float
) -> float:
    glyph_count = sum(
        _line_break_property(char) not in {"BK", "CR", "LF", "NL"}
        for char in text[start:end]
    )
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

    The text preserves source code points except that a CRLF pair becomes one
    transient line-feed code point. Breakable spaces and mandatory separators
    may become ``"\\n"`` for the renderer, while non-space UAX #14 breaks stay
    in place and are represented only by the line map.
    """
    if not text:
        return text, [0], 1

    original_text = text
    if measure is None and len(widths) != len(original_text):
        raise ValueError("widths must contain one advance per text code point")

    text, source_indices = _collapse_crlf(original_text)
    if text != original_text:
        if measure is not None:
            original_measure = measure

            def normalized_measure(start: int, end: int) -> float:
                if start >= end:
                    return 0.0
                return original_measure(source_indices[start], source_indices[end - 1] + 1)

            measure = normalized_measure
        if len(widths) == len(original_text):
            widths = [
                widths[index] + (
                    widths[index + 1]
                    if index + 1 < len(original_text)
                    and original_text[index] == "\r"
                    and original_text[index + 1] == "\n"
                    else 0
                )
                for index in source_indices
            ]
        else:
            widths = ()

    if measure is None:
        if len(widths) != len(text):
            raise ValueError("widths must contain one advance per text code point")
        measure = lambda start, end: _default_measure(
            widths, text, start, end, letter_spacing
        )

    clusters, boundaries = _line_break_data(text)
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
