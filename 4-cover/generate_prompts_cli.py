#!/usr/bin/env python3
"""
4-cover/generate_prompts_cli.py
--------------------------------
CLI standalone para gerar prompts de imagem de capa (Frente 1 do Cover v2).
Separado de main.py porque não depende da contagem de páginas do PDF impresso.
"""

import argparse
from pathlib import Path
import yaml

from design_engine.prompt_engine import generate_cover_prompt_set, save_prompt_set, format_for_tool


def load_yaml(path: Path) -> dict:
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def main() -> None:
    parser = argparse.ArgumentParser(description="Cover (Projeto 4): Gerador de Prompts de Capa")
    parser.add_argument("--book-dir", required=True, help="Nome da pasta do livro em inputs/")
    parser.add_argument("--tool", default="plain", choices=["plain", "midjourney"],
                         help="Formato de saída do prompt (padrão: plain)")
    parser.add_argument("--directions", action="store_true", help="Gera direções figurativa, simbólica e gráfica")
    args = parser.parse_args()

    book_dir = Path("inputs") / args.book_dir
    config = load_yaml(book_dir / "book_config.yaml")
    if args.directions:
        config["gerar_direcoes_visuais"] = True

    prompts = generate_cover_prompt_set(config, config.get("cover_prompt_briefs"))
    out_dir = save_prompt_set(prompts, book_dir)

    print(f"🖋️  [Cover] {len(prompts)} prompt(s) gerado(s) em: {out_dir}")
    for prompt_data in prompts:
        print(f"\n--- {prompt_data['label']} ({prompt_data['structured']['estilo_key']}) ---")
        print(format_for_tool(prompt_data, tool=args.tool))


if __name__ == "__main__":
    main()
