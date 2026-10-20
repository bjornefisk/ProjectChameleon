import unittest
from unittest.mock import patch

try:
    import engine.layout.search as search_module
    from engine.contract import validate_response
    from engine.errors import InfeasibleLayoutError, InfeasibleReasonCode
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
    import chameleon.engine.layout.search as search_module
    from chameleon.engine.contract import validate_response
    from chameleon.engine.errors import InfeasibleLayoutError, InfeasibleReasonCode
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
    def test_each_variant_invokes_solver_and_derived_variants_render_once(self):
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
        solver_calls = []

        def fake_solver(*args, **kwargs):
            solver_calls.append(kwargs["variant"])
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
            solver_calls,
            ["source_proportional", "dominant_media", "dominant_copy"],
        )
        self.assertEqual(
            [candidate.rendered_png for candidate in result.candidates],
            [b"solver-render", b"derived-render-1", b"derived-render-2"],
        )
        self.assertEqual(result.candidates[0].warnings, ("solver-warning",))

    def test_variant_dispatch_continues_after_failed_base_generation(self):
        source = {"canvas": {"width": 100, "height": 100}, "elements": []}
        target = {"width": 200, "height": 100}
        specs = (
            CandidateSpec("near_isomorphic", "source_proportional", 0, 0, 0, 0),
            CandidateSpec("near_isomorphic", "dominant_media", 0, 1, 0, 1),
        )
        calls = []
        solver_result = RenderedCandidate(
            response={"canvas": target, "elements": []},
            rendered_png=b"solver-render",
        )

        def solver(_source, _target, **kwargs):
            calls.append(kwargs["variant"])
            if kwargs["variant"] == "source_proportional":
                raise InfeasibleLayoutError(
                    InfeasibleReasonCode.INCOMPLETE_SEARCH,
                    "base candidate unavailable",
                )
            return solver_result

        with (
            patch("engine.layout.search.enumerate_candidate_specs", return_value=specs),
            patch("engine.layout.search._TOPOLOGY_SOLVERS", (solver,)),
            patch("engine.layout.search._render_candidate", return_value=(b"png", ())),
        ):
            result = search(source, target)

        self.assertEqual(calls, ["source_proportional", "dominant_media"])
        self.assertEqual(result.selected.variant, "dominant_media")



    def test_selected_fixed_point_components_are_diagnostic_only(self):
        source = {
            "canvas": {"width": 100, "height": 100},
            "elements": [],
        }
        target = {"width": 200, "height": 100}
        spec = CandidateSpec("near_isomorphic", "source_proportional", 0, 0, 0, 0)
        solver_result = RenderedCandidate(
            response={"canvas": target, "elements": []},
            rendered_png=b"solver-render",
        )
        with (
            patch("engine.layout.search.enumerate_candidate_specs", return_value=(spec,)),
            patch("engine.layout.search._TOPOLOGY_SOLVERS", (lambda *args, **kwargs: solver_result,)),
        ):
            result = search(source, target)

        self.assertEqual(
            result.diagnostics["selected_quality"],
            {
                "readability": 1000,
                "balance": 1000,
                "alignment": 1000,
                "hierarchy": 1000,
            },
        )
        self.assertEqual(result.response, {"canvas": target, "elements": []})

    def test_cutoff_without_candidate_is_incomplete_not_infeasible(self):
        source = {"canvas": {"width": 100, "height": 100}, "elements": []}
        target = {"width": 200, "height": 100}
        specs = (
            CandidateSpec("near_isomorphic", "source_proportional", 0, 0, 0, 0),
            CandidateSpec("column_pivot", "source_proportional", 1, 0, 0, 1),
        )

        def exhausted_solver(*args, **kwargs):
            raise InfeasibleLayoutError(
                InfeasibleReasonCode.NO_HARD_VALID_CANDIDATE,
                "this work item is exhausted",
                {"search_exhausted": True, "status": "INFEASIBLE_LAYOUT"},
            )

        with self.assertRaises(InfeasibleLayoutError) as raised:
            with (
                patch("engine.layout.search.enumerate_candidate_specs", return_value=specs),
                patch("engine.layout.search._TOPOLOGY_SOLVERS", (exhausted_solver,)),
            ):
                search(source, target, max_candidates=1)

        error = raised.exception
        self.assertEqual(error.reason_code, InfeasibleReasonCode.INCOMPLETE_SEARCH)
        self.assertEqual(error.details["status"], "INCOMPLETE_SEARCH")
        self.assertTrue(error.details["cutoff"])
        self.assertFalse(error.details["finite_work_exhausted"])
        self.assertFalse(error.details["search_exhausted"])
        self.assertTrue(error.details["failures"][0]["search_exhausted"])
        self.assertEqual(error.details["failures"][0]["status"], "INFEASIBLE_LAYOUT")

    def test_complete_explicitly_exhausted_work_is_infeasible(self):
        source = {"canvas": {"width": 100, "height": 100}, "elements": []}
        target = {"width": 200, "height": 100}
        spec = CandidateSpec("near_isomorphic", "source_proportional", 0, 0, 0, 0)

        def exhausted_solver(*args, **kwargs):
            raise InfeasibleLayoutError(
                InfeasibleReasonCode.NO_HARD_VALID_CANDIDATE,
                "this work item is exhausted",
                {"search_exhausted": True, "status": "INFEASIBLE_LAYOUT"},
            )

        with self.assertRaises(InfeasibleLayoutError) as raised:
            with (
                patch("engine.layout.search.enumerate_candidate_specs", return_value=(spec,)),
                patch("engine.layout.search._TOPOLOGY_SOLVERS", (exhausted_solver,)),
            ):
                search(source, target)

        error = raised.exception
        self.assertEqual(error.reason_code, InfeasibleReasonCode.NO_HARD_VALID_CANDIDATE)
        self.assertEqual(error.details["status"], "INFEASIBLE_LAYOUT")
        self.assertTrue(error.details["finite_work_exhausted"])
        self.assertTrue(error.details["search_exhausted"])
        self.assertTrue(error.details["failures"][0]["search_exhausted"])

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
            [(topology, 0) for topology in TOPOLOGY_ORDER],
        )

    def test_role_variants_change_role_relevant_geometry(self):
        source = {
            "canvas": {"width": 400, "height": 300},
            "elements": [
                {
                    "id": "bg",
                    "type": "image",
                    "x": 0,
                    "y": 0,
                    "width": 400,
                    "height": 300,
                    "asset_id": "background.png",
                    "fit": "cover",
                },
                {
                    "id": "hero",
                    "type": "image",
                    "x": 40,
                    "y": 80,
                    "width": 100,
                    "height": 100,
                    "asset_id": "hero.png",
                    "fit": "contain",
                },
                {
                    "id": "headline",
                    "type": "text",
                    "x": 220,
                    "y": 80,
                    "width": 120,
                    "height": 40,
                    "content": "Headline",
                    "font_family": "Solstice Sans",
                    "font_size": 20,
                    "color": "rgba(255,255,255,1)",
                },
            ],
        }
        base = {
            "canvas": {"width": 600, "height": 300},
            "elements": [
                {**source["elements"][0], "x": 0, "y": 0, "width": 600, "height": 300},
                {**source["elements"][1], "x": 80, "y": 100, "width": 120, "height": 120},
                {**source["elements"][2], "x": 340, "y": 100, "width": 180, "height": 50},
            ],
        }
        roles = infer_roles(source)
        media = _derive_variant_response(
            base,
            source,
            base["canvas"],
            roles,
            CandidateSpec("near_isomorphic", "dominant_media", 0, 1, 1, 1),
        )
        copy = _derive_variant_response(
            base,
            source,
            base["canvas"],
            roles,
            CandidateSpec("near_isomorphic", "dominant_copy", 0, 2, 2, 2),
        )

        self.assertGreater(media["elements"][1]["width"], base["elements"][1]["width"])
        self.assertGreater(media["elements"][1]["height"], base["elements"][1]["height"])
        self.assertGreater(copy["elements"][2]["width"], base["elements"][2]["width"])
        self.assertGreater(copy["elements"][2]["height"], base["elements"][2]["height"])
        self.assertGreater(copy["elements"][2]["font_size"], base["elements"][2]["font_size"])
        self.assertEqual(media["elements"][2]["width"], base["elements"][2]["width"])

    def test_badge_role_produces_copy_variant(self):
        source = {
            "canvas": {"width": 400, "height": 200},
            "elements": [
                {
                    "id": "background",
                    "type": "image",
                    "x": 0,
                    "y": 0,
                    "width": 400,
                    "height": 200,
                    "asset_id": "background.png",
                    "fit": "cover",
                },
                {
                    "id": "badge",
                    "type": "text",
                    "x": 20,
                    "y": 20,
                    "width": 100,
                    "height": 30,
                    "content": "SALE",
                    "font_family": "Solstice Sans",
                    "font_size": 16,
                    "color": "rgba(255,255,255,1)",
                    "group_id": "badge",
                },
            ],
        }

        specs = enumerate_candidate_specs(source, {"width": 800, "height": 200})

        copy_specs = [spec for spec in specs if spec.variant == "dominant_copy"]
        self.assertTrue(copy_specs)
        self.assertEqual(copy_specs[0].source_order, 1)

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
    def test_role_variants_change_role_relevant_geometry(self):
        source = {
            "canvas": {"width": 400, "height": 300},
            "elements": [
                {
                    "id": "bg",
                    "type": "image",
                    "x": 0,
                    "y": 0,
                    "width": 400,
                    "height": 300,
                    "asset_id": "background.png",
                    "fit": "cover",
                },
                {
                    "id": "hero",
                    "type": "image",
                    "x": 40,
                    "y": 80,
                    "width": 100,
                    "height": 100,
                    "asset_id": "hero.png",
                    "fit": "contain",
                },
                {
                    "id": "headline",
                    "type": "text",
                    "x": 220,
                    "y": 80,
                    "width": 120,
                    "height": 40,
                    "content": "Headline",
                    "font_family": "Solstice Sans",
                    "font_size": 20,
                    "color": "rgba(255,255,255,1)",
                },
            ],
        }
        base = {
            "canvas": {"width": 600, "height": 300},
            "elements": [
                {**source["elements"][0], "x": 0, "y": 0, "width": 600, "height": 300},
                {**source["elements"][1], "x": 80, "y": 100, "width": 120, "height": 120},
                {**source["elements"][2], "x": 340, "y": 100, "width": 180, "height": 50},
            ],
        }
        roles = infer_roles(source)
        media = _derive_variant_response(
            base,
            source,
            base["canvas"],
            roles,
            CandidateSpec("near_isomorphic", "dominant_media", 0, 1, 1, 1),
        )
        copy = _derive_variant_response(
            base,
            source,
            base["canvas"],
            roles,
            CandidateSpec("near_isomorphic", "dominant_copy", 0, 2, 2, 2),
        )
        self.assertGreater(media["elements"][1]["width"], base["elements"][1]["width"])
        self.assertGreater(media["elements"][1]["height"], base["elements"][1]["height"])
        self.assertGreater(copy["elements"][2]["width"], base["elements"][2]["width"])
        self.assertGreater(copy["elements"][2]["height"], base["elements"][2]["height"])
        self.assertGreater(copy["elements"][2]["font_size"], base["elements"][2]["font_size"])
        self.assertEqual(media["elements"][2]["width"], base["elements"][2]["width"])
    def test_variant_dispatch_continues_after_failed_base_generation(self):
        source = {"canvas": {"width": 100, "height": 100}, "elements": []}
        target = {"width": 200, "height": 100}
        specs = (
            CandidateSpec("near_isomorphic", "source_proportional", 0, 0, 0, 0),
            CandidateSpec("near_isomorphic", "dominant_media", 0, 1, 0, 1),
        )
        calls = []
        solver_result = RenderedCandidate(
            response={"canvas": target, "elements": []},
            rendered_png=b"solver-render",
        )

        def solver(_source, _target, **kwargs):
            calls.append(kwargs["variant"])
            if kwargs["variant"] == "source_proportional":
                raise InfeasibleLayoutError(
                    InfeasibleReasonCode.INCOMPLETE_SEARCH,
                    "base candidate unavailable",
                )
            return solver_result

        with patch.object(search_module, "enumerate_candidate_specs", return_value=specs):
            with patch.object(search_module, "_TOPOLOGY_SOLVERS", (solver,)):
                with patch.object(
                    search_module, "_render_candidate", return_value=(b"png", ())
                ):
                    result = search_module.search(source, target)

        self.assertEqual(calls, ["source_proportional", "dominant_media"])
        self.assertEqual(result.selected.variant, "dominant_media")


if __name__ == "__main__":
    unittest.main()
