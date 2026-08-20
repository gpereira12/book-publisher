#!/usr/bin/env python3
"""Gera os três padrões, ranking técnico e prancha comparativa."""

import argparse
from pathlib import Path
import yaml

from design_engine.variant_engine import generate_pattern_variants
from spine_calculator import calculate_spine_width_mm, count_pdf_pages


def main() -> None:
    parser = argparse.ArgumentParser(description="Cover: gerador de variantes de composição")
    parser.add_argument("--book-dir", required=True)
    parser.add_argument("--color", help="Sobrescreve cor_capa em HEX somente nesta prancha")
    parser.add_argument("--theme", help="Sobrescreve tema somente nesta prancha")
    parser.add_argument("--output-tag", default="variantes", help="Subpasta em outputs/<livro>/capas/")
    args = parser.parse_args()
    book_dir = Path("inputs") / args.book_dir
    config = yaml.safe_load((book_dir / "book_config.yaml").read_text(encoding="utf-8")) or {}
    if args.color:
        config["cor_capa"] = args.color
    if args.theme:
        config["tema"] = args.theme
    interior = Path("outputs") / args.book_dir / "pdf" / f"{args.book_dir}_impressao.pdf"
    pages = count_pdf_pages(interior, strict=True)
    spine = calculate_spine_width_mm(pages, config.get("papel", "polen_soft_80g"), config.get("acabamento", "brochura"))
    variants, sheet = generate_pattern_variants(config, spine, book_dir, output_tag=args.output_tag)
    print(f"🧭 Prancha comparativa: {sheet}")
    for variant in variants:
        print(f"  {variant.label}: {variant.score}/100 — {'; '.join(variant.reasons)}")


if __name__ == "__main__":
    main()
