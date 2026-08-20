import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from rules.flesch_readability import analyze_readability, calculate_flesch_siqueira


SAMPLE = """---
title: Teste
---

# Primeiro conto

O menino caminhou devagar pela estrada.

— Eu consigo chegar antes do anoitecer! — disse ele.

Esta frase deliberadamente possui palavras demais para o limite pequeno definido neste teste editorial.

## Reflexão

A perseverança extraordinariamente importante ajuda o menino a continuar.
"""


class ReadabilityTests(unittest.TestCase):
    def test_frontmatter_is_not_counted(self):
        result = calculate_flesch_siqueira("---\ntitle: Palavra Fantasma\n---\n\nTexto simples.")
        self.assertEqual(result["total_palavras"], 2)

    def test_analysis_separates_chapter_section_and_content_type(self):
        result = analyze_readability(SAMPLE)
        self.assertEqual(len(result["chapters"]), 1)
        self.assertEqual(len(result["sections"]), 2)
        self.assertEqual(
            {item["type"] for item in result["content_types"]},
            {"narracao", "dialogo", "reflexao"},
        )

    def test_book_configuration_controls_targets(self):
        config = {
            "faixa_etaria": "8 anos",
            "revisao": {"legibilidade": {"min_flesch": 99, "max_palavras_frase": 5}},
        }
        result = analyze_readability(SAMPLE, config)
        self.assertEqual(result["config"]["faixa_etaria"], 8)
        self.assertFalse(result["target_met"])
        self.assertTrue(result["long_sentences"])

    def test_difficult_words_have_line_and_estimated_syllables(self):
        config = {
            "revisao": {
                "legibilidade": {
                    "silabas_palavra_dificil": 4,
                    "min_letras_palavra_dificil": 8,
                }
            }
        }
        words = analyze_readability(SAMPLE, config)["difficult_words"]
        extraordinary = next(item for item in words if item["word"].lower() == "extraordinariamente")
        self.assertGreaterEqual(extraordinary["syllables_estimate"], 4)
        self.assertGreater(extraordinary["first_line"], 1)
        self.assertEqual(extraordinary["first_chapter"], "Primeiro conto")

    def test_hardest_excerpts_are_located(self):
        excerpts = analyze_readability(SAMPLE)["hardest_excerpts"]
        self.assertTrue(excerpts)
        self.assertIn("line", excerpts[0])
        self.assertIn("chapter", excerpts[0])


if __name__ == "__main__":
    unittest.main()
