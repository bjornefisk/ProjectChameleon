"""Renderer-seam semantic PNG conformance tests.

Positive cases always use the pinned adapter. Negative cases mutate a decoded
render or deliberately provide the wrong renderer metadata; no canned image is
used as evidence of conformance.
"""

import json
import unittest
from decimal import Decimal

from PIL import ImageDraw

from .support import (
    ArtifactTestCase,
    FIXTURE_NAMES,
    SAMPLES,
    design_of,
    image_element,
    load_design,
    only,
    render,
    shape_element,
    text_element,
)

try:
    from engine.contract import validate_source
    from engine.resize import resize
except ModuleNotFoundError:
    from chameleon.engine.contract import validate_source
    from chameleon.engine.resize import resize


class ConformantRenderTests(ArtifactTestCase):
    def test_artifact_fixtures_are_contract_valid_sources(self):
        for name in FIXTURE_NAMES:
            with self.subTest(name=name):
                validate_source(load_design(name))

    def test_real_render_of_each_fixture_conforms(self):
        for name in FIXTURE_NAMES:
            with self.subTest(name=name):
                design = load_design(name)
                image, warnings = render(design)
                self.assertConforms(design, image, warnings)

    def test_public_level_one_and_two_resized_renders_conform(self):
        for name in ("chameleon_sample_level1_warmup", "chameleon_sample_level2_core"):
            with self.subTest(name=name):
                task = json.loads(
                    (SAMPLES / f"{name}.json").read_text(encoding="utf-8"),
                    parse_int=int,
                    parse_float=Decimal,
                )
                response = resize(task["source"], task["target_canvas"])
                image, warnings = render(response)
                self.assertConforms(response, image, warnings)

    def test_empty_canvas_is_a_valid_opaque_artifact(self):
        design = design_of(20, 13)
        image, warnings = render(design)
        self.assertConforms(design, image, warnings)

    def test_rgb_png_is_normalized_as_opaque(self):
        design = only(load_design("composite"), "backdrop")
        image, warnings = render(design)
        self.assertConforms(design, image.convert("RGB"), warnings)

    def test_low_contrast_text_is_hard_valid(self):
        design = load_design("low_contrast_text")
        image, warnings = render(design)
        self.assertConforms(design, image, warnings)

    def test_off_canvas_bleed_and_overlap_are_not_false_rejected(self):
        design = load_design("bleed_overlap")
        image, warnings = render(design)
        self.assertConforms(design, image, warnings)

    def test_rotated_shape_pixels_match_the_pinned_renderer(self):
        design = design_of(
            120,
            100,
            shape_element("rotated", 30, 25, 50, 30, rotation=Decimal("27")),
        )
        image, warnings = render(design)
        self.assertConforms(design, image, warnings)
        tampered = image.copy()
        tampered.putpixel((55, 40), (0, 0, 0, 255))
        self.assertRejected("render_pixels", design, tampered, warnings)

    def test_translucent_shape_pixels_match_the_pinned_renderer(self):
        design = design_of(
            120,
            100,
            shape_element("veil", 30, 25, 50, 30, opacity=Decimal("0.5")),
        )
        image, warnings = render(design)
        self.assertConforms(design, image, warnings)
        tampered = image.copy()
        tampered.putpixel((55, 40), (255, 0, 0, 255))
        self.assertRejected("render_pixels", design, tampered, warnings)

    def test_zero_area_records_follow_renderer_noop_semantics(self):
        for element in (
            shape_element("shape", 10, 10, 0, 20),
            image_element("image", "absent.png", 10, 10, 20, 0),
        ):
            with self.subTest(element=element["id"]):
                design = design_of(80, 60, element)
                image, warnings = render(design)
                self.assertConforms(design, image, warnings)


class DimensionAndCanvasTests(ArtifactTestCase):
    def test_wrong_dimensions_are_rejected(self):
        design = only(load_design("composite"), "backdrop")
        image, warnings = render(design)
        wrong = image.resize((image.width + 1, image.height))
        error = self.assertRejected("dimensions", design, wrong, warnings)
        self.assertEqual(error.details["actual_size"], (image.width + 1, image.height))

    def test_large_canvas_uses_the_pinned_2048_limit(self):
        design = load_design("large_canvas")
        image, warnings = render(design)
        self.assertEqual(image.size, (2048, 1365))
        self.assertConforms(design, image, warnings)
        self.assertRejected(
            "dimensions", design, image.resize((2100, 1400)), warnings
        )

    def test_any_transparent_canvas_pixel_is_rejected(self):
        design = only(load_design("composite"), "backdrop")
        image, warnings = render(design)
        damaged = image.copy()
        damaged.putpixel((0, 0), (255, 255, 255, 254))
        self.assertRejected("opacity", design, damaged, warnings, pixel=(0, 0))

    def test_fully_transparent_png_is_rejected(self):
        design = design_of(30, 20)
        image, warnings = render(design)
        damaged = image.copy()
        damaged.putalpha(0)
        self.assertRejected("opacity", design, damaged, warnings)


class MissingAssetPolicyTests(ArtifactTestCase):
    def test_placeholder_is_accepted_only_with_exact_warning(self):
        design = load_design("missing_asset")
        image, warnings = render(design)
        self.assertEqual(
            warnings,
            [
                "Missing asset 'absent_hero.png' for element 'hero' - rendered a placeholder."
            ],
        )
        self.assertConforms(design, image, warnings)
        self.assertRejected("missing_asset_warning", design, image, ())
        self.assertRejected(
            "missing_asset_warning",
            design,
            image,
            ["Missing asset 'absent_hero.png' for element 'wrong' - rendered a placeholder."],
        )

    def test_present_asset_with_a_missing_warning_is_rejected(self):
        design = only(load_design("composite"), "bottle")
        image, _warnings = render(design)
        self.assertRejected(
            "missing_asset_warning",
            design,
            image,
            ["Missing asset 'solstice_bottle.png' for element 'bottle' - rendered a placeholder."],
        )

    def test_missing_asset_placeholder_pixel_mutation_is_rejected(self):
        design = load_design("missing_asset")
        image, warnings = render(design)
        damaged = image.copy()
        damaged.putpixel((10, 10), (255, 255, 255, 255))
        self.assertRejected("image_pixels", design, damaged, warnings)


class BoundsAndPixelTests(ArtifactTestCase):
    def test_exact_shape_has_no_margin_ring(self):
        design = design_of(80, 60, shape_element("box", 20, 15, 30, 20))
        image, warnings = render(design)
        for point in ((19, 20), (50, 20), (20, 14), (20, 35)):
            with self.subTest(point=point):
                damaged = image.copy()
                damaged.putpixel(point, (0, 0, 0, 255))
                self.assertRejected("bounds", design, damaged, warnings)

    def test_non_exact_element_rejects_unauthorized_exterior_ink(self):
        design = design_of(
            80,
            60,
            shape_element("veil", 20, 15, 30, 20, opacity=Decimal("0.5")),
        )
        image, warnings = render(design)
        for point in (
            (19, 20),
            (50, 20),
            (20, 14),
            (20, 35),
            (18, 20),
            (51, 20),
            (20, 13),
            (20, 36),
        ):
            with self.subTest(point=point):
                damaged = image.copy()
                damaged.putpixel(point, (0, 0, 0, 255))
                self.assertRejected("bounds", design, damaged, warnings)

    def test_exact_image_pixels_are_replayed(self):
        design = design_of(80, 60, image_element("swatch", "swatch.png", 20, 15, 30, 20))
        image, warnings = self.render_here(design)
        damaged = image.copy()
        damaged.putpixel((25, 20), (255, 255, 255, 255))
        self.assertRejected("image_pixels", design, damaged, warnings, assets_dir=self.assets)

    def test_exact_image_shift_is_rejected_even_inside_the_same_box(self):
        design = design_of(80, 60, image_element("swatch", "swatch.png", 20, 15, 30, 20))
        image, warnings = self.render_here(design)
        damaged = image.copy()
        crop = image.crop((21, 15, 50, 35))
        damaged.paste(crop, (20, 15))
        self.assertRejected("image_pixels", design, damaged, warnings, assets_dir=self.assets)

    def test_exact_shape_pixels_are_replayed(self):
        design = design_of(80, 60, shape_element("box", 20, 15, 30, 20))
        image, warnings = render(design)
        damaged = image.copy()
        damaged.putpixel((25, 20), (255, 0, 0, 255))
        self.assertRejected("shape_pixels", design, damaged, warnings)

    def test_transparent_source_hole_cannot_hide_stray_ink(self):
        design = design_of(80, 60, image_element("ring", "ring.png", 20, 10, 40, 40))
        image, warnings = self.render_here(design)
        damaged = image.copy()
        damaged.putpixel((40, 30), (0, 0, 0, 255))
        self.assertRejected("bounds", design, damaged, warnings, assets_dir=self.assets)

    def test_later_opaque_element_reestablishes_known_pixels(self):
        design = design_of(
            80,
            60,
            image_element("under", "swatch.png", 10, 10, 40, 30, z_index=0),
            shape_element(
                "over", 10, 10, 40, 30, z_index=1, fill_color="rgba(200,30,30,1)"
            ),
        )
        image, warnings = self.render_here(design)
        damaged = image.copy()
        damaged.putpixel((25, 20), (0, 0, 0, 255))
        self.assertRejected("shape_pixels", design, damaged, warnings, assets_dir=self.assets)

    def test_invisible_cover_does_not_obstruct_an_exact_layer(self):
        design = design_of(
            80,
            60,
            image_element("under", "swatch.png", 10, 10, 40, 30, z_index=0),
            shape_element("cover", 10, 10, 40, 30, z_index=1, opacity=Decimal("0")),
        )
        image, warnings = self.render_here(design)
        damaged = image.copy()
        damaged.putpixel((25, 20), (255, 255, 255, 255))
        self.assertRejected("image_pixels", design, damaged, warnings, assets_dir=self.assets)

    def test_first_failure_reports_first_row_major_pixel(self):
        design = design_of(80, 60, shape_element("box", 20, 15, 30, 20))
        image, warnings = render(design)
        damaged = image.copy()
        damaged.putpixel((26, 20), (0, 0, 0, 255))
        damaged.putpixel((25, 20), (0, 0, 0, 255))
        error = self.assertRejected("shape_pixels", design, damaged, warnings)
        self.assertEqual(error.details["pixel"], (25, 20))

    def test_validation_does_not_repair_the_image(self):
        design = design_of(80, 60, shape_element("box", 20, 15, 30, 20))
        image, warnings = render(design)
        damaged = image.copy()
        damaged.putpixel((25, 20), (0, 0, 0, 255))
        before = damaged.tobytes()
        with self.assertRaises(Exception):
            self.validate(design, damaged, warnings)
        self.assertEqual(damaged.tobytes(), before)


class RenderedPixelTests(ArtifactTestCase):
    def test_text_interior_must_match_the_pinned_renderer(self):
        design = design_of(
            160,
            80,
            text_element("label", 20, 15, 120, 45, content="Hello"),
        )
        image, warnings = render(design)
        damaged = image.copy()
        ImageDraw.Draw(damaged).rectangle(
            [40, 25, 90, 45], fill=(255, 0, 0, 255)
        )
        self.assertRejected("render_pixels", design, damaged, warnings)

    def test_downscaled_interior_must_match_the_pinned_renderer(self):
        design = load_design("large_canvas")
        image, warnings = render(design)
        damaged = image.copy()
        damaged.putpixel((1000, 700), (0, 0, 0, 255))
        self.assertRejected("render_pixels", design, damaged, warnings)

    def test_partial_alpha_source_pixel_must_match_the_pinned_renderer(self):
        design = design_of(80, 60, image_element("soft", "soft.png", 20, 10, 40, 40))
        image, warnings = self.render_here(design)
        damaged = image.copy()
        damaged.putpixel((30, 25), (0, 255, 0, 255))
        self.assertRejected(
            "render_pixels", design, damaged, warnings, assets_dir=self.assets
        )


if __name__ == "__main__":
    unittest.main()
