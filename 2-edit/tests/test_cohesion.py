import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from rules.cohesion import analyze_cohesion


ENTITY_CONFIG = {
    "revisao": {
        "coesao": {
            "entidades": {
                "joao": {"genero": "masculino", "aliases": ["João"]},
                "pedro": {"genero": "masculino", "aliases": ["Pedro"]},
            }
        }
    }
}


class CohesionTests(unittest.TestCase):
    def test_redundant_connectors_are_flagged(self):
        result = analyze_cohesion("Ele queria partir, mas porém ficou.")
        self.assertEqual(result["issues"][0]["rule"], "cohesion.connector.redundant_pair")

    def test_concessive_and_adversative_overlap_is_flagged(self):
        result = analyze_cohesion("Embora estivesse cansado, mas continuou caminhando.")
        self.assertEqual(
            result["issues"][0]["rule"],
            "cohesion.connector.concessive_adversative_overlap",
        )

    def test_three_repeated_sentence_openings_are_flagged(self):
        result = analyze_cohesion("Mas ele voltou. Mas ele caiu. Mas ele se levantou.")
        issue = next(item for item in result["issues"] if item["rule"] == "cohesion.connector.repeated_opening")
        self.assertEqual(issue["subtype"], "repeticao_de_conector")

    def test_two_repeated_openings_are_accepted_by_default(self):
        result = analyze_cohesion("Mas ele voltou. Mas ele caiu. Então se levantou.")
        self.assertFalse(any(item["rule"] == "cohesion.connector.repeated_opening" for item in result["issues"]))

    def test_configured_entities_reveal_ambiguous_pronoun(self):
        result = analyze_cohesion("João encontrou Pedro. Ele estava preocupado.", ENTITY_CONFIG)
        issue = next(item for item in result["issues"] if item["rule"] == "cohesion.reference.ambiguous_pronoun")
        self.assertIn("joao", issue["explanation"])
        self.assertIn("pedro", issue["explanation"])

    def test_single_candidate_does_not_create_ambiguity(self):
        config = {
            "revisao": {
                "coesao": {
                    "entidades": {"joao": {"genero": "masculino", "aliases": ["João"]}}
                }
            }
        }
        result = analyze_cohesion("João chegou. Ele estava preocupado.", config)
        self.assertFalse(any(item["rule"] == "cohesion.reference.ambiguous_pronoun" for item in result["issues"]))

    def test_appositive_noun_and_name_are_one_referent(self):
        result = analyze_cohesion("João era um jovem guerreiro. Ele estava preocupado.", ENTITY_CONFIG)
        self.assertFalse(any(item["rule"] == "cohesion.reference.ambiguous_pronoun" for item in result["issues"]))

    def test_name_and_epithet_with_dash_are_one_referent(self):
        config = {
            "revisao": {"coesao": {"entidades": {
                "sai_weng": {"genero": "masculino", "aliases": ["Sai Weng"]},
            }}}
        }
        text = (
            "Lá vivia um velho mestre conhecido como Sai Weng — o Velho da Fronteira. "
            "Ele permaneceu sereno."
        )
        result = analyze_cohesion(text, config)
        self.assertFalse(any(item["rule"] == "cohesion.reference.ambiguous_pronoun" for item in result["issues"]))

    def test_apposition_does_not_hide_second_real_referent(self):
        result = analyze_cohesion(
            "O jovem guerreiro, João, encontrou Pedro. Ele estava preocupado.",
            ENTITY_CONFIG,
        )
        issue = next(item for item in result["issues"] if item["rule"] == "cohesion.reference.ambiguous_pronoun")
        self.assertIn("joao", issue["explanation"])
        self.assertIn("pedro", issue["explanation"])

    def test_adjacent_titles_are_one_generic_referent(self):
        result = analyze_cohesion("O velho mestre olhou a montanha. Ele sorriu.")
        self.assertFalse(any(item["rule"] == "cohesion.reference.ambiguous_pronoun" for item in result["issues"]))

    def test_dialogue_pronoun_is_not_treated_as_narrative_ambiguity(self):
        result = analyze_cohesion("João encontrou Pedro.\n\n— Ele está preocupado — disse Maria.", ENTITY_CONFIG)
        self.assertFalse(any(item["rule"] == "cohesion.reference.ambiguous_pronoun" for item in result["issues"]))

    def test_ignored_rule_is_removed(self):
        config = {
            "revisao": {
                "coesao": {"ignorar_regras": ["cohesion.connector.redundant_pair"]}
            }
        }
        self.assertEqual(analyze_cohesion("Mas porém ele voltou.", config)["issues"], [])

    def test_metrics_count_connectors_by_function(self):
        result = analyze_cohesion("Mas ele voltou. Portanto, todos sorriram.")
        self.assertEqual(result["metrics"]["leading_connectors"]["mas"], 1)
        self.assertEqual(result["metrics"]["connector_groups"]["conclusao"], 1)

    def test_frontmatter_and_source_lines_are_ignored(self):
        text = "---\ntitle: Mas porém\n---\n\n> Embora fosse antigo, mas ficou.\n\nTexto correto."
        self.assertEqual(analyze_cohesion(text)["issues"], [])


if __name__ == "__main__":
    unittest.main()
