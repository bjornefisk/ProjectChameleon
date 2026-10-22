import math
from decimal import Decimal
from fractions import Fraction
import unittest

from engine.geometry.bounds import (
    AABB,
    check_source_bleed,
    clipped_sides,
    intersects_canvas,
    is_contained_in_canvas,
    positive_aabb_intersection,
    rotated_aabb,
    source_bleed_sides,
)
from engine.geometry.groups import (
    GroupTransform,
    apply_transform,
    derive_common_transform,
    derive_quantized_common_transform,
    has_quantized_common_transform,
)
from engine.geometry.math_util import quantize_to_int, to_fraction
from engine.geometry.ratios import (
    is_ratio_lattice,
    lattice_dimensions,
    preserves_source_ratio,
    reduced_ratio,
)


class ExactMathTests(unittest.TestCase):
    def test_exact_ingress_accepts_integer_decimal_and_fraction(self):
        self.assertEqual(to_fraction(3), Fraction(3))
        self.assertEqual(to_fraction(Decimal("1.25e2")), Fraction(125))
        self.assertEqual(to_fraction(Fraction(2, 7)), Fraction(2, 7))

    def test_exact_ingress_rejects_bool_float_and_nonfinite_decimal(self):
        for value in (True, 0.5):
            with self.assertRaises(TypeError):
                to_fraction(value)
        for value in (Decimal("NaN"), Decimal("Infinity"), Decimal("-Infinity")):
            with self.assertRaises(ValueError):
                to_fraction(value)

    def test_quantization_is_half_even_for_both_signs(self):
        self.assertEqual(quantize_to_int(Fraction(5, 2)), 2)
        self.assertEqual(quantize_to_int(Fraction(7, 2)), 4)
        self.assertEqual(quantize_to_int(Fraction(-5, 2)), -2)
        self.assertEqual(quantize_to_int(Fraction(-7, 2)), -4)
        self.assertEqual(quantize_to_int(Decimal("2.5")), 2)
        self.assertEqual(quantize_to_int(Decimal("3.5")), 4)
        self.assertEqual(quantize_to_int(Decimal("-2.5")), -2)
        self.assertEqual(quantize_to_int(Decimal("-3.5")), -4)


class BoundsTests(unittest.TestCase):
    def test_right_angle_aabb_is_exact(self):
        self.assertEqual(rotated_aabb(10, 20, 8, 4, 90), AABB(12, 18, 16, 26))
        self.assertEqual(rotated_aabb(10, 20, 8, 4, -180), AABB(10, 20, 18, 24))

    def test_nonright_aabb_uses_pinned_runtime_trig_coefficients(self):
        box = rotated_aabb({"x": 0, "y": 0, "width": 2, "height": 2, "rotation": 45})
        sine = math.sin(math.radians(45))
        cosine = math.cos(math.radians(45))
        self.assertIsInstance(box.min_x, Fraction)
        expected_extent = Fraction.from_float(cosine) + Fraction.from_float(sine)
        self.assertEqual(box.min_x, 1 - expected_extent)
        self.assertEqual(box.max_x, 1 + expected_extent)

    def test_containment_and_positive_area_boundaries(self):
        edge = AABB(0, 0, 10, 10)
        self.assertTrue(is_contained_in_canvas(edge, {"width": 10, "height": 10}))
        self.assertFalse(is_contained_in_canvas(AABB(-1, 0, 10, 10), 10, 10))
        self.assertFalse(positive_aabb_intersection(AABB(0, 0, 2, 2), AABB(2, 0, 4, 2)))
        self.assertFalse(positive_aabb_intersection(AABB(0, 0, 0, 2), AABB(0, 0, 2, 2)))
        self.assertTrue(positive_aabb_intersection(AABB(0, 0, 2, 2), AABB(1, 1, 3, 3)))

    def test_source_bleed_preserves_sides_and_visibility(self):
        source = AABB(-2, -1, 20, 10)
        target = AABB(-3, -4, 30, 10)
        self.assertEqual(clipped_sides(source, (10, 10)), frozenset({"left", "top", "right"}))
        self.assertIsNone(
            source_bleed_sides({"type": "shape", "opacity": 1}, source, (10, 10))
        )
        self.assertEqual(
            source_bleed_sides({"type": "shape", "opacity": Decimal("0.5")}, source, (10, 10)),
            frozenset({"left", "top", "right"}),
        )
        self.assertTrue(check_source_bleed(source, target, (10, 10), (10, 10)))
        self.assertFalse(check_source_bleed(source, AABB(0, 0, 10, 10), (10, 10), (10, 10)))
        self.assertTrue(intersects_canvas(source, (10, 10)))


class RatioTests(unittest.TestCase):
    def test_reduced_ratio_and_positive_lattice(self):
        ratio = reduced_ratio(Decimal("1920"), Decimal("1080"))
        self.assertEqual(ratio, (16, 9))
        self.assertEqual(lattice_dimensions(ratio, 3), (48, 27))
        self.assertTrue(is_ratio_lattice(48, 27, ratio))
        self.assertFalse(is_ratio_lattice(48, 28, ratio))
        self.assertFalse(is_ratio_lattice(0, 0, ratio))

    def test_degenerate_source_has_no_ratio_constraint(self):
        self.assertIsNone(reduced_ratio(0, 10))
        self.assertTrue(preserves_source_ratio(7, 4, 0, 10))
        with self.assertRaises(ValueError):
            lattice_dimensions((0, 1), 2)


class GroupTests(unittest.TestCase):
    def test_transform_preserves_fields_and_common_relationship(self):
        source = [
            {"id": "a", "type": "shape", "x": 10, "y": 20, "width": 4, "height": 6},
            {"id": "b", "type": "text", "x": 30, "y": 20, "width": 8, "height": 4, "font_size": 12},
        ]
        transform = GroupTransform(Fraction(3, 2), Fraction(5), Fraction(-2))
        target = [apply_transform(element, transform) for element in source]
        self.assertEqual(derive_common_transform(source, target), transform)
        self.assertEqual(target[1]["font_size"], 12)
        self.assertEqual(source[0]["x"], 10)
        self.assertEqual(target[0]["width"], 6)

    def test_quantized_common_transform_accepts_fractional_geometry(self):
        source = [
            {"x": 10, "y": 10, "width": 20, "height": 10},
            {"x": 10, "y": 20, "width": 20, "height": 10},
        ]
        serialized = [
            {"x": 6, "y": 6, "width": 10, "height": 5},
            {"x": 6, "y": 10, "width": 10, "height": 5},
        ]
        transform = derive_quantized_common_transform(source, serialized)

        for source_element, response_element in zip(source, serialized):
            for field, translation in (("x", transform.tx), ("y", transform.ty)):
                self.assertEqual(
                    quantize_to_int(transform.scale * to_fraction(source_element[field]) + translation),
                    response_element[field],
                )
            for field in ("width", "height"):
                self.assertEqual(
                    quantize_to_int(transform.scale * to_fraction(source_element[field])),
                    response_element[field],
                )
        self.assertTrue(has_quantized_common_transform(source, serialized))
        self.assertFalse(
            has_quantized_common_transform(
                source,
                [serialized[0], {**serialized[1], "x": 7}],
            )
        )

    def test_zero_dimension_and_rejection_cases(self):
        source = [{"x": 0, "y": 0, "width": 0, "height": 4}]
        target = [{"x": 5, "y": 8, "width": 0, "height": 8}]
        self.assertEqual(derive_common_transform(source, target).scale, 2)
        with self.assertRaises(ValueError):
            derive_common_transform(source, [{"x": 5, "y": 8, "width": 1, "height": 8}])
        with self.assertRaises(ValueError):
            GroupTransform(0, 0, 0)
        with self.assertRaises(TypeError):
            apply_transform(source[0], object())


if __name__ == "__main__":
    unittest.main()
