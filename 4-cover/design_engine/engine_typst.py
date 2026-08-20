"""
4-cover/design_engine/engine_typst.py
-------------------------------------
Motor B (Typst Presets): Usado para capas minimalistas, acadêmicas e tipográficas sem imagens.
"""

import os
import sys
import subprocess
from pathlib import Path
from typing import Dict, Any

from barcode_generator import generate_ean13_svg
from design_engine.cover_spec import build_cover_spec
from design_engine.composition_intelligence import build_composition_plan
from design_engine.design_tokens import get_tokens
from design_engine.editorial_brief import EditorialBrief
from design_engine.title_lettering import resolve_title_asset_path, render_vector_title, save_vector_title_svg


def _typst_escape(value: Any) -> str:
    """Escapa conteúdo editorial inserido em content blocks do Typst."""
    text = str(value)
    for char in ("\\", "#", "[", "]", "<", ">"):
        text = text.replace(char, "\\" + char)
    return text


def _typst_string_escape(value: Any) -> str:
    return str(value).replace("\\", "\\\\").replace('"', '\\"')


def _shade_hex(color: str, factor: float) -> str:
    value = color.lstrip("#")
    if len(value) != 6:
        return color
    try:
        channels = [round(int(value[index:index + 2], 16) * factor) for index in (0, 2, 4)]
    except ValueError:
        return color
    return "#" + "".join(f"{max(0, min(255, channel)):02x}" for channel in channels)


def render_typst_cover(config: Dict[str, Any], spine_mm: float, book_dir: Path) -> Path:
    tokens = get_tokens(config)
    pal = tokens["palette"]
    fonts = tokens["fonts"]
    estilo_key = tokens["estilo_tipografico"]
    spine_bg = _shade_hex(str(pal["bg_color"]), 0.42)

    title_raw = str(config.get("titulo", "Título do Livro"))
    subtitle_raw = str(config.get("subtitulo", ""))
    author_raw = str(config.get("autor", "Autor"))
    title = _typst_escape(title_raw)
    subtitle = _typst_escape(subtitle_raw)
    author = _typst_escape(author_raw)
    isbn = config.get("isbn", "978-65-988202-7-5")
    synopsis = _typst_escape(config.get("sinopse", "Sinopse do livro aqui."))

    spec = build_cover_spec(config, spine_mm)
    composition = build_composition_plan(config, EditorialBrief.from_config(config), spec, has_image=False)
    page_w_mm = spec.page_w_mm
    page_h_mm = spec.page_h_mm
    bleed_mm = spec.bleed_mm
    total_w_mm = spec.total_w_mm
    total_h_mm = spec.total_h_mm

    # Gera código de barras EAN-13
    assets_dir = book_dir / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)
    barcode_file = assets_dir / "isbn_barcode.svg"
    generate_ean13_svg(isbn, barcode_file)

    # Caminhos relativos ao próprio arquivo .typ gerado (escrito em book_dir)
    try:
        barcode_rel = Path(os.path.relpath(barcode_file, book_dir)).as_posix()
    except ValueError:
        barcode_rel = str(barcode_file)

    selo = config.get("selo", "coala").lower()
    logo_file = Path("resources") / "logos" / selo / "logo.svg"
    try:
        logo_rel = Path(os.path.relpath(logo_file, book_dir)).as_posix()
    except ValueError:
        logo_rel = str(logo_file)

    # Letreiro de Título Customizado (Frente 3, opt-in via titulo_lettering_modo)
    titulo_modo = config.get("titulo_lettering_modo", "nenhum")
    title_asset_path = resolve_title_asset_path(config, book_dir)
    if title_asset_path is None and titulo_modo == "vetorial":
        title_asset_path = save_vector_title_svg(
            render_vector_title(
                title_raw, estilo_key, pal, fonts,
                lettering_style=str(config.get("titulo_lettering_estilo", "auto")),
            ),
            book_dir,
        )

    if title_asset_path:
        try:
            title_rel = Path(os.path.relpath(title_asset_path, book_dir)).as_posix()
        except ValueError:
            title_rel = str(title_asset_path)
        front_title_typst = f'#image("{title_rel}", width: 70%)'
    else:
        front_title_typst = f'#text(size: {composition.type_display_pt}pt, weight: "bold", fill: gold, tracking: 1.5pt)[{title.upper()}]'

    left_flap_typst = f'rect(width: {spec.flap_mm}mm, height: 100%, fill: rgb("{pal["bg_color"]}")),' if spec.flap_mm else ""
    right_flap_typst = f'rect(width: {spec.flap_mm}mm, height: 100%, fill: rgb("{pal["bg_color"]}")),' if spec.flap_mm else ""
    left_hinge_typst = f'rect(width: {spec.hinge_mm}mm, height: 100%, fill: rgb("{spine_bg}")),' if spec.hinge_mm else ""
    right_hinge_typst = f'rect(width: {spec.hinge_mm}mm, height: 100%, fill: rgb("{spine_bg}")),' if spec.hinge_mm else ""
    front_outer_bleed_mm = bleed_mm if not spec.flap_mm else 0.0
    right_bleed_typst = f'rect(width: {bleed_mm}mm, height: 100%, fill: rgb("{pal["bg_color"]}")),' if spec.flap_mm and bleed_mm else ""
    typst_font = _typst_string_escape(config.get("font_typst", "Georgia"))
    back_title_typst = (
        f'#text(size: {composition.type_heading_pt}pt, weight: "bold", fill: gold, tracking: 1.5pt)[{title.upper()}]'
        if config.get("mostrar_titulo_contracapa", True) else ""
    )

    typst_code = f"""
#set page(
  width: {total_w_mm}mm,
  height: {total_h_mm}mm,
  margin: 0pt,
  fill: rgb("{pal['bg_color']}")
)

#set text(font: "{typst_font}", fill: rgb("ffffff"), lang: "pt")
#let gold = rgb("{pal['gold_color']}")

#box(width: 100%, height: 100%)[
  #stack(dir: ltr,
    // 1. Sangria Esquerda
    rect(width: {bleed_mm}mm, height: 100%, fill: rgb("{pal['bg_color']}")),
    {left_flap_typst}

    // 2. Contracapa Minimalista
    rect(width: {page_w_mm}mm, height: 100%, fill: rgb("{pal['bg_color']}"), inset: 20pt)[
      #v(2cm)
      #align(center)[
        {back_title_typst}
        #v(0.4cm)
        #line(length: 40pt, stroke: 0.8pt + gold)
      ]

      #v(1cm)
      #rect(width: 100%, fill: rgb("1c191c"), radius: 4pt, inset: 14pt, stroke: 0.5pt + rgb("2a262a"))[
        #set par(leading: 0.7em)
        #text(size: {composition.type_base_pt}pt, fill: rgb("e2e2e2"))[{synopsis}]
      ]

      #v(1fr)
      #grid(
        columns: (1fr, auto),
        align: (left + horizon, right + horizon),
        image("{logo_rel}", width: 65pt),
        image("{barcode_rel}", width: 105pt)
      )
    ],

    {left_hinge_typst}

    // 3. Lombada
    rect(width: {spec.spine_mm}mm, height: 100%, fill: rgb("{spine_bg}"), inset: 0pt)[
      #place(center + horizon)[
        #rotate(-90deg)[
          #block(width: {page_h_mm - 20}mm)[
            #align(center)[
              #text(size: 7.5pt, weight: "bold", fill: gold, tracking: 1pt)[{title.upper()} • {author.upper()}]
            ]
          ]
        ]
      ]
    ],
    {right_hinge_typst}

    // 4. Capa Frontal - Preset Tipográfico Minimalista
    rect(width: {page_w_mm + front_outer_bleed_mm}mm, height: 100%, fill: rgb("{pal['bg_color']}"), inset: 25pt)[
      #v(2.5cm)
      #align(center)[
        #rect(stroke: 1.5pt + gold, radius: 4pt, inset: 20pt)[
          #v(0.5cm)
          {front_title_typst}
          #v(10pt)
          #line(length: 50pt, stroke: 1pt + gold)
          #v(10pt)
          #text(size: {composition.type_base_pt}pt, style: "italic", fill: rgb("f0e6d2"))[{subtitle}]
          #v(0.5cm)
        ]

        #v(3cm)
        #text(size: {composition.type_base_pt}pt, weight: "bold", tracking: 2.5pt)[{author.upper()}]
      ]
    ],
    {right_flap_typst}
    {right_bleed_typst}
  )
]
"""

    typ_file = book_dir / "capa_horizontal.typ"
    typ_file.write_text(typst_code, encoding="utf-8")

    out_capas_dir = Path("outputs") / book_dir.name / "capas"
    out_capas_dir.mkdir(parents=True, exist_ok=True)
    out_pdf = out_capas_dir / "capa_horizontal_grafica.pdf"

    cmd = ["typst", "compile", "--root", str(Path.cwd().resolve())]
    font_dirs = set()
    for value in (config.get("fontes_locais") or {}).values():
        font_file = Path(str(value))
        if not font_file.is_absolute():
            book_candidate = book_dir / font_file
            font_file = book_candidate if book_candidate.exists() else Path.cwd() / font_file
        if font_file.exists():
            font_dirs.add(str(font_file.resolve().parent))
    for font_dir in sorted(font_dirs):
        cmd.extend(["--font-path", font_dir])
    cmd.extend([str(typ_file), str(out_pdf)])
    subprocess.run(cmd, check=True)
    print(f"✨ [Cover - Motor B Typst Minimalista] Capa gerada em: {out_pdf}")
    return out_pdf
