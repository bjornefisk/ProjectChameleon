"""Load a brand-kit fonts folder into a `cr_renderer.fonts.FontManager`.

The brand kit ships plain `.ttf`/`.otf` files named `<Family>-<Suffix>.ttf`
(e.g. `SolsticeSans-BoldItalic.ttf`), not the `fonts.pickle` cr-renderer's
`FontManager` normally downloads from Hugging Face. This module scans that
folder into the same in-memory shape `FontManager` uses internally
(`{normalized_family: [{"fontFamily", "fontWeight", "fontStyle", "bytes"}]}`)
and hands it to a `FontManager` instance directly. It validates filename and
embedded metadata, rejects duplicate mappings, and keeps exact face lookup
fail-closed without silent substitution or network access.
"""

import re
from pathlib import Path
from typing import Any, Dict, List, Tuple

import skia
from cr_renderer.fonts import FONT_WEIGHTS, FontManager, normalize_family

_CAMEL_SPLIT_RE = re.compile(r"(?<!^)(?=[A-Z])")
_ITALIC_RE = re.compile("italic", re.IGNORECASE)
_FONT_EXTENSIONS = {".ttf", ".otf"}
_ITALIC_STYLES = {"italic", "bolditalic"}
_WEIGHT_VALUES = {
    "thin": 100,
    "extralight": 200,
    "light": 300,
    "regular": 400,
    "medium": 500,
    "semibold": 600,
    "bold": 700,
    "extrabold": 800,
    "black": 900,
}


class MissingFontError(FileNotFoundError):
    """Raised when a requested local font family or face is unavailable."""


def _validate_embedded_metadata(
    path: Path,
    family: str,
    weight: str,
    style: str,
    font_bytes: bytes,
) -> None:
    typeface = skia.Typeface.MakeFromData(font_bytes)
    if typeface is None:
        raise MissingFontError(f"font file is invalid: {path.name}")
    if normalize_family(typeface.getFamilyName()) != normalize_family(family):
        raise MissingFontError(
            f"font family metadata does not match filename: {path.name}"
        )
    font_style = typeface.fontStyle()
    if font_style.weight() != _WEIGHT_VALUES[weight]:
        raise MissingFontError(
            f"font weight metadata does not match filename: {path.name}"
        )
    if (font_style.slant() == skia.FontStyle.kItalic_Slant) != (
        style in _ITALIC_STYLES
    ):
        raise MissingFontError(
            f"font style metadata does not match filename: {path.name}"
        )


def lookup_exact_font(
    font_manager: FontManager, family: str, weight: str, style: str
) -> bytes:
    """Return requested face bytes without using upstream fallback behavior."""
    font_dict = getattr(font_manager, "_fonts", None)
    if not isinstance(font_dict, dict):
        raise MissingFontError("font manager has no local font dictionary")
    normalized_family = normalize_family(family)
    for face in font_dict.get(normalized_family, []):
        if face.get("fontWeight") == weight and face.get("fontStyle") == style:
            return face["bytes"]
    raise MissingFontError(
        f"font face is unavailable: family={family!r}, weight={weight!r}, style={style!r}"
    )


def _split_family_suffix(stem: str) -> Tuple[str, str]:
    prefix, _, suffix = stem.partition("-")
    family = _CAMEL_SPLIT_RE.sub(" ", prefix).strip()
    return family, suffix


def _suffix_to_weight_style(suffix: str) -> Tuple[str, str]:
    suffix = suffix or "Regular"
    is_italic = bool(_ITALIC_RE.search(suffix))
    weight_token = _ITALIC_RE.sub("", suffix).strip().lower() or "regular"
    if weight_token not in FONT_WEIGHTS:
        raise MissingFontError(f"unsupported font filename suffix: {suffix!r}")
    weight = weight_token
    if is_italic:
        style = "bolditalic" if weight == "bold" else "italic"
    else:
        style = "bold" if weight == "bold" else "regular"
    return weight, style


def build_font_dict(fonts_dir: str) -> Dict[str, List[Dict[str, Any]]]:
    """Scan a flat directory of brand-kit font files into a `FontDict`."""
    font_dict: Dict[str, List[Dict[str, Any]]] = {}
    seen_faces: Dict[Tuple[str, str, str], Path] = {}
    for path in sorted(Path(fonts_dir).glob("*")):
        if path.suffix.lower() not in _FONT_EXTENSIONS:
            continue
        family, suffix = _split_family_suffix(path.stem)
        weight, style = _suffix_to_weight_style(suffix)
        key = normalize_family(family)
        face_key = (key, weight, style)
        previous_path = seen_faces.get(face_key)
        if previous_path is not None:
            raise MissingFontError(
                f"duplicate font face mapping: {previous_path.name} and {path.name}"
            )
        font_bytes = path.read_bytes()
        _validate_embedded_metadata(path, family, weight, style, font_bytes)
        seen_faces[face_key] = path
        font_dict.setdefault(key, []).append(
            {
                "fontFamily": family,
                "fontWeight": weight,
                "fontStyle": style,
                "bytes": font_bytes,
            }
        )
    return font_dict


def load_brand_font_manager(fonts_dir: str) -> FontManager:
    """Build a `FontManager` populated from local brand-kit font files."""
    font_dict = build_font_dict(fonts_dir)
    if not font_dict:
        raise FileNotFoundError(f"No .ttf/.otf font files found in: {fonts_dir}")
    manager = FontManager.__new__(FontManager)
    manager._fonts = font_dict
    return manager
