"""
4-cover/design_engine/engine_html.py
------------------------------------
Motor A (HTML5/CSS3 + Playwright): Gerador Multipadronizado (Padrões 1, 2 e 3).
"""

from html import escape
from pathlib import Path
from typing import Dict, Any
from playwright.sync_api import sync_playwright

from barcode_generator import generate_ean13_svg
from design_engine.design_tokens import get_tokens
from design_engine.cover_spec import build_cover_spec
from design_engine.composition_intelligence import build_composition_plan
from design_engine.editorial_brief import EditorialBrief
from design_engine.svg_ornaments import render_border_band, render_divider, render_corner_flourish, render_medallion
from design_engine.title_lettering import resolve_title_asset, render_vector_title
from design_engine.layout_patterns.pattern_1_full_bleed import render_pattern_1
from design_engine.layout_patterns.pattern_2_split_tarja import render_pattern_2
from design_engine.layout_patterns.pattern_3_framed_moldura import render_pattern_3


def _shade_hex(color: str, factor: float) -> str:
    value = color.lstrip("#")
    if len(value) != 6:
        return color
    try:
        channels = [round(int(value[index:index + 2], 16) * factor) for index in (0, 2, 4)]
    except ValueError:
        return color
    return "#" + "".join(f"{max(0, min(255, channel)):02x}" for channel in channels)


def render_html_cover(config: Dict[str, Any], spine_mm: float, book_dir: Path, pattern_id: int | None = None) -> Path:
    tokens = get_tokens(config)
    pal = tokens["palette"]
    fonts = tokens["fonts"].copy()
    dark_bg = _shade_hex(str(pal["bg_color"]), 0.55)
    spine_bg = _shade_hex(str(pal["bg_color"]), 0.42)

    title_raw = str(config.get("titulo", "Título do Livro"))
    subtitle_raw = str(config.get("subtitulo", ""))
    author_raw = str(config.get("autor", "Autor"))
    publisher_raw = str(config.get("editora", "Editora Coala"))
    title = escape(title_raw)
    subtitle = escape(subtitle_raw)
    author = escape(author_raw)
    publisher = escape(publisher_raw)
    isbn = config.get("isbn", "978-65-988202-7-5")
    synopsis = escape(str(config.get("sinopse", "Sinopse do livro aqui.")))

    spec = build_cover_spec(config, spine_mm)
    page_w_mm = spec.page_w_mm
    page_h_mm = spec.page_h_mm
    bleed_mm = spec.bleed_mm
    total_w_mm = spec.total_w_mm
    total_h_mm = spec.total_h_mm

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
    brief = EditorialBrief.from_config(config)
    composition = build_composition_plan(config, brief, spec, cover_img_file.exists())
    
    selo = config.get("selo", "coala").lower()
    logo_file = Path("resources") / "logos" / selo / "logo.svg"
    logo_uri = logo_file.resolve().as_uri() if logo_file.exists() else ""

    local_font_css = []
    local_fonts = config.get("fontes_locais") or {}
    role_names = {"title": ("font_title", "CoverTitle"), "body": ("font_body", "CoverBody"), "tag": ("font_tag", "CoverTag")}
    for role, (token_name, family_name) in role_names.items():
        if not local_fonts.get(role):
            continue
        font_file = Path(str(local_fonts[role]))
        if not font_file.is_absolute():
            book_candidate = book_dir / font_file
            font_file = book_candidate if book_candidate.exists() else Path.cwd() / font_file
        if font_file.exists():
            local_font_css.append(f'@font-face {{ font-family: "{family_name}"; src: url("{font_file.resolve().as_uri()}"); font-display: block; }}')
            fonts[token_name] = f'"{family_name}"'
    google_font_links = "" if len(local_font_css) == 3 else f'''<link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?{fonts['google_fonts_url']}&display=swap" rel="stylesheet">'''

    # Elementos Gráficos Ornamentais (opt-in via ornamentos_capa)
    ornamentos_on = bool(config.get("ornamentos_capa", False))
    estilo_key = tokens["estilo_tipografico"]
    ornament_complexity = composition.ornament_complexity
    divider_svg = render_divider(estilo_key, pal, complexity=ornament_complexity) if ornamentos_on else None
    corner_svg = render_corner_flourish(estilo_key, pal, complexity=ornament_complexity) if ornamentos_on else None
    medallion_svg = render_medallion(estilo_key, pal, size_px=90, complexity=ornament_complexity) if ornamentos_on else None
    band_svg = render_border_band(estilo_key, pal, complexity=ornament_complexity) if ornamentos_on and ornament_complexity >= 3 else None
    back_divider_html = divider_svg if divider_svg else '<div class="gold-divider"></div>'
    medallion_html = f'<div class="medallion-seal">{medallion_svg}</div>' if medallion_svg else ""
    back_title_html = f'<div class="back-title">{title.upper()}</div>' if config.get("mostrar_titulo_contracapa", True) else ""

    # Letreiro de Título Customizado (Frente 3, opt-in via titulo_lettering_modo)
    titulo_modo = config.get("titulo_lettering_modo", "nenhum")
    title_asset_uri = resolve_title_asset(config, book_dir)
    title_html = None
    if title_asset_uri:
        title_html = f'<img class="front-title-img" src="{title_asset_uri}">'
    elif titulo_modo == "vetorial":
        title_html = render_vector_title(
            title_raw, estilo_key, pal, fonts,
            lettering_style=str(config.get("titulo_lettering_estilo", "auto")),
        )

    # Escolhe o Padrão de Composição (1, 2 ou 3)
    if pattern_id is not None:
        p_num = pattern_id
    elif config.get("padrao_capa") in (1, 2, 3):
        p_num = config["padrao_capa"]
    elif config.get("composicao_inteligente"):
        p_num = composition.recommended_pattern
    else:
        p_num = 1
    if p_num == 2:
        front_cover_html = render_pattern_2(title, subtitle, author, cover_img_uri, pal, fonts, bleed_mm,
                                             divider_html=divider_svg, title_html=title_html, band_html=band_svg)
    elif p_num == 3:
        front_cover_html = render_pattern_3(title, subtitle, author, cover_img_uri, pal, fonts, bleed_mm,
                                             divider_html=divider_svg, corner_svg=corner_svg, title_html=title_html)
    else:
        front_cover_html = render_pattern_1(title, subtitle, author, cover_img_uri, pal, fonts, bleed_mm,
                                             divider_html=divider_svg, title_html=title_html)

    left_flap_html = f'<div class="outer-panel flap-panel" style="width:{spec.flap_mm}mm"></div>' if spec.flap_mm else ""
    right_flap_html = f'<div class="outer-panel flap-panel" style="width:{spec.flap_mm}mm"></div>' if spec.flap_mm else ""
    left_hinge_html = f'<div class="hinge" style="width:{spec.hinge_mm}mm"></div>' if spec.hinge_mm else ""
    right_hinge_html = f'<div class="hinge" style="width:{spec.hinge_mm}mm"></div>' if spec.hinge_mm else ""
    # Sem orelha/vira, a sangria externa direita continua integrada à arte frontal.
    # Com orelha/vira, ela precisa ser um painel físico separado depois da dobra.
    front_outer_bleed_mm = bleed_mm if not spec.flap_mm else 0.0
    right_bleed_html = f'<div class="outer-panel bleed-panel" style="width:{bleed_mm}mm"></div>' if spec.flap_mm and bleed_mm else ""
    spine_text_html = (
        f'<div class="spine-text">{title.upper()} • {author.upper()}</div>'
        if spec.spine_mm >= 6 else ""
    )

    html_content = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <title>Capa Horizontal - Padrão {p_num}</title>
  {google_font_links}
  <style>
    {''.join(local_font_css)}
    @page {{ size: {total_w_mm}mm {total_h_mm}mm; margin: 0; }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      --type-base: {composition.type_base_pt}pt;
      --type-heading: {composition.type_heading_pt}pt;
      --type-display: {composition.type_display_pt}pt;
      --color-dominant: {pal['bg_color']};
      --color-secondary: {pal['secondary_color']};
      --color-accent: {pal['accent_color']};
      width: {total_w_mm}mm;
      height: {total_h_mm}mm;
      background-color: {pal['bg_color']};
      color: {pal['text_light']};
      font-family: {fonts['font_body']};
      display: flex;
      flex-direction: row;
      overflow: hidden;
    }}
    /* A sangria pertence ao arquivo de gráfica, mas precisa continuar o tom da
       borda da contracapa para não parecer uma orelha ou faixa adicional. */
    .bleed-left {{ width: {bleed_mm}mm; height: 100%; background: {dark_bg}; }}
    .outer-panel {{ height: 100%; flex: 0 0 auto; background: {pal['bg_color']}; }}
    .flap-panel {{ border-left: 0.2mm dashed rgba(255,255,255,0.22); border-right: 0.2mm dashed rgba(255,255,255,0.22); }}
    .hinge {{ height: 100%; flex: 0 0 auto; background: {spine_bg}; border-left: 0.2mm dashed rgba(255,255,255,0.28); border-right: 0.2mm dashed rgba(255,255,255,0.28); }}
    
    .back-cover {{
      width: {page_w_mm}mm;
      height: 100%;
      padding: 22mm 15mm 15mm 15mm;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      background: radial-gradient(circle at center, {pal['bg_color']} 0%, {dark_bg} 100%);
    }}
    .back-title {{ font-family: {fonts['font_title']}; color: {pal['gold_color']}; font-size: var(--type-heading); line-height: 1.08; letter-spacing: 2px; text-align: center; }}
    .gold-divider {{ width: 40px; height: 1.5px; background: {pal['gold_color']}; margin: 10px auto; }}
    .synopsis-box {{
      background: {pal['box_bg']};
      border: 1px solid {pal['box_border']};
      border-radius: 6px;
      padding: 16px;
      font-size: 10pt;
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
      background: {spine_bg};
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
      width: calc({page_w_mm}mm + {front_outer_bleed_mm}mm);
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
    .pattern-1 .front-title {{ font-family: {fonts['font_title']}; font-size: var(--type-display); font-weight: 900; color: {pal['gold_color']}; letter-spacing: 1.4px; line-height: 1.04; overflow-wrap: anywhere; }}
    .pattern-1 .front-subtitle-italic {{ font-style: italic; font-size: var(--type-base); line-height: 1.25; color: {pal['soft_gold']}; margin-top: 8px; }}
    .pattern-1 .overlay-bottom {{
      position: absolute; bottom: 0; left: 0; width: 100%; height: 25%;
      background: linear-gradient(to top, {pal['bg_color']} 0%, rgba(20,18,20,0) 100%);
      padding-bottom: {bleed_mm + 10}mm;
      display: flex; justify-content: center; align-items: flex-end;
    }}

    /* Estilos do Padrão 2 (Split / Tarja Editorial) */
    .pattern-2 {{ display: flex; flex-direction: column; justify-content: space-between; padding: {bleed_mm + 10}mm 0 {bleed_mm + 10}mm 0; background: linear-gradient(145deg, var(--color-dominant) 0 70%, var(--color-secondary) 100%); }}
    .pattern-2 .split-top-bar {{ text-align: center; padding: 0 15mm; }}
    .pattern-2 .front-title-split {{ font-family: {fonts['font_title']}; font-size: var(--type-display); font-weight: 900; color: {pal['gold_color']}; letter-spacing: 1.4px; line-height: 1.04; overflow-wrap: anywhere; }}
    .pattern-2 .front-subtitle-split {{ font-style: italic; font-size: var(--type-base); line-height: 1.25; color: {pal['soft_gold']}; }}
    .pattern-2 .split-image-container {{ position: relative; width: 100%; height: 55%; border-top: 2px solid {pal['gold_color']}; border-bottom: 2px solid {pal['gold_color']}; overflow: hidden; }}
    .pattern-2 .split-art {{ width: 100%; height: 100%; object-fit: cover; }}
    .split-ornament-band {{ position: absolute; left: 0; width: 100%; height: 14px; z-index: 2; opacity: 0.72; overflow: hidden; }}
    .split-ornament-band.band-top {{ top: 0; }}
    .split-ornament-band.band-bottom {{ bottom: 0; transform: rotate(180deg); }}
    .split-ornament-band svg {{ display: block; width: 100%; height: 100%; }}
    .pattern-2 .split-bottom-bar {{ text-align: center; padding: 0 15mm; }}

    /* Estilos do Padrão 3 (Moldura / Quadro Oriental) */
    .pattern-3 {{ display: flex; flex-direction: column; justify-content: space-between; padding: {bleed_mm + 12}mm 15mm {bleed_mm + 12}mm 15mm; text-align: center; }}
    .pattern-3 .framed-header {{ margin-bottom: 10px; }}
    .pattern-3 .front-title {{ font-family: {fonts['font_title']}; font-size: calc(var(--type-display) - 2.2pt); font-weight: 900; color: {pal['gold_color']}; letter-spacing: 1.3px; line-height: 1.04; overflow-wrap: anywhere; }}
    .pattern-3 .front-subtitle-italic {{ font-style: italic; font-size: var(--type-base); line-height: 1.25; color: {pal['soft_gold']}; }}
    .pattern-3 .gold-frame-wrapper {{ flex: 1 1 auto; min-height: 0; display: flex; justify-content: center; align-items: center; margin: 10px 0; }}
    .pattern-3 .gold-frame-border {{
      position: relative;
      width: 90%; height: 95%;
      border: 3px double {pal['gold_color']};
      border-radius: 8px;
      padding: 6px;
      box-shadow: 0 6px 16px rgba(0,0,0,0.6);
      overflow: hidden;
      background: #1c191c;
    }}
    .pattern-3 .framed-art {{ display: block; width: 100%; height: 100%; object-fit: cover; border-radius: 4px; }}
    .pattern-3 .framed-footer {{ flex: 0 0 auto; margin-top: 10px; }}

    /* Elementos Ornamentais (opt-in via ornamentos_capa) */
    .ornament-divider {{ display: block; width: min(75%, 300px); max-height: 32px; margin: 10px auto; overflow: visible; }}
    .frame-corner {{ position: absolute; width: 40px; height: 40px; z-index: 2; }}
    .frame-corner.corner-tl {{ top: 6px; left: 6px; }}
    .frame-corner.corner-tr {{ top: 6px; right: 6px; transform: rotate(90deg); }}
    .frame-corner.corner-br {{ bottom: 6px; right: 6px; transform: rotate(180deg); }}
    .frame-corner.corner-bl {{ bottom: 6px; left: 6px; transform: rotate(270deg); }}
    .medallion-seal svg {{ height: 42px; width: 42px; }}
    .front-title-img {{ max-width: 90%; height: auto; display: block; margin: 0 auto; }}
    .title-lettering {{ display: block; margin: 0 auto; max-width: 95%; }}

    .author-name {{ font-family: {fonts['font_tag']}; font-size: var(--type-base); font-weight: 700; color: #ffffff; letter-spacing: 3px; text-transform: uppercase; }}
  </style>
</head>
<body>
  <div class="bleed-left"></div>
  {left_flap_html}
  <div class="back-cover">
    <div>
      {back_title_html}
      {back_divider_html}
      <div class="synopsis-box">{synopsis}</div>
    </div>
    <div class="back-footer">
      <div class="publisher-seal">{"<img src='" + logo_uri + "'>" if logo_uri else "<span>" + publisher + "</span>"}</div>
      {medallion_html}
      <div class="barcode-img"><img src="{barcode_uri}"></div>
    </div>
  </div>
  {left_hinge_html}
  <div class="spine">
    {spine_text_html}
  </div>
  {right_hinge_html}

  <!-- Capa Frontal com Padrão Selecionado (1, 2 ou 3) -->
  {front_cover_html}
  {right_flap_html}
  {right_bleed_html}
  <script>
    async function prepareForPrint() {{
      await document.fonts.ready;
      await Promise.all([...document.images].map(img => img.complete ? Promise.resolve() : new Promise(resolve => {{ img.onload = img.onerror = resolve; }})));
      for (const node of document.querySelectorAll('.front-title, .front-title-split')) {{
        let size = parseFloat(getComputedStyle(node).fontSize);
        let guard = 0;
        while ((node.scrollWidth > node.clientWidth || node.scrollHeight > node.clientHeight) && size > 11 && guard++ < 30) {{
          size -= 0.5;
          node.style.fontSize = `${{size}}px`;
        }}
      }}
      document.documentElement.dataset.printReady = 'true';
    }}
    prepareForPrint();
  </script>
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
        page.goto(html_file.resolve().as_uri(), wait_until="networkidle")
        page.wait_for_function("document.documentElement.dataset.printReady === 'true'")
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
