import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from rules.factuality import analyze_factuality


def config(**factuality):
    return {"revisao": {"factualidade": factuality}}


class FactualityTests(unittest.TestCase):
    def test_supported_verified_claim_is_accepted(self):
        result = analyze_factuality("# Conto\n\nHan foi general.", config(
            fontes={"fonte": {"titulo": "Fonte", "url": "https://example.test", "tipo": "primaria"}},
            alegacoes=[{"id": "han", "natureza": "historica", "status": "verificada", "padroes": ["Han foi"], "fontes": ["fonte"]}],
        ))
        self.assertEqual(result["total_issues"], 0)

    def test_historical_claim_without_source_is_flagged(self):
        result = analyze_factuality("# Conto\n\nHan venceu.", config(
            alegacoes=[{"id": "han", "natureza": "historica", "padroes": ["Han venceu"]}],
        ))
        self.assertEqual(result["issues"][0]["rule"], "factuality.source.missing_support")

    def test_deliberate_fiction_does_not_require_source(self):
        result = analyze_factuality("# Conto\n\nZhang bebeu o elixir.", config(
            alegacoes=[{"id": "zhang", "natureza": "ficcao_deliberada", "status": "adaptada", "padroes": ["Zhang bebeu"]}],
        ))
        self.assertEqual(result["total_issues"], 0)

    def test_imprecise_supported_claim_is_flagged(self):
        result = analyze_factuality("# Conto\n\nHan unificou tudo.", config(
            fontes={"f": {"titulo": "Biografia", "url": "https://example.test"}},
            alegacoes=[{"id": "han", "natureza": "historica", "status": "imprecisa", "padroes": ["unificou"], "fontes": ["f"]}],
        ))
        self.assertEqual(result["summary"], {"alegacao": 1})

    def test_unknown_source_reference_is_configuration_error(self):
        result = analyze_factuality("# Conto\n\nAconteceu.", config(
            alegacoes=[{"padroes": ["Aconteceu"], "fontes": ["ausente"]}],
        ))
        self.assertEqual(result["issues"][0]["severity"], "erro")

    def test_incomplete_source_metadata_is_configuration_error(self):
        result = analyze_factuality("# Conto\n\nAconteceu.", config(
            fontes={"incompleta": {"titulo": "Sem endereço"}},
            alegacoes=[{"padroes": ["Aconteceu"], "fontes": ["incompleta"]}],
        ))
        self.assertEqual(
            result["issues"][0]["rule"],
            "factuality.source.incomplete_metadata",
        )

    def test_temporal_term_in_narrative_is_flagged(self):
        result = analyze_factuality("# China antiga\n\nA espada era de plástico.", config(
            termos_temporais=[{"id": "plastico", "padroes": [r"\bplástico\b"]}],
        ))
        self.assertEqual(result["summary"], {"anacronismo": 1})

    def test_temporal_term_in_reflection_is_ignored(self):
        result = analyze_factuality("# Conto\n\n## Reflexão\n\nNão vivam grudados na internet.", config(
            termos_temporais=[{"id": "internet", "padroes": [r"\binternet\b"]}],
        ))
        self.assertEqual(result["total_issues"], 0)

    def test_coverage_distinguishes_unmatched_claim(self):
        result = analyze_factuality("# Conto\n\nOutro texto.", config(
            alegacoes=[{"id": "ausente", "padroes": ["não aparece"]}],
        ))
        self.assertEqual(result["coverage"]["claims"][0]["matches"], 0)

    def test_frontmatter_is_ignored(self):
        text = "---\nresumo: espada de plástico\n---\n# Conto\n\nEspada de madeira."
        result = analyze_factuality(text, config(
            termos_temporais=[{"padroes": ["plástico"]}],
        ))
        self.assertEqual(result["total_issues"], 0)


if __name__ == "__main__":
    unittest.main()
