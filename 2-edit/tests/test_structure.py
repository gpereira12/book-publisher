import sys
import tempfile
import unittest
from pathlib import Path

import yaml


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from rules.structure import analyze_structure


def config(**structure):
    return {"revisao": {"estrutura": structure}}


class StructureTests(unittest.TestCase):
    def _write_plan(self, book_dir, *, phase="planejamento", include_direction=True):
        plan = {
            "status": phase,
            "miolo": {"total_paginas": 12},
            "direcao_visual": ({
                "estilo_ilustracao": "guache", "fotografia": {"abertura": "50 mm", "spread": "35 mm"},
                "cinematografia": "regra dos terços", "cenografia": "histórica", "cor_e_luz": "luz motivada",
            } if include_direction else {}),
            "capitulos": [{
                "ordem": 1, "titulo": "Conto", "paginas": [3, 10], "pagina_reflexao": 10,
                "cenas": [
                    self._scene("s1", "abertura", [3], "a.png"),
                    self._scene("s2", "spread", [4, 5], "b.png"),
                    self._scene("s3", "spread", [6, 7], "c.png"),
                    self._scene("s4", "spread", [8, 9], "d.png"),
                ],
            }],
        }
        (book_dir / "plano.yaml").write_text(yaml.safe_dump(plan, allow_unicode=True), encoding="utf-8")

    @staticmethod
    def _scene(scene_id, kind, pages, asset):
        return {
            "id": scene_id, "tipo": kind, "paginas": pages, "funcao": "narrar", "ancora_textual": "trecho",
            "descricao": "cena", "zona_texto": "céu", "personagens": ["Pessoa"],
            "elementos_continuidade": ["roupa"], "alt_texto": "descrição", "arquivo": asset,
            "status": "planejada",
        }

    @staticmethod
    def _plan_config(phase="planejamento"):
        return config(plano_ilustracoes={
            "arquivo": "plano.yaml", "fase": phase, "paginas_iniciais": 2, "paginas_por_capitulo": 8,
            "paginas_finais": 2, "cenas_por_capitulo": 4, "inicio_capitulo_impar": True,
            "abertura_pagina_unica": True, "cenas_internas_em_spread": 3,
        })

    def test_no_universal_reflection_requirement(self):
        result = analyze_structure("# Romance\n\nTexto contínuo.", config())
        self.assertEqual(result["total_issues"], 0)

    def test_configured_required_section_is_enforced(self):
        result = analyze_structure("# Conto\n\nHistória.", config(
            secoes_obrigatorias=["Reflexão"], capitulos_ignorados=[],
        ))
        self.assertEqual(result["issues"][0]["rule"], "structure.section.missing")

    def test_ignored_preface_does_not_require_story_elements(self):
        text = "# Prefácio\n\nTexto.\n\n# Conto\n\n> Fonte\n\n![Cena](cena.png)\n\n## Reflexão\n\nLição."
        result = analyze_structure(text, config(
            capitulos_ignorados=["Prefácio"], secoes_obrigatorias=["Reflexão"],
            elementos_obrigatorios={"atribuicao": True, "imagem": True},
        ))
        self.assertEqual(result["total_issues"], 0)

    def test_missing_image_alt_is_flagged(self):
        result = analyze_structure("# Conto\n\n![](cena.png)", config(
            elementos_obrigatorios={"texto_alternativo_imagem": True},
        ))
        self.assertEqual(result["issues"][0]["rule"], "structure.image.missing_alt")

    def test_missing_local_image_file_is_flagged_when_enabled(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = analyze_structure(
                "# Conto\n\n![Cena](assets/ausente.png)",
                config(elementos_obrigatorios={"arquivo_imagem": True}),
                Path(tmp),
            )
        self.assertEqual(result["issues"][0]["rule"], "structure.image.missing_file")

    def test_existing_local_image_file_is_accepted(self):
        with tempfile.TemporaryDirectory() as tmp:
            book_dir = Path(tmp)
            (book_dir / "cena.png").write_bytes(b"imagem")
            result = analyze_structure(
                "# Conto\n\n![Cena](cena.png)",
                config(elementos_obrigatorios={"arquivo_imagem": True}),
                book_dir,
            )
        self.assertEqual(result["total_issues"], 0)

    def test_heading_jump_is_flagged(self):
        result = analyze_structure("# Capítulo\n\n### Subseção\n\nTexto.", config())
        self.assertEqual(result["issues"][0]["rule"], "structure.heading.level_jump")

    def test_matching_framework_is_accepted(self):
        text = "---\nframework_used: romance\n---\n# Capítulo\n\nTexto."
        result = analyze_structure(text, {"framework": "romance", "revisao": {"estrutura": {}}})
        self.assertEqual(result["total_issues"], 0)

    def test_framework_mismatch_is_flagged(self):
        text = "---\nframework_used: ensaio\n---\n# Capítulo\n\nTexto."
        result = analyze_structure(text, {"framework": "romance", "revisao": {"estrutura": {}}})
        self.assertEqual(result["issues"][0]["rule"], "structure.framework.mismatch")

    def test_pending_registry_entries_are_aggregated(self):
        text = "# Primeiro\n\nTexto.\n\n# Segundo\n\nTexto."
        book = {
            "historias": [{"titulo": "Primeiro"}, {"titulo": "Pendente"}],
            "revisao": {"estrutura": {
                "registro_capitulos": {"campo": "historias", "campo_titulo": "titulo", "valores_pendentes": ["Pendente"]},
            }},
        }
        result = analyze_structure(text, book)
        self.assertEqual(result["summary"], {"registro": 1})

    def test_registry_title_order_mismatch_is_flagged(self):
        text = "# Segundo\n\nTexto.\n\n# Primeiro\n\nTexto."
        book = {
            "historias": [{"titulo": "Primeiro"}, {"titulo": "Segundo"}],
            "revisao": {"estrutura": {"registro_capitulos": {"campo": "historias"}}},
        }
        result = analyze_structure(text, book)
        self.assertEqual(result["summary"], {"registro": 2})

    def test_section_proportion_is_configurable(self):
        text = "# Conto\n\nUm dois três quatro cinco seis sete oito.\n\n## Nota\n\nNove dez."
        result = analyze_structure(text, config(
            proporcoes_secoes={"Nota": {"min": 0.4, "max": 0.8}},
        ))
        self.assertEqual(result["issues"][0]["rule"], "structure.section.proportion_outside_range")

    def test_valid_illustration_plan_is_accepted_without_assets_during_planning(self):
        with tempfile.TemporaryDirectory() as tmp:
            book_dir = Path(tmp)
            self._write_plan(book_dir)
            result = analyze_structure("# Conto\n\nTexto.", self._plan_config(), book_dir)
        self.assertEqual(result["total_issues"], 0)
        self.assertEqual(result["metrics"]["illustration_plan"]["scenes"], 4)
        self.assertEqual(result["metrics"]["illustration_plan"]["existing_assets"], 0)

    def test_illustration_plan_requires_multidisciplinary_art_direction(self):
        with tempfile.TemporaryDirectory() as tmp:
            book_dir = Path(tmp)
            self._write_plan(book_dir, include_direction=False)
            result = analyze_structure("# Conto\n\nTexto.", self._plan_config(), book_dir)
        self.assertIn("structure.illustration_plan.missing_art_direction", [item["rule"] for item in result["issues"]])

    def test_production_phase_requires_planned_assets(self):
        with tempfile.TemporaryDirectory() as tmp:
            book_dir = Path(tmp)
            self._write_plan(book_dir, phase="producao")
            result = analyze_structure("# Conto\n\nTexto.", self._plan_config("producao"), book_dir)
        missing = [item for item in result["issues"] if item["rule"] == "structure.illustration_plan.missing_asset"]
        self.assertEqual(len(missing), 4)

    def test_book_without_images_skips_visual_plan(self):
        book = config(plano_ilustracoes={
            "modo": "sem_imagens", "gerar_prompts": False, "arquivo": "nao_deve_ser_lido.yaml",
        })
        result = analyze_structure("# Romance\n\nTexto.", book, Path("/diretorio/inexistente"))
        self.assertEqual(result["total_issues"], 0)
        self.assertTrue(result["metrics"]["illustration_plan"]["skipped"])

    def test_adaptive_plan_accepts_more_than_three_spreads(self):
        with tempfile.TemporaryDirectory() as tmp:
            book_dir = Path(tmp)
            scenes = [self._scene("s1", "abertura", [3], "a.png")]
            for index, pages in enumerate(([4, 5], [6, 7], [8, 9], [10, 11]), 2):
                scenes.append(self._scene(f"s{index}", "spread", list(pages), f"{index}.png"))
            plan = {
                "status": "planejamento",
                "miolo": {"total_paginas": 14},
                "direcao_visual": {
                    "estilo_ilustracao": "guache",
                    "fotografia": {"abertura": "50 mm", "spread": "35 mm"},
                    "cinematografia": "regra dos terços", "cenografia": "histórica",
                    "cor_e_luz": "luz motivada",
                },
                "capitulos": [{
                    "ordem": 1, "titulo": "Conto", "paginas": [3, 12],
                    "pagina_reflexao": 12, "cenas": scenes,
                }],
            }
            (book_dir / "plano.yaml").write_text(
                yaml.safe_dump(plan, allow_unicode=True), encoding="utf-8"
            )
            book = config(plano_ilustracoes={
                "arquivo": "plano.yaml", "fase": "planejamento",
                "paginas_iniciais": 2, "paginas_finais": 2,
                "quantidade_spreads": "adaptativa", "min_spreads_por_capitulo": 3,
                "inicio_capitulo_impar": True, "abertura_pagina_unica": True,
            })
            result = analyze_structure("# Conto\n\nTexto.", book, book_dir)
        self.assertEqual(result["total_issues"], 0)
        self.assertEqual(result["metrics"]["illustration_plan"]["scenes"], 5)

    def test_adaptive_plan_warns_before_compressing_long_chapter(self):
        with tempfile.TemporaryDirectory() as tmp:
            book_dir = Path(tmp)
            self._write_plan(book_dir)
            book = config(plano_ilustracoes={
                "arquivo": "plano.yaml", "fase": "planejamento",
                "paginas_iniciais": 2, "paginas_finais": 2,
                "quantidade_spreads": "adaptativa", "min_spreads_por_capitulo": 3,
                "palavras_por_spread_referencia": 20,
                "tolerancia_superior_densidade": 1.0,
                "inicio_capitulo_impar": True, "abertura_pagina_unica": True,
            })
            long_text = "# Conto\n\n" + " ".join(["palavra"] * 85)
            result = analyze_structure(long_text, book, book_dir)
        density = [
            item for item in result["issues"]
            if item["rule"] == "structure.illustration_plan.spread_density"
        ]
        self.assertEqual(len(density), 1)
        self.assertEqual(density[0]["severity"], "alerta")
        self.assertFalse(density[0]["auto_fixable"])


if __name__ == "__main__":
    unittest.main()
