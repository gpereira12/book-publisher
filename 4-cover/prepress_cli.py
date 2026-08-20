#!/usr/bin/env python3
"""Audita um PDF de capa para fechamento gráfico."""

import argparse
from pathlib import Path
import yaml

from design_engine.composition_intelligence import build_composition_plan
from design_engine.cover_spec import build_cover_spec
from design_engine.editorial_brief import EditorialBrief
from design_engine.prepress import inspect_print_pdf, save_prepress_report
from spine_calculator import calculate_spine_width_mm, count_pdf_pages


def main() -> None:
    parser = argparse.ArgumentParser(description="Cover: relatório de prepress")
    parser.add_argument("--book-dir", required=True)
    parser.add_argument("--cover-pdf", type=Path)
    args = parser.parse_args()
    book_dir = Path("inputs") / args.book_dir
    config = yaml.safe_load((book_dir / "book_config.yaml").read_text(encoding="utf-8")) or {}
    interior = Path("outputs") / args.book_dir / "pdf" / f"{args.book_dir}_impressao.pdf"
    pages = count_pdf_pages(interior, strict=True)
    spine = calculate_spine_width_mm(pages, config.get("papel", "polen_soft_80g"), config.get("acabamento", "brochura"))
    spec = build_cover_spec(config, spine)
    assets = book_dir / "assets"
    plan = build_composition_plan(config, EditorialBrief.from_config(config), spec, (assets / "capa.jpg").exists() or (assets / "capa.png").exists())
    pdf = args.cover_pdf or Path("outputs") / args.book_dir / "capas" / f"capa_padrao_{plan.recommended_pattern}.pdf"
    report = inspect_print_pdf(pdf, spec, config)
    output = save_prepress_report(report, Path("outputs") / args.book_dir / "capas" / "prepress.json")
    print(f"🖨️  Prepress: {report['status']} — {output}")
    for check in report["checks"]:
        print(f"  - {check['severity'].upper()} [{check['code']}] {check['message']}")


if __name__ == "__main__":
    main()
