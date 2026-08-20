from pathlib import Path
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from barcode_generator import clean_digits, validate_ean13
from spine_calculator import calculate_spine_width_mm
from design_engine.compositor import composite_cover_art
from design_engine.color_strategy import build_color_plan
from design_engine.composition_intelligence import build_composition_plan
from design_engine.cover_spec import build_cover_spec, validate_config
from design_engine.design_tokens import get_tokens
from design_engine.editorial_brief import EditorialBrief
from design_engine.parametric_svg import render_complex_band, render_complex_rosette
from design_engine.title_lettering import LETTERING_STYLES, _balanced_title_lines, render_lettering_variant, render_vector_title
from design_engine.variant_engine import _trim_external_bleed
from design_engine.svg_ornaments import render_corner_flourish, render_divider, render_medallion


class CoverSpecTests(unittest.TestCase):
    def test_segments_sum_to_total_width_for_every_finish(self):
        for finish in ("brochura", "capadura", "grampo", "espiral"):
            with self.subTest(finish=finish):
                config = {"acabamento": finish, "formato": "14x21", "orelhas": finish == "brochura"}
                spec = build_cover_spec(config, 8.5)
                self.assertAlmostEqual(sum(float(item["width_mm"]) for item in spec.segments), spec.total_w_mm)

    def test_hardcover_has_turn_ins_and_hinges(self):
        spec = build_cover_spec({"acabamento": "capadura", "formato": "Trade"}, 12)
        self.assertEqual(spec.flap_mm, 35)
        self.assertEqual(spec.hinge_mm, 10)
        self.assertTrue(spec.is_hardcover)

    def test_invalid_config_is_reported(self):
        issues = validate_config({"formato": "gigante", "acabamento": "cola", "cor_capa": "red"})
        codes = {item["code"] for item in issues}
        self.assertTrue({"missing_titulo", "missing_autor", "missing_isbn", "invalid_format", "invalid_finish", "invalid_cover_color"} <= codes)


class BarcodeTests(unittest.TestCase):
    def test_valid_ean13_is_preserved(self):
        value = clean_digits("978-65-988202-7-5")
        self.assertEqual(value, "9786598820275")
        self.assertTrue(validate_ean13(value))

    def test_invalid_ean13_is_rejected(self):
        with self.assertRaises(ValueError):
            clean_digits("978-65-988202-7-4")


class SpineTests(unittest.TestCase):
    def test_odd_page_count_rounds_up_to_physical_leaf(self):
        self.assertEqual(
            calculate_spine_width_mm(101, "polen_soft_80g"),
            calculate_spine_width_mm(102, "polen_soft_80g"),
        )


class CompositorTests(unittest.TestCase):
    def test_crop_preserves_target_ratio_without_upscaling(self):
        texture = Image.new("RGB", (300, 300), "white")
        illustration = Image.new("RGB", (400, 200), "black")
        result = composite_cover_art(texture, illustration, target_aspect_ratio=0.5)
        self.assertEqual(result.size, (100, 200))

    def test_invalid_focus_is_rejected(self):
        image = Image.new("RGB", (20, 20), "black")
        with self.assertRaises(ValueError):
            composite_cover_art(image, image, focus=(1.5, 0.5))


class TitleTests(unittest.TestCase):
    def test_title_wrapping_keeps_word_order(self):
        title = "Um título muito longo para uma capa pequena"
        lines = _balanced_title_lines(title)
        self.assertEqual(" ".join(lines), title.upper())

    def test_svg_escapes_editorial_text(self):
        svg = render_vector_title("A & B <C>", "imperial_oriental", {"gold_color": "#fff000"}, {"font_title": "Georgia"})
        self.assertIn("A &amp; B &lt;C&gt;", svg)

    def test_all_lettering_directions_are_valid_svg(self):
        palette = {"gold_color": "#dbb666", "soft_gold": "#f0e6d2"}
        fonts = {"font_title": "Georgia", "font_body": "Baskerville"}
        for style in LETTERING_STYLES:
            with self.subTest(style=style):
                root = ET.fromstring(render_lettering_variant("Crônicas Chinesas para Pequenos Guerreiros", style, palette, fonts))
                self.assertTrue(root.tag.endswith("svg"))

    def test_han_lettering_keeps_rules_outside_hero_word(self):
        svg = render_lettering_variant(
            "Crônicas Chinesas para Pequenos Guerreiros",
            "han_pincel",
            {"gold_color": "#d4af37", "soft_gold": "#f0e6d2"},
            {"font_title": "Georgia", "font_body": "Baskerville"},
        )
        root = ET.fromstring(svg)
        hero = next(node for node in root.iter() if node.attrib.get("id") == "han-hero")
        self.assertFalse(any(node.tag.endswith("path") for node in hero.iter()))
        self.assertIn("han-brush-accents", svg)


class TokenTests(unittest.TestCase):
    def test_dark_custom_background_adapts_light_text_roles(self):
        palette = get_tokens({"tema": "creme", "cor_capa": "#111111"})["palette"]
        self.assertEqual(palette["text_light"], "#ffffff")
        self.assertEqual(palette["soft_gold"], "#f0e6d2")


class VariantTests(unittest.TestCase):
    def test_evaluation_preview_removes_external_bleed(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "preview.png"
            Image.new("RGB", (100, 100), "#4a1525").save(source)
            trimmed = _trim_external_bleed(source, 10, dpi=25.4)
            with Image.open(trimmed) as image:
                self.assertEqual(image.size, (80, 80))


class OrnamentTests(unittest.TestCase):
    def test_oriental_ornaments_are_valid_svg(self):
        palette = {"gold_color": "#dbb666"}
        for renderer in (render_divider, render_corner_flourish, render_medallion):
            with self.subTest(renderer=renderer.__name__):
                root = ET.fromstring(renderer("imperial_oriental", palette))
                self.assertTrue(root.tag.endswith("svg"))

    def test_parametric_complexity_adds_svg_detail(self):
        simple = render_complex_rosette("#dbb666", complexity=1)
        complex_svg = render_complex_rosette("#dbb666", complexity=5)
        ET.fromstring(render_complex_band("#dbb666", complexity=5))
        ET.fromstring(complex_svg)
        self.assertGreater(len(complex_svg), len(simple))


class StrategyTests(unittest.TestCase):
    def test_color_plan_defaults_to_70_20_10(self):
        plan = build_color_plan({}, {"bg_color": "#401020", "gold_color": "#dbb666"})
        self.assertAlmostEqual(plan.dominant.ratio, 0.7)
        self.assertAlmostEqual(plan.secondary.ratio, 0.2)
        self.assertAlmostEqual(plan.accent.ratio, 0.1)

    def test_long_illustrated_title_recommends_dedicated_title_zone(self):
        config = {"titulo": "Crônicas Chinesas para Pequenos Guerreiros", "autor": "Autor", "genero": "infantojuvenil"}
        brief = EditorialBrief.from_config(config)
        spec = build_cover_spec({}, 3)
        plan = build_composition_plan(config, brief, spec, has_image=True)
        self.assertEqual(plan.recommended_pattern, 2)
        self.assertEqual(plan.title_zone, "tarja_superior")
        self.assertGreater(plan.type_display_pt, plan.type_heading_pt)


if __name__ == "__main__":
    unittest.main()
