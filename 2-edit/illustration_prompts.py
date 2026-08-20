#!/usr/bin/env python3
"""Compila um plano visual YAML em prompts de ilustração editáveis e reproduzíveis."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import yaml


def _text(value: Any) -> str:
    if isinstance(value, list):
        return ", ".join(str(item) for item in value)
    return str(value or "").strip()


def compile_prompt(plan: dict[str, Any], chapter: dict[str, Any], scene: dict[str, Any]) -> str:
    direction = plan["direcao_visual"]
    composition = plan["composicao"]
    is_spread = scene["tipo"] == "spread"
    support = composition["spread" if is_spread else "abertura"]
    camera = direction["fotografia"]["spread" if is_spread else "abertura"]
    movement = _text(direction.get("movimento_e_ritmo"))
    variety = _text(direction.get("variedade_cinematografica"))
    pages = "–".join(str(page) for page in scene["paginas"])
    lines = [
        f"Crie uma ilustração editorial infantil para o capítulo “{chapter['titulo']}”, páginas {pages}.",
        f"CENA E FUNÇÃO NARRATIVA — {scene['descricao']} Função: {scene['funcao']}",
        f"MOMENTO DO TEXTO — “{scene['ancora_textual']}”",
        f"LINGUAGEM DE ILUSTRAÇÃO — {_text(direction['estilo_ilustracao'])}",
        f"FOTOGRAFIA VIRTUAL — {_text(camera)}",
        f"CINEMATOGRAFIA E COMPOSIÇÃO — {_text(direction['cinematografia'])}",
        f"MOVIMENTO E RITMO — {movement}" if movement else "",
        f"VARIEDADE ENTRE CENAS — {variety}" if variety else "",
        f"CENOGRAFIA — {_text(direction['cenografia'])}",
        f"COR E LUZ — {_text(direction['cor_e_luz'])}",
        f"PERSONAGENS — {_text(scene['personagens'])}. {_text(direction['personagens'])}",
        f"CONTINUIDADE — {_text(scene['elementos_continuidade'])}",
        f"ÁREA EDITORIAL PARA TEXTO — Reserve deliberadamente {scene['zona_texto']}. "
        "Essa área deve ter contraste previsível, baixa informação visual e textura discreta, "
        "sem personagens, rostos, mãos, armas ou objetos narrativos. O texto será aplicado depois na diagramação.",
        f"FORMATO — {support['tamanho_com_sangria_mm'][0]} × {support['tamanho_com_sangria_mm'][1]} mm "
        f"com sangria, {support['tamanho_recomendado_px'][0]} × {support['tamanho_recomendado_px'][1]} px, "
        f"{plan['miolo']['resolucao_dpi']} dpi. {_text(direction['acabamento'])}",
        "RESTRIÇÕES — " + " ".join(composition["restricoes"]),
        "EVITAR — " + _text(plan["prompt_negativo"]),
    ]
    return "\n".join(line for line in lines if line)


def compile_document(plan: dict[str, Any], source: Path) -> str:
    lines = [
        f"# Prompts de ilustração — {plan['livro']}",
        "",
        "> Documento gerado a partir de `" + source.name + "`. Edite o plano YAML e recompile; "
        "não peça ao gerador de imagens que desenhe o texto do livro.",
        "",
    ]
    for chapter in plan["capitulos"]:
        lines.extend([f"## Capítulo {chapter['ordem']} — {chapter['titulo']}", ""])
        for scene in chapter["cenas"]:
            lines.extend([
                f"### {scene['id']} — {scene['tipo']} — páginas {', '.join(map(str, scene['paginas']))}",
                "",
                "```text",
                compile_prompt(plan, chapter, scene),
                "```",
                "",
                f"**Texto alternativo previsto:** {scene['alt_texto']}",
                "",
                f"**Destino futuro do ativo:** `{scene['arquivo']}`",
                "",
            ])
    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", type=Path, help="plano_ilustracoes.yaml")
    parser.add_argument("--output", type=Path, help="arquivo Markdown de saída")
    args = parser.parse_args()
    plan = yaml.safe_load(args.plan.read_text(encoding="utf-8"))
    output = args.output or args.plan.with_name("prompts_ilustracoes.md")
    output.write_text(compile_document(plan, args.plan), encoding="utf-8")
    print(f"Prompts compilados: {output}")


if __name__ == "__main__":
    main()
