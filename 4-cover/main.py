#!/usr/bin/env python3
"""
4-cover/main.py
---------------
Motor do Cover (Projeto 4 — Capas & Artes): Sistema Híbrido de Capas.
- Seleciona automaticamente o Motor A (HTML5/CSS3) para capas ilustradas/full-bleed.
- Seleciona automaticamente o Motor B (Typst Presets) para capas minimalistas/tipográficas sem imagens.
"""

import os
import sys
import argparse
from pathlib import Path
from typing import Dict, Any
import yaml

from spine_calculator import count_pdf_pages, calculate_spine_width_mm
from design_engine.engine_html import render_html_cover
from design_engine.engine_typst import render_typst_cover


def load_yaml(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def main() -> None:
    parser = argparse.ArgumentParser(description="Cover (Projeto 4): Capas & Artes - Motor Híbrido de Capas")
    parser.add_argument("--book-dir", required=True, help="Nome da pasta do livro em inputs/")
    parser.add_argument("--engine", choices=["auto", "html", "typst"], default="auto", help="Força o uso do Motor A (html) ou Motor B (typst)")
    args = parser.parse_args()

    book_dir = Path("inputs") / args.book_dir
    config_file = book_dir / "book_config.yaml"
    config = load_yaml(config_file)

    pdf_file = Path("outputs") / args.book_dir / "pdf" / f"{args.book_dir}_impressao.pdf"
    
    # 1. Contagem de Páginas e Cálculo de Lombada
    page_count = count_pdf_pages(pdf_file)
    paper_type = config.get("papel", "polen_soft_80g")
    acabamento = config.get("acabamento", "brochura")
    spine_mm = calculate_spine_width_mm(page_count, paper_type, acabamento)

    print(f"🎨 [Cover] Gerando Capa Gráfica para '{args.book_dir}'...")
    print(f"📊 Páginas do Miolo: {page_count} | Lombada: {spine_mm}mm | Acabamento: {acabamento}")

    # Detecta se existe imagem de capa em assets/
    assets_dir = book_dir / "assets"
    has_image = (assets_dir / "capa.jpg").exists() or (assets_dir / "capa.png").exists()
    template_pref = config.get("template_capa", "ilustrado_full_bleed")

    # Roteamento Inteligente de Motores
    use_html = False
    if args.engine == "html":
        use_html = True
    elif args.engine == "typst":
        use_html = False
    else: # auto
        if has_image or template_pref == "ilustrado_full_bleed":
            use_html = True
        else:
            use_html = False

    if use_html:
        print("🚀 [Motor A] Selecionado: HTML5/CSS3 + Playwright (Full-Bleed / Ilustrado)")
        out_pdf = render_html_cover(config, spine_mm, book_dir)
    else:
        print("⚡ [Motor B] Selecionado: Typst Presets (Minimalista / Tipográfico)")
        out_pdf = render_typst_cover(config, spine_mm, book_dir)

    print(f"✨ [Cover] Capa Horizontal Aberta gerada com sucesso em: {out_pdf}")


if __name__ == "__main__":
    main()
