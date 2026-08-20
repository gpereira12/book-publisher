"""Geração de padrões comparáveis e prancha de seleção editorial."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
import subprocess
from typing import Any, Dict, List

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageStat

from design_engine.cover_spec import build_cover_spec
from design_engine.composition_intelligence import build_composition_plan
from design_engine.editorial_brief import EditorialBrief
from design_engine.engine_html import render_html_cover


@dataclass
class CoverVariant:
    pattern_id: int
    label: str
    score: float
    reasons: List[str]
    pdf: str
    preview: str


def _visual_noise(image: Image.Image, region: tuple[float, float, float, float]) -> float:
    width, height = image.size
    box = (round(width * region[0]), round(height * region[1]), round(width * region[2]), round(height * region[3]))
    gray = image.convert("L").crop(box)
    edges = gray.filter(ImageFilter.FIND_EDGES)
    return min(1.0, ImageStat.Stat(edges).mean[0] / 48.0)


def score_variant(pattern_id: int, preview: Image.Image, config: Dict[str, Any]) -> tuple[float, List[str]]:
    """Heurística objetiva; não tenta substituir a escolha estética humana."""
    reasons: List[str] = []
    score = 75.0
    if pattern_id == 1:
        noise = _visual_noise(preview, (0.50, 0.0, 1.0, 0.42))
        penalty = noise * 25
        score -= penalty
        reasons.append(f"ruído visual na área do título: {noise:.2f}")
    else:
        score += 8
        reasons.append("título apoiado em área tipográfica dedicada")
    if not str(config.get("sinopse", "")).strip():
        score -= 8
        reasons.append("sinopse ausente")
    if len(str(config.get("titulo", ""))) > 55:
        score -= 4 if pattern_id == 1 else 1
        reasons.append("título longo")
    recommended = config.get("_recommended_pattern")
    if recommended == pattern_id:
        score += 10
        reasons.append("recomendado pelo plano de composição")
    return round(max(0, min(100, score)), 1), reasons


def _render_pdf_preview(pdf: Path, output_base: Path, dpi: int = 110) -> Path:
    subprocess.run(
        ["pdftoppm", "-png", "-f", "1", "-singlefile", "-r", str(dpi), str(pdf), str(output_base)],
        check=True,
        capture_output=True,
        text=True,
    )
    return output_base.with_suffix(".png")


def _trim_external_bleed(preview: Path, bleed_mm: float, dpi: int = 110) -> Path:
    """Cria preview de avaliação no corte; preserva o PNG técnico com sangria."""
    if bleed_mm <= 0:
        return preview
    bleed_px = round(bleed_mm * dpi / 25.4)
    with Image.open(preview) as image:
        if image.width <= 2 * bleed_px or image.height <= 2 * bleed_px:
            raise ValueError("Sangria maior que o preview renderizado")
        trimmed = image.crop((bleed_px, bleed_px, image.width - bleed_px, image.height - bleed_px))
        output = preview.with_name(f"{preview.stem}_aparado.png")
        trimmed.save(output)
    return output


def _contact_sheet(variants: List[CoverVariant], output: Path) -> Path:
    opened = [Image.open(item.preview).convert("RGB") for item in variants]
    thumb_w = 680
    thumbs = []
    for image in opened:
        height = round(image.height * thumb_w / image.width)
        thumbs.append(image.resize((thumb_w, height), Image.Resampling.LANCZOS))
    label_h = 86
    margin = 32
    sheet_w = thumb_w + 2 * margin
    sheet_h = sum(image.height + label_h + margin for image in thumbs) + margin
    sheet = Image.new("RGB", (sheet_w, sheet_h), "#f5f2ea")
    draw = ImageDraw.Draw(sheet)
    font_path = Path("/System/Library/Fonts/Supplemental/Arial Unicode.ttf")
    font = ImageFont.truetype(str(font_path), 22) if font_path.exists() else ImageFont.load_default(size=22)
    y = margin
    for variant, image in zip(variants, thumbs):
        sheet.paste(image, (margin, y))
        y += image.height + 14
        draw.text((margin, y), f"{variant.label}  •  score técnico {variant.score}/100", fill="#171717", font=font)
        y += label_h + margin - 14
    output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output, quality=92)
    for image in opened:
        image.close()
    return output


def generate_pattern_variants(
    config: Dict[str, Any],
    spine_mm: float,
    book_dir: Path,
    *,
    output_tag: str = "variantes",
) -> tuple[List[CoverVariant], Path]:
    spec = build_cover_spec(config, spine_mm)  # falha cedo antes de abrir três renderizações
    safe_tag = "".join(char for char in output_tag.lower() if char.isalnum() or char in {"_", "-"}).strip("_-")
    if not safe_tag:
        raise ValueError("output_tag precisa conter ao menos um caractere alfanumérico")
    output_dir = Path("outputs") / book_dir.name / "capas" / safe_tag
    output_dir.mkdir(parents=True, exist_ok=True)
    variants: List[CoverVariant] = []
    variant_config = dict(config)
    variant_config.pop("padrao_capa", None)
    assets = book_dir / "assets"
    has_image = (assets / "capa.jpg").exists() or (assets / "capa.png").exists()
    composition = build_composition_plan(config, EditorialBrief.from_config(config), spec, has_image)
    scoring_config = dict(config)
    scoring_config["_recommended_pattern"] = composition.recommended_pattern
    for pattern_id in (1, 2, 3):
        pdf = render_html_cover(variant_config, spine_mm, book_dir, pattern_id=pattern_id)
        technical_preview = _render_pdf_preview(pdf, output_dir / f"padrao_{pattern_id}")
        preview = _trim_external_bleed(technical_preview, spec.bleed_mm)
        with Image.open(preview) as image:
            score, reasons = score_variant(pattern_id, image, scoring_config)
        variants.append(CoverVariant(pattern_id, f"Padrão {pattern_id}", score, reasons, str(pdf), str(preview)))
    variants.sort(key=lambda item: item.score, reverse=True)
    report = output_dir / "ranking.json"
    report.write_text(json.dumps([asdict(item) for item in variants], indent=2, ensure_ascii=False), encoding="utf-8")
    sheet = _contact_sheet(variants, output_dir / "prancha_comparativa.jpg")
    return variants, sheet
