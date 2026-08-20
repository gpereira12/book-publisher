"""Preflight técnico da capa antes de enviá-la à gráfica."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from html import escape
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from PIL import Image

from barcode_generator import clean_digits
from design_engine.cover_spec import CoverSpec, build_cover_spec, validate_config
from design_engine.color_strategy import validate_color_plan
from design_engine.design_tokens import COLOR_PALETTES, FONT_THEMES, get_tokens
from design_engine.editorial_brief import EditorialBrief
from spine_calculator import count_pdf_pages


@dataclass
class PreflightIssue:
    severity: str
    code: str
    message: str
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PreflightReport:
    book: str
    generated_at: str
    status: str
    geometry: Dict[str, Any]
    page_count: Optional[int]
    assets: Dict[str, Any]
    issues: List[PreflightIssue]

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["summary"] = {
            "errors": sum(issue.severity == "error" for issue in self.issues),
            "warnings": sum(issue.severity == "warning" for issue in self.issues),
            "info": sum(issue.severity == "info" for issue in self.issues),
        }
        return data


def _find_cover_image(book_dir: Path) -> Optional[Path]:
    for name in ("capa.jpg", "capa.png"):
        candidate = book_dir / "assets" / name
        if candidate.exists():
            return candidate
    return None


def _image_info(path: Path, spec: CoverSpec) -> Dict[str, Any]:
    with Image.open(path) as image:
        width, height = image.size
        dpi_x = width / (spec.page_w_mm / 25.4)
        dpi_y = height / (spec.page_h_mm / 25.4)
        return {
            "path": str(path),
            "width_px": width,
            "height_px": height,
            "mode": image.mode,
            "format": image.format,
            "effective_dpi": round(min(dpi_x, dpi_y), 1),
        }


def _contrast_ratio(first: str, second: str) -> Optional[float]:
    def luminance(color: str) -> Optional[float]:
        value = color.lstrip("#")
        if len(value) != 6:
            return None
        try:
            channels = [int(value[index:index + 2], 16) / 255 for index in (0, 2, 4)]
        except ValueError:
            return None
        linear = [channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4 for channel in channels]
        return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]

    lum_a, lum_b = luminance(first), luminance(second)
    if lum_a is None or lum_b is None:
        return None
    return (max(lum_a, lum_b) + 0.05) / (min(lum_a, lum_b) + 0.05)


def run_preflight(
    config: Dict[str, Any],
    book_dir: Path,
    pdf_file: Path,
    spine_mm: float,
) -> PreflightReport:
    issues = [PreflightIssue(**item) for item in validate_config(config)]

    try:
        spec = build_cover_spec(config, spine_mm)
    except ValueError as exc:
        issues.append(PreflightIssue("error", "invalid_geometry", str(exc)))
        spec = build_cover_spec({}, max(0.0, spine_mm))

    try:
        page_count = count_pdf_pages(pdf_file, strict=True)
    except (FileNotFoundError, RuntimeError) as exc:
        page_count = None
        issues.append(PreflightIssue("error", "unreadable_interior_pdf", str(exc)))
    if page_count is not None and page_count % 2:
        issues.append(PreflightIssue(
            "warning",
            "odd_page_count",
            f"O miolo tem {page_count} páginas; confirme a página branca de fechamento e o valor usado na lombada.",
        ))

    try:
        clean_digits(str(config.get("isbn", "")))
    except ValueError as exc:
        issues.append(PreflightIssue("error", "invalid_isbn", str(exc)))

    style = str(config.get("estilo_tipografico", "")).strip().lower()
    if style and style not in FONT_THEMES:
        issues.append(PreflightIssue("error", "unknown_typographic_style", f"estilo_tipografico desconhecido: {style!r}"))
    visual_style = str(config.get("estilo_visual", "")).strip().lower()
    if visual_style and visual_style not in FONT_THEMES:
        issues.append(PreflightIssue("error", "unknown_visual_style", f"estilo_visual desconhecido: {visual_style!r}"))
    theme = str(config.get("tema", "nanquim")).strip().lower()
    if theme not in COLOR_PALETTES:
        issues.append(PreflightIssue("warning", "unknown_palette", f"Paleta {theme!r} cairá no fallback 'nanquim'"))

    palette = get_tokens(config)["palette"]
    issues.extend(PreflightIssue(**item) for item in validate_color_plan(config, palette))
    brief_audit = EditorialBrief.from_config(config).audit()
    if not brief_audit["ready_for_art_direction"]:
        issues.append(PreflightIssue(
            "info",
            "incomplete_editorial_brief",
            f"Brief editorial {brief_audit['score']}% completo; faltam: {', '.join(brief_audit['missing'])}.",
            brief_audit,
        ))
    for role in ("gold_color", "soft_gold", "text_light"):
        ratio = _contrast_ratio(str(palette.get(role, "")), str(palette.get("bg_color", "")))
        if ratio is not None and ratio < 3:
            issues.append(PreflightIssue(
                "warning",
                "low_palette_contrast",
                f"Contraste de {role} sobre bg_color é {ratio:.2f}:1; recomendado para texto grande: pelo menos 3:1.",
                {"role": role, "ratio": round(ratio, 2)},
            ))

    assets: Dict[str, Any] = {}
    assets["color_plan"] = get_tokens(config)["color_plan"]
    assets["editorial_brief"] = brief_audit
    cover_image = _find_cover_image(book_dir)
    template = str(config.get("template_capa", config.get("layout_mídias", "ilustrado_full_bleed")))
    if cover_image:
        try:
            assets["cover_image"] = _image_info(cover_image, spec)
            dpi = assets["cover_image"]["effective_dpi"]
            if dpi < 150:
                issues.append(PreflightIssue("error", "cover_image_low_resolution", f"Imagem de capa tem apenas {dpi} DPI efetivos"))
            elif dpi < 300:
                issues.append(PreflightIssue("warning", "cover_image_below_300dpi", f"Imagem de capa tem {dpi} DPI efetivos; recomendado: 300"))
        except OSError as exc:
            issues.append(PreflightIssue("error", "unreadable_cover_image", str(exc)))
    elif "ilustrado" in template:
        issues.append(PreflightIssue("error", "missing_cover_image", "Template ilustrado selecionado, mas assets/capa.jpg ou capa.png não existe"))

    logo = Path("resources") / "logos" / str(config.get("selo", "coala")).lower() / "logo.svg"
    assets["logo"] = {"path": str(logo), "exists": logo.exists()}
    if not logo.exists():
        issues.append(PreflightIssue("warning", "missing_publisher_logo", f"Logotipo não encontrado: {logo}"))

    local_fonts = config.get("fontes_locais") or {}
    assets["local_fonts"] = {}
    for role in ("title", "body", "tag"):
        if not local_fonts.get(role):
            continue
        font_file = Path(str(local_fonts[role]))
        if not font_file.is_absolute():
            book_candidate = book_dir / font_file
            font_file = book_candidate if book_candidate.exists() else Path.cwd() / font_file
        assets["local_fonts"][role] = {"path": str(font_file), "exists": font_file.exists()}
        if not font_file.exists():
            issues.append(PreflightIssue("error", "missing_local_font", f"Fonte local de {role} não encontrada: {font_file}"))

    if 0 < spec.spine_mm < 6:
        issues.append(PreflightIssue("warning", "spine_too_narrow_for_text", f"Lombada de {spec.spine_mm:.2f} mm é estreita para texto confiável"))
    if spec.safe_mm < 5:
        issues.append(PreflightIssue("warning", "small_safe_area", f"Área segura de {spec.safe_mm:.1f} mm é inferior a 5 mm"))

    issues.append(PreflightIssue(
        "warning",
        "rgb_output_pipeline",
        "O motor atual gera PDF em RGB; conversão CMYK com perfil ICC da gráfica ainda é uma etapa separada.",
    ))
    if len(local_fonts) < 3:
        issues.append(PreflightIssue(
            "info",
            "font_reproducibility",
            "O motor HTML ainda depende parcialmente de Google Fonts; forneça title/body/tag em fontes_locais para builds reprodutíveis.",
        ))

    status = "failed" if any(issue.severity == "error" for issue in issues) else "passed_with_warnings" if any(issue.severity == "warning" for issue in issues) else "passed"
    return PreflightReport(
        book=book_dir.name,
        generated_at=datetime.now(timezone.utc).isoformat(),
        status=status,
        geometry=spec.to_dict(),
        page_count=page_count,
        assets=assets,
        issues=issues,
    )


def save_preflight_report(report: PreflightReport, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "preflight.json"
    path.write_text(json.dumps(report.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def save_geometry_proof(report: PreflightReport, output_dir: Path) -> Path:
    """Gera uma prova vetorial simples com painéis, cortes e áreas seguras."""
    geometry = report.geometry
    scale = 3.0
    width = geometry["total_w_mm"] * scale
    height = geometry["total_h_mm"] * scale
    bleed = geometry["bleed_mm"] * scale
    safe = geometry["safe_mm"] * scale
    colors = {
        "bleed_left": "#fecaca", "bleed_right": "#fecaca",
        "flap_left": "#fde68a", "flap_right": "#fde68a",
        "back": "#bfdbfe", "front": "#bbf7d0", "spine": "#ddd6fe",
        "hinge_left": "#fed7aa", "hinge_right": "#fed7aa",
    }
    panels = []
    for segment in geometry["segments"]:
        x = segment["x_mm"] * scale
        w = segment["width_mm"] * scale
        name = str(segment["name"])
        panels.append(
            f'<rect x="{x}" y="0" width="{w}" height="{height}" fill="{colors.get(name, "#e5e7eb")}" stroke="#334155" stroke-width="1"/>'
            f'<text x="{x + w / 2}" y="18" text-anchor="middle" font-size="10" fill="#111827">{escape(name)}</text>'
        )
        if name in {"front", "back"} and w > 2 * safe and height > 2 * (bleed + safe):
            panels.append(
                f'<rect x="{x + safe}" y="{bleed + safe}" width="{w - 2 * safe}" height="{height - 2 * (bleed + safe)}" '
                'fill="none" stroke="#dc2626" stroke-width="1" stroke-dasharray="5 4"/>'
            )
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
<rect width="100%" height="100%" fill="#ffffff"/>
{''.join(panels)}
</svg>'''
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "prova_geometria.svg"
    path.write_text(svg, encoding="utf-8")
    return path
