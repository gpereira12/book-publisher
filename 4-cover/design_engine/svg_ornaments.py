"""
4-cover/design_engine/svg_ornaments.py
---------------------------------------
Elementos gráficos SVG ornamentais (divisor, florão de canto, medalhão),
gerados parametricamente por gênero — sem depender de nenhum asset externo
(mesmo espírito do barcode_generator.py: SVG hand-rolled via string).
"""

from pathlib import Path
from typing import Dict, Any

from design_engine.parametric_svg import render_complex_band, render_rosette_fragment

ORNAMENT_STYLES: Dict[str, Dict[str, str]] = {
    "imperial_oriental": {"motif": "cloud_scroll"},
    "romance_classico": {"motif": "floral_rococo"},
    "infantojuvenil": {"motif": "simple_dots"},
    "academico_solene": {"motif": "laurel"},
    "misterio_thriller": {"motif": "angular_crack"},
    "poesia_contemporanea": {"motif": "ink_brush"},
    "geek_scifi": {"motif": "circuit_line"},
}

DEFAULT_MOTIF = "cloud_scroll"


def _motif_for(estilo_key: str) -> str:
    return ORNAMENT_STYLES.get(estilo_key, ORNAMENT_STYLES["imperial_oriental"])["motif"]


# --- Ícones centrais (usados pelo divisor e pelo medalhão) --------------------

def _motif_icon_svg(motif: str, color: str, size: float) -> str:
    """Retorna um fragmento <g> centrado em (0,0) com o ícone do motivo, para
    ser composto dentro de outros elementos (divisor/medalhão). Formas
    simples e preenchidas (não curvas finas orgânicas) — em tamanho pequeno,
    traços finos e bezier complexos leem como rabisco, não como o motivo."""
    s = size
    if motif == "cloud_scroll":
        # Nuvem ruyi simétrica: leitura oriental sem recorrer a caracteres.
        return f"""<g fill="none" stroke="{color}" stroke-width="{s*0.085}" stroke-linecap="round" stroke-linejoin="round">
          <path d="M {-s*0.92},{s*0.14}
                   C {-s*0.72},{-s*0.12} {-s*0.48},{-s*0.12} {-s*0.4},{s*0.04}
                   C {-s*0.5},{-s*0.34} {-s*0.12},{-s*0.48} 0,{-s*0.18}
                   C {s*0.12},{-s*0.48} {s*0.5},{-s*0.34} {s*0.4},{s*0.04}
                   C {s*0.48},{-s*0.12} {s*0.72},{-s*0.12} {s*0.92},{s*0.14}" />
          <path d="M {-s*0.62},{s*0.22} Q {-s*0.34},{s*0.42} 0,{s*0.18} Q {s*0.34},{s*0.42} {s*0.62},{s*0.22}" />
          <circle cx="0" cy="{s*0.18}" r="{s*0.07}" fill="{color}" stroke="none" />
        </g>"""
    if motif == "floral_rococo":
        # Flor de 4 pontas (dois losangos cruzados)
        return f"""<g fill="{color}">
          <path d="M 0,{-s*0.5} L {s*0.16},0 L 0,{s*0.5} L {-s*0.16},0 Z" />
          <path d="M {-s*0.5},0 L 0,{-s*0.16} L {s*0.5},0 L 0,{s*0.16} Z" />
        </g>"""
    if motif == "simple_dots":
        return f"""<g fill="{color}">
          <circle cx="0" cy="0" r="{s*0.2}" />
          <circle cx="{-s*0.55}" cy="0" r="{s*0.12}" />
          <circle cx="{s*0.55}" cy="0" r="{s*0.12}" />
        </g>"""
    if motif == "laurel":
        # Duas folhas preenchidas (não contorno fino)
        return f"""<g fill="{color}">
          <path d="M 0,0 Q {-s*0.32},{-s*0.42} {-s*0.62},{-s*0.08} Q {-s*0.3},{s*0.04} 0,0 Z" />
          <path d="M 0,0 Q {s*0.32},{-s*0.42} {s*0.62},{-s*0.08} Q {s*0.3},{s*0.04} 0,0 Z" />
        </g>"""
    if motif == "angular_crack":
        return f"""<g stroke="{color}" fill="none" stroke-width="{s*0.14}" stroke-linejoin="miter" stroke-linecap="square">
          <path d="M {-s},{s*0.25} L {-s*0.3},{-s*0.25} L 0,{s*0.15} L {s*0.3},{-s*0.25} L {s},{s*0.25}" />
        </g>"""
    if motif == "ink_brush":
        # Pincelada única em formato de gota — silhueta simples e confiante
        return f"""<g fill="{color}">
          <path d="M 0,{-s*0.42} Q {s*0.38},{-s*0.28} {s*0.28},{s*0.12} Q {s*0.12},{s*0.44} {-s*0.16},{s*0.32} Q {-s*0.38},{s*0.16} 0,{-s*0.42} Z" />
        </g>"""
    if motif == "circuit_line":
        return f"""<g stroke="{color}" fill="{color}" stroke-width="{s*0.07}">
          <line x1="{-s}" y1="0" x2="{s}" y2="0" />
          <circle cx="{-s*0.5}" cy="0" r="{s*0.11}" />
          <circle cx="0" cy="0" r="{s*0.13}" />
          <circle cx="{s*0.5}" cy="0" r="{s*0.11}" />
        </g>"""
    return _motif_icon_svg(DEFAULT_MOTIF, color, size)


def render_divider(estilo_key: str, pal: Dict[str, Any], width_px: int = 300, complexity: int = 3) -> str:
    """Divisor horizontal ornamental — substitui a linha reta simples (.gold-divider)
    por um motivo fino característico do gênero."""
    motif = _motif_for(estilo_key)
    color = pal.get("gold_color", "#d4af37")
    h = width_px * 0.12
    icon_size = width_px * 0.09
    icon = _motif_icon_svg(motif, color, icon_size)
    if motif == "cloud_scroll":
        # Terminações recurvadas ecoam os padrões de nuvem e mobiliário ruyi.
        detail = ""
        if complexity >= 4:
            detail = f'<line x1="{-width_px*0.32}" y1="{h*0.23}" x2="{width_px*0.32}" y2="{h*0.23}" stroke="{color}" stroke-width="{h*0.025}" opacity="0.55"/>'
        return f"""<svg class="ornament-divider ornament-divider-ruyi" viewBox="{-width_px/2} {-h/2} {width_px} {h}" width="{width_px}" height="{h}" xmlns="http://www.w3.org/2000/svg">
  <g fill="none" stroke="{color}" stroke-width="{h*0.065}" stroke-linecap="round">
    <path d="M {-width_px/2},0 H {-icon_size*1.35} Q {-icon_size*1.05},0 {-icon_size*1.05},{-h*0.2}" />
    <path d="M {width_px/2},0 H {icon_size*1.35} Q {icon_size*1.05},0 {icon_size*1.05},{-h*0.2}" />
    <path d="M {-width_px/2},0 q {h*0.18},{-h*0.2} {h*0.36},0 q {-h*0.18},{h*0.2} {-h*0.36},0" />
    <path d="M {width_px/2},0 q {-h*0.18},{-h*0.2} {-h*0.36},0 q {h*0.18},{h*0.2} {h*0.36},0" />
  </g>
  {icon}
  {detail}
</svg>"""
    return f"""<svg class="ornament-divider" viewBox="{-width_px/2} {-h/2} {width_px} {h}" width="{width_px}" height="{h}" xmlns="http://www.w3.org/2000/svg">
  <line x1="{-width_px/2}" y1="0" x2="{-icon_size*1.4}" y2="0" stroke="{color}" stroke-width="{h*0.08}" />
  <line x1="{icon_size*1.4}" y1="0" x2="{width_px/2}" y2="0" stroke="{color}" stroke-width="{h*0.08}" />
  {icon}
</svg>"""


def render_corner_flourish(estilo_key: str, pal: Dict[str, Any], size_px: int = 80, complexity: int = 3) -> str:
    """Florão de canto — pensado para o canto superior-esquerdo; os outros 3 cantos
    reaproveitam o mesmo SVG rotacionado via CSS (transform: rotate(90/180/270deg))."""
    motif = _motif_for(estilo_key)
    color = pal.get("gold_color", "#d4af37")
    s = size_px
    icon = _motif_icon_svg(motif, color, s * 0.22)
    if motif == "cloud_scroll":
        detail = f'<circle cx="{s*0.31}" cy="{s*0.31}" r="{s*0.018}" fill="{color}"/>' if complexity >= 4 else ""
        return f"""<svg class="ornament-corner ornament-corner-ruyi" viewBox="0 0 {s} {s}" width="{s}" height="{s}" xmlns="http://www.w3.org/2000/svg">
  <g fill="none" stroke="{color}" stroke-width="{s*0.028}" stroke-linecap="round" stroke-linejoin="round">
    <path d="M 3,{s*0.62} V 3 H {s*0.62}" />
    <path d="M 3,{s*0.38} Q {s*0.18},{s*0.38} {s*0.18},{s*0.22} Q {s*0.18},{s*0.08} {s*0.34},{s*0.08}" />
    <path d="M {s*0.08},{s*0.34} Q {s*0.08},{s*0.18} {s*0.22},{s*0.18} Q {s*0.38},{s*0.18} {s*0.38},3" />
    <path d="M {s*0.17},{s*0.48} C {s*0.25},{s*0.34} {s*0.43},{s*0.34} {s*0.5},{s*0.48}" />
  </g>
  <circle cx="{s*0.18}" cy="{s*0.18}" r="{s*0.045}" fill="{color}" />
  {detail}
</svg>"""
    return f"""<svg class="ornament-corner" viewBox="0 0 {s} {s}" width="{s}" height="{s}" xmlns="http://www.w3.org/2000/svg">
  <path d="M 2,{s*0.4} L 2,2 L {s*0.4},2" stroke="{color}" stroke-width="{s*0.035}" fill="none" stroke-linecap="round" />
  <g transform="translate({s*0.22},{s*0.22})">{icon}</g>
</svg>"""


def render_medallion(estilo_key: str, pal: Dict[str, Any], size_px: int = 200, complexity: int = 3) -> str:
    """Medalhão/selo circular — usado hoje como reforço discreto no rodapé da
    contracapa; disponível para uso de destaque futuro (ex: uma pattern dedicada)."""
    motif = _motif_for(estilo_key)
    color = pal.get("gold_color", "#d4af37")
    s = size_px
    r_outer = s * 0.48
    r_inner = s * 0.38
    icon = _motif_icon_svg(motif, color, s * 0.22)
    if motif == "cloud_scroll":
        # Medalhão de treliça geométrica com núcleo ruyi; funciona como selo,
        # sem simular caligrafia chinesa ou usar um ideograma fora de contexto.
        rosette = f'<g transform="translate({s*0.15},{s*0.15})" opacity="0.38">{render_rosette_fragment(color, s*0.7, complexity)}</g>' if complexity >= 3 else ""
        return f"""<svg class="ornament-medallion ornament-medallion-oriental" viewBox="0 0 {s} {s}" width="{s}" height="{s}" xmlns="http://www.w3.org/2000/svg">
  <circle cx="{s/2}" cy="{s/2}" r="{r_outer}" fill="none" stroke="{color}" stroke-width="{s*0.018}" />
  <circle cx="{s/2}" cy="{s/2}" r="{r_inner}" fill="none" stroke="{color}" stroke-width="{s*0.009}" stroke-dasharray="{s*0.035} {s*0.025}" />
  {rosette}
  <rect x="{s*0.28}" y="{s*0.28}" width="{s*0.44}" height="{s*0.44}" rx="{s*0.035}" fill="none" stroke="{color}" stroke-width="{s*0.014}" transform="rotate(45 {s/2} {s/2})" />
  <g transform="translate({s/2},{s/2})">{icon}</g>
</svg>"""
    return f"""<svg class="ornament-medallion" viewBox="0 0 {s} {s}" width="{s}" height="{s}" xmlns="http://www.w3.org/2000/svg">
  <circle cx="{s/2}" cy="{s/2}" r="{r_outer}" fill="none" stroke="{color}" stroke-width="{s*0.02}" />
  <circle cx="{s/2}" cy="{s/2}" r="{r_inner}" fill="none" stroke="{color}" stroke-width="{s*0.012}" />
  <g transform="translate({s/2},{s/2})">{icon}</g>
</svg>"""


def render_border_band(estilo_key: str, pal: Dict[str, Any], width_px: int = 360, complexity: int = 3) -> str:
    """Faixa repetitiva para limites de imagem e molduras editoriais."""
    color = pal.get("gold_color", "#d4af37")
    if _motif_for(estilo_key) == "cloud_scroll":
        return render_complex_band(color, width=width_px, height=20, complexity=complexity)
    return f'''<svg class="ornament-band" viewBox="0 0 {width_px} 10" width="{width_px}" height="10" xmlns="http://www.w3.org/2000/svg">
  <line x1="0" y1="5" x2="{width_px}" y2="5" stroke="{color}" stroke-width="1.5"/>
</svg>'''


def save_ornament_svg(svg_content: str, book_dir: Path, name: str) -> Path:
    """Grava o SVG em assets/ornaments/<name>.svg — necessário para o Motor B
    (Typst), cujo image() só aceita caminho de arquivo, não SVG inline."""
    ornaments_dir = book_dir / "assets" / "ornaments"
    ornaments_dir.mkdir(parents=True, exist_ok=True)
    out_file = ornaments_dir / f"{name}.svg"
    out_file.write_text(svg_content, encoding="utf-8")
    return out_file
