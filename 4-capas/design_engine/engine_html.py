"""
4-capas/design_engine/engine_html.py
------------------------------------
Motor A (HTML5/CSS3 + Playwright): Gerador Multipadronizado (Padrões 1, 2 e 3).
"""

import os
import sys
from pathlib import Path
from typing import Dict, Any
from playwright.sync_api import sync_playwright

from barcode_generator import generate_ean13_svg
from design_engine.design_tokens import get_tokens
from design_engine.geometry_engine import calculate_cover_geometry
from design_engine.layout_patterns.pattern_1_full_bleed import render_pattern_1
from design_engine.layout_patterns.pattern_2_split_tarja import render_pattern_2
from design_engine.layout_patterns.pattern_3_framed_moldura import render_pattern_3


def render_html_cover(config: Dict[str, Any], spine_mm: float, book_dir: Path, pattern_id: int = 1) -> Path:
    tokens = get_tokens(config)
    pal = tokens["palette"]
    fonts = tokens["fonts"]

    title = config.get("titulo", "Título do Livro")
    subtitle = config.get("subtitulo", "")
    author = config.get("autor", "Autor")
    publisher = config.get("editora", "Editora Coala")
    isbn = config.get("isbn", "978-65-988202-7-5")
    synopsis = config.get("sinopse", "Sinopse do livro aqui.")

    geom = calculate_cover_geometry(config, spine_mm)
    page_w_mm = geom["page_w_mm"]
    page_h_mm = geom["page_h_mm"]
    bleed_mm = geom["bleed_mm"]
    total_w_mm = geom["total_w_mm"]
    total_h_mm = geom["total_h_mm"]

    # Código de barras
    assets_dir = book_dir / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)
    barcode_file = assets_dir / "isbn_barcode.svg"
    generate_ean13_svg(isbn, barcode_file)

    cover_img_file = assets_dir / "capa.jpg"
    if not cover_img_file.exists():
        cover_img_file = assets_dir / "capa.png"

    cover_img_uri = cover_img_file.resolve().as_uri() if cover_img_file.exists() else ""
    barcode_uri = barcode_file.resolve().as_uri()
    
    selo = config.get("selo", "coala").lower()
    logo_file = Path("resources") / "logos" / selo / "logo.svg"
    logo_uri = logo_file.resolve().as_uri() if logo_file.exists() else ""

    # Escolhe o Padrão de Composição (1, 2 ou 3)
    p_num = config.get("padrao_capa", pattern_id)
    if p_num == 2:
        front_cover_html = render_pattern_2(title, subtitle, author, cover_img_uri, pal, fonts, bleed_mm)
    elif p_num == 3:
        front_cover_html = render_pattern_3(title, subtitle, author, cover_img_uri, pal, fonts, bleed_mm)
    else:
        front_cover_html = render_pattern_1(title, subtitle, author, cover_img_uri, pal, fonts, bleed_mm)

    html_content = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <title>Capa Horizontal - Padrão {p_num}</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?{fonts['google_fonts_url']}&display=swap" rel="stylesheet">
  <style>
    @page {{ size: {total_w_mm}mm {total_h_mm}mm; margin: 0; }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      width: {total_w_mm}mm;
      height: {total_h_mm}mm;
      background-color: {pal['bg_color']};
      color: {pal['text_light']};
      font-family: {fonts['font_body']};
      display: flex;
      flex-direction: row;
      overflow: hidden;
    }}
    .bleed-left {{ width: {bleed_mm}mm; height: 100%; background: {pal['bg_color']}; }}
    
    .back-cover {{
      width: {page_w_mm}mm;
      height: 100%;
      padding: 22mm 15mm 15mm 15mm;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      background: radial-gradient(circle at center, #1c1a1c 0%, #121012 100%);
    }}
    .back-title {{ font-family: {fonts['font_title']}; color: {pal['gold_color']}; font-size: 13pt; letter-spacing: 2px; text-align: center; }}
    .gold-divider {{ width: 40px; height: 1.5px; background: {pal['gold_color']}; margin: 10px auto; }}
    .synopsis-box {{
      background: {pal['box_bg']};
      border: 1px solid {pal['box_border']};
      border-radius: 6px;
      padding: 16px;
      font-size: 9.5pt;
      line-height: 1.6;
      color: #e0e0e0;
      text-align: justify;
    }}
    .back-footer {{ display: flex; flex-direction: row; justify-content: space-between; align-items: center; }}
    .publisher-seal img {{ height: 45px; }}
    .barcode-img img {{ width: 125px; border-radius: 3px; }}

    .spine {{
      width: {spine_mm}mm;
      height: 100%;
      background: #0d0c0e;
      display: flex;
      justify-content: center;
      align-items: center;
    }}
    .spine-text {{
      writing-mode: vertical-rl;
      transform: rotate(180deg);
      font-family: {fonts['font_title']};
      font-size: 8pt;
      font-weight: 700;
      color: {pal['gold_color']};
      letter-spacing: 2px;
      white-space: nowrap;
    }}

    .front-cover {{
      width: calc({page_w_mm}mm + {bleed_mm}mm);
      height: 100%;
      position: relative;
      background: {pal['bg_color']};
      overflow: hidden;
    }}

    /* Estilos do Padrão 1 (Full-Bleed) */
    .pattern-1 .art-bg {{ position: absolute; top: 0; left: 0; width: 100%; height: 100%; object-fit: cover; }}
    .pattern-1 .overlay-top {{
      position: absolute; top: 0; left: 0; width: 100%; height: 45%;
      background: linear-gradient(to bottom, {pal['bg_color']} 0%, rgba(20,18,20,0.65) 60%, rgba(20,18,20,0) 100%);
      padding: {bleed_mm + 15}mm 15mm 0 15mm;
      text-align: center;
    }}
    .pattern-1 .front-title {{ font-family: {fonts['font_title']}; font-size: 20pt; font-weight: 900; color: {pal['gold_color']}; letter-spacing: 2px; }}
    .pattern-1 .front-subtitle-italic {{ font-style: italic; font-size: 9.5pt; color: {pal['soft_gold']}; margin-top: 8px; }}
    .pattern-1 .overlay-bottom {{
      position: absolute; bottom: 0; left: 0; width: 100%; height: 25%;
      background: linear-gradient(to top, {pal['bg_color']} 0%, rgba(20,18,20,0) 100%);
      padding-bottom: {bleed_mm + 10}mm;
      display: flex; justify-content: center; align-items: flex-end;
    }}

    /* Estilos do Padrão 2 (Split / Tarja Editorial) */
    .pattern-2 {{ display: flex; flex-direction: column; justify-content: space-between; padding: {bleed_mm + 10}mm 0 {bleed_mm + 10}mm 0; }}
    .pattern-2 .split-top-bar {{ text-align: center; padding: 0 15mm; }}
    .pattern-2 .front-title-split {{ font-family: {fonts['font_title']}; font-size: 18pt; font-weight: 900; color: {pal['gold_color']}; letter-spacing: 2px; }}
    .pattern-2 .front-subtitle-split {{ font-style: italic; font-size: 9.5pt; color: {pal['soft_gold']}; }}
    .pattern-2 .split-image-container {{ width: 100%; height: 55%; border-top: 2px solid {pal['gold_color']}; border-bottom: 2px solid {pal['gold_color']}; overflow: hidden; }}
    .pattern-2 .split-art {{ width: 100%; height: 100%; object-fit: cover; }}
    .pattern-2 .split-bottom-bar {{ text-align: center; padding: 0 15mm; }}

    /* Estilos do Padrão 3 (Moldura / Quadro Oriental) */
    .pattern-3 {{ display: flex; flex-direction: column; justify-content: space-between; padding: {bleed_mm + 12}mm 15mm {bleed_mm + 12}mm 15mm; text-align: center; }}
    .pattern-3 .framed-header {{ margin-bottom: 10px; }}
    .pattern-3 .front-title {{ font-family: {fonts['font_title']}; font-size: 18pt; font-weight: 900; color: {pal['gold_color']}; letter-spacing: 2px; }}
    .pattern-3 .front-subtitle-italic {{ font-style: italic; font-size: 9pt; color: {pal['soft_gold']}; }}
    .pattern-3 .gold-frame-wrapper {{ flex: 1; display: flex; justify-content: center; align-items: center; margin: 10px 0; }}
    .pattern-3 .gold-frame-border {{
      width: 90%; height: 95%;
      border: 3px double {pal['gold_color']};
      border-radius: 8px;
      padding: 6px;
      box-shadow: 0 6px 16px rgba(0,0,0,0.6);
      overflow: hidden;
      background: #1c191c;
    }}
    .pattern-3 .framed-art {{ width: 100%; height: 100%; object-fit: cover; border-radius: 4px; }}
    .pattern-3 .framed-footer {{ margin-top: 10px; }}

    .author-name {{ font-family: {fonts['font_tag']}; font-size: 10pt; font-weight: 700; color: #ffffff; letter-spacing: 3.5px; text-transform: uppercase; }}
  </style>
</head>
<body>
  <div class="bleed-left"></div>
  <div class="back-cover">
    <div>
      <div class="back-title">{title.upper()}</div>
      <div class="gold-divider"></div>
      <div class="synopsis-box">{synopsis}</div>
    </div>
    <div class="back-footer">
      <div class="publisher-seal">{"<img src='" + logo_uri + "'>" if logo_uri else "<span>" + publisher + "</span>"}</div>
      <div class="barcode-img"><img src="{barcode_uri}"></div>
    </div>
  </div>
  <div class="spine">
    <div class="spine-text">{title.upper()} • {author.upper()}</div>
  </div>

  <!-- Capa Frontal com Padrão Selecionado (1, 2 ou 3) -->
  {front_cover_html}
</body>
</html>
"""

    html_file = book_dir / f"capa_padrao_{p_num}.html"
    html_file.write_text(html_content, encoding="utf-8")

    out_capas_dir = Path("outputs") / book_dir.name / "capas"
    out_capas_dir.mkdir(parents=True, exist_ok=True)
    out_pdf = out_capas_dir / f"capa_padrao_{p_num}.pdf"

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

    print(f"✨ [Padrão {p_num}] Capa compilada em: {out_pdf}")
    return out_pdf
