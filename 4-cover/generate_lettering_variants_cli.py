#!/usr/bin/env python3
"""Exporta direções SVG de lettering para aprovação editorial."""

import argparse
from html import escape
from pathlib import Path
import yaml

from design_engine.design_tokens import get_tokens
from design_engine.title_lettering import LETTERING_STYLES, render_lettering_variant


def main() -> None:
    parser = argparse.ArgumentParser(description="Cover: variantes de lettering vetorial")
    parser.add_argument("--book-dir", required=True)
    args = parser.parse_args()
    book_dir = Path("inputs") / args.book_dir
    config = yaml.safe_load((book_dir / "book_config.yaml").read_text(encoding="utf-8")) or {}
    tokens = get_tokens(config)
    title = str(config.get("titulo", "Título do Livro"))
    output = book_dir / "assets" / "lettering" / "catalog"
    output.mkdir(parents=True, exist_ok=True)
    cards = []
    for style in LETTERING_STYLES:
        svg = render_lettering_variant(title, style, tokens["palette"], tokens["fonts"])
        filename = f"{style}.svg"
        (output / filename).write_text(svg, encoding="utf-8")
        cards.append(
            f'<article><h2>{escape(style.replace("_", " ").title())}</h2>{svg}'
            f'<p><a href="{filename}">Abrir SVG isolado</a></p></article>'
        )
    google_fonts_url = tokens["fonts"]["google_fonts_url"]
    html = f'''<!doctype html><meta charset="utf-8"><title>Lettering — {escape(title)}</title>
<link href="https://fonts.googleapis.com/css2?{google_fonts_url}&display=swap" rel="stylesheet">
<style>body{{font-family:system-ui;background:#f4efe4;color:#2b1018;padding:36px}}article{{background:#4A1525;padding:28px;margin:24px 0;border-radius:8px}}h1{{margin-bottom:28px}}h2{{color:#DBB666}}svg{{display:block;width:min(900px,100%);margin:auto}}a{{color:#f0e6d2}}</style>
<h1>Direções de lettering — {escape(title)}</h1>{''.join(cards)}'''
    catalog = output / "index.html"
    catalog.write_text(html, encoding="utf-8")
    print(f"✒️  Catálogo de lettering: {catalog}")


if __name__ == "__main__":
    main()
