"""
4-capas/design_engine/layout_patterns/pattern_1_full_bleed.py
--------------------------------------------------------------
Padrão 1: Full-Bleed (Imagem Inteira com Gradiente Suave de Fusão).
"""

def render_pattern_1(title: str, subtitle: str, author: str, cover_img_uri: str, pal: dict, fonts: dict, bleed_mm: float) -> str:
    return f"""
    <div class="front-cover pattern-1">
      {"<img class='art-bg' src='" + cover_img_uri + "'>" if cover_img_uri else ""}
      <div class="overlay-top">
        <div class="front-title">{title.upper()}</div>
        <div class="gold-divider"></div>
        <div class="front-subtitle-italic">{subtitle}</div>
      </div>
      <div class="overlay-bottom">
        <div class="author-name">{author.upper()}</div>
      </div>
    </div>
    """
