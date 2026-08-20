"""
4-cover/design_engine/layout_patterns/pattern_3_framed_moldura.py
------------------------------------------------------------------
Padrão 3: Moldura / Medalhão (Ilustração emoldurada em quadro ornamental de ouro com textura).
"""

def render_pattern_3(title: str, subtitle: str, author: str, cover_img_uri: str, pal: dict, fonts: dict, bleed_mm: float,
                      divider_html: str = None, corner_svg: str = None, title_html: str = None) -> str:
    divider = divider_html if divider_html else '<div class="gold-divider"></div>'
    title_block = title_html if title_html else f'<div class="front-title">{title.upper()}</div>'
    corners = ""
    if corner_svg:
        corners = f"""
          <div class="frame-corner corner-tl">{corner_svg}</div>
          <div class="frame-corner corner-tr">{corner_svg}</div>
          <div class="frame-corner corner-bl">{corner_svg}</div>
          <div class="frame-corner corner-br">{corner_svg}</div>
        """
    return f"""
    <div class="front-cover pattern-3">
      <div class="framed-header">
        {title_block}
        {divider}
        <div class="front-subtitle-italic">{subtitle}</div>
      </div>

      <!-- Quadro Ornamental em Ouro -->
      <div class="gold-frame-wrapper">
        <div class="gold-frame-border">
          {"<img class='framed-art' src='" + cover_img_uri + "'>" if cover_img_uri else ""}
          {corners}
        </div>
      </div>

      <div class="framed-footer">
        <div class="author-name">{author.upper()}</div>
      </div>
    </div>
    """
