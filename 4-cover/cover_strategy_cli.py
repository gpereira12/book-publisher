#!/usr/bin/env python3
"""Gera o diagnóstico estratégico que antecede prompts e renderização."""

import argparse
import json
from pathlib import Path
import yaml

from design_engine.color_strategy import build_color_plan
from design_engine.composition_intelligence import build_composition_plan
from design_engine.cover_spec import build_cover_spec
from design_engine.design_tokens import get_tokens
from design_engine.editorial_brief import EditorialBrief
from spine_calculator import calculate_spine_width_mm, count_pdf_pages


def main() -> None:
    parser = argparse.ArgumentParser(description="Cover: estratégia editorial e de composição")
    parser.add_argument("--book-dir", required=True)
    args = parser.parse_args()
    book_dir = Path("inputs") / args.book_dir
    config = yaml.safe_load((book_dir / "book_config.yaml").read_text(encoding="utf-8")) or {}
    interior = Path("outputs") / args.book_dir / "pdf" / f"{args.book_dir}_impressao.pdf"
    pages = count_pdf_pages(interior, strict=True)
    spine = calculate_spine_width_mm(pages, config.get("papel", "polen_soft_80g"), config.get("acabamento", "brochura"))
    spec = build_cover_spec(config, spine)
    brief = EditorialBrief.from_config(config)
    tokens = get_tokens(config)
    color_plan = build_color_plan(config, tokens["palette"])
    assets = book_dir / "assets"
    has_image = (assets / "capa.jpg").exists() or (assets / "capa.png").exists()
    composition = build_composition_plan(config, brief, spec, has_image)
    report = {
        "editorial_brief": brief.to_dict(),
        "color_plan": color_plan.to_dict(),
        "composition_plan": composition.to_dict(),
        "geometry": spec.to_dict(),
    }
    output = Path("outputs") / args.book_dir / "capas" / "estrategia_capa.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"🧭 Estratégia de capa: {output}")
    print(f"   Brief: {brief.audit()['score']}% | Padrão recomendado: {composition.recommended_pattern} | Ornamentos: nível {composition.ornament_complexity}")


if __name__ == "__main__":
    main()
