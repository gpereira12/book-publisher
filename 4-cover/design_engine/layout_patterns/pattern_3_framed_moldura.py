"""
4-cover/design_engine/layout_patterns/pattern_3_framed_moldura.py
------------------------------------------------------------------
Padrão 3: Moldura / Medalhão (Ilustração emoldurada em quadro ornamental de ouro com textura).
"""

def render_pattern_3(title: str, subtitle: str, author: str, cover_img_uri: str, pal: dict, fonts: dict, bleed_mm: float) -> str:
    return f"""
    <div class="front-cover pattern-3">
      <div class="framed-header">
        <div class="front-title">{title.upper()}</div>
        <div class="gold-divider"></div>
        <div class="front-subtitle-italic">{subtitle}</div>
      </div>

      <!-- Quadro Ornamental em Ouro -->
      <div class="gold-frame-wrapper">
        <div class="gold-frame-border">
          {"<img class='framed-art' src='" + cover_img_uri + "'>" if cover_img_uri else ""}
        </div>
      </div>

      <div class="framed-footer">
        <div class="author-name">{author.upper()}</div>
      </div>
    </div>
    """
