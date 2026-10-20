import hashlib
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT))

try:
    from engine.contract import validate_response
    from engine.layout.search import (
        MAX_CANDIDATES,
        MAX_VARIANTS_PER_FAMILY,
        TOPOLOGY_ORDER,
        enumerate_candidate_specs,
        search,
    )
except ModuleNotFoundError:
    from chameleon.engine.contract import validate_response
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


SOURCE = {
    "canvas": {"width": 1000, "height": 1000},
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


class Issue23SearchEvidenceTests(unittest.TestCase):
    def test_source_variants_are_stable_bounded_and_not_invented(self):
        target = {"width": 800, "height": 200}
        first = enumerate_candidate_specs(SOURCE, target)
        second = enumerate_candidate_specs(SOURCE, target)

        self.assertEqual(first, second)
        self.assertLessEqual(len(first), MAX_CANDIDATES)
        self.assertLessEqual(
            max((spec.variant_index for spec in first), default=-1) + 1,
            MAX_VARIANTS_PER_FAMILY,
        )

        expected_families = (
            "near_isomorphic",
            "column_pivot",
            "horizontal_ribbon",
        )
        expected_variants = (
            "source_proportional",
            "dominant_media",
            "dominant_copy",
        )
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
        self.assertTrue(all(spec.variant in expected_variants for spec in first))
        self.assertEqual(
            tuple(spec.candidate_index for spec in first), tuple(range(len(first)))
        )

    def test_representative_targets_observe_supported_topology_families(self):
        targets = {
            "square": {"width": 1000, "height": 1000},
            "wide": {"width": 800, "height": 200},
            "tall": {"width": 200, "height": 1600},
            "extreme": {"width": 900, "height": 100},
        }
        expected = {
            "square": {"near_isomorphic"},
            "wide": {"near_isomorphic", "column_pivot", "horizontal_ribbon"},
            "tall": {"near_isomorphic", "vertical_restack"},
            "extreme": {"near_isomorphic", "column_pivot", "horizontal_ribbon"},
        }

        observed = set()
        for name, target in targets.items():
            families = {
                spec.topology for spec in enumerate_candidate_specs(SOURCE, target)
            }
            self.assertEqual(families, expected[name])
            observed.update(families)

        self.assertEqual(observed, set(TOPOLOGY_ORDER))

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
                self.assertTrue(candidate.rendered_png.startswith(b"\x89PNG\r\n\x1a\n"))
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
