"""
4-cover/design_engine/layout_patterns/pattern_1_full_bleed.py
--------------------------------------------------------------
Padrão 1: Full-Bleed (Imagem Inteira com Gradiente Suave de Fusão).
"""

def render_pattern_1(title: str, subtitle: str, author: str, cover_img_uri: str, pal: dict, fonts: dict, bleed_mm: float,
                      divider_html: str = None, title_html: str = None) -> str:
    divider = divider_html if divider_html else '<div class="gold-divider"></div>'
    title_block = title_html if title_html else f'<div class="front-title">{title.upper()}</div>'
    return f"""
    <div class="front-cover pattern-1">
      {"<img class='art-bg' src='" + cover_img_uri + "'>" if cover_img_uri else ""}
      <div class="overlay-top">
        {title_block}
        {divider}
        <div class="front-subtitle-italic">{subtitle}</div>
      </div>
      <div class="overlay-bottom">
        <div class="author-name">{author.upper()}</div>
      </div>
    </div>
    """
