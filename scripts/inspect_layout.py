#!/usr/bin/env python3
"""
Terminal Layout Visualizer for Project Chameleon.
Allows AI subagents and human engineers to 'see' element positions,
boundaries, and collisions directly in terminal output.
"""

import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple


def calculate_aabb(el: Dict[str, Any]) -> Tuple[float, float, float, float]:
    """Calculate axis-aligned bounding box (min_x, min_y, max_x, max_y)."""
    import math

    x = float(el.get("x", 0.0))
    y = float(el.get("y", 0.0))
    w = float(el.get("width", 0.0))
    h = float(el.get("height", 0.0))
    rot_deg = float(el.get("rotation", 0.0))

    if rot_deg == 0:
        return x, y, x + w, y + h

    rad = math.radians(rot_deg)
    cx = x + w / 2.0
    cy = y + h / 2.0
    a = abs(w * math.cos(rad)) + abs(h * math.sin(rad))
    b = abs(w * math.sin(rad)) + abs(h * math.cos(rad))
    return cx - a / 2.0, cy - b / 2.0, cx + a / 2.0, cy + b / 2.0

def _background_ids(source: Dict[str, Any] | None) -> set[str]:
    """Return the contract-qualified source background, if source context exists."""

    if not isinstance(source, dict):
        return set()
    canvas = source.get("canvas")
    elements = source.get("elements")
    if not isinstance(canvas, dict) or not isinstance(elements, list):
        return set()

    width = float(canvas.get("width", 0))
    height = float(canvas.get("height", 0))
    candidates = []
    for index, element in enumerate(elements):
        if not isinstance(element, dict):
            continue
        if element.get("type") != "image" or element.get("fit") != "cover":
            continue
        min_x, min_y, max_x, max_y = calculate_aabb(element)
        if min_x > 0 or min_y > 0 or max_x < width or max_y < height:
            continue
        area = (max_x - min_x) * (max_y - min_y)
        candidates.append(
            (
                element.get("z_index", 0),
                -area,
                index,
                element.get("id"),
            )
        )
    if not candidates:
        return set()
    return {min(candidates)[3]}


def _foreground_elements(
    elements: List[Dict[str, Any]], background_ids: set[str] | None = None
) -> List[Dict[str, Any]]:
    background_ids = background_ids or set()
    return [
        element
        for element in elements
        if element.get("id") not in background_ids
    ]


def check_collisions(
    elements: List[Dict[str, Any]], background_ids: set[str] | None = None
) -> List[str]:
    """Check for positive-area collisions between non-background elements."""
    warnings = []
    foreground = _foreground_elements(elements, background_ids)

    for i in range(len(foreground)):
        for j in range(i + 1, len(foreground)):
            e1, e2 = foreground[i], foreground[j]
            # Ignore same rigid group
            if e1.get("group_id") and e1.get("group_id") == e2.get("group_id"):
                continue

            b1 = calculate_aabb(e1)
            b2 = calculate_aabb(e2)

            # Intersection
            ix0 = max(b1[0], b2[0])
            iy0 = max(b1[1], b2[1])
            ix1 = min(b1[2], b2[2])
            iy1 = min(b1[3], b2[3])

            if ix1 > ix0 and iy1 > iy0:
                overlap_area = (ix1 - ix0) * (iy1 - iy0)
                if overlap_area > 0.0:
                    warnings.append(
                        f"COLLISION: '{e1['id']}' and '{e2['id']}' overlap by {overlap_area:.0f}px² "
                        f"at [{ix0:.0f}, {iy0:.0f}, {ix1:.0f}, {iy1:.0f}]"
                    )
    return warnings


def render_ascii_canvas(
    canvas: Dict[str, Any],
    elements: List[Dict[str, Any]],
    cols: int = 60,
    rows: int = 24,
    background_ids: set[str] | None = None,
) -> str:
    """Render an ASCII grid representing the canvas and elements."""
    cw = float(canvas.get("width", 100))
    ch = float(canvas.get("height", 100))
    scale_x = cols / cw
    scale_y = rows / ch

    # Create empty grid
    grid = [["·" for _ in range(cols)] for _ in range(rows)]

    # Draw border
    for r in range(rows):
        grid[r][0] = "|"
        grid[r][-1] = "|"
    for c in range(cols):
        grid[0][c] = "-"
        grid[-1][c] = "-"
    grid[0][0] = "+"
    grid[0][-1] = "+"
    grid[-1][0] = "+"
    grid[-1][-1] = "+"

    char_map = {
        "text": "T",
        "image": "I",
        "shape": "S"
    }

    # Sort elements by z_index
    sorted_els = sorted(elements, key=lambda e: e.get("z_index", 0))

    for el in sorted_els:
        # Skip only the source-qualified background.
        if el.get("id") in (background_ids or set()):
            continue

        min_x, min_y, max_x, max_y = calculate_aabb(el)
        gx0 = max(1, min(cols - 2, int(min_x * scale_x)))
        gy0 = max(1, min(rows - 2, int(min_y * scale_y)))
        gx1 = max(1, min(cols - 2, int(max_x * scale_x)))
        gy1 = max(1, min(rows - 2, int(max_y * scale_y)))

        marker = char_map.get(el.get("type"), "?")
        label = el.get("id", marker)[: max(1, gx1 - gx0)]

        for r in range(gy0, min(rows - 1, gy1 + 1)):
            for c in range(gx0, min(cols - 1, gx1 + 1)):
                if r == gy0 or r == gy1 or c == gx0 or c == gx1:
                    grid[r][c] = "#"
                elif grid[r][c] == "·":
                    grid[r][c] = " "

        # Place label inside box if room
        if gy0 < rows - 1 and gx0 + len(label) < cols - 1:
            for idx, ch in enumerate(label):
                if gx0 + 1 + idx < cols - 1 and gy0 + 1 < rows - 1:
                    grid[gy0 + 1][gx0 + 1 + idx] = ch

    return "\n".join("".join(row) for row in grid)


def inspect_design(
    doc: Dict[str, Any],
    title: str = "Design",
    source_context: Dict[str, Any] | None = None,
) -> None:
    """Print complete diagnostic layout inspection for a design document."""
    canvas = doc.get("canvas", {})
    elements = doc.get("elements", [])
    background_ids = _background_ids(source_context)
    cw, ch = canvas.get("width", 0), canvas.get("height", 0)

    print(f"\n========================================================")
    print(f"LAYOUT INSPECTION: {title}")
    print(f"Canvas: {cw} x {ch} px  |  Elements: {len(elements)}")
    print(f"========================================================")

    # ASCII Canvas
    print(render_ascii_canvas(canvas, elements, background_ids=background_ids))
    print("Legend: # = boundary, T = text, I = image, S = shape, · = canvas area")

    # Element Table
    print(f"\n{'ID':<18} {'TYPE':<7} {'X':<6} {'Y':<6} {'W':<6} {'H':<7} {'ROT':<5} {'Z':<3} {'DETAILS'}")
    print("-" * 80)
    for el in sorted(elements, key=lambda e: (e.get("z_index", 0), e.get("id"))):
        eid = el.get("id", "?")[:17]
        etype = el.get("type", "?")
        x, y = f"{el.get('x', 0):.0f}", f"{el.get('y', 0):.0f}"
        w, h = f"{el.get('width', 0):.0f}", f"{el.get('height', 0):.0f}"
        rot = f"{el.get('rotation', 0):.0f}°"
        z = str(el.get("z_index", 0))

        extra = []
        if el.get("group_id"):
            extra.append(f"group={el['group_id']}")
        if etype == "text":
            extra.append(f"size={el.get('font_size', '?')}")
            content = el.get("content", "").replace("\n", " ")
            extra.append(f'"{content[:20]}..."' if len(content) > 20 else f'"{content}"')
        elif etype == "image":
            extra.append(f"fit={el.get('fit', '?')}")
            extra.append(f"{el.get('asset_id', '?')}")
        elif etype == "shape":
            extra.append(f"{el.get('shape_type', '?')}")

        print(f"{eid:<18} {etype:<7} {x:<6} {y:<6} {w:<6} {h:<7} {rot:<5} {z:<3} {', '.join(extra)}")

    # Off-canvas checks
    off_canvas = []
    for el in elements:
        if el.get("id") in background_ids:
            continue
        min_x, min_y, max_x, max_y = calculate_aabb(el)
        if min_x < -0.5 or min_y < -0.5 or max_x > cw + 0.5 or max_y > ch + 0.5:
            off_canvas.append(f"'{el['id']}': bounds [{min_x:.1f}, {min_y:.1f}, {max_x:.1f}, {max_y:.1f}] exceed {cw}x{ch}")

    if off_canvas:
        print("\n[!] OFF-CANVAS WARNINGS:")
        for w in off_canvas:
            print(f"    - {w}")

    # Collisions
    collisions = check_collisions(elements, background_ids)
    if collisions:
        print("\n[!] COLLISION WARNINGS:")
        for c in collisions:
            print(f"    - {c}")
    else:
        print("\n[✓] Non-collision check: PASSED (zero unintended foreground overlaps)")


def _is_committed_pair(json_path: Path) -> bool:
    if not json_path.name.endswith("_output.json"):
        return False
    stem = json_path.name[: -len("_output.json")]
    png_path = json_path.with_name(f"{stem}_output.png")
    commit_path = json_path.with_name(f".{stem}_output.commit")
    try:
        marker = json.loads(commit_path.read_text(encoding="utf-8"))
        if not isinstance(marker, dict) or marker.get("committed") is not True:
            return False
        if (
            marker.get("json") != json_path.name
            or marker.get("png") != png_path.name
            or not png_path.is_file()
        ):
            return False
        return (
            marker.get("json_sha256")
            == hashlib.sha256(json_path.read_bytes()).hexdigest()
            and marker.get("png_sha256")
            == hashlib.sha256(png_path.read_bytes()).hexdigest()
        )
    except (OSError, TypeError, ValueError):
        return False


def _committed_json_files(target_path: Path) -> list[Path]:
    return [
        json_path
        for json_path in sorted(target_path.glob("*_output.json"))
        if _is_committed_pair(json_path)
    ]

def _uncommitted_artifacts(target_path: Path) -> list[Path]:
    candidates = sorted(
        set(target_path.glob("*_output.json"))
        | set(target_path.glob("*_output.png"))
    )
    uncommitted = []
    for path in candidates:
        if path.name.endswith("_output.json"):
            stem = path.name[: -len("_output.json")]
        else:
            stem = path.name[: -len("_output.png")]
        json_path = path.with_name(f"{stem}_output.json")
        if not _is_committed_pair(json_path):
            uncommitted.append(path)
    return uncommitted



def _source_context_for_output(json_path: Path) -> Dict[str, Any] | None:
    """Load matching source context when output sits beside the input directory."""

    stem = json_path.name[: -len("_output.json")]
    input_path = json_path.parent.parent / "input" / f"{stem}.json"
    try:
        task = json.loads(input_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    source = task.get("source") if isinstance(task, dict) else None
    return source if isinstance(source, dict) else None


def _design_and_source_context(
    doc: Dict[str, Any], json_path: Path | None = None
) -> tuple[Dict[str, Any], Dict[str, Any] | None]:
    inline_source = doc.get("source") if isinstance(doc, dict) else None
    if isinstance(inline_source, dict):
        return inline_source, inline_source
    source_context = (
        _source_context_for_output(json_path) if json_path is not None else None
    )
    return doc, source_context


def main() -> int:
    if len(sys.argv) < 2:
        target_path = Path("chameleon/output")
    else:
        target_path = Path(sys.argv[1])

    if target_path.is_file():
        if target_path.name.endswith("_output.json") and not _is_committed_pair(target_path):
            print(f"Uncommitted or invalid output pair: {target_path}", file=sys.stderr)
            return 1
        try:
            doc = json.loads(target_path.read_text())
        except (OSError, json.JSONDecodeError) as error:
            print(
                f"Unable to read layout document {target_path}: {error}",
                file=sys.stderr,
            )
            return 1
        design, source_context = _design_and_source_context(doc, target_path)
        inspect_design(design, target_path.name, source_context)
        return 0

    if target_path.is_dir():
        uncommitted = _uncommitted_artifacts(target_path)
        if uncommitted:
            for artifact_path in uncommitted:
                print(
                    f"Uncommitted or invalid output pair: {artifact_path}",
                    file=sys.stderr,
                )
            return 1
        json_files = _committed_json_files(target_path)
        if not json_files:
            print(f"No committed *_output.json files found in {target_path}")
            return 1
        for f in json_files:
            try:
                doc = json.loads(f.read_text())
            except (OSError, json.JSONDecodeError) as error:
                print(
                    f"Unable to read layout document {f}: {error}",
                    file=sys.stderr,
                )
                return 1
            design, source_context = _design_and_source_context(doc, f)
            inspect_design(design, f.name, source_context)
        return 0

    print(f"Path does not exist: {target_path}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
