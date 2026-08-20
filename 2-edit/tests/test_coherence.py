import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from rules.coherence import analyze_coherence


def config(**coherence):
    return {"revisao": {"coerencia": coherence}}


class CoherenceTests(unittest.TestCase):
    def test_activity_after_terminal_state_is_flagged(self):
        text = "# Conto\n\nAna morreu.\n\nAna caminhou até a praça."
        result = analyze_coherence(text, config(estados=[{
            "id": "vida_de_ana", "escopo": "capitulo",
            "padroes_terminais": [r"Ana morreu"],
            "padroes_atividade": [r"Ana caminhou"],
        }]))
        self.assertEqual(result["summary"], {"continuidade_de_estado": 1})
        self.assertEqual(result["issues"][0]["rule"], "coherence.state.incompatible_after_terminal")
        self.assertFalse(result["issues"][0]["auto_fixable"])

    def test_activity_before_terminal_state_is_accepted(self):
        text = "# Conto\n\nAna caminhou até a praça.\n\nAna morreu."
        result = analyze_coherence(text, config(estados=[{
            "padroes_terminais": [r"Ana morreu"],
            "padroes_atividade": [r"Ana caminhou"],
        }]))
        self.assertEqual(result["total_issues"], 0)

    def test_destroyed_object_reused_is_one_continuity_issue(self):
        text = (
            "# Conto\n\nA flecha quebrou.\n\n"
            "Ele reuniu o feixe de sete flechas.\n\nO feixe de sete flechas resistiu."
        )
        result = analyze_coherence(text, config(estados=[{
            "id": "flechas", "padroes_terminais": [r"flecha quebrou"],
            "padroes_incompativeis": [r"feixe de sete flechas"],
        }]))
        self.assertEqual(result["total_issues"], 1)

    def test_sections_isolate_terminal_states(self):
        text = "# Conto\n\n## História\n\nAna morreu.\n\n## Reflexão\n\nAna caminhou com coragem."
        result = analyze_coherence(text, config(estados=[{
            "escopo": "secao", "padroes_terminais": [r"Ana morreu"],
            "padroes_atividade": [r"Ana caminhou"],
        }]))
        self.assertEqual(result["total_issues"], 0)

    def test_reversed_milestones_are_flagged(self):
        text = "# Conto\n\nA viagem terminou.\n\nA viagem começou."
        result = analyze_coherence(text, config(sequencias=[{
            "id": "viagem", "marcos": [
                {"id": "inicio", "padroes": [r"viagem começou"]},
                {"id": "fim", "padroes": [r"viagem terminou"]},
            ],
        }]))
        self.assertEqual(result["summary"], {"cronologia": 1})

    def test_ordered_milestones_are_accepted(self):
        text = "# Conto\n\nA viagem começou.\n\nA viagem terminou."
        rule = {"marcos": [
            {"id": "inicio", "padroes": [r"viagem começou"]},
            {"id": "fim", "padroes": [r"viagem terminou"]},
        ]}
        self.assertEqual(analyze_coherence(text, config(sequencias=[rule]))["total_issues"], 0)

    def test_conflicting_numeric_fact_is_flagged(self):
        text = "# Conto\n\nO rei tinha sete filhos.\n\nOs oito irmãos chegaram."
        result = analyze_coherence(text, config(fatos_numericos=[{
            "id": "filhos", "padroes": [
                r"(?P<valor>sete|7) filhos", r"(?P<valor>oito|8) irmãos",
            ],
        }]))
        self.assertEqual(result["summary"], {"fato_quantificado": 1})

    def test_equivalent_word_and_digit_are_accepted(self):
        text = "# Conto\n\nO rei tinha sete filhos.\n\nOs 7 irmãos chegaram."
        result = analyze_coherence(text, config(fatos_numericos=[{
            "padroes": [r"(?P<valor>sete|7) filhos", r"(?P<valor>sete|7) irmãos"],
        }]))
        self.assertEqual(result["total_issues"], 0)

    def test_coverage_proves_milestones_were_found(self):
        text = "# Conto\n\nA viagem começou.\n\nA viagem terminou."
        result = analyze_coherence(text, config(sequencias=[{
            "id": "viagem", "marcos": [
                {"id": "inicio", "padroes": [r"viagem começou"]},
                {"id": "fim", "padroes": [r"viagem terminou"]},
            ],
        }]))
        self.assertEqual(
            result["coverage"]["sequences"][0]["milestones"],
            {"inicio": 1, "fim": 1},
        )

    def test_ignored_rule_is_removed(self):
        text = "# Conto\n\nAna morreu.\n\nAna caminhou."
        result = analyze_coherence(text, config(
            ignorar_regras=["coherence.state.incompatible_after_terminal"],
            estados=[{"padroes_terminais": ["morreu"], "padroes_atividade": ["caminhou"]}],
        ))
        self.assertEqual(result["total_issues"], 0)

    def test_frontmatter_is_not_analyzed(self):
        text = "---\nresumo: Ana morreu e Ana caminhou\n---\n# Conto\n\nTudo começou."
        result = analyze_coherence(text, config(estados=[{
            "padroes_terminais": ["Ana morreu"], "padroes_atividade": ["Ana caminhou"],
        }]))
        self.assertEqual(result["total_issues"], 0)


if __name__ == "__main__":
    unittest.main()
