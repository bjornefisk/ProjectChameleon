import unittest

try:
    from engine.layout.ranking import QualityScore, select_best
    from engine.layout.search import (
        MAX_CANDIDATES,
        MAX_VARIANTS_PER_FAMILY,
        TOPOLOGY_ORDER,
        Candidate,
        enumerate_candidate_specs,
    )
except ModuleNotFoundError:
    from chameleon.engine.layout.ranking import QualityScore, select_best
    from chameleon.engine.layout.search import (
        MAX_CANDIDATES,
        MAX_VARIANTS_PER_FAMILY,
        TOPOLOGY_ORDER,
        Candidate,
        enumerate_candidate_specs,
    )


class SearchRankingTests(unittest.TestCase):
    def test_candidate_specs_are_bounded_and_stably_ordered(self):
        source = {
            "canvas": {"width": 100, "height": 100},
            "elements": [],
        }
        target = {"width": 1600, "height": 400}
        specs = enumerate_candidate_specs(source, target)

        self.assertLessEqual(len(specs), MAX_CANDIDATES)
        self.assertLessEqual(
            max((spec.variant_index for spec in specs), default=-1) + 1,
            MAX_VARIANTS_PER_FAMILY,
        )
        self.assertEqual(
            [spec.topology for spec in specs],
            sorted(
                (spec.topology for spec in specs),
                key=TOPOLOGY_ORDER.index,
            ),
        )
        self.assertEqual(
            [(spec.topology, spec.variant_index) for spec in specs],
            [("near_isomorphic", 0)],
        )

    def test_ranker_uses_fixed_point_quality_and_stable_ties(self):
        quality = QualityScore(readability=900, balance=800, alignment=700, hierarchy=600)
        self.assertTrue(all(type(value) is int for value in quality.as_tuple()))
        self.assertEqual(quality.as_tuple(), (900, 600, 700, 800))

        low_topology = Candidate(
            topology="near_isomorphic",
            variant="source_proportional",
            topology_order=0,
            variant_index=0,
            source_order=4,
            response={"canvas": {}, "elements": []},
            rendered_png=b"",
            quality=quality,
        )
        later_topology = Candidate(
            topology="column_pivot",
            variant="source_proportional",
            topology_order=1,
            variant_index=0,
            source_order=0,
            response={"canvas": {}, "elements": []},
            rendered_png=b"",
            quality=quality,
        )
        self.assertIs(select_best([later_topology, low_topology]), low_topology)

    def test_ranker_prefers_quality_before_topology(self):
        weaker = Candidate(
            topology="near_isomorphic",
            variant="source_proportional",
            topology_order=0,
            variant_index=0,
            source_order=0,
            response={"canvas": {}, "elements": []},
            rendered_png=b"",
            quality=QualityScore(900, 1000, 1000, 1000),
        )
        stronger = Candidate(
            topology="vertical_restack",
            variant="source_proportional",
            topology_order=3,
            variant_index=0,
            source_order=0,
            response={"canvas": {}, "elements": []},
            rendered_png=b"",
            quality=QualityScore(901, 0, 0, 0),
        )
        self.assertIs(select_best([weaker, stronger]), stronger)

    def test_ranker_uses_candidate_and_source_order_after_quality(self):
        quality = QualityScore(700, 700, 700, 700)
        later_candidate = Candidate(
            topology="near_isomorphic",
            variant="dominant_copy",
            topology_order=0,
            variant_index=2,
            candidate_index=2,
            source_order=0,
            response={"canvas": {}, "elements": []},
            rendered_png=b"",
            quality=quality,
        )
        earlier_candidate = Candidate(
            topology="near_isomorphic",
            variant="dominant_media",
            topology_order=0,
            variant_index=1,
            candidate_index=1,
            source_order=99,
            response={"canvas": {}, "elements": []},
            rendered_png=b"",
            quality=quality,
        )
        self.assertIs(
            select_best([later_candidate, earlier_candidate]),
            earlier_candidate,
        )
        later_source = Candidate(
            topology="near_isomorphic",
            variant="dominant_media",
            topology_order=0,
            variant_index=1,
            candidate_index=1,
            source_order=5,
            response={"canvas": {}, "elements": []},
            rendered_png=b"",
            quality=quality,
        )
        earlier_source = Candidate(
            topology="near_isomorphic",
            variant="dominant_media",
            topology_order=0,
            variant_index=1,
            candidate_index=1,
            source_order=2,
            response={"canvas": {}, "elements": []},
            rendered_png=b"",
            quality=quality,
        )
        self.assertIs(
            select_best([later_source, earlier_source]),
            earlier_source,
        )


if __name__ == "__main__":
    unittest.main()
