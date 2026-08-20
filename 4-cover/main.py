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
from design_engine.cover_spec import validate_config


def load_yaml(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def main() -> None:
    parser = argparse.ArgumentParser(description="Cover (Projeto 4): Capas & Artes - Motor Híbrido de Capas")
    parser.add_argument("--book-dir", required=True, help="Nome da pasta do livro em inputs/")
    parser.add_argument("--engine", choices=["auto", "html", "typst"], default="auto", help="Força o uso do Motor A (html) ou Motor B (typst)")
    parser.add_argument("--preflight", action="store_true", help="Valida configuração, assets e geometria; não renderiza a capa")
    parser.add_argument("--strict", action="store_true", help="Interrompe em warnings do preflight e não aceita fallback de contagem de páginas")
    args = parser.parse_args()

    book_dir = Path("inputs") / args.book_dir
    config_file = book_dir / "book_config.yaml"
    config = load_yaml(config_file)
    config_issues = validate_config(config)
    config_errors = [issue for issue in config_issues if issue["severity"] == "error"]
    if config_errors:
        messages = "\n".join(f"- [{issue['code']}] {issue['message']}" for issue in config_errors)
        raise SystemExit(f"Configuração de capa inválida em {config_file}:\n{messages}")
    for issue in config_issues:
        if issue["severity"] == "warning" and not args.preflight:
            print(f"⚠️  [Config] [{issue['code']}] {issue['message']}")

    pdf_file = Path("outputs") / args.book_dir / "pdf" / f"{args.book_dir}_impressao.pdf"
    
    # 1. Contagem de Páginas e Cálculo de Lombada
    page_count = count_pdf_pages(pdf_file, strict=not args.preflight)
    paper_type = config.get("papel", "polen_soft_80g")
    acabamento = config.get("acabamento", "brochura")
    spine_mm = calculate_spine_width_mm(page_count, paper_type, acabamento)

    if args.preflight:
        from design_engine.preflight import run_preflight, save_geometry_proof, save_preflight_report

        out_dir = Path("outputs") / args.book_dir / "capas"
        report = run_preflight(config, book_dir, pdf_file, spine_mm)
        report_file = save_preflight_report(report, out_dir)
        proof_file = save_geometry_proof(report, out_dir)
        summary = report.to_dict()["summary"]
        print(f"🔎 [Preflight] {report.status}: {summary['errors']} erro(s), {summary['warnings']} aviso(s)")
        for issue in report.issues:
            print(f"  - {issue.severity.upper()} [{issue.code}] {issue.message}")
        print(f"📋 Relatório: {report_file}")
        print(f"📐 Prova geométrica: {proof_file}")
        if summary["errors"] or (args.strict and summary["warnings"]):
            raise SystemExit(2)
        return

    print(f"🎨 [Cover] Gerando Capa Gráfica para '{args.book_dir}'...")
    print(f"📊 Páginas do Miolo: {page_count} | Lombada: {spine_mm}mm | Acabamento: {acabamento}")

    # Compositing (Frente 2, opt-in): textura + ilustração + degradê -> assets/capa.jpg
    if config.get("composicao_capa"):
        from design_engine.compositor import build_cover_art
        build_cover_art(config, book_dir)

    # Detecta se existe imagem de capa em assets/
    assets_dir = book_dir / "assets"
    has_image = (assets_dir / "capa.jpg").exists() or (assets_dir / "capa.png").exists()
    template_pref = config.get("template_capa", config.get("layout_mídias", "ilustrado_full_bleed"))

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
