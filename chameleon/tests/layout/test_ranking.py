import io
import unittest

try:
    from engine.layout.ranking import _contrast_score, score_candidate
except ModuleNotFoundError:
    from chameleon.engine.layout.ranking import _contrast_score, score_candidate


class RankingContrastTests(unittest.TestCase):
    @staticmethod
    def _png(background, foreground=(0, 0, 0, 255)):
        from PIL import Image, ImageDraw

        image = Image.new("RGBA", (20, 20), background)
        # A small glyph-like patch models rendered ink without making the text
        # box uniformly foreground-colored.
        ImageDraw.Draw(image).rectangle((8, 8, 10, 10), fill=foreground)
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        return buffer.getvalue()

    @staticmethod
    def _elements(color="rgba(0,0,0,1)", style_runs=None):
        return [{
            "id": "contrast-text",
            "type": "text",
            "x": 0,
            "y": 0,
            "width": 20,
            "height": 20,
            "font_size": 12,
            "color": color,
            "content": "Text",
            "style_runs": style_runs or [],
        }]

    def test_same_fill_scores_differently_over_light_and_dark_local_background(self):
        elements = self._elements()
        indices = [0]
        light = _contrast_score(self._png((255, 255, 255, 255)), elements, indices, {"width": 20, "height": 20})
        dark = _contrast_score(self._png((0, 0, 0, 255)), elements, indices, {"width": 20, "height": 20})
        self.assertGreater(light, dark)

    def test_higher_wcag_contrast_ranks_higher(self):
        response = {"canvas": {"width": 20, "height": 20}, "elements": self._elements()}
        source = {"canvas": {"width": 20, "height": 20}, "elements": self._elements()}
        high = score_candidate(source, response, self._png((255, 255, 255, 255)))
        low = score_candidate(source, response, self._png((120, 120, 120, 255)))
        self.assertGreater(high.readability, low.readability)

    def test_contrast_score_is_a_deterministic_fixed_point_integer(self):
        elements = self._elements("rgba(255,255,255,1)")
        args = (
            self._png((0, 0, 0, 255), foreground=(255, 255, 255, 255)),
            elements,
            [0],
            {"width": 20, "height": 20},
        )
        first = _contrast_score(*args)
        second = _contrast_score(*args)
        self.assertEqual(first, 1000)
        self.assertEqual(first, second)
        self.assertIs(type(first), int)

    def test_rgba_style_run_override_is_included_in_effective_fills(self):
        elements = self._elements(
            "rgba(255,255,255,1)",
            [{"start": 0, "end": 4, "color": "rgba(0,0,0,1)"}],
        )
        score = _contrast_score(self._png((255, 255, 255, 255)), elements, [0], {"width": 20, "height": 20})
        self.assertEqual(score, 1000)

    def test_unmeasurable_low_contrast_base_fill_is_not_omitted(self):
        elements = self._elements(
            "rgba(255,255,255,1)",
            [{"start": 0, "end": 1, "color": "rgba(0,0,0,1)"}],
        )
        score = _contrast_score(
            self._png((255, 255, 255, 255)),
            elements,
            [0],
            {"width": 20, "height": 20},
        )
        self.assertEqual(score, 0)

    def test_missing_png_and_no_text_keep_deterministic_behavior(self):
        self.assertEqual(_contrast_score(None, self._elements(), [0], {"width": 20, "height": 20}), 500)
        self.assertEqual(_contrast_score(None, [], [], {"width": 20, "height": 20}), 1000)


if __name__ == "__main__":
    unittest.main()
