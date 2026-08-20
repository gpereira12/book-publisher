import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from illustration_prompts import compile_document, compile_prompt


class IllustrationPromptTests(unittest.TestCase):
    def setUp(self):
        self.scene = {
            "id": "c01_s01", "tipo": "spread", "paginas": [2, 3], "descricao": "Uma travessia.",
            "funcao": "Apresentar a jornada.", "ancora_textual": "A viagem começou.",
            "personagens": ["Viajante"], "elementos_continuidade": ["manto azul"],
            "zona_texto": "o céu à esquerda", "alt_texto": "Um viajante na estrada.",
            "arquivo": "assets/cena.png",
        }
        self.chapter = {"ordem": 1, "titulo": "A Jornada", "cenas": [self.scene]}
        self.plan = {
            "livro": "Livro", "miolo": {"resolucao_dpi": 300},
            "direcao_visual": {
                "estilo_ilustracao": "guache", "acabamento": "editorial",
                "fotografia": {"abertura": "50 mm", "spread": "35 mm"},
                "cinematografia": "regra dos terços",
                "movimento_e_ritmo": "gestos em curso e poeira no ar",
                "variedade_cinematografica": "alternar escala e altura da câmera",
                "cenografia": "madeira e pedra",
                "cor_e_luz": "luz motivada", "personagens": "continuidade facial",
            },
            "composicao": {
                "abertura": {"tamanho_com_sangria_mm": [131, 186], "tamanho_recomendado_px": [1547, 2197]},
                "spread": {"tamanho_com_sangria_mm": [256, 186], "tamanho_recomendado_px": [3024, 2197]},
                "restricoes": ["Não gerar letras."],
            },
            "prompt_negativo": "texto, marca-d'água", "capitulos": [self.chapter],
        }

    def test_prompt_combines_visual_disciplines_and_text_safe_area(self):
        prompt = compile_prompt(self.plan, self.chapter, self.scene)
        for marker in ("LINGUAGEM DE ILUSTRAÇÃO", "FOTOGRAFIA VIRTUAL", "CINEMATOGRAFIA",
                       "MOVIMENTO E RITMO", "VARIEDADE ENTRE CENAS", "CENOGRAFIA",
                       "COR E LUZ", "ÁREA EDITORIAL PARA TEXTO"):
            self.assertIn(marker, prompt)
        self.assertIn("3024 × 2197 px", prompt)
        self.assertIn("O texto será aplicado depois", prompt)

    def test_document_contains_prompt_alt_text_and_future_asset_path(self):
        document = compile_document(self.plan, Path("plano.yaml"))
        self.assertIn("```text", document)
        self.assertIn("Um viajante na estrada.", document)
        self.assertIn("assets/cena.png", document)


if __name__ == "__main__":
    unittest.main()
