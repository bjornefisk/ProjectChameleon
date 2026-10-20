import unittest
from unittest.mock import patch

try:
    from engine.contract import validate_response
    from engine.layout.ranking import QualityScore, select_best
    from engine.layout.candidate import RenderedCandidate
    from engine.layout.roles import infer_roles
    from engine.layout.search import (
        MAX_CANDIDATES,
        MAX_VARIANTS_PER_FAMILY,
        TOPOLOGY_ORDER,
        Candidate,
        CandidateSpec,
        _derive_variant_response,
        enumerate_candidate_specs,
        search,
    )
except ModuleNotFoundError:
    from chameleon.engine.contract import validate_response
    from chameleon.engine.layout.ranking import QualityScore, select_best
    from chameleon.engine.layout.candidate import RenderedCandidate
    from chameleon.engine.layout.roles import infer_roles
    from chameleon.engine.layout.search import (
        MAX_CANDIDATES,
        MAX_VARIANTS_PER_FAMILY,
        TOPOLOGY_ORDER,
        Candidate,
        CandidateSpec,
        _derive_variant_response,
        enumerate_candidate_specs,
        search,
    )


class SearchRankingTests(unittest.TestCase):
    def test_solver_render_is_reused_and_derived_variants_render_once(self):
        source = {
            "canvas": {"width": 100, "height": 100},
            "elements": [],
        }
        target = {"width": 200, "height": 100}
        specs = (
            CandidateSpec("near_isomorphic", "source_proportional", 0, 0, 0, 0),
            CandidateSpec("near_isomorphic", "dominant_media", 0, 1, 0, 1),
            CandidateSpec("near_isomorphic", "dominant_copy", 0, 2, 0, 2),
        )
        solver_response = {"canvas": target, "elements": []}
        solver_result = RenderedCandidate(
            response=solver_response,
            rendered_png=b"solver-render",
            warnings=("solver-warning",),
        )
        render_calls = []

        def fake_solver(*args, **kwargs):
            return solver_result

        def fake_render(response, **kwargs):
            render_calls.append(response)
            return f"derived-render-{len(render_calls)}".encode(), ()

        with (
            patch("engine.layout.search.enumerate_candidate_specs", return_value=specs),
            patch("engine.layout.search._TOPOLOGY_SOLVERS", (fake_solver,)),
            patch("engine.layout.search._render_candidate", side_effect=fake_render),
        ):
            result = search(source, target)

        self.assertEqual(len(render_calls), 2)
        self.assertEqual(
            [candidate.rendered_png for candidate in result.candidates],
            [b"solver-render", b"derived-render-1", b"derived-render-2"],
        )

        self.assertEqual(result.candidates[0].warnings, ("solver-warning",))

    def test_variant_translations_round_complete_coordinate_once(self):
        source = {
            "canvas": {"width": 10, "height": 10},
            "elements": [
                {
                    "id": "shape",
                    "type": "shape",
                    "x": 1,
                    "y": 1,
                    "width": 2,
                    "height": 2,
                    "shape_type": "rectangle",
                    "fill_color": "rgba(0,0,0,1)",
                }
            ],
        }
        target = {"width": 6, "height": 6}
        base = {
            "canvas": dict(target),
            "elements": [dict(source["elements"][0])],
        }
        roles = infer_roles(source)

        for variant_index, field in ((1, "x"), (2, "y")):
            with self.subTest(field=field):
                spec = CandidateSpec(
                    "near_isomorphic",
                    "dominant_media" if variant_index == 1 else "dominant_copy",
                    0,
                    variant_index,
                    0,
                    variant_index,
                )
                response = _derive_variant_response(base, source, target, roles, spec)

                self.assertEqual(response["elements"][0][field], 2)
                self.assertIs(type(response["elements"][0][field]), int)
                validate_response(source, target, response)

    def test_derived_response_is_validated_before_render(self):
        source = {
            "canvas": {"width": 100, "height": 100},
            "elements": [],
        }
        target = {"width": 200, "height": 100}
        specs = (
            CandidateSpec("near_isomorphic", "source_proportional", 0, 0, 0, 0),
            CandidateSpec("near_isomorphic", "dominant_media", 0, 1, 0, 1),
        )
        solver_response = {"canvas": target, "elements": []}
        solver_result = RenderedCandidate(
            response=solver_response,
            rendered_png=b"solver-render",
        )

        def fake_solver(*args, **kwargs):
            return solver_result

        def unexpected_render(*args, **kwargs):
            raise AssertionError("invalid derived response reached renderer")

        invalid_response = {"canvas": {"width": 999, "height": 100}, "elements": []}
        with (
            patch("engine.layout.search.enumerate_candidate_specs", return_value=specs),
            patch("engine.layout.search._TOPOLOGY_SOLVERS", (fake_solver,)),
            patch(
                "engine.layout.search._derive_variant_response",
                return_value=invalid_response,
            ),
            patch("engine.layout.search._render_candidate", side_effect=unexpected_render),
        ):
            result = search(source, target)

        self.assertEqual(result.response, solver_response)

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
