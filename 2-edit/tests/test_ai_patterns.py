import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from rules.ai_patterns import analyze_ai_patterns, find_anaphora_repetition


class AiPatternsTests(unittest.TestCase):
    def test_narrative_contrast_is_not_antithesis(self):
        text = "O som que veio do horizonte não foi de cavalos, mas de tambores."
        self.assertEqual(analyze_ai_patterns(text)["antithesis"], [])

    def test_nao_so_without_tambem_is_not_formulaic(self):
        text = "Ele chorou, não só pelo arroz perdido, mas porque entendeu o erro."
        self.assertEqual(analyze_ai_patterns(text)["antithesis"], [])

    def test_dialogue_emphasis_is_not_anaphora(self):
        text = "— Que espírito! Que foco! Não está vendo? Não cabe mais nada!"
        self.assertEqual(find_anaphora_repetition(text), [])

    def test_two_repetitions_are_not_anaphora(self):
        self.assertEqual(find_anaphora_repetition("Que lute. Que vença."), [])

    def test_three_repetitions_outside_dialogue_are_anaphora(self):
        result = find_anaphora_repetition("Que lute. Que aprenda. Que cresça.")
        self.assertEqual(len(result), 1)

    def test_isolated_marker_does_not_recommend_review(self):
        text = ("Esta história tem palavras suficientes para dar contexto. " * 100)
        text += "Não é sorte, mas trabalho."
        assessment = analyze_ai_patterns(text)["assessment"]
        self.assertEqual(assessment["level"], "ocorrencias_isoladas")
        self.assertFalse(assessment["review_recommended"])

    def test_concentrated_markers_recommend_review(self):
        text = " ".join(
            [
                "Não é sorte, mas trabalho.",
                "Não é pressa, mas cuidado.",
                "Não é medo, mas prudência.",
                "Não é fraqueza, mas escolha.",
            ]
        )
        self.assertTrue(analyze_ai_patterns(text)["assessment"]["review_recommended"])


if __name__ == "__main__":
    unittest.main()
