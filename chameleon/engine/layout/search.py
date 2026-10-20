"""Bounded deterministic candidate search for the Stage 1 layout engine.

This module is deliberately independent of the public ``resize`` seam.  It
owns candidate enumeration, the renderer/contract gate, and ranking, while
the topology modules remain the source-aware geometry generators.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from fractions import Fraction
from pathlib import Path
from tempfile import TemporaryDirectory
from types import MappingProxyType
from typing import Any, Callable, Mapping

from ..contract import validate_response, validate_source, validate_target_canvas
from ..errors import InfeasibleLayoutError, InfeasibleReasonCode, TaskStatus
from ..geometry.bounds import rotated_aabb, source_bleed_sides
from ..geometry.math_util import quantize_to_int, to_fraction
from ..geometry.ratios import reduced_ratio
from .column_pivot import is_column_pivot_suitable, solve_column_pivot
from .horizontal_ribbon import is_horizontal_ribbon_suitable, solve_horizontal_ribbon
from .near_isomorphic import solve_near_isomorphic
from .ranking import QualityScore, score_candidate, select_best
from .roles import RoleKind, RoleModel, infer_roles
from .vertical_restack import is_vertical_restack_suitable, solve_vertical_restack


TOPOLOGY_ORDER: tuple[str, ...] = (
    "near_isomorphic",
    "column_pivot",
    "horizontal_ribbon",
    "vertical_restack",
)
MAX_VARIANTS_PER_FAMILY = 3
MAX_CANDIDATES = len(TOPOLOGY_ORDER) * MAX_VARIANTS_PER_FAMILY
_VARIANT_NAMES: tuple[str, ...] = (
    "source_proportional",
    "dominant_media",
    "dominant_copy",
)


@dataclass(frozen=True, slots=True)
class CandidateSpec:
    """One stable, source-derived topology/variant work item."""

    topology: str
    variant: str
    topology_order: int
    variant_index: int
    source_order: int
    candidate_index: int


@dataclass(frozen=True, slots=True)
class Candidate:
    """A rendered and hard-valid candidate admitted to ranking."""

    topology: str
    variant: str
    topology_order: int
    variant_index: int
    source_order: int
    response: Mapping[str, Any]
    rendered_png: bytes
    quality: QualityScore
    candidate_index: int | None = None
    hard_validity: int = 1
    warnings: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        # Older callers identify candidates by their per-family variant index;
        # use that stable value when a global index was not supplied.
        if self.candidate_index is None:
            object.__setattr__(self, "candidate_index", self.variant_index)


@dataclass(frozen=True, slots=True)
class SearchResult:
    """Successful search outcome and inspectable deterministic diagnostics."""

    response: Mapping[str, Any]
    selected: Candidate
    candidates: tuple[Candidate, ...]
    status: TaskStatus = TaskStatus.SUCCESS
    diagnostics: Mapping[str, Any] = field(
        default_factory=lambda: MappingProxyType({})
    )

    @property
    def candidate(self) -> Candidate:
        """Compatibility alias for the selected candidate."""

        return self.selected


# Kept as a discoverable seam for tests and future topology additions.  Values
# are imported solver functions and are never reordered at runtime.
_TOPOLOGY_SOLVERS: tuple[Callable[..., Mapping[str, Any]], ...] = (
    solve_near_isomorphic,
    solve_column_pivot,
    solve_horizontal_ribbon,
    solve_vertical_restack,
)


def _source_variant_indices(source: Mapping[str, Any], roles: RoleModel) -> tuple[int, ...]:
    """Return variant indices supported by source evidence in stable order."""

    if not source["elements"]:
        # A source-free design has no evidence for media or copy emphasis.
        return (0,)
    role_values = {assignment.role for assignment in roles.assignments}
    has_media = bool(role_values & {RoleKind.HERO_MEDIA, RoleKind.IMAGE, RoleKind.LOGO})
    has_copy = bool(
        role_values
        & {RoleKind.HEADLINE, RoleKind.SUPPORTING_TEXT, RoleKind.CTA, RoleKind.TEXT}
    )
    indices = [0]
    if has_media:
        indices.append(1)
    if has_copy:
        indices.append(2)
    return tuple(indices[:MAX_VARIANTS_PER_FAMILY])


def _source_variant_orders(roles: RoleModel) -> dict[int, int]:
    """Map variant indices to evidence-bearing source array positions."""

    orders = {0: 0}
    for variant_index, role_set in (
        (1, {RoleKind.HERO_MEDIA, RoleKind.LOGO, RoleKind.IMAGE}),
        (2, {RoleKind.HEADLINE, RoleKind.SUPPORTING_TEXT, RoleKind.CTA, RoleKind.TEXT}),
    ):
        positions = [
            assignment.index
            for assignment in roles.assignments
            if assignment.role in role_set
        ]
        if positions:
            orders[variant_index] = min(positions)
    return orders


def enumerate_candidate_specs(
    source: Mapping[str, Any],
    target_canvas: Mapping[str, Any],
    *,
    roles: RoleModel | None = None,
) -> tuple[CandidateSpec, ...]:
    """Enumerate at most twelve stable topology/variant specifications."""

    validate_source(source)
    validate_target_canvas(target_canvas)
    role_model = roles or infer_roles(source)
    variant_indices = _source_variant_indices(source, role_model)
    suitable: tuple[bool, ...] = (
        True,
        is_column_pivot_suitable(source, target_canvas, role_model),
        is_horizontal_ribbon_suitable(source, target_canvas),
        is_vertical_restack_suitable(source, target_canvas),
    )
    specs: list[CandidateSpec] = []
    for topology_order, (topology, is_suitable) in enumerate(zip(TOPOLOGY_ORDER, suitable)):
        if not is_suitable:
            continue
        for variant_index in variant_indices:
            specs.append(
                CandidateSpec(
                    topology=topology,
                    variant=_VARIANT_NAMES[variant_index],
                    topology_order=topology_order,
                    variant_index=variant_index,
                    source_order=_source_variant_orders(role_model).get(
                        variant_index, variant_index
                    ),
                    candidate_index=len(specs),
                )
            )
            if len(specs) == MAX_CANDIDATES:
                return tuple(specs)
    return tuple(specs)


def _integer_bounds(low: Fraction, high: Fraction) -> tuple[int, int] | None:
    """Return the inclusive integer interval contained in an exact interval."""

    lower = -((-low.numerator) // low.denominator)
    upper = high.numerator // high.denominator
    return (lower, upper) if lower <= upper else None


_MEDIA_ROLES = frozenset({RoleKind.HERO_MEDIA, RoleKind.LOGO, RoleKind.IMAGE})
_COPY_ROLES = frozenset(
    {RoleKind.HEADLINE, RoleKind.SUPPORTING_TEXT, RoleKind.CTA, RoleKind.BADGE, RoleKind.TEXT}
)


def _variant_focus_indices(
    source: Mapping[str, Any], roles: RoleModel, variant_index: int
) -> frozenset[int]:
    role_set = _MEDIA_ROLES if variant_index == 1 else _COPY_ROLES
    return frozenset(
        assignment.index
        for assignment in roles.assignments
        if assignment.role in role_set
        and assignment.index != roles.background_index
    )


def _variant_lattice_dimensions(
    source_element: Mapping[str, Any],
    response_element: Mapping[str, Any],
    factor: Fraction,
) -> tuple[int, int]:
    ratio = reduced_ratio(source_element["width"], source_element["height"])
    if ratio is None:
        return (
            quantize_to_int(to_fraction(response_element["width"]) * factor),
            quantize_to_int(to_fraction(response_element["height"]) * factor),
        )
    numerator, denominator = ratio
    current_width = to_fraction(response_element["width"])
    current_height = to_fraction(response_element["height"])
    current_multiplier = min(
        current_width.numerator // (current_width.denominator * numerator),
        current_height.numerator // (current_height.denominator * denominator),
    )
    desired_multiplier = min(
        (current_width * factor).numerator
        // ((current_width * factor).denominator * numerator),
        (current_height * factor).numerator
        // ((current_height * factor).denominator * denominator),
    )
    multiplier = max(current_multiplier, desired_multiplier, 1)
    return multiplier * numerator, multiplier * denominator


def _scaled_variant_records(
    response: dict[str, Any],
    source: Mapping[str, Any],
    indices: Sequence[int],
    *,
    origin: tuple[Fraction, Fraction],
    factor: Fraction,
    lattice_images: bool,
) -> None:
    origin_x, origin_y = origin
    for index in indices:
        source_element = source["elements"][index]
        element = response["elements"][index]
        center_x = to_fraction(element["x"]) + to_fraction(element["width"]) / 2
        center_y = to_fraction(element["y"]) + to_fraction(element["height"]) / 2
        next_center_x = origin_x + (center_x - origin_x) * factor
        next_center_y = origin_y + (center_y - origin_y) * factor
        if lattice_images and element.get("type") == "image":
            next_width, next_height = _variant_lattice_dimensions(
                source_element, element, factor
            )
        else:
            next_width = to_fraction(element["width"]) * factor
            next_height = to_fraction(element["height"]) * factor
        element["x"] = next_center_x - to_fraction(next_width) / 2
        element["y"] = next_center_y - to_fraction(next_height) / 2
        element["width"] = next_width
        element["height"] = next_height
        if element.get("type") == "text":
            element["font_size"] = to_fraction(element["font_size"]) * factor


def _variant_fits(
    response: Mapping[str, Any],
    indices: Sequence[int],
    target_canvas: Mapping[str, Any],
) -> bool:
    target_width = to_fraction(target_canvas["width"])
    target_height = to_fraction(target_canvas["height"])
    for index in indices:
        box = rotated_aabb(response["elements"][index])
        if box[0] < 0 or box[1] < 0 or box[2] > target_width or box[3] > target_height:
            return False
    return True


def _apply_variant_emphasis(
    response: dict[str, Any],
    source: Mapping[str, Any],
    roles: RoleModel,
    target_canvas: Mapping[str, Any],
    spec: CandidateSpec,
) -> None:
    focus = _variant_focus_indices(source, roles, spec.variant_index)
    if not focus:
        return
    groups: dict[Any, list[int]] = {}
    individual: list[int] = []
    for index in sorted(focus):
        group_id = source["elements"][index].get("group_id")
        if group_id is None:
            individual.append(index)
            continue
        groups.setdefault(group_id, [])
    for group_id in groups:
        groups[group_id] = [
            index
            for index, element in enumerate(source["elements"])
            if element.get("group_id") == group_id
        ]
    for indices in groups.values():
        if roles.background_index in indices:
            continue
        aabbs = [rotated_aabb(response["elements"][index]) for index in indices]
        origin = (
            (min(box[0] for box in aabbs) + max(box[2] for box in aabbs)) / 2,
            (min(box[1] for box in aabbs) + max(box[3] for box in aabbs)) / 2,
        )
        for factor in (Fraction(2), Fraction(3, 2), Fraction(1)):
            trial = deepcopy(response)
            _scaled_variant_records(
                trial,
                source,
                indices,
                origin=origin,
                factor=factor,
                lattice_images=False,
            )
            if _variant_fits(trial, indices, target_canvas):
                response["elements"] = trial["elements"]
                break
    for index in individual:
        element = response["elements"][index]
        origin = (
            to_fraction(element["x"]) + to_fraction(element["width"]) / 2,
            to_fraction(element["y"]) + to_fraction(element["height"]) / 2,
        )
        for factor in (Fraction(5, 4), Fraction(9, 8), Fraction(1)):
            trial = deepcopy(response)
            _scaled_variant_records(
                trial,
                source,
                [index],
                origin=origin,
                factor=factor,
                lattice_images=True,
            )
            if _variant_fits(trial, [index], target_canvas):
                response["elements"] = trial["elements"]
                break


def _serialize_variant_response(response: Mapping[str, Any]) -> dict[str, Any]:
    result = deepcopy(dict(response))
    for element in result.get("elements", []):
        for field in ("x", "y", "width", "height"):
            if field in element:
                element[field] = quantize_to_int(element[field])
        if element.get("type") == "text" and "font_size" in element:
            element["font_size"] = quantize_to_int(element["font_size"])
    return result


def _derive_variant_response(
    base: Mapping[str, Any],
    source: Mapping[str, Any],
    target_canvas: Mapping[str, Any],
    roles: RoleModel,
    spec: CandidateSpec,
) -> dict[str, Any]:
    """Derive role-specific emphasis geometry from a hard-safe base candidate."""

    response = deepcopy(dict(base))
    if spec.variant_index == 0 or not response.get("elements"):
        return response

    background_index = roles.background_index
    blocked = {background_index} if background_index is not None else set()
    if background_index is not None:
        background_group = source["elements"][background_index].get("group_id")
        if background_group is not None:
            blocked.update(
                index
                for index, element in enumerate(source["elements"])
                if element.get("group_id") == background_group
            )
    eligible: list[int] = []
    for index, element in enumerate(source["elements"]):
        if index in blocked:
            continue
        source_aabb = rotated_aabb(element)
        if source_bleed_sides(element, source_aabb, source["canvas"]) is not None:
            continue
        eligible.append(index)
    if not eligible:
        return response

    target_width = to_fraction(target_canvas["width"])
    target_height = to_fraction(target_canvas["height"])
    lower_x, upper_x = Fraction(0), target_width
    lower_y, upper_y = Fraction(0), target_height
    boxes = {index: rotated_aabb(response["elements"][index]) for index in eligible}
    for box in boxes.values():
        lower_x = max(lower_x, -box[0])
        upper_x = min(upper_x, target_width - box[2])
        lower_y = max(lower_y, -box[1])
        upper_y = min(upper_y, target_height - box[3])
    x_interval = _integer_bounds(lower_x, upper_x)
    y_interval = _integer_bounds(lower_y, upper_y)
    if x_interval is None or y_interval is None:
        return response

    anchor_index = spec.source_order if spec.source_order in eligible else eligible[0]
    anchor_box = boxes[anchor_index]
    anchor_x = (anchor_box[0] + anchor_box[2]) / 2
    anchor_y = (anchor_box[1] + anchor_box[3]) / 2
    if spec.variant_index == 1:
        desired = (target_width / 2 - anchor_x) / 2
        translation = max(Fraction(x_interval[0]), min(Fraction(x_interval[1]), desired))
        for index in eligible:
            response["elements"][index]["x"] += translation
    else:
        desired = (target_height / 2 - anchor_y) / 2
        translation = max(Fraction(y_interval[0]), min(Fraction(y_interval[1]), desired))
        for index in eligible:
            response["elements"][index]["y"] += translation
    _apply_variant_emphasis(response, source, roles, target_canvas, spec)
    return response


def _renderer_classes() -> tuple[type[BaseException], ...]:
    """Load text exceptions lazily, preserving offline import of this module."""

    try:
        from ...renderer.converter.wrap import TextLayoutError
    except ImportError:
        try:
            from renderer.converter.wrap import TextLayoutError
        except ImportError:
            return ()
    return (TextLayoutError,)


def _render_candidate(
    response: Mapping[str, Any],
    *,
    assets_dir: str | Path | None,
    fonts_dir: str | Path | None,
    font_manager: Any,
) -> tuple[bytes, tuple[str, ...]]:
    """Render one response through the local converter and return PNG bytes."""

    try:
        try:
            from ...renderer.converter.convert import render_design_to_png
        except ImportError:
            from renderer.converter.convert import render_design_to_png
        default_assets = Path(__file__).resolve().parents[2] / "brand_kit" / "assets"
        default_fonts = Path(__file__).resolve().parents[2] / "brand_kit" / "fonts"
        resolved_assets = str(assets_dir or default_assets)
        resolved_fonts = str(fonts_dir or default_fonts)
        with TemporaryDirectory(prefix=".chameleon-search-") as directory:
            png_path = Path(directory) / "candidate.png"
            warnings = render_design_to_png(
                deepcopy(dict(response)),
                resolved_assets,
                png_path,
                resolved_fonts,
                font_manager=font_manager,
            )
            return png_path.read_bytes(), tuple(str(warning) for warning in warnings)
    except _renderer_classes() as error:
        raise error


def _runtime_error(error: Exception, spec: CandidateSpec) -> InfeasibleLayoutError:
    return InfeasibleLayoutError(
        InfeasibleReasonCode.RUNTIME_IO_FAILURE,
        "renderer or candidate runtime failure",
        {
            "status": TaskStatus.RUNTIME_IO_FAILURE.value,
            "topology": spec.topology,
            "variant": spec.variant,
            "candidate_index": spec.candidate_index,
            "error_type": type(error).__name__,
            "error": str(error),
        },
    )


def _invoke_solver(
    spec: CandidateSpec,
    source: Mapping[str, Any],
    target_canvas: Mapping[str, Any],
    roles: RoleModel,
    *,
    variant: str,
    font_manager: Any,
    fonts_dir: str | Path | None,
    assets_dir: str | Path | None,
) -> Mapping[str, Any]:
    solver = _TOPOLOGY_SOLVERS[spec.topology_order]
    kwargs: dict[str, Any] = {
        "variant": variant,
        "font_manager": font_manager,
        "fonts_dir": str(fonts_dir) if fonts_dir is not None else None,
        "assets_dir": str(assets_dir) if assets_dir is not None else None,
    }
    if spec.topology == "column_pivot":
        kwargs["roles"] = roles
    # Every solver receives private copies: a topology implementation cannot
    # mutate caller-owned source data or leak mutations between variants.
    response = solver(deepcopy(source), deepcopy(target_canvas), **kwargs)
    if not isinstance(response, Mapping):
        raise ValueError("topology solver did not return a design mapping")
    return response


def search(
    source: Mapping[str, Any],
    target_canvas: Mapping[str, Any],
    *,
    max_candidates: int = MAX_CANDIDATES,
    assets_dir: str | Path | None = None,
    fonts_dir: str | Path | None = None,
    font_manager: Any = None,
) -> SearchResult:
    """Run bounded renderer-gated search and return the selected result.

    Hard layout/text failures reject only that candidate.  Renderer imports,
    filesystem errors, and other infrastructure failures raise a typed
    ``RUNTIME_IO_FAILURE``.  Exhausting the finite work set raises
    ``NO_HARD_VALID_CANDIDATE`` with ``INFEASIBLE_LAYOUT`` status; an explicit
    smaller work limit with no valid result raises ``INCOMPLETE_SEARCH``.
    """

    validate_source(source)
    validate_target_canvas(target_canvas)
    if not isinstance(max_candidates, int) or isinstance(max_candidates, bool) or max_candidates < 1:
        raise ValueError("max_candidates must be a positive integer")
    roles = infer_roles(source)
    specs = enumerate_candidate_specs(source, target_canvas, roles=roles)
    limit = min(max_candidates, len(specs), MAX_CANDIDATES)
    cutoff = limit < len(specs)
    admitted: list[Candidate] = []
    failures: list[dict[str, Any]] = []
    saw_incomplete = False

    for spec in specs[:limit]:
        try:
            response = _invoke_solver(
                spec,
                source,
                target_canvas,
                roles,
                variant=spec.variant,
                font_manager=font_manager,
                fonts_dir=fonts_dir,
                assets_dir=assets_dir,
            )
            if spec.variant_index != 0:
                response = _derive_variant_response(
                    response,
                    source,
                    target_canvas,
                    roles,
                    spec,
                )
            response = _serialize_variant_response(response)
            # Reject serialized structural failures before spending renderer
            # work.  The renderer then supplies the actual text/glyph gate.
            validate_response(source, target_canvas, response)
            rendered_png, warnings = _render_candidate(
                response,
                assets_dir=assets_dir,
                fonts_dir=fonts_dir,
                font_manager=font_manager,
            )
            # Re-read the candidate at the renderer boundary as an explicit
            # post-serialization hard gate before fixed-point scoring.
            validate_response(source, target_canvas, response)
            quality = score_candidate(source, response, rendered_png, roles=roles)
            admitted.append(
                Candidate(
                    topology=spec.topology,
                    variant=spec.variant,
                    topology_order=spec.topology_order,
                    variant_index=spec.variant_index,
                    source_order=spec.source_order,
                    candidate_index=spec.candidate_index,
                    response=deepcopy(dict(response)),
                    rendered_png=bytes(rendered_png),
                    quality=quality,
                    warnings=warnings,
                )
            )
        except InfeasibleLayoutError as error:
            if error.reason_code is InfeasibleReasonCode.RUNTIME_IO_FAILURE:
                raise _runtime_error(error, spec) from error
            saw_incomplete = saw_incomplete or (
                error.reason_code is InfeasibleReasonCode.INCOMPLETE_SEARCH
            )
            failures.append(
                {
                    "topology": spec.topology,
                    "variant": spec.variant,
                    "candidate_index": spec.candidate_index,
                    "reason_code": error.reason_code.value,
                    "reason": error.message,
                    "details": deepcopy(error.details),
                }
            )
        except _renderer_classes() as error:
            failures.append(
                {
                    "topology": spec.topology,
                    "variant": spec.variant,
                    "candidate_index": spec.candidate_index,
                    "reason_code": InfeasibleReasonCode.TEXT_OVERFLOW.value,
                    "reason": str(error),
                }
            )
        except Exception as error:
            raise _runtime_error(error, spec) from error

    if not admitted:
        status = (
            TaskStatus.INCOMPLETE_SEARCH
            if cutoff or saw_incomplete
            else TaskStatus.INFEASIBLE_LAYOUT
        )
        reason = (
            InfeasibleReasonCode.INCOMPLETE_SEARCH
            if cutoff or saw_incomplete
            else InfeasibleReasonCode.NO_HARD_VALID_CANDIDATE
        )
        raise InfeasibleLayoutError(
            reason,
            "bounded search found no hard-valid candidate",
            {
                "status": status.value,
                "evaluated_candidates": limit,
                "candidate_count": len(specs),
                "cutoff": cutoff,
                "failures": failures,
            },
        )

    selected = select_best(admitted)
    result_diagnostics = {
        "status": TaskStatus.SUCCESS.value,
        "candidate_count": len(specs),
        "evaluated_candidates": limit,
        "hard_valid_candidates": len(admitted),
        "cutoff": cutoff,
        "failures": tuple(failures),
    }
    return SearchResult(
        response=deepcopy(dict(selected.response)),
        selected=selected,
        candidates=tuple(admitted),
        diagnostics=MappingProxyType(result_diagnostics),
    )


# Explicit aliases make the discoverable seam convenient without adding a
# second implementation or changing the public resize response shape.
search_candidates = search
run_search = search
bounded_search = search
search_layout = search


__all__ = [
    "Candidate",
    "CandidateSpec",
    "MAX_CANDIDATES",
    "MAX_VARIANTS_PER_FAMILY",
    "SearchResult",
    "TOPOLOGY_ORDER",
    "enumerate_candidate_specs",
    "run_search",
    "search",
    "search_candidates",
    "bounded_search",
    "search_layout",
]
