"""
4-cover/design_engine/title_lettering.py
-------------------------------------------
Letreiro de título customizado por livro (Frente 3 do Cover v2).
Dois modos, nenhum deles uma "fonte reutilizável":
- "imagem": prompt (via prompt_engine) para gerar externamente um logotipo em
  assets/titulo_lettering.png (manual até termos uma API de imagem integrada).
- "vetorial": tratamento tipográfico decorado (fonte do gênero + cor + leve
  contorno) via SVG — não é hand-lettering orgânico de verdade, é decoração.
"""

from pathlib import Path
from typing import Dict, Any, Optional
from html import escape

from design_engine.prompt_engine import build_cover_prompt


LETTERING_STYLES = ("imperial_ruyi", "han_pincel", "pincel_celestial", "selo_monumental")


def _balanced_title_lines(title: str, max_lines: int = 3) -> list[str]:
    words = title.upper().split()
    if not words:
        return [""]
    desired = 1 if len(title) <= 24 else 2 if len(title) <= 52 else max_lines
    lines: list[list[str]] = [[]]
    target = max(1, (sum(len(item) for item in words) + len(words) - 1) // desired)
    for word in words:
        current_length = len(" ".join(lines[-1]))
        remaining_words = len(words) - sum(len(line) for line in lines)
        remaining_lines = desired - len(lines)
        should_break = (
            len(lines) < desired
            and lines[-1]
            and current_length + len(word) + 1 > target
            and remaining_words >= remaining_lines
        )
        if should_break:
            lines.append([])
        lines[-1].append(word)
    return [" ".join(line) for line in lines if line]


def _title_roles(title: str) -> tuple[str, str, str]:
    """Separa contexto, ponte e palavra de impacto preservando a ordem."""
    words = title.upper().split()
    if len(words) >= 5:
        return " ".join(words[:2]), " ".join(words[2:-1]), words[-1]
    lines = _balanced_title_lines(title)
    if len(lines) == 1:
        return "", "", lines[0]
    if len(lines) == 2:
        return lines[0], "", lines[1]
    return lines[0], lines[1], " ".join(lines[2:])


def render_lettering_variant(title: str, style: str, pal: Dict[str, Any], fonts: Dict[str, Any]) -> str:
    """Cria um lockup editorial exclusivo; continua vetorial e editável."""
    line_one, line_two, hero = (escape(item) for item in _title_roles(title))
    accent = escape(str(pal.get("gold_color", "#d4af37")), quote=True)
    light = escape(str(pal.get("soft_gold", "#f0e6d2")), quote=True)
    title_font = escape(str(fonts["font_title"]), quote=True)
    body_font = escape(str(fonts.get("font_body", fonts["font_title"])), quote=True)
    style = style if style in LETTERING_STYLES else "imperial_ruyi"

    common_defs = f'''<defs>
    <linearGradient id="lettering-gold" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="{light}"/><stop offset="0.48" stop-color="{accent}"/><stop offset="1" stop-color="{accent}" stop-opacity="0.82"/>
    </linearGradient>
  </defs>'''

    if style == "pincel_celestial":
        return f'''<svg class="title-lettering lettering-pincel" viewBox="0 0 620 180" width="100%" xmlns="http://www.w3.org/2000/svg">
  {common_defs}
  <path d="M 62,43 C 170,16 420,20 560,48" fill="none" stroke="{accent}" stroke-width="3" stroke-linecap="round" opacity="0.72"/>
  <text x="310" y="42" text-anchor="middle" font-family="{body_font}" font-size="30" font-style="italic" letter-spacing="5" fill="{light}">{line_one}</text>
  <text x="310" y="83" text-anchor="middle" font-family="{title_font}" font-size="25" letter-spacing="7" fill="{accent}">{line_two}</text>
  <text x="310" y="137" text-anchor="middle" font-family="{title_font}" font-size="55" font-weight="900" letter-spacing="2" fill="url(#lettering-gold)" stroke="#2b0813" stroke-width="1.1">{hero}</text>
  <path d="M 72,154 C 175,137 238,168 324,151 C 406,135 477,155 561,143 C 490,169 397,157 324,169 C 224,184 151,151 72,164 Z" fill="{accent}" opacity="0.78"/>
</svg>'''

    if style == "selo_monumental":
        return f'''<svg class="title-lettering lettering-selo" viewBox="0 0 620 180" width="100%" xmlns="http://www.w3.org/2000/svg">
  {common_defs}
  <rect x="28" y="15" width="564" height="148" rx="6" fill="none" stroke="{accent}" stroke-width="2"/>
  <rect x="38" y="25" width="544" height="128" rx="3" fill="none" stroke="{accent}" stroke-width="0.8" opacity="0.7"/>
  <path d="M 38,54 H 125 M 495,54 H 582 M 38,126 H 125 M 495,126 H 582" stroke="{accent}" stroke-width="2"/>
  <text x="310" y="48" text-anchor="middle" font-family="{title_font}" font-size="29" letter-spacing="4" fill="{light}">{line_one}</text>
  <text x="310" y="82" text-anchor="middle" font-family="{body_font}" font-size="22" letter-spacing="6" fill="{accent}">{line_two}</text>
  <text x="310" y="137" text-anchor="middle" font-family="{title_font}" font-size="54" font-weight="900" letter-spacing="2" fill="url(#lettering-gold)">{hero}</text>
  <circle cx="38" cy="54" r="4" fill="{accent}"/><circle cx="582" cy="54" r="4" fill="{accent}"/>
  <circle cx="38" cy="126" r="4" fill="{accent}"/><circle cx="582" cy="126" r="4" fill="{accent}"/>
</svg>'''

    if style == "han_pincel":
        # A identidade chinesa vem da composição e dos gestos vetoriais. A
        # fonte editorial incorporada evita substituições instáveis no PDF.
        han_font = title_font
        return f'''<svg class="title-lettering lettering-han" viewBox="0 0 620 184" width="100%" xmlns="http://www.w3.org/2000/svg">
  {common_defs}
  <g id="han-crown" fill="none" stroke="{accent}" stroke-linecap="round" stroke-linejoin="round">
    <path d="M 270,14 H 298 L 310,5 L 322,14 H 350" stroke-width="1.8"/>
    <path d="M 292,18 Q 310,29 328,18" stroke-width="1" opacity="0.65"/>
  </g>
  <text x="310" y="47" text-anchor="middle" font-family="{han_font}" font-size="30" font-weight="700" letter-spacing="5.4" fill="{light}">{line_one}</text>
  <text x="310" y="82" text-anchor="middle" font-family="{body_font}" font-size="21" font-weight="600" letter-spacing="8" fill="{accent}">{line_two}</text>
  <g id="han-hero" aria-label="{hero}">
    <text x="313" y="145" text-anchor="middle" font-family="{han_font}" font-size="67" font-weight="900" letter-spacing="1.2" fill="#2b0813" stroke="#2b0813" stroke-width="2.4" paint-order="stroke fill">{hero}</text>
    <text x="310" y="141" text-anchor="middle" font-family="{han_font}" font-size="67" font-weight="900" letter-spacing="1.2" fill="url(#lettering-gold)" stroke="{light}" stroke-opacity="0.32" stroke-width="0.65" paint-order="stroke fill">{hero}</text>
  </g>
  <!-- Os gestos de pincel ficam fora da caixa da palavra; nenhum filete cruza o texto. -->
  <g id="han-brush-accents" fill="{accent}" opacity="0.9">
    <path d="M 43,132 C 58,126 75,126 96,132 C 78,134 61,138 48,145 C 52,139 50,135 43,132 Z"/>
    <path d="M 577,132 C 562,126 545,126 524,132 C 542,134 559,138 572,145 C 568,139 570,135 577,132 Z"/>
  </g>
  <g id="han-seal" transform="translate(293 158)" fill="none" stroke="{accent}" stroke-linecap="round" stroke-linejoin="round">
    <rect x="0" y="0" width="34" height="20" rx="2" stroke-width="1.5"/>
    <path d="M 7,13 Q 11,5 17,11 Q 23,5 27,13 M 9,16 H 25" stroke-width="1.4"/>
  </g>
</svg>'''

    # Imperial ruyi: curva superior, palavra-herói monumental e swashes simétricos.
    return f'''<svg class="title-lettering lettering-imperial" viewBox="0 0 620 180" width="100%" xmlns="http://www.w3.org/2000/svg">
  {common_defs}
  <path id="lettering-arc" d="M 76,50 Q 310,4 544,50" fill="none"/>
  <text font-family="{title_font}" font-size="31" letter-spacing="4.2" fill="{light}">
    <textPath href="#lettering-arc" startOffset="50%" text-anchor="middle">{line_one}</textPath>
  </text>
  <text x="310" y="86" text-anchor="middle" font-family="{body_font}" font-size="23" font-weight="600" letter-spacing="7" fill="{accent}">{line_two}</text>
  <text x="310" y="140" text-anchor="middle" font-family="{title_font}" font-size="57" font-weight="900" letter-spacing="1.5" fill="url(#lettering-gold)" stroke="#2b0813" stroke-width="0.9">{hero}</text>
  <g fill="none" stroke="{accent}" stroke-width="2.6" stroke-linecap="round">
    <path d="M 44,154 H 190 Q 211,154 211,143 Q 211,132 225,132"/>
    <path d="M 576,154 H 430 Q 409,154 409,143 Q 409,132 395,132"/>
    <path d="M 225,154 C 246,129 270,130 278,148 C 286,126 302,126 310,146 C 318,126 334,126 342,148 C 350,130 374,129 395,154"/>
  </g>
  <circle cx="44" cy="154" r="4" fill="{accent}"/><circle cx="576" cy="154" r="4" fill="{accent}"/>
</svg>'''


def build_lettering_prompt(config: Dict[str, Any], estilo_key: str) -> Dict[str, Any]:
    """Prompt especializado para um logotipo/letreiro do título, reaproveitando
    o vocabulário de estilo por gênero do prompt_engine."""
    title = config.get("titulo", "Título do Livro")
    return build_cover_prompt(
        subject=f'the words "{title}" rendered as a custom hand-lettered logotype',
        estilo_key=estilo_key,
        composition="centered_symmetry",
        negative_space_for_title=False,
        exclude_text=False,
        extra_keywords=[
            "bespoke hand lettering", "typographic illustration", "vector logotype",
            "isolated on transparent background", "no photographic elements", "no human figures",
        ],
    )


def render_vector_title(title: str, estilo_key: str, pal: Dict[str, Any], fonts: Dict[str, Any],
                         font_size_px: int = 42, lettering_style: str = "auto") -> str:
    """Fragmento SVG com o título em tipografia decorada — usado no lugar do
    <div class="front-title"> quando titulo_lettering_modo == 'vetorial'. O
    divisor/florão logo abaixo (Frente 4) já complementa o tratamento; esta
    função cuida só do bloco de texto do título."""
    if lettering_style in LETTERING_STYLES or (lettering_style == "auto" and estilo_key == "imperial_oriental"):
        chosen = "imperial_ruyi" if lettering_style == "auto" else lettering_style
        return render_lettering_variant(title, chosen, pal, fonts)

    color = pal.get("gold_color", "#d4af37")
    lines = _balanced_title_lines(title)
    longest = max(len(line) for line in lines)
    resolved_size = min(font_size_px, 42 if len(lines) == 1 else 36 if len(lines) == 2 else 31)
    est_width = max(240, int(longest * resolved_size * 0.61))
    line_height = resolved_size * 1.12
    height = int(line_height * len(lines) + resolved_size * 0.55)
    start_y = resolved_size * 0.9
    tspans = "\n".join(
        f'    <tspan x="50%" y="{start_y + index * line_height:.1f}">{escape(line)}</tspan>'
        for index, line in enumerate(lines)
    )
    font_family = escape(str(fonts["font_title"]), quote=True)
    return f"""<svg class="title-lettering" viewBox="0 0 {est_width} {height}" width="100%" height="{height}" xmlns="http://www.w3.org/2000/svg">
  <text text-anchor="middle" font-family="{font_family}" font-size="{resolved_size}" font-weight="900"
        letter-spacing="2" fill="{color}" stroke="#000000" stroke-opacity="0.35" stroke-width="0.6">
{tspans}
  </text>
</svg>"""


def resolve_title_asset(config: Dict[str, Any], book_dir: Path) -> Optional[str]:
    """Retorna file:// URI se assets/titulo_lettering.png existir (gerado
    externamente via build_lettering_prompt, modo 'imagem'); senão None."""
    if config.get("titulo_lettering_modo") != "imagem":
        return None
    asset_file = book_dir / "assets" / "titulo_lettering.png"
    return asset_file.resolve().as_uri() if asset_file.exists() else None


def resolve_title_asset_path(config: Dict[str, Any], book_dir: Path) -> Optional[Path]:
    """Equivalente a resolve_title_asset, mas retornando um Path (para o Motor
    Typst, que referencia arquivos por caminho relativo, não URI)."""
    if config.get("titulo_lettering_modo") != "imagem":
        return None
    asset_file = book_dir / "assets" / "titulo_lettering.png"
    return asset_file if asset_file.exists() else None


def save_vector_title_svg(svg_content: str, book_dir: Path) -> Path:
    """Grava o SVG do título vetorial em assets/titulo_lettering.svg —
    necessário para o Motor B (Typst), cujo image() só aceita caminho de arquivo."""
    assets_dir = book_dir / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)
    out_file = assets_dir / "titulo_lettering.svg"
    out_file.write_text(svg_content, encoding="utf-8")
    return out_file
