#!/usr/bin/env python3
"""
4-capas/engines/engine_b_typst.py
---------------------------------
Opção B: Motor Typst com Presets Homologados Rígidos.
Oferece layouts pré-desenhados (Minimalista Clássico vs. Ilustrado com Moldura).
"""

import os
import sys
import subprocess
from pathlib import Path
from typing import Dict, Any
import yaml

sys.path.append(str(Path(__file__).parent.parent))
from barcode_generator import generate_ean13_svg


def generate_typst_preset_cover(config: Dict[str, Any], spine_mm: float, book_dir: Path, preset: str = "b1_minimalist") -> Path:
    title = config.get("titulo", "Crônicas Chinesas para Pequenos Guerreiros")
    subtitle = config.get("subtitulo", "Histórias Milenares de Coragem, Sabedoria e Autocontrole")
    author = config.get("autor", "Gabriel Pereira")
    publisher = config.get("editora", "Editora Coala")
    isbn = config.get("isbn", "978-65-988202-7-5")
    synopsis = config.get("sinopse", "Uma coletânea inesquecível de contos chineses tradicionais.")
    cor_capa = config.get("cor_capa", "#141214")

    # Gera código de barras
    assets_dir = book_dir / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)
    barcode_file = assets_dir / "isbn_barcode.svg"
    generate_ean13_svg(isbn, barcode_file)

    template_dir = Path("src") / "templates_typst"
    try:
        barcode_rel = Path(os.path.relpath(barcode_file, template_dir)).as_posix()
    except ValueError:
        barcode_rel = str(barcode_file)

    logo_file = Path("resources") / "logos" / "coala" / "logo.svg"
    try:
        logo_rel = Path(os.path.relpath(logo_file, template_dir)).as_posix()
    except ValueError:
        logo_rel = str(logo_file)

    # Escreve código Typst com preset de Grade Rígida
    typst_code = f"""
#set page(
  width: 273mm,
  height: 200mm,
  margin: 0pt,
  fill: rgb("{cor_capa}")
)

#set text(font: "Georgia", fill: rgb("ffffff"), lang: "pt")

#let gold = rgb("d4af37")

#box(width: 100%, height: 100%)[
  #stack(dir: ltr,
    // 1. Sangria Esquerda
    rect(width: 10mm, height: 100%, fill: rgb("{cor_capa}")),

    // 2. Contracapa Minimalista Homologada
    rect(width: 125mm, height: 100%, fill: rgb("141214"), inset: 20pt)[
      #v(2cm)
      #align(center)[
        #text(size: 14pt, weight: "bold", fill: gold, tracking: 1.5pt)[CRÔNICAS CHINESAS]
        #v(3pt)
        #text(size: 8.5pt, tracking: 2pt, fill: rgb("cccccc"))[PARA PEQUENOS GUERREIROS]
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
          #block(width: 160mm)[
            #align(center)[
              #text(size: 7.5pt, weight: "bold", fill: gold, tracking: 1pt)[CRÔNICAS CHINESAS • {author.upper()}]
            ]
          ]
        ]
      ]
    ],

    // 4. Capa Frontal - Preset B1 Minimalista Homologado
    rect(width: 135mm, height: 100%, fill: rgb("141214"), inset: 25pt)[
      #v(3cm)
      #align(center)[
        #rect(stroke: 1.5pt + gold, radius: 4pt, inset: 20pt)[
          #v(0.5cm)
          #text(size: 22pt, weight: "bold", fill: gold, tracking: 1.5pt)[CRÔNICAS CHINESAS]
          #v(8pt)
          #text(size: 10pt, weight: "bold", fill: rgb("ffffff"), tracking: 2.5pt)[PARA PEQUENOS GUERREIROS]
          #v(10pt)
          #line(length: 50pt, stroke: 1pt + gold)
          #v(10pt)
          #text(size: 9pt, style: "italic", fill: rgb("f0e6d2"))[{subtitle}]
          #v(0.5cm)
        ]

        #v(3.5cm)
        #text(size: 11pt, weight: "bold", tracking: 2.5pt)[{author.upper()}]
      ]
    ]
  )
]
"""

    typ_file = book_dir / "capa_opcao_b.typ"
    typ_file.write_text(typst_code, encoding="utf-8")

    out_capas_dir = Path("outputs") / book_dir.name / "capas"
    out_capas_dir.mkdir(parents=True, exist_ok=True)
    out_pdf = out_capas_dir / "capa_opcao_b_typst.pdf"

    cmd = ["typst", "compile", "--root", str(Path.cwd().resolve()), str(typ_file), str(out_pdf)]
    subprocess.run(cmd, check=True)
    print(f"✨ [Opção B Typst Presets] Capa compilada em: {out_pdf}")
    return out_pdf


if __name__ == "__main__":
    b_dir = Path("inputs") / "cronicas_chinesas_para_pequenos_guerreiros"
    cfg = yaml.safe_load((b_dir / "book_config.yaml").read_text(encoding="utf-8"))
    generate_typst_preset_cover(cfg, 3.0, b_dir)
