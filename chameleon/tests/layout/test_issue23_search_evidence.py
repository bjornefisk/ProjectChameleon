import hashlib
import io
import sys
import unittest
from pathlib import Path

from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT))

try:
    from engine.contract import validate_response
    from engine.errors import InfeasibleLayoutError, InfeasibleReasonCode, TaskStatus
    from engine.layout.roles import RoleKind, infer_roles
    from engine.layout.search import (
        MAX_CANDIDATES,
        MAX_VARIANTS_PER_FAMILY,
        TOPOLOGY_ORDER,
        enumerate_candidate_specs,
        search,
    )
except ModuleNotFoundError:
    from chameleon.engine.contract import validate_response
    from chameleon.engine.errors import (
        InfeasibleLayoutError,
        InfeasibleReasonCode,
        TaskStatus,
    )
    from chameleon.engine.layout.roles import RoleKind, infer_roles
    from chameleon.engine.layout.search import (
        MAX_CANDIDATES,
        MAX_VARIANTS_PER_FAMILY,
        TOPOLOGY_ORDER,
        enumerate_candidate_specs,
        search,
    )


ROOT = PROJECT_ROOT / "chameleon"
ASSETS = ROOT / "brand_kit" / "assets"
FONTS = ROOT / "brand_kit" / "fonts"

SOURCE_CANVAS = {"width": 1000, "height": 1000}
SOURCE = {
    "canvas": dict(SOURCE_CANVAS),
    "elements": [
        {
            "id": "media",
            "type": "image",
            "x": 150,
            "y": 100,
            "width": 600,
            "height": 600,
            "asset_id": "solstice_bottle.png",
            "fit": "contain",
        },
        {
            "id": "copy",
            "type": "text",
            "x": 120,
            "y": 780,
            "width": 760,
            "height": 100,
            "content": "A bright seasonal collection",
            "font_family": "Solstice Sans",
            "font_size": 40,
            "font_weight": "bold",
            "color": "rgba(35,25,35,1)",
            "text_align": "center",
        },
    ],
}

SQUARE = {"width": 1000, "height": 1000}
TARGETS = {
    "square": SQUARE,
    "wide": {"width": 800, "height": 200},
    "tall": {"width": 200, "height": 1600},
    "extreme": {"width": 900, "height": 100},
}
WIDE = TARGETS["wide"]

# ADR-009 section 3 implementation labels, in the listed variant order.
BASE = "source_proportional"
MEDIA = "dominant_media"
COPY = "dominant_copy"


def _text(element_id, *, x=100, y=100, **overrides):
    element = {
        "id": element_id,
        "type": "text",
        "x": x,
        "y": y,
        "width": 400,
        "height": 80,
        "content": "Hello world",
        "font_family": "Solstice Sans",
        "font_size": 40,
        "color": "rgba(0,0,0,1)",
    }
    element.update(overrides)
    return element


def _image(element_id, *, x=100, y=300, **overrides):
    element = {
        "id": element_id,
        "type": "image",
        "x": x,
        "y": y,
        "width": 300,
        "height": 300,
        "asset_id": "solstice_bottle.png",
    }
    element.update(overrides)
    return element


def _shape(element_id, *, x=50, y=50, **overrides):
    element = {
        "id": element_id,
        "type": "shape",
        "x": x,
        "y": y,
        "width": 200,
        "height": 100,
        "shape_type": "rectangle",
        "fill_color": "rgba(200,200,200,1)",
    }
    element.update(overrides)
    return element


def _full_canvas_cover_background(element_id="bg"):
    return _image(
        element_id,
        x=0,
        y=0,
        width=SOURCE_CANVAS["width"],
        height=SOURCE_CANVAS["height"],
        asset_id="solstice_bg_gradient.png",
        fit="cover",
    )


def _source(*elements):
    return {"canvas": dict(SOURCE_CANVAS), "elements": list(elements)}


def _variants_by_family(specs):
    grouped = {}
    for spec in specs:
        grouped.setdefault(spec.topology, []).append(spec.variant)
    return {family: tuple(variants) for family, variants in grouped.items()}


class Issue23SearchEvidenceTests(unittest.TestCase):
    def test_source_variants_are_stable_bounded_and_not_invented(self):
        target = WIDE
        first = enumerate_candidate_specs(SOURCE, target)
        second = enumerate_candidate_specs(SOURCE, target)

        self.assertEqual(first, second)
        self.assertLessEqual(len(first), MAX_CANDIDATES)
        self.assertLessEqual(
            max((spec.variant_index for spec in first), default=-1) + 1,
            MAX_VARIANTS_PER_FAMILY,
        )

        expected_families = TOPOLOGY_ORDER
        expected_variants = (BASE, MEDIA, COPY)
        self.assertEqual(
            tuple(dict.fromkeys(spec.topology for spec in first)), expected_families
        )
        self.assertEqual(
            tuple((spec.topology, spec.variant) for spec in first),
            tuple(
                (family, variant)
                for family in expected_families
                for variant in expected_variants
            ),
        )
        self.assertEqual(
            tuple(spec.candidate_index for spec in first), tuple(range(len(first)))
        )

    def test_enumeration_is_target_independent(self):
        # engine/layout/search.py (enumerate_candidate_specs comment): suitability is
        # decided by each topology solver, so an unsuitable family stays in the work
        # set as an explicit rejected attempt instead of being silently omitted per
        # target shape.  ADR-009 section 3 generates all four families and counts
        # its twelve-candidate ceiling before any rejection but does not itself
        # require target-independent enumeration, so this pins the implemented
        # design as a regression guard, not an ADR mandate.
        sequences = {
            name: tuple(
                (spec.topology, spec.variant)
                for spec in enumerate_candidate_specs(SOURCE, target)
            )
            for name, target in TARGETS.items()
        }
        self.assertEqual(len(sequences["square"]), len(TOPOLOGY_ORDER) * 3)
        for name, sequence in sequences.items():
            with self.subTest(target=name):
                self.assertEqual(sequence, sequences["square"])

    def _assert_work_set_accounting(self, specs, admitted, failures, evaluated):
        """Every enumerated work item is admitted xor an explicit typed failure."""

        enumerated = [
            (spec.topology, spec.variant, spec.candidate_index) for spec in specs
        ]
        admitted_keys = [
            (item.topology, item.variant, item.candidate_index) for item in admitted
        ]
        failure_keys = [
            (item["topology"], item["variant"], item["candidate_index"])
            for item in failures
        ]
        # No duplicates: each work item appears exactly once across both lists.
        self.assertEqual(len(admitted_keys) + len(failure_keys), evaluated)
        self.assertEqual(evaluated, len(enumerated))
        self.assertEqual(set(admitted_keys) & set(failure_keys), set())
        self.assertEqual(set(admitted_keys) | set(failure_keys), set(enumerated))
        self.assertEqual(len(set(admitted_keys + failure_keys)), len(enumerated))
        reason_codes = {code.value for code in InfeasibleReasonCode}
        statuses = {status.value for status in TaskStatus}
        for failure in failures:
            self.assertIn(failure["reason_code"], reason_codes)
            self.assertIn(failure["status"], statuses)
            self.assertIs(type(failure["search_exhausted"]), bool)

    def test_search_accounts_for_every_work_item_on_non_square_targets(self):
        # ADR-009 section 4 (every generated candidate is hard-validated and admitted
        # only if all checks pass) and section 8 (each hard-failure reason code is
        # recorded): each enumerated family/variant is either admitted or has a
        # recorded typed rejection, whatever the target shape.  Which families are
        # admitted for a given target is a solver outcome, not a contract
        # requirement, so only accounting and hard validity are asserted here;
        # per-family admission is guarded by the authored held-out corpus.
        for name in ("wide", "tall", "extreme"):
            target = TARGETS[name]
            with self.subTest(target=name):
                specs = enumerate_candidate_specs(SOURCE, target)
                try:
                    result = search(
                        SOURCE, target, assets_dir=ASSETS, fonts_dir=FONTS
                    )
                except InfeasibleLayoutError as error:
                    admitted = ()
                    failures = error.details["failures"]
                    evaluated = error.details["evaluated_candidates"]
                else:
                    admitted = result.candidates
                    failures = result.diagnostics["failures"]
                    evaluated = result.diagnostics["evaluated_candidates"]
                    for candidate in admitted:
                        validate_response(SOURCE, target, candidate.response)
                self._assert_work_set_accounting(specs, admitted, failures, evaluated)

    def test_search_on_unfittable_target_accounts_for_every_rejection(self):
        # A 10x10 canvas cannot hold the headline at the readable floor plus the
        # image: nothing is admitted, so the typed InfeasibleLayoutError must carry
        # one record per work item.  The target is deliberately far from any
        # boundary: borderline sizes such as 40x12 or 400x12 are infeasible with
        # macOS (fractional) Skia advances but feasible with Linux (hinted integer)
        # advances, so they would make this test platform dependent.
        target = {"width": 10, "height": 10}
        specs = enumerate_candidate_specs(SOURCE, target)
        with self.assertRaises(InfeasibleLayoutError) as caught:
            search(SOURCE, target, assets_dir=ASSETS, fonts_dir=FONTS)

        error = caught.exception
        self.assertIn(
            error.reason_code,
            (
                InfeasibleReasonCode.NO_HARD_VALID_CANDIDATE,
                InfeasibleReasonCode.INCOMPLETE_SEARCH,
            ),
        )
        self.assertIn(
            error.details["status"],
            (TaskStatus.INFEASIBLE_LAYOUT.value, TaskStatus.INCOMPLETE_SEARCH.value),
        )
        self.assertEqual(len(error.details["failures"]), len(specs))
        self._assert_work_set_accounting(
            specs, (), error.details["failures"], error.details["evaluated_candidates"]
        )

    def test_text_only_source_omits_dominant_media(self):
        # ADR-009 section 3: a missing source signal omits the variant rather than
        # inventing a hero/logo role.
        source = _source(_text("headline"))
        specs = enumerate_candidate_specs(source, WIDE)

        self.assertEqual(len(specs), 8)
        self.assertEqual(
            _variants_by_family(specs),
            {family: (BASE, COPY) for family in TOPOLOGY_ORDER},
        )
        self.assertNotIn(MEDIA, {spec.variant for spec in specs})

    def test_foreground_image_only_source_omits_dominant_copy(self):
        source = _source(_image("photo"))
        specs = enumerate_candidate_specs(source, WIDE)

        self.assertEqual(len(specs), 8)
        self.assertEqual(
            _variants_by_family(specs),
            {family: (BASE, MEDIA) for family in TOPOLOGY_ORDER},
        )
        self.assertNotIn(COPY, {spec.variant for spec in specs})

    def test_empty_source_has_only_base_variants_and_returns_target_canvas(self):
        source = _source()
        specs = enumerate_candidate_specs(source, WIDE)

        self.assertEqual(len(specs), len(TOPOLOGY_ORDER))
        self.assertEqual(
            _variants_by_family(specs), {family: (BASE,) for family in TOPOLOGY_ORDER}
        )

        # Contract section 4: an empty source returns the target canvas and an
        # empty element array.
        result = search(source, WIDE, assets_dir=ASSETS, fonts_dir=FONTS)
        self.assertEqual(dict(result.response), {"canvas": dict(WIDE), "elements": []})
        self.assertEqual(result.selected.variant, BASE)
        validate_response(source, WIDE, result.response)

    def test_shape_only_source_has_no_media_or_copy_variants(self):
        source = _source(_shape("decor"))
        specs = enumerate_candidate_specs(source, WIDE)

        self.assertEqual(len(specs), len(TOPOLOGY_ORDER))
        self.assertEqual(
            _variants_by_family(specs), {family: (BASE,) for family in TOPOLOGY_ORDER}
        )

    def test_full_canvas_cover_background_is_not_media_evidence(self):
        background = _full_canvas_cover_background()
        text = _text("headline", x=300, y=400)
        source = _source(background, text)

        # Precondition from role inference: the full-canvas fit=cover image is the
        # background, not hero/logo/image media (contract section 7, ADR-009 section 2).
        roles = infer_roles(source)
        self.assertEqual(roles.role_for("bg"), RoleKind.BACKGROUND)
        self.assertEqual(roles.background_index, 0)

        specs = enumerate_candidate_specs(source, WIDE)
        self.assertEqual(len(specs), 8)
        self.assertEqual(
            _variants_by_family(specs),
            {family: (BASE, COPY) for family in TOPOLOGY_ORDER},
        )
        self.assertNotIn(MEDIA, {spec.variant for spec in specs})

        # Background alone supplies no emphasis signal at all.
        background_only = enumerate_candidate_specs(_source(background), WIDE)
        self.assertEqual(
            _variants_by_family(background_only),
            {family: (BASE,) for family in TOPOLOGY_ORDER},
        )

    def test_variant_source_order_is_first_evidence_array_index(self):
        # ADR-009 section 5 uses source_order as the final ranking tie-break, so each
        # variant must carry the array index of its first evidence element and the
        # base variant 0. Later duplicates of each kind guard against "last wins".
        text_first = _source(
            _shape("decor"),
            _text("headline", x=100, y=100),
            _image("hero", y=300),
            _text("caption", x=100, y=700),
            _image("badge", x=600, y=300, width=100, height=100),
        )
        media_first = _source(
            _shape("decor"),
            _image("hero", y=300),
            _text("headline", x=100, y=100),
            _image("badge", x=600, y=300, width=100, height=100),
            _text("caption", x=100, y=700),
        )

        orders = {}
        for name, source in (("text_first", text_first), ("media_first", media_first)):
            elements = source["elements"]
            first_text = next(
                index for index, item in enumerate(elements) if item["type"] == "text"
            )
            first_image = next(
                index for index, item in enumerate(elements) if item["type"] == "image"
            )
            specs = enumerate_candidate_specs(source, WIDE)
            with self.subTest(order=name):
                self.assertEqual(len(specs), 12)
                for spec in specs:
                    expected = {BASE: 0, COPY: first_text, MEDIA: first_image}[
                        spec.variant
                    ]
                    self.assertEqual(spec.source_order, expected, spec)
            orders[name] = {spec.variant: spec.source_order for spec in specs}

        # Text-before-media vs media-before-text swaps the two evidence positions.
        self.assertEqual(orders["text_first"], {BASE: 0, COPY: 1, MEDIA: 2})
        self.assertEqual(orders["media_first"], {BASE: 0, MEDIA: 1, COPY: 2})

    def test_many_elements_still_enumerate_exactly_twelve_bounded_specs(self):
        elements = [
            _image(f"photo_{index}", x=20 + 90 * index, y=20, width=80, height=80)
            for index in range(8)
        ]
        elements.extend(
            _text(f"line_{index}", x=20, y=200 + 70 * index, width=900, height=60)
            for index in range(8)
        )
        source = _source(*elements)
        specs = enumerate_candidate_specs(source, WIDE)

        # ADR-009 section 3: at most four families x three variants.
        self.assertEqual(len(specs), 12)
        self.assertEqual(
            tuple(spec.candidate_index for spec in specs), tuple(range(12))
        )
        self.assertEqual(
            _variants_by_family(specs),
            {family: (BASE, MEDIA, COPY) for family in TOPOLOGY_ORDER},
        )
        for family in TOPOLOGY_ORDER:
            family_specs = [spec for spec in specs if spec.topology == family]
            self.assertLessEqual(len(family_specs), 3)
            self.assertEqual([spec.variant_index for spec in family_specs], [0, 1, 2])
        self.assertEqual(
            [spec.topology_order for spec in specs],
            [order for order in range(4) for _ in range(3)],
        )

    def test_bounded_search_admits_hard_valid_candidates_and_repeats_byte_stably(self):
        runs = [
            search(
                SOURCE,
                SQUARE,
                max_candidates=MAX_CANDIDATES,
                assets_dir=ASSETS,
                fonts_dir=FONTS,
            )
            for _ in range(2)
        ]

        run_signatures = []
        for result in runs:
            candidate_signatures = []
            for candidate in result.candidates:
                # Hard validation is the admission evidence; quality is not used
                # to establish this contract property.
                validate_response(SOURCE, SQUARE, candidate.response)
                # Independent PNG decode: dimensions must equal the target canvas.
                with Image.open(io.BytesIO(candidate.rendered_png)) as image:
                    self.assertEqual(image.format, "PNG")
                    self.assertEqual(image.size, (SQUARE["width"], SQUARE["height"]))
                candidate_signatures.append(
                    (
                        candidate.topology,
                        candidate.variant,
                        candidate.candidate_index,
                        candidate.response,
                        hashlib.sha256(candidate.rendered_png).hexdigest(),
                    )
                )
            validate_response(SOURCE, SQUARE, result.response)
            self.assertEqual(
                result.diagnostics["work_set_topologies"], TOPOLOGY_ORDER
            )
            specs = enumerate_candidate_specs(SOURCE, SQUARE)
            self._assert_work_set_accounting(
                specs,
                result.candidates,
                result.diagnostics["failures"],
                result.diagnostics["evaluated_candidates"],
            )
            run_signatures.append(
                (
                    result.selected.topology,
                    result.selected.variant,
                    result.selected.candidate_index,
                    result.response,
                    hashlib.sha256(result.selected.rendered_png).hexdigest(),
                    tuple(candidate_signatures),
                )
            )

        self.assertEqual(run_signatures[0], run_signatures[1])


if __name__ == "__main__":
    unittest.main()
