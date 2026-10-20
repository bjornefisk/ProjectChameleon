import copy
import json
import math
import unittest
from pathlib import Path

from decimal import Decimal
from engine.contract import validate_response, validate_source
from engine.errors import InfeasibleLayoutError, InfeasibleReasonCode


FIXTURES = Path(__file__).parents[1] / "fixtures" / "contract"


def load_fixture(name):
    return json.loads((FIXTURES / name).read_text(), parse_float=Decimal)


def design_with_elements(elements, width=200, height=100):
    return {"canvas": {"width": width, "height": height}, "elements": elements}


def grouped_source():
    return design_with_elements(
        [
            {
                "id": "plate",
                "type": "shape",
                "x": 10,
                "y": 10,
                "width": 20,
                "height": 10,
                "shape_type": "rectangle",
                "fill_color": "rgba(0,0,0,1)",
                "group_id": "unit",
            },
            {
                "id": "label",
                "type": "text",
                "x": 10,
                "y": 20,
                "width": 20,
                "height": 10,
                "content": "Label",
                "font_family": "Solstice Sans",
                "font_size": 10,
                "color": "rgba(255,255,255,1)",
                "text_align": "center",
                "group_id": "unit",
            },
        ]
    )


def separated_source():
    return design_with_elements(
        [
            {
                "id": "left",
                "type": "shape",
                "x": 10,
                "y": 10,
                "width": 30,
                "height": 30,
                "shape_type": "rectangle",
                "fill_color": "rgba(0,0,0,1)",
            },
            {
                "id": "right",
                "type": "shape",
                "x": 100,
                "y": 10,
                "width": 30,
                "height": 30,
                "shape_type": "rectangle",
                "fill_color": "rgba(255,255,255,1)",
            },
        ]
    )


class ContractValidatorTests(unittest.TestCase):
    def assert_reason(self, source, target, response, expected):
        with self.assertRaises(InfeasibleLayoutError) as raised:
            validate_response(source, target, response)
        self.assertEqual(raised.exception.reason_code, expected)
        self.assertEqual(raised.exception.code, expected.value)
        self.assertTrue(str(raised.exception))

    def test_reason_taxonomy_and_error_details(self):
        expected = {
            "INVALID_SOURCE",
            "INVALID_TARGET",
            "MALFORMED_INPUT",
            "IMMUTABLE_FIELD_CHANGED",
            "CONTAINMENT_VIOLATION",
            "IMAGE_RATIO_VIOLATION",
            "GROUP_VIOLATION",
            "SOURCE_SEPARATION_VIOLATION",
            "TEXT_OVERFLOW",
            "NO_HARD_VALID_CANDIDATE",
            "INCOMPLETE_SEARCH",
            "RUNTIME_IO_FAILURE",
        }
        self.assertEqual({code.value for code in InfeasibleReasonCode}, expected)

        error = InfeasibleLayoutError(
            InfeasibleReasonCode.NO_HARD_VALID_CANDIDATE,
            "no candidate",
            {"candidate_count": 0},
        )
        self.assertEqual(error.reason_code, InfeasibleReasonCode.NO_HARD_VALID_CANDIDATE)
        self.assertEqual(error.details, {"candidate_count": 0})

    def test_contract_fixtures_validate(self):
        empty = load_fixture("empty_design.json")
        validate_source(empty)
        validate_response(empty, {"width": 640, "height": 360}, {"canvas": {"width": 640, "height": 360}, "elements": []})

        minimal = load_fixture("minimal_design.json")
        validate_source(minimal)
        minimal_response = copy.deepcopy(minimal)
        validate_response(minimal, minimal["canvas"], minimal_response)

        styled = load_fixture("style_run_boundary.json")
        validate_source(styled)
        validate_response(styled, styled["canvas"], copy.deepcopy(styled))

        ratio_task = load_fixture("image_ratio.json")
        ratio_source = ratio_task["source"]
        ratio_response = copy.deepcopy(ratio_source)
        ratio_response["canvas"] = ratio_task["target_canvas"]
        ratio_response["elements"][0].update({"x": 40, "y": 20, "width": 320, "height": 200})
        validate_source(ratio_source)
        validate_response(ratio_source, ratio_task["target_canvas"], ratio_response)

        bleed = load_fixture("offcanvas_decoration.json")
        bleed_response = copy.deepcopy(bleed)
        bleed_response["canvas"] = {"width": 640, "height": 480}
        bleed_response["elements"][0].update({"width": 640, "height": 480})
        bleed_response["elements"][1].update({"x": -20, "y": -20, "width": 300, "height": 300})
        validate_source(bleed)
        validate_response(bleed, bleed_response["canvas"], bleed_response)

        infeasible = load_fixture("infeasible_target.json")
        validate_source(infeasible["source"])


    def test_decimal_source_numbers_are_compared_exactly(self):
        source = design_with_elements(
            [
                {
                    "id": "decimal_shape",
                    "type": "shape",
                    "x": Decimal("10.50"),
                    "y": Decimal("10.25"),
                    "width": Decimal("20.0"),
                    "height": Decimal("10.0"),
                    "rotation": Decimal("90.0"),
                    "opacity": Decimal("0.50"),
                    "shape_type": "rectangle",
                    "fill_color": "rgba(0,0,0,1)",
                }
            ]
        )
        validate_source(source)
        response = copy.deepcopy(source)
        response["canvas"] = {"width": 300, "height": 200}
        response["elements"][0].update({"x": 40, "y": 20, "width": 20, "height": 10})
        validate_response(source, response["canvas"], response)

    def test_binary_float_sources_are_rejected_and_decimal_json_stays_exact(self):
        raw = (
            '{"canvas":{"width":100,"height":100},"elements":['
            '{"id":"img","type":"image","x":1,"y":1,'
            '"width":0.100000000000000005,"height":1,"asset_id":"a.png"}]}'
        )
        lossy_source = json.loads(raw)
        with self.assertRaises(InfeasibleLayoutError) as raised:
            validate_source(lossy_source)
        self.assertEqual(raised.exception.reason_code, InfeasibleReasonCode.INVALID_SOURCE)

        source = json.loads(raw, parse_float=Decimal)
        response = copy.deepcopy(source)
        response["elements"][0].update({"width": 1, "height": 10})
        self.assert_reason(
            source,
            source["canvas"],
            response,
            InfeasibleReasonCode.IMAGE_RATIO_VIOLATION,
        )

    def test_integral_decimal_tokens_are_integers_per_json_schema(self):
        raw = (
            '{"canvas":{"width":640.0,"height":360.0},"elements":['
            '{"id":"a","type":"shape","x":1.0,"y":1.0,"width":10.0,"height":10.0,'
            '"z_index":1.0,"shape_type":"rectangle","fill_color":"rgba(0,0,0,1)"}]}'
        )
        source = json.loads(raw, parse_float=Decimal)
        validate_source(source)
        response = copy.deepcopy(source)
        response["canvas"] = {"width": 640, "height": 360}
        response["elements"][0].update({"x": 1, "y": 1, "width": 10, "height": 10})
        validate_response(source, response["canvas"], response)
        validate_response(source, source["canvas"], response)

    def test_source_validation_rejects_invalid_source_and_duplicate_ids(self):
        source = load_fixture("minimal_design.json")
        invalid = copy.deepcopy(source)
        invalid["canvas"]["width"] = 0
        with self.assertRaises(InfeasibleLayoutError) as raised:
            validate_source(invalid)
        self.assertEqual(raised.exception.reason_code, InfeasibleReasonCode.INVALID_SOURCE)

        duplicate = copy.deepcopy(source)
        duplicate["elements"][1]["id"] = duplicate["elements"][0]["id"]
        with self.assertRaises(InfeasibleLayoutError) as raised:
            validate_source(duplicate)
        self.assertEqual(raised.exception.reason_code, InfeasibleReasonCode.INVALID_SOURCE)

    def test_target_and_response_structure_are_typed(self):
        source = load_fixture("minimal_design.json")
        response = copy.deepcopy(source)
        self.assert_reason(source, {"width": 0, "height": 100}, response, InfeasibleReasonCode.INVALID_TARGET)
        self.assert_reason(source, {"width": 320, "height": 180}, None, InfeasibleReasonCode.MALFORMED_INPUT)

        wrong_canvas = copy.deepcopy(source)
        wrong_canvas["canvas"] = {"width": 321, "height": 180}
        self.assert_reason(source, source["canvas"], wrong_canvas, InfeasibleReasonCode.MALFORMED_INPUT)

    def test_ids_count_order_and_types_are_immutable(self):
        source = load_fixture("minimal_design.json")
        target = source["canvas"]

        for mutate in (
            lambda response: response["elements"][0].update({"id": "renamed"}),
            lambda response: response["elements"].reverse(),
            lambda response: response["elements"].pop(),
            lambda response: response["elements"][0].update(
                {"type": "shape", "shape_type": "rectangle", "fill_color": "rgba(0,0,0,1)"}
            ),
        ):
            response = copy.deepcopy(source)
            mutate(response)
            self.assert_reason(source, target, response, InfeasibleReasonCode.IMMUTABLE_FIELD_CHANGED)

    def test_all_non_geometry_fields_and_annotations_are_immutable(self):
        source = load_fixture("minimal_design.json")
        target = source["canvas"]
        mutations = (
            (0, "content", "Changed"),
            (0, "font_family", "Other"),
            (0, "style_runs", []),
            (1, "shape_type", "ellipse"),
            (1, "fill_color", "rgba(1,1,1,1)"),
            (1, "_fixture_note", "changed"),
        )
        for index, field, value in mutations:
            response = copy.deepcopy(source)
            response["elements"][index][field] = value
            self.assert_reason(source, target, response, InfeasibleReasonCode.IMMUTABLE_FIELD_CHANGED)

        image_task = load_fixture("image_ratio.json")
        image_source = image_task["source"]
        image_response = copy.deepcopy(image_source)
        image_response["canvas"] = image_task["target_canvas"]
        image_response["elements"][0].update({"width": 320, "height": 200, "asset_id": "other.png"})
        self.assert_reason(
            image_source,
            image_task["target_canvas"],
            image_response,
            InfeasibleReasonCode.IMMUTABLE_FIELD_CHANGED,
        )

    def test_serialized_mutable_values_are_finite_integers(self):
        source = load_fixture("minimal_design.json")
        target = source["canvas"]
        for field, value in (("x", 20.5), ("width", math.inf), ("height", 10.0)):
            response = copy.deepcopy(source)
            response["elements"][0][field] = value
            self.assert_reason(source, target, response, InfeasibleReasonCode.MALFORMED_INPUT)

        response = copy.deepcopy(source)
        response["elements"][0]["font_size"] = 24.5
        self.assert_reason(source, target, response, InfeasibleReasonCode.MALFORMED_INPUT)

    def test_rotated_containment_and_source_bleed_side_set(self):
        source = load_fixture("minimal_design.json")
        response = copy.deepcopy(source)
        response["elements"][1].update({"x": -10, "y": 20})
        self.assert_reason(source, source["canvas"], response, InfeasibleReasonCode.CONTAINMENT_VIOLATION)

        bleed = load_fixture("offcanvas_decoration.json")
        changed_sides = copy.deepcopy(bleed)
        changed_sides["elements"][1].update({"x": 10, "y": -20})
        self.assert_reason(bleed, bleed["canvas"], changed_sides, InfeasibleReasonCode.CONTAINMENT_VIOLATION)

    def test_rotated_aabb_is_the_containment_predicate(self):
        source = design_with_elements(
            [
                {
                    "id": "rotated",
                    "type": "shape",
                    "x": 40,
                    "y": 20,
                    "width": 20,
                    "height": 20,
                    "rotation": 45,
                    "shape_type": "rectangle",
                    "fill_color": "rgba(0,0,0,1)",
                }
            ]
        )
        response = copy.deepcopy(source)
        response["elements"][0]["x"] = 0
        self.assert_reason(
            source,
            source["canvas"],
            response,
            InfeasibleReasonCode.CONTAINMENT_VIOLATION,
        )

    def test_exact_aabb_rejects_one_pixel_overflow_above_float_precision(self):
        source = design_with_elements(
            [
                {
                    "id": "edge",
                    "type": "shape",
                    "x": 10,
                    "y": 10,
                    "width": 10,
                    "height": 10,
                    "shape_type": "rectangle",
                    "fill_color": "rgba(0,0,0,1)",
                }
            ]
        )
        target = {"width": 2**53, "height": 100}
        response = copy.deepcopy(source)
        response["canvas"] = target
        response["elements"][0].update({"x": 2**53 - 1, "width": 2})

        boundary = copy.deepcopy(response)
        boundary["elements"][0]["x"] = 2**53 - 2
        validate_response(source, target, boundary)

        self.assert_reason(
            source,
            target,
            response,
            InfeasibleReasonCode.CONTAINMENT_VIOLATION,
        )

    def test_explicit_text_line_overflow_has_a_typed_reason(self):
        source = design_with_elements(
            [
                {
                    "id": "copy",
                    "type": "text",
                    "x": 10,
                    "y": 10,
                    "width": 180,
                    "height": 10,
                    "content": "first" + chr(10) + "second",
                    "font_family": "Solstice Sans",
                    "font_size": 10,
                    "line_height": 1,
                    "max_lines": 1,
                    "color": "rgba(255,255,255,1)",
                }
            ]
        )
        self.assert_reason(
            source,
            source["canvas"],
            copy.deepcopy(source),
            InfeasibleReasonCode.TEXT_OVERFLOW,
        )
    def test_wrapped_text_is_checked_at_authoritative_response_boundary(self):
        source = design_with_elements(
            [
                {
                    "id": "copy",
                    "type": "text",
                    "x": 10,
                    "y": 10,
                    "width": 1,
                    "height": 80,
                    "content": "A A",
                    "font_family": "Solstice Sans",
                    "font_size": 20,
                    "color": "rgba(255,255,255,1)",
                }
            ]
        )
        self.assert_reason(
            source,
            source["canvas"],
            copy.deepcopy(source),
            InfeasibleReasonCode.TEXT_OVERFLOW,
        )
    def test_authoritative_text_validation_uses_effective_style_face_metrics(self):
        from renderer.converter.brand_fonts import load_brand_font_manager
        from renderer.converter.wrap import char_widths

        fonts = Path(__file__).parents[2] / "brand_kit" / "fonts"
        manager = load_brand_font_manager(str(fonts))
        content = "WW WW"
        regular_width = sum(
            char_widths(manager, "Solstice Sans", "regular", "regular", 24, content)
        )
        bold_width = sum(
            char_widths(manager, "Solstice Sans", "bold", "bold", 24, content)
        )
        width = math.floor((regular_width + bold_width) / 2)
        self.assertLess(regular_width, width)
        self.assertGreater(bold_width, width)

        source = design_with_elements(
            [
                {
                    "id": "copy",
                    "type": "text",
                    "x": 0,
                    "y": 0,
                    "width": width,
                    "height": 80,
                    "content": content,
                    "font_family": "Solstice Sans",
                    "font_size": 24,
                    "color": "rgba(255,255,255,1)",
                    "style_runs": [{"start": 0, "end": len(content), "font_weight": "bold"}],
                    "max_lines": 1,
                    "text_align": "center",
                }
            ],
        )
        self.assert_reason(
            source,
            source["canvas"],
            copy.deepcopy(source),
            InfeasibleReasonCode.TEXT_OVERFLOW,
        )

    def test_authoritative_text_validation_maps_missing_font_to_runtime_failure(self):
        source = design_with_elements(
            [
                {
                    "id": "copy",
                    "type": "text",
                    "x": 0,
                    "y": 0,
                    "width": 100,
                    "height": 80,
                    "content": "copy",
                    "font_family": "Not Installed",
                    "font_size": 20,
                    "color": "rgba(255,255,255,1)",
                }
            ]
        )
        self.assert_reason(
            source,
            source["canvas"],
            copy.deepcopy(source),
            InfeasibleReasonCode.RUNTIME_IO_FAILURE,
        )

    def test_authoritative_text_validation_maps_numeric_overflow_to_runtime_failure(self):
        huge = 10**400
        source = design_with_elements(
            [
                {
                    "id": "copy",
                    "type": "text",
                    "x": 0,
                    "y": 0,
                    "width": huge,
                    "height": huge,
                    "content": "copy",
                    "font_family": "Solstice Sans",
                    "font_size": 20,
                    "color": "rgba(255,255,255,1)",
                }
            ],
            width=huge,
            height=huge,
        )
        self.assert_reason(
            source,
            source["canvas"],
            copy.deepcopy(source),
            InfeasibleReasonCode.RUNTIME_IO_FAILURE,
        )


    def test_positioned_glyph_bounds_are_checked_at_authoritative_response_boundary(self):
        source = design_with_elements(
            [
                {
                    "id": "copy",
                    "type": "text",
                    "x": 10,
                    "y": 10,
                    "width": 6,
                    "height": 80,
                    "content": "j",
                    "font_family": "Solstice Sans",
                    "font_size": 24,
                    "font_style": "italic",
                    "color": "rgba(255,255,255,1)",
                }
            ]
        )
        self.assert_reason(
            source,
            source["canvas"],
            copy.deepcopy(source),
            InfeasibleReasonCode.TEXT_OVERFLOW,
        )


    def test_foreground_image_ratio_is_exact_and_background_is_exempt(self):
        task = load_fixture("image_ratio.json")
        source = task["source"]
        response = copy.deepcopy(source)
        response["canvas"] = task["target_canvas"]
        response["elements"][0].update({"width": 161, "height": 100})
        self.assert_reason(source, task["target_canvas"], response, InfeasibleReasonCode.IMAGE_RATIO_VIOLATION)

        bleed = load_fixture("offcanvas_decoration.json")
        background_response = copy.deepcopy(bleed)
        background_response["canvas"] = {"width": 200, "height": 100}
        background_response["elements"][0].update({"width": 200, "height": 100})
        background_response["elements"][1].update({"x": -20, "y": -20, "width": 100, "height": 100})
        validate_response(bleed, background_response["canvas"], background_response)

    def test_group_children_require_one_common_scale_and_translation(self):
        source = grouped_source()
        target = {"width": 400, "height": 200}
        valid = copy.deepcopy(source)
        valid["canvas"] = target
        valid["elements"][0].update({"x": 30, "y": 20, "width": 40, "height": 20})
        valid["elements"][1].update({"x": 30, "y": 40, "width": 40, "height": 20})
        validate_response(source, target, valid)

        drift = copy.deepcopy(valid)
        drift["elements"][1]["x"] += 1
        self.assert_reason(source, target, drift, InfeasibleReasonCode.GROUP_VIOLATION)

        scale_drift = copy.deepcopy(valid)
        scale_drift["elements"][1]["width"] = 42
        self.assert_reason(source, target, scale_drift, InfeasibleReasonCode.GROUP_VIOLATION)

    def test_singleton_group_still_requires_uniform_scale(self):
        source = design_with_elements(
            [
                {
                    "id": "single",
                    "type": "shape",
                    "x": 10,
                    "y": 10,
                    "width": 20,
                    "height": 10,
                    "shape_type": "rectangle",
                    "fill_color": "rgba(0,0,0,1)",
                    "group_id": "g",
                }
            ]
        )
        response = copy.deepcopy(source)
        response["elements"][0].update({"x": 20, "y": 20, "width": 40, "height": 30})

        self.assert_reason(
            source,
            source["canvas"],
            response,
            InfeasibleReasonCode.GROUP_VIOLATION,
        )

    def test_zero_size_group_scale_is_inferred_from_centers(self):
        source = design_with_elements(
            [
                {
                    "id": "first",
                    "type": "shape",
                    "x": 10,
                    "y": 10,
                    "width": 0,
                    "height": 0,
                    "shape_type": "rectangle",
                    "fill_color": "rgba(0,0,0,1)",
                    "group_id": "g",
                },
                {
                    "id": "second",
                    "type": "shape",
                    "x": 30,
                    "y": 10,
                    "width": 0,
                    "height": 0,
                    "shape_type": "rectangle",
                    "fill_color": "rgba(255,255,255,1)",
                    "group_id": "g",
                },
                {
                    "id": "third",
                    "type": "shape",
                    "x": 10,
                    "y": 30,
                    "width": 0,
                    "height": 0,
                    "shape_type": "rectangle",
                    "fill_color": "rgba(255,255,255,1)",
                    "group_id": "g",
                }
            ]
        )
        target = {"width": 200, "height": 200}
        response = copy.deepcopy(source)
        response["canvas"] = target
        response["elements"][0].update({"x": 20, "y": 20})
        response["elements"][1].update({"x": 60, "y": 20})
        response["elements"][2].update({"x": 20, "y": 60})
        validate_response(source, target, response)

        drift = copy.deepcopy(response)
        drift["elements"][1]["x"] += 1
        self.assert_reason(source, target, drift, InfeasibleReasonCode.GROUP_VIOLATION)

    def test_expanded_degenerate_source_cannot_create_collision(self):
        source = design_with_elements(
            [
                {
                    "id": "degenerate",
                    "type": "shape",
                    "x": 10,
                    "y": 10,
                    "width": 0,
                    "height": 20,
                    "shape_type": "rectangle",
                    "fill_color": "rgba(0,0,0,1)",
                },
                {
                    "id": "other",
                    "type": "shape",
                    "x": 100,
                    "y": 10,
                    "width": 20,
                    "height": 20,
                    "shape_type": "rectangle",
                    "fill_color": "rgba(255,255,255,1)",
                },
            ]
        )
        response = copy.deepcopy(source)
        response["elements"][0].update({"x": 100, "width": 20})

        self.assert_reason(
            source,
            source["canvas"],
            response,
            InfeasibleReasonCode.SOURCE_SEPARATION_VIOLATION,
        )

    def test_source_separated_elements_cannot_gain_positive_area_collision(self):
        source = separated_source()
        response = copy.deepcopy(source)
        response["elements"][1]["x"] = 35
        self.assert_reason(source, source["canvas"], response, InfeasibleReasonCode.SOURCE_SEPARATION_VIOLATION)

        touching = copy.deepcopy(source)
        touching["elements"][1]["x"] = 40
        validate_response(source, source["canvas"], touching)

    def test_source_positive_area_cannot_be_shed_and_missing_asset_id_is_preserved(self):
        task = load_fixture("image_ratio.json")
        source = task["source"]
        response = copy.deepcopy(source)
        response["canvas"] = task["target_canvas"]
        response["elements"][0].update({"width": 0, "height": 0})
        self.assert_reason(source, task["target_canvas"], response, InfeasibleReasonCode.MALFORMED_INPUT)

        missing = copy.deepcopy(source)
        missing["canvas"] = task["target_canvas"]
        missing["elements"][0]["asset_id"] = "missing.png"
        self.assert_reason(source, task["target_canvas"], missing, InfeasibleReasonCode.IMMUTABLE_FIELD_CHANGED)

    def test_background_exemption_does_not_allow_a_hidden_background(self):
        bleed = load_fixture("offcanvas_decoration.json")
        hidden = copy.deepcopy(bleed)
        hidden["elements"][0].update({"x": -5000, "y": -5000})
        self.assert_reason(bleed, bleed["canvas"], hidden, InfeasibleReasonCode.CONTAINMENT_VIOLATION)

    def test_background_boundary_contact_hides_but_one_pixel_overlap_stays_visible(self):
        bleed = load_fixture("offcanvas_decoration.json")
        touching = copy.deepcopy(bleed)
        touching["elements"][0].update({"x": -1080})
        self.assert_reason(bleed, bleed["canvas"], touching, InfeasibleReasonCode.CONTAINMENT_VIOLATION)

        one_pixel = copy.deepcopy(bleed)
        one_pixel["elements"][0].update({"x": -1079})
        validate_response(bleed, one_pixel["canvas"], one_pixel)

    def test_full_canvas_contain_image_is_not_a_background(self):
        source = design_with_elements(
            [
                {
                    "id": "photo",
                    "type": "image",
                    "x": 0,
                    "y": 0,
                    "width": 200,
                    "height": 100,
                    "asset_id": "solstice_bottle.png",
                    "fit": "contain",
                }
            ]
        )
        response = copy.deepcopy(source)
        response["elements"][0]["x"] = -1
        self.assert_reason(source, source["canvas"], response, InfeasibleReasonCode.CONTAINMENT_VIOLATION)

    def test_omitted_source_fields_stay_omitted_in_the_response(self):
        source = separated_source()
        response = copy.deepcopy(source)
        response["elements"][0]["rotation"] = 0
        self.assert_reason(source, source["canvas"], response, InfeasibleReasonCode.IMMUTABLE_FIELD_CHANGED)

    def test_infeasible_target_fixture_rejects_unmodified_geometry(self):
        task = load_fixture("infeasible_target.json")
        source = task["source"]
        candidate = copy.deepcopy(source)
        candidate["canvas"] = copy.deepcopy(task["target_canvas"])
        self.assert_reason(source, task["target_canvas"], candidate, InfeasibleReasonCode.CONTAINMENT_VIOLATION)

    def test_sample_envelopes_validate_only_after_extracting_source_and_target(self):
        samples = sorted((Path(__file__).parents[2] / "input").glob("chameleon_sample_*.json"))
        self.assertEqual(len(samples), 3)
        for path in samples:
            with self.subTest(sample=path.name):
                envelope = json.loads(path.read_text(encoding="utf-8"), parse_float=Decimal)
                source = envelope["source"]
                target = envelope["target_canvas"]
                validate_source(source)

                with self.assertRaises(InfeasibleLayoutError) as raised:
                    validate_source(envelope)
                self.assertEqual(raised.exception.reason_code, InfeasibleReasonCode.INVALID_SOURCE)

                candidate = copy.deepcopy(source)
                candidate["canvas"] = copy.deepcopy(target)
                try:
                    validate_response(source, target, candidate)
                except InfeasibleLayoutError as error:
                    # Geometry may legitimately fail at the new canvas; the target itself must be accepted.
                    self.assertNotIn(
                        error.reason_code,
                        {InfeasibleReasonCode.INVALID_TARGET, InfeasibleReasonCode.MALFORMED_INPUT},
                    )

    def test_empty_zero_size_and_text_free_sources_validate_identity(self):
        empty = design_with_elements([])
        validate_source(empty)
        validate_response(empty, empty["canvas"], copy.deepcopy(empty))

        zero_size = design_with_elements(
            [
                {
                    "id": "dot",
                    "type": "shape",
                    "x": 10,
                    "y": 10,
                    "width": 0,
                    "height": 0,
                    "shape_type": "rectangle",
                    "fill_color": "rgba(0,0,0,1)",
                }
            ]
        )
        validate_source(zero_size)
        validate_response(zero_size, zero_size["canvas"], copy.deepcopy(zero_size))

        text_free = separated_source()
        validate_source(text_free)
        validate_response(text_free, text_free["canvas"], copy.deepcopy(text_free))


if __name__ == "__main__":
    unittest.main()
