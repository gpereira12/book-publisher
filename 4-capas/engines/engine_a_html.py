#!/usr/bin/env python3
"""
4-capas/engines/engine_a_html.py
--------------------------------
Opção A: Motor HTML5/CSS3 + Playwright (Headless Chromium)
Oferece controle total de CSS Grid, Flexbox, Google Fonts, filtros de mesclagem e transparência real.
"""

import os
import sys
from pathlib import Path
from typing import Dict, Any
import yaml
from playwright.sync_api import sync_playwright

# Tenta importar gerador de código de barras
sys.path.append(str(Path(__file__).parent.parent))
from barcode_generator import generate_ean13_svg, clean_digits


def generate_html_cover(config: Dict[str, Any], spine_mm: float, book_dir: Path) -> Path:
    title = config.get("titulo", "Crônicas Chinesas para Pequenos Guerreiros")
    subtitle = config.get("subtitulo", "Histórias Milenares de Coragem, Sabedoria e Autocontrole")
    author = config.get("autor", "Gabriel Pereira")
    publisher = config.get("editora", "Editora Coala")
    isbn = config.get("isbn", "978-65-988202-7-5")
    synopsis = config.get("sinopse", "Uma coletânea inesquecível de contos chineses tradicionais que ensinam virtudes como resiliência, autocontrole, paciência e coragem.")
    author_bio = config.get("bio_autor", "Gabriel Pereira é autor e apaixonado pela literatura e sabedoria oriental.")
    cor_capa = config.get("cor_capa", "#141214")

    # Dimensões Pocket em mm (125mm x 180mm) + Sangria 10mm + Lombada 3mm
    page_w_mm = 125.0
    page_h_mm = 180.0
    bleed_mm = 10.0
    total_w_mm = (bleed_mm * 2) + (page_w_mm * 2) + spine_mm
    total_h_mm = (bleed_mm * 2) + page_h_mm

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

    html_content = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <title>Capa - Opção A HTML</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Cinzel:wght@700;900&family=Cormorant+Garamond:ital,wght@0,600;1,400&family=Montserrat:wght@500;700&display=swap" rel="stylesheet">
  <style>
    @page {{
      size: {total_w_mm}mm {total_h_mm}mm;
      margin: 0;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      width: {total_w_mm}mm;
      height: {total_h_mm}mm;
      background-color: {cor_capa};
      color: #ffffff;
      font-family: 'Cormorant Garamond', serif;
      display: flex;
      flex-direction: row;
      overflow: hidden;
    }}
    
    /* 1. Sangria Esquerda */
    .bleed-left {{
      width: {bleed_mm}mm;
      height: 100%;
      background: {cor_capa};
    }}

    /* 2. Contracapa */
    .back-cover {{
      width: {page_w_mm}mm;
      height: 100%;
      padding: 25mm 15mm 15mm 15mm;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      background: radial-gradient(circle at center, #1e1b1e 0%, #121012 100%);
      border-right: 1px solid rgba(212, 175, 55, 0.15);
    }}
    .back-title {{
      font-family: 'Cinzel', serif;
      color: #d4af37;
      font-size: 14pt;
      letter-spacing: 2px;
      text-align: center;
    }}
    .back-subtitle {{
      font-family: 'Montserrat', sans-serif;
      font-size: 7.5pt;
      color: #cccccc;
      letter-spacing: 2.5px;
      text-align: center;
      margin-top: 4px;
      text-transform: uppercase;
    }}
    .gold-divider {{
      width: 40px;
      height: 1px;
      background: #d4af37;
      margin: 12px auto;
    }}
    .synopsis-box {{
      background: rgba(255, 255, 255, 0.03);
      border: 1px solid rgba(212, 175, 55, 0.2);
      border-radius: 6px;
      padding: 16px;
      font-size: 9.5pt;
      line-height: 1.6;
      color: #e0e0e0;
      text-align: justify;
    }}
    .back-footer {{
      display: flex;
      flex-direction: row;
      justify-content: space-between;
      align-items: center;
    }}
    .publisher-seal img {{
      height: 45px;
      filter: drop-shadow(0 2px 4px rgba(0,0,0,0.5));
    }}
    .barcode-img img {{
      width: 130px;
      border-radius: 4px;
    }}

    /* 3. Lombada */
    .spine {{
      width: {spine_mm}mm;
      height: 100%;
      background: #0d0c0e;
      display: flex;
      justify-content: center;
      align-items: center;
      border-left: 1px solid rgba(255,255,255,0.05);
      border-right: 1px solid rgba(255,255,255,0.05);
    }}
    .spine-text {{
      writing-mode: vertical-rl;
      transform: rotate(180deg);
      font-family: 'Cinzel', serif;
      font-size: 8pt;
      font-weight: 700;
      color: #d4af37;
      letter-spacing: 2px;
      white-space: nowrap;
    }}

    /* 4. Capa Frontal Full-Bleed */
    .front-cover {{
      width: calc({page_w_mm}mm + {bleed_mm}mm);
      height: 100%;
      position: relative;
      background: #141214;
    }}
    .art-bg {{
      position: absolute;
      top: 0; left: 0;
      width: 100%; height: 100%;
      object-fit: cover;
    }}
    .overlay-top {{
      position: absolute;
      top: 0; left: 0; width: 100%;
      height: 45%;
      background: linear-gradient(to bottom, rgba(18,16,18,0.95) 0%, rgba(18,16,18,0.7) 60%, rgba(18,16,18,0) 100%);
      padding: {bleed_mm + 15}mm 15mm 0 15mm;
      text-align: center;
    }}
    .front-title {{
      font-family: 'Cinzel', serif;
      font-size: 20pt;
      font-weight: 900;
      color: #d4af37;
      letter-spacing: 2px;
      text-shadow: 0 4px 12px rgba(0,0,0,0.8);
    }}
    .front-subtitle-tag {{
      font-family: 'Montserrat', sans-serif;
      font-size: 8pt;
      font-weight: 700;
      color: #ffffff;
      letter-spacing: 3px;
      margin-top: 6px;
      text-transform: uppercase;
    }}
    .front-subtitle-italic {{
      font-style: italic;
      font-size: 9.5pt;
      color: #f0e6d2;
      margin-top: 8px;
    }}
    .overlay-bottom {{
      position: absolute;
      bottom: 0; left: 0; width: 100%;
      height: 25%;
      background: linear-gradient(to top, rgba(18,16,18,0.95) 0%, rgba(18,16,18,0) 100%);
      padding-bottom: {bleed_mm + 10}mm;
      display: flex;
      justify-content: center;
      align-items: flex-end;
    }}
    .author-name {{
      font-family: 'Montserrat', sans-serif;
      font-size: 10pt;
      font-weight: 700;
      color: #ffffff;
      letter-spacing: 4px;
      text-transform: uppercase;
    }}
  </style>
</head>
<body>

  <div class="bleed-left"></div>

  <!-- Contracapa -->
  <div class="back-cover">
    <div>
      <div class="back-title">CRÔNICAS CHINESAS</div>
      <div class="back-subtitle">PARA PEQUENOS GUERREIROS</div>
      <div class="gold-divider"></div>
      <div class="synopsis-box">
        {synopsis}
      </div>
    </div>
    
    <div class="back-footer">
      <div class="publisher-seal">
        {"<img src='" + logo_uri + "'>" if logo_uri else "<span>" + publisher + "</span>"}
      </div>
      <div class="barcode-img">
        <img src="{barcode_uri}">
      </div>
    </div>
  </div>

  <!-- Lombada -->
  <div class="spine">
    <div class="spine-text">CRÔNICAS CHINESAS • {author.upper()}</div>
  </div>

  <!-- Capa Frontal -->
  <div class="front-cover">
    {"<img class='art-bg' src='" + cover_img_uri + "'>" if cover_img_uri else ""}
    <div class="overlay-top">
      <div class="front-title">CRÔNICAS CHINESAS</div>
      <div class="front-subtitle-tag">PARA PEQUENOS GUERREIROS</div>
      <div class="gold-divider"></div>
      <div class="front-subtitle-italic">{subtitle}</div>
    </div>
    <div class="overlay-bottom">
      <div class="author-name">{author.upper()}</div>
    </div>
  </div>

</body>
</html>
"""

    html_file = book_dir / "capa_opcao_a.html"
    html_file.write_text(html_content, encoding="utf-8")

    out_capas_dir = Path("outputs") / book_dir.name / "capas"
    out_capas_dir.mkdir(parents=True, exist_ok=True)
    out_pdf = out_capas_dir / "capa_opcao_a_html.pdf"

    # Renderiza via Playwright
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(html_file.resolve().as_uri())
        page.pdf(
            path=str(out_pdf),
            width=f"{total_w_mm}mm",
            height=f"{total_h_mm}mm",
            print_background=True,
            margin={"top": "0", "right": "0", "bottom": "0", "left": "0"}
        )
        browser.close()

    print(f"✨ [Opção A HTML5/CSS3] Capa compilada em: {out_pdf}")
    return out_pdf


if __name__ == "__main__":
    b_dir = Path("inputs") / "cronicas_chinesas_para_pequenos_guerreiros"
    cfg = yaml.safe_load((b_dir / "book_config.yaml").read_text(encoding="utf-8"))
    generate_html_cover(cfg, 3.0, b_dir)
