#!/usr/bin/env python3
"""
4-capas/engines/engine_c_svg.py
-------------------------------
Opção C: Motor SVG Vetorial 2D (Padrão Figma / Illustrator API).
Gera um SVG vetorial puro com elementos <g>, <text>, <image>, <rect> e converte para PDF.
"""

import os
import sys
from pathlib import Path
from typing import Dict, Any
import yaml
from playwright.sync_api import sync_playwright

sys.path.append(str(Path(__file__).parent.parent))
from barcode_generator import generate_ean13_svg


def generate_svg_composite_cover(config: Dict[str, Any], spine_mm: float, book_dir: Path) -> Path:
    title = config.get("titulo", "CRÔNICAS CHINESAS")
    subtitle = config.get("subtitulo", "Histórias Milenares de Coragem, Sabedoria e Autocontrole")
    author = config.get("autor", "Gabriel Pereira")
    publisher = config.get("editora", "Editora Coala")
    isbn = config.get("isbn", "978-65-988202-7-5")
    synopsis = config.get("sinopse", "Uma coletânea inesquecível de contos chineses tradicionais que ensinam virtudes como resiliência, autocontrole, paciência e coragem.")
    cor_capa = config.get("cor_capa", "#141214")

    # Gera código de barras
    assets_dir = book_dir / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)
    barcode_file = assets_dir / "isbn_barcode.svg"
    generate_ean13_svg(isbn, barcode_file)

    cover_img_file = assets_dir / "capa.jpg"
    cover_img_uri = cover_img_file.resolve().as_uri() if cover_img_file.exists() else ""
    barcode_uri = barcode_file.resolve().as_uri()
    logo_file = Path("resources") / "logos" / "coala" / "logo.svg"
    logo_uri = logo_file.resolve().as_uri() if logo_file.exists() else ""

    # Dimensões exatas em pixels (300 DPI / scale)
    width_px = 1031
    height_px = 756
    
    svg_content = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width_px}" height="{height_px}" viewBox="0 0 {width_px} {height_px}">
  <!-- Definições de Estilos e Gradientes -->
  <defs>
    <linearGradient id="goldGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#f3e5ab" />
      <stop offset="50%" stop-color="#d4af37" />
      <stop offset="100%" stop-color="#aa7c11" />
    </linearGradient>
    <linearGradient id="overlayTop" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#141214" stop-opacity="0.95" />
      <stop offset="70%" stop-color="#141214" stop-opacity="0.7" />
      <stop offset="100%" stop-color="#141214" stop-opacity="0" />
    </linearGradient>
    <linearGradient id="overlayBottom" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#141214" stop-opacity="0" />
      <stop offset="100%" stop-color="#141214" stop-opacity="0.95" />
    </linearGradient>
    <style>
      .title-gold {{ font-family: 'Georgia', serif; font-size: 26px; font-weight: bold; fill: url(#goldGrad); letter-spacing: 3px; }}
      .sub-tag {{ font-family: 'Helvetica', sans-serif; font-size: 11px; font-weight: bold; fill: #ffffff; letter-spacing: 4px; }}
      .sub-italic {{ font-family: 'Georgia', serif; font-size: 12px; font-style: italic; fill: #f0e6d2; }}
      .author-txt {{ font-family: 'Helvetica', sans-serif; font-size: 13px; font-weight: bold; fill: #ffffff; letter-spacing: 5px; }}
      .synopsis-txt {{ font-family: 'Georgia', serif; font-size: 12px; fill: #e0e0e0; line-height: 1.6; }}
    </style>
  </defs>

  <!-- 1. Fundo Base -->
  <rect width="{width_px}" height="{height_px}" fill="{cor_capa}" />

  <!-- 2. Contracapa (X: 38px até 510px) -->
  <g transform="translate(38, 38)">
    <rect width="472" height="680" fill="#181618" rx="6" />
    <text x="236" y="70" class="title-gold" text-anchor="middle">CRÔNICAS CHINESAS</text>
    <text x="236" y="95" class="sub-tag" text-anchor="middle">PARA PEQUENOS GUERREIROS</text>
    <line x1="186" y1="115" x2="286" y2="115" stroke="#d4af37" stroke-width="1.5" />
    
    <!-- Caixa de Sinopse -->
    <rect x="30" y="150" width="412" height="220" fill="#201d20" rx="8" stroke="#332d33" stroke-width="1" />
    <foreignObject x="45" y="165" width="382" height="190">
      <div xmlns="http://www.w3.org/1999/xhtml" style="color:#e0e0e0; font-family: Georgia, serif; font-size: 13px; line-height: 1.6; text-align: justify;">
        {synopsis}
      </div>
    </foreignObject>

    <!-- Rodapé Contracapa -->
    <image href="{logo_uri}" x="40" y="580" width="90" height="50" />
    <image href="{barcode_uri}" x="300" y="570" width="130" height="65" />
  </g>

  <!-- 3. Lombada (X: 510px até 521px) -->
  <rect x="510" y="38" width="11" height="680" fill="#0b0a0c" />
  <g transform="translate(515, 378) rotate(-90)">
    <text x="0" y="4" font-family="Georgia" font-size="10" font-weight="bold" fill="#d4af37" letter-spacing="2" text-anchor="middle">
      CRÔNICAS CHINESAS • {author.upper()}
    </text>
  </g>

  <!-- 4. Capa Frontal Full-Bleed SVG (X: 521px até 993px) -->
  <g transform="translate(521, 0)">
    <!-- Arte de Fundo -->
    <image href="{cover_img_uri}" x="0" y="0" width="510" height="{height_px}" preserveAspectRatio="xMidYMid slice" />
    
    <!-- Gradiente Topo -->
    <rect x="0" y="0" width="510" height="320" fill="url(#overlayTop)" />
    <text x="255" y="90" class="title-gold" text-anchor="middle">CRÔNICAS CHINESAS</text>
    <text x="255" y="118" class="sub-tag" text-anchor="middle">PARA PEQUENOS GUERREIROS</text>
    <line x1="205" y1="135" x2="305" y2="135" stroke="#d4af37" stroke-width="1.5" />
    <text x="255" y="165" class="sub-italic" text-anchor="middle">{subtitle}</text>

    <!-- Gradiente Rodapé -->
    <rect x="0" y="550" width="510" height="206" fill="url(#overlayBottom)" />
    <text x="255" y="700" class="author-txt" text-anchor="middle">{author.upper()}</text>
  </g>
</svg>
"""

    svg_file = book_dir / "capa_opcao_c.svg"
    svg_file.write_text(svg_content, encoding="utf-8")

    out_capas_dir = Path("outputs") / book_dir.name / "capas"
    out_capas_dir.mkdir(parents=True, exist_ok=True)
    out_pdf = out_capas_dir / "capa_opcao_c_svg.pdf"

    # Converte SVG para PDF via Playwright
    html_wrapper = f"""<!DOCTYPE html><html><body style="margin:0;padding:0;overflow:hidden;"><img src="{svg_file.resolve().as_uri()}" style="width:100%;height:100%;"></body></html>"""
    wrapper_html_file = book_dir / "capa_opcao_c_wrapper.html"
    wrapper_html_file.write_text(html_wrapper, encoding="utf-8")

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(wrapper_html_file.resolve().as_uri())
        page.pdf(
            path=str(out_pdf),
            width="273mm",
            height="200mm",
            print_background=True,
            margin={"top": "0", "right": "0", "bottom": "0", "left": "0"}
        )
        browser.close()

    print(f"✨ [Opção C SVG Composite] Capa compilada em: {out_pdf}")
    return out_pdf


if __name__ == "__main__":
    b_dir = Path("inputs") / "cronicas_chinesas_para_pequenos_guerreiros"
    cfg = yaml.safe_load((b_dir / "book_config.yaml").read_text(encoding="utf-8"))
    generate_svg_composite_cover(cfg, 3.0, b_dir)
