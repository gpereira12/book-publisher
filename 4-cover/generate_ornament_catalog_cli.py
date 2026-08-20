#!/usr/bin/env python3
"""Exporta um catálogo SVG nos cinco níveis de complexidade ornamental."""

import argparse
from html import escape
from pathlib import Path
import yaml

from design_engine.design_tokens import get_tokens
from design_engine.parametric_svg import render_complex_band, render_complex_rosette
from design_engine.svg_ornaments import render_corner_flourish, render_divider, render_medallion


def main() -> None:
    parser = argparse.ArgumentParser(description="Cover: catálogo de ornamentos SVG")
    parser.add_argument("--book-dir", required=True)
    args = parser.parse_args()
    book_dir = Path("inputs") / args.book_dir
    config = yaml.safe_load((book_dir / "book_config.yaml").read_text(encoding="utf-8")) or {}
    tokens = get_tokens(config)
    style = tokens["estilo_tipografico"]
    palette = tokens["palette"]
    color = palette["gold_color"]
    output = book_dir / "assets" / "ornaments" / "catalog"
    output.mkdir(parents=True, exist_ok=True)
    cards = []
    for level in range(1, 6):
        items = {
            "divider": render_divider(style, palette, complexity=level),
            "corner": render_corner_flourish(style, palette, size_px=100, complexity=level),
            "medallion": render_medallion(style, palette, size_px=180, complexity=level),
            "band": render_complex_band(color, complexity=level),
            "rosette": render_complex_rosette(color, complexity=level),
        }
        for name, svg in items.items():
            (output / f"nivel_{level}_{name}.svg").write_text(svg, encoding="utf-8")
        cards.append(
            f'<section><h2>Nível {level}</h2>'
            + "".join(f'<figure><img src="nivel_{level}_{name}.svg"><figcaption>{escape(name)}</figcaption></figure>' for name in items)
            + "</section>"
        )
    html = f'''<!doctype html><meta charset="utf-8"><title>Catálogo ornamental — {escape(style)}</title>
<style>body{{font-family:system-ui;background:#f5f1e8;color:#211;padding:32px}}section{{display:grid;grid-template-columns:repeat(5,1fr);gap:20px;align-items:center;border-bottom:1px solid #bbb;padding:20px 0}}h2{{grid-column:1/-1}}figure{{margin:0;text-align:center}}img{{max-width:100%;max-height:150px}}figcaption{{margin-top:8px}}</style>
<h1>Catálogo ornamental — {escape(style)}</h1>{''.join(cards)}'''
    catalog = output / "index.html"
    catalog.write_text(html, encoding="utf-8")
    print(f"🏮 Catálogo SVG: {catalog}")


if __name__ == "__main__":
    main()
