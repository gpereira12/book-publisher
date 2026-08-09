"""
4-cover/design_engine/layout_patterns/pattern_2_split_tarja.py
---------------------------------------------------------------
Padrão 2: Split / Tarja Editorial (Divisão de Tela entre Tarja Tipográfica e Imagem Ilustrada).
"""

def render_pattern_2(title: str, subtitle: str, author: str, cover_img_uri: str, pal: dict, fonts: dict, bleed_mm: float) -> str:
    return f"""
    <div class="front-cover pattern-2">
      <!-- Tarja Tipográfica Superior -->
      <div class="split-top-bar">
        <div class="front-title-split">{title.upper()}</div>
        <div class="gold-divider"></div>
        <div class="front-subtitle-split">{subtitle}</div>
      </div>
      
      <!-- Container da Arte Ilustrada no Centro/Base -->
      <div class="split-image-container">
        {"<img class='split-art' src='" + cover_img_uri + "'>" if cover_img_uri else ""}
      </div>

      <!-- Tarja do Autor no Rodapé -->
      <div class="split-bottom-bar">
        <div class="author-name">{author.upper()}</div>
      </div>
    </div>
    """
