import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from rules.grammar import analyze_grammar


class GrammarTests(unittest.TestCase):
    def test_safe_spelling_fix_preserves_initial_capitalization(self):
        result = analyze_grammar("# Capítulo\n\nConcerteza ele voltará.")
        self.assertIn("Com certeza ele voltará.", result["corrected_text"])
        self.assertEqual(result["auto_fixable_count"], 1)

    def test_elapsed_time_fazer_is_flagged_but_not_auto_fixed(self):
        result = analyze_grammar("Fazem dois anos que ele partiu.")
        issue = result["issues"][0]
        self.assertEqual(issue["rule"], "grammar.agreement.elapsed_time_fazer")
        self.assertFalse(issue["auto_fixable"])
        self.assertEqual(result["corrected_text"], "Fazem dois anos que ele partiu.")

    def test_plural_subject_with_fazem_is_not_flagged(self):
        result = analyze_grammar("Fazem dois homens o trabalho da aldeia.")
        self.assertEqual(result["issues"], [])

    def test_crasis_fixed_expression_is_auto_fixable(self):
        result = analyze_grammar("As mudanças vieram a medida que o tempo passou.")
        self.assertIn("à medida que", result["corrected_text"])
        self.assertEqual(result["issues"][0]["subcategory"], "crase")

    def test_pronoun_before_infinitive_is_only_observation(self):
        result = analyze_grammar("Ele deixou o livro para mim estudar.")
        self.assertEqual(result["issues"][0]["severity"], "observacao")
        self.assertFalse(result["issues"][0]["auto_fixable"])

    def test_duplicate_word_is_located(self):
        result = analyze_grammar("# Conto\n\nO menino menino voltou.")
        issue = result["issues"][0]
        self.assertEqual(issue["rule"], "grammar.duplication.adjacent_word")
        self.assertEqual(issue["line"], 3)
        self.assertEqual(issue["chapter"], "Conto")

    def test_colloquial_que_que_is_not_flagged_as_duplicate(self):
        self.assertEqual(analyze_grammar("O que que aconteceu?")["issues"], [])

    def test_frontmatter_and_source_attribution_are_ignored(self):
        text = "---\ntitle: Concerteza\n---\n\n> Derrepente\n\nTexto correto."
        self.assertEqual(analyze_grammar(text)["issues"], [])

    def test_unbalanced_parentheses_are_reported(self):
        result = analyze_grammar("Ele voltou (mas não ficou.")
        self.assertEqual(result["issues"][0]["rule"], "grammar.punctuation.unbalanced_parentheses")
        self.assertFalse(result["issues"][0]["auto_fixable"])

    def test_unbalanced_straight_quotes_are_reported(self):
        result = analyze_grammar('Ele disse: "Voltarei amanhã.')
        self.assertEqual(result["issues"][0]["rule"], "grammar.punctuation.unbalanced_straight_quotes")

    def test_existir_agrees_with_plural_subject(self):
        result = analyze_grammar("Existe muitas razões para partir.")
        self.assertEqual(result["issues"][0]["rule"], "grammar.agreement.existir_plural_noun")
        self.assertEqual(result["issues"][0]["severity"], "alerta")

    def test_ignored_rule_from_book_config(self):
        config = {"revisao": {"gramatica": {"ignorar_regras": ["grammar.crasis.as_vezes"]}}}
        self.assertEqual(analyze_grammar("As vezes ele volta.", config)["issues"], [])

    def test_report_limit_does_not_hide_structured_issues(self):
        config = {"revisao": {"gramatica": {"max_itens_relatorio": 1}}}
        result = analyze_grammar("Concerteza. Derrepente.", config)
        self.assertEqual(result["total_issues"], 2)
        self.assertEqual(len(result["issues"]), 2)
        self.assertEqual(len(result["display_issues"]), 1)

    def test_dialogue_preserves_possible_character_spelling(self):
        result = analyze_grammar("— Concerteza eu vou!")
        self.assertEqual(result["issues"][0]["context"], "dialogo")
        self.assertEqual(result["issues"][0]["severity"], "observacao")
        self.assertFalse(result["issues"][0]["auto_fixable"])
        self.assertIn("Concerteza", result["corrected_text"])

    def test_dialogue_still_allows_safe_punctuation_fix(self):
        result = analyze_grammar("— Você vem ?")
        self.assertTrue(result["issues"][0]["auto_fixable"])
        self.assertEqual(result["corrected_text"], "— Você vem?")

    def test_a_gente_with_plural_verb_is_observation(self):
        result = analyze_grammar("A gente fomos até a aldeia.")
        self.assertEqual(result["issues"][0]["rule"], "grammar.agreement.a_gente_plural")
        self.assertEqual(result["issues"][0]["severity"], "observacao")

    def test_plural_pronoun_with_singular_verb_is_flagged(self):
        result = analyze_grammar("Eles vai voltar amanhã.")
        self.assertEqual(result["issues"][0]["rule"], "grammar.agreement.eles_singular")

    def test_simple_singular_subject_with_rangeram_is_safely_fixed(self):
        result = analyze_grammar("A madeira rangeram durante a tempestade.")
        self.assertEqual(
            result["issues"][0]["rule"],
            "grammar.agreement.simple_singular_subject_rangeram",
        )
        self.assertEqual(result["corrected_text"], "A madeira rangeu durante a tempestade.")
        self.assertTrue(result["issues"][0]["auto_fixable"])

    def test_old_orthography_is_safely_updated(self):
        result = analyze_grammar("A idéia central mudou.")
        self.assertEqual(result["corrected_text"], "A ideia central mudou.")

    def test_obedecer_direct_article_is_contextual(self):
        result = analyze_grammar("Ele decidiu obedecer o mestre.")
        self.assertEqual(result["issues"][0]["subcategory"], "regencia")
        self.assertFalse(result["issues"][0]["auto_fixable"])


if __name__ == "__main__":
    unittest.main()
