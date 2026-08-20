"""
4-cover/design_engine/layout_patterns/pattern_2_split_tarja.py
---------------------------------------------------------------
Padrão 2: Split / Tarja Editorial (Divisão de Tela entre Tarja Tipográfica e Imagem Ilustrada).
"""

def render_pattern_2(title: str, subtitle: str, author: str, cover_img_uri: str, pal: dict, fonts: dict, bleed_mm: float,
                      divider_html: str = None, title_html: str = None, band_html: str = None) -> str:
    divider = divider_html if divider_html else '<div class="gold-divider"></div>'
    title_block = title_html if title_html else f'<div class="front-title-split">{title.upper()}</div>'
    return f"""
    <div class="front-cover pattern-2">
      <!-- Tarja Tipográfica Superior -->
      <div class="split-top-bar">
        {title_block}
        {divider}
        <div class="front-subtitle-split">{subtitle}</div>
      </div>
      
      <!-- Container da Arte Ilustrada no Centro/Base -->
      <div class="split-image-container">
        {"<img class='split-art' src='" + cover_img_uri + "'>" if cover_img_uri else ""}
        {f'<div class="split-ornament-band band-top">{band_html}</div><div class="split-ornament-band band-bottom">{band_html}</div>' if band_html else ""}
      </div>

      <!-- Tarja do Autor no Rodapé -->
      <div class="split-bottom-bar">
        <div class="author-name">{author.upper()}</div>
      </div>
    </div>
    """
