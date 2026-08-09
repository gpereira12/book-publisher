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
from design_engine.design_tokens import get_tokens


def render_typst_cover(config: Dict[str, Any], spine_mm: float, book_dir: Path) -> Path:
    tokens = get_tokens(config)
    pal = tokens["palette"]

    title = config.get("titulo", "Título do Livro")
    subtitle = config.get("subtitulo", "")
    author = config.get("autor", "Autor")
    publisher = config.get("editora", "Editora Coala")
    isbn = config.get("isbn", "978-65-988202-7-5")
    synopsis = config.get("sinopse", "Sinopse do livro aqui.")

    # Formato e dimensões
    fmt = config.get("formato", "Pocket")
    page_w_mm = 125.0 if fmt == "Pocket" else 148.0
    page_h_mm = 180.0 if fmt == "Pocket" else 210.0
    bleed_mm = 10.0 if config.get("acabamento", "brochura") == "brochura" else 0.0

    total_w_mm = (bleed_mm * 2) + (page_w_mm * 2) + spine_mm
    total_h_mm = (bleed_mm * 2) + page_h_mm

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

    typst_code = f"""
#set page(
  width: {total_w_mm}mm,
  height: {total_h_mm}mm,
  margin: 0pt,
  fill: rgb("{pal['bg_color']}")
)

#set text(font: "Georgia", fill: rgb("ffffff"), lang: "pt")
#let gold = rgb("{pal['gold_color']}")

#box(width: 100%, height: 100%)[
  #stack(dir: ltr,
    // 1. Sangria Esquerda
    rect(width: {bleed_mm}mm, height: 100%, fill: rgb("{pal['bg_color']}")),

    // 2. Contracapa Minimalista
    rect(width: {page_w_mm}mm, height: 100%, fill: rgb("{pal['bg_color']}"), inset: 20pt)[
      #v(2cm)
      #align(center)[
        #text(size: 13pt, weight: "bold", fill: gold, tracking: 1.5pt)[{title.upper()}]
        #v(0.4cm)
        #line(length: 40pt, stroke: 0.8pt + gold)
      ]

      #v(1cm)
      #rect(width: 100%, fill: rgb("1c191c"), radius: 4pt, inset: 14pt, stroke: 0.5pt + rgb("2a262a"))[
        #set par(leading: 0.7em)
        #text(size: 9.5pt, fill: rgb("e2e2e2"))[{synopsis}]
      ]

      #v(1fr)
      #grid(
        columns: (1fr, auto),
        align: (left + horizon, right + horizon),
        image("{logo_rel}", width: 65pt),
        image("{barcode_rel}", width: 105pt)
      )
    ],

    // 3. Lombada
    rect(width: {spine_mm}mm, height: 100%, fill: rgb("0e0d0f"), inset: 0pt)[
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

    // 4. Capa Frontal - Preset Tipográfico Minimalista
    rect(width: {page_w_mm + bleed_mm}mm, height: 100%, fill: rgb("{pal['bg_color']}"), inset: 25pt)[
      #v(2.5cm)
      #align(center)[
        #rect(stroke: 1.5pt + gold, radius: 4pt, inset: 20pt)[
          #v(0.5cm)
          #text(size: 20pt, weight: "bold", fill: gold, tracking: 1.5pt)[{title.upper()}]
          #v(10pt)
          #line(length: 50pt, stroke: 1pt + gold)
          #v(10pt)
          #text(size: 9pt, style: "italic", fill: rgb("f0e6d2"))[{subtitle}]
          #v(0.5cm)
        ]

        #v(3cm)
        #text(size: 11pt, weight: "bold", tracking: 2.5pt)[{author.upper()}]
      ]
    ]
  )
]
"""

    typ_file = book_dir / "capa_horizontal.typ"
    typ_file.write_text(typst_code, encoding="utf-8")

    out_capas_dir = Path("outputs") / book_dir.name / "capas"
    out_capas_dir.mkdir(parents=True, exist_ok=True)
    out_pdf = out_capas_dir / "capa_horizontal_grafica.pdf"

    cmd = ["typst", "compile", "--root", str(Path.cwd().resolve()), str(typ_file), str(out_pdf)]
    subprocess.run(cmd, check=True)
    print(f"✨ [Cover - Motor B Typst Minimalista] Capa gerada em: {out_pdf}")
    return out_pdf
