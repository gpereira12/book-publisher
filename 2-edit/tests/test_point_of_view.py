#!/usr/bin/env python3
"""
tests/test_point_of_view.py
----------------------------
Testes unitários para o Ponto 6 — Ponto de Vista e Voz Narrativa.
"""

import unittest
from rules.point_of_view import audit_point_of_view


class TestPointOfView(unittest.TestCase):

    def setUp(self):
        self.config = {
            "revisao": {
                "ponto_de_vista": {
                    "voz_esperada": "3a_pessoa",
                    "secoes_permitidas_1a_pessoa": ["Prefácio", "Reflexão"],
                    "secoes_permitidas_endereçamento": ["Prefácio", "Reflexão"]
                }
            }
        }

    def test_deslize_1a_pessoa_na_narracao(self):
        markdown = (
            "# O Mestre da Fronteira\n\n"
            "Sai Weng caminhava pelo campo calmo. De repente, eu vi o cavalo fugindo para as montanhas."
        )
        findings = audit_point_of_view(markdown, self.config)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].rule, "ponto_de_vista.deslize_1a_pessoa")
        self.assertEqual(findings[0].chapter, "O Mestre da Fronteira")

    def test_1a_pessoa_permitida_no_prefacio_e_reflexao(self):
        markdown = (
            "# Prefácio\n\n"
            "Escolhi contar histórias em vez de regras. Eu pensei muito sobre este livro.\n\n"
            "# O Mestre da Fronteira\n\n"
            "Sai Weng olhava o horizonte.\n\n"
            "## Reflexão\n\n"
            "Eu percebi que Sai Weng ensina a prudência."
        )
        findings = audit_point_of_view(markdown, self.config)
        self.assertEqual(len(findings), 0)

    def test_dialogo_isento_de_deslize_pov(self):
        markdown = (
            "# O Mestre da Fronteira\n\n"
            "— Eu vi o cavalo fugir! — gritou o vizinho assustado."
        )
        findings = audit_point_of_view(markdown, self.config)
        self.assertEqual(len(findings), 0)

    def test_enderecamento_leitor_fora_de_secao_permitida(self):
        markdown = (
            "# O Mestre da Fronteira\n\n"
            "Como você verá a seguir, o destino de Sai Weng mudou totalmente."
        )
        findings = audit_point_of_view(markdown, self.config)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].rule, "ponto_de_vista.enderecamento_leitor")


if __name__ == "__main__":
    unittest.main()
