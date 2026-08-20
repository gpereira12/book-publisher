"""Inspeção de acabamento gráfico do PDF; não substitui a prova da gráfica."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
import re
from typing import Any, Dict, List

try:
    from pypdf import PdfReader
except ImportError:  # compatibilidade com instalações legadas do projeto
    from PyPDF2 import PdfReader

from design_engine.cover_spec import CoverSpec


@dataclass
class PrepressCheck:
    severity: str
    code: str
    message: str


def _page_stream(page: Any) -> bytes:
    contents = page.get_contents()
    if contents is None:
        return b""
    if isinstance(contents, list):
        return b"\n".join(item.get_data() for item in contents)
    return contents.get_data()


def _font_embedding(page: Any) -> Dict[str, bool]:
    resources = page.get("/Resources") or {}
    fonts = resources.get("/Font") or {}
    result: Dict[str, bool] = {}
    for name, reference in fonts.items():
        font = reference.get_object()
        if font.get("/Subtype") == "/Type3":
            # Type 3 incorpora os glifos em /CharProcs; não possui FontFile.
            result[str(name)] = bool(font.get("/CharProcs"))
            continue
        descriptor_ref = font.get("/FontDescriptor")
        if descriptor_ref is None and font.get("/DescendantFonts"):
            descendant = font["/DescendantFonts"][0].get_object()
            descriptor_ref = descendant.get("/FontDescriptor")
        descriptor = descriptor_ref.get_object() if descriptor_ref else {}
        result[str(name)] = any(key in descriptor for key in ("/FontFile", "/FontFile2", "/FontFile3"))
    return result


def inspect_print_pdf(pdf_path: Path, spec: CoverSpec, config: Dict[str, Any]) -> Dict[str, Any]:
    checks: List[PrepressCheck] = []
    if not pdf_path.exists():
        return {"status": "failed", "pdf": str(pdf_path), "checks": [asdict(PrepressCheck("error", "missing_pdf", "PDF de capa não encontrado"))]}

    reader = PdfReader(str(pdf_path))
    if len(reader.pages) != 1:
        checks.append(PrepressCheck("error", "cover_page_count", f"Capa aberta deve ter uma página; encontrado: {len(reader.pages)}"))
    page = reader.pages[0]
    width_mm = float(page.mediabox.width) * 25.4 / 72
    height_mm = float(page.mediabox.height) * 25.4 / 72
    if abs(width_mm - spec.total_w_mm) > 0.5 or abs(height_mm - spec.total_h_mm) > 0.5:
        checks.append(PrepressCheck("error", "wrong_media_box", f"MediaBox {width_mm:.2f}×{height_mm:.2f} mm; esperado {spec.total_w_mm:.2f}×{spec.total_h_mm:.2f} mm"))
    else:
        checks.append(PrepressCheck("info", "media_box_ok", f"Dimensão confirmada: {width_mm:.2f}×{height_mm:.2f} mm"))

    root = reader.trailer["/Root"]
    if "/OutputIntents" not in root:
        checks.append(PrepressCheck("warning", "missing_output_intent", "PDF não possui OutputIntent ICC; ainda não é um fechamento PDF/X controlado"))
    if "/TrimBox" not in page:
        checks.append(PrepressCheck("warning", "missing_trim_box", "PDF não declara TrimBox separado do MediaBox"))
    if "/BleedBox" not in page:
        checks.append(PrepressCheck("warning", "missing_bleed_box", "PDF não declara BleedBox"))

    fonts = _font_embedding(page)
    missing_fonts = [name for name, embedded in fonts.items() if not embedded]
    if missing_fonts:
        checks.append(PrepressCheck("error", "fonts_not_embedded", f"Fontes não incorporadas: {', '.join(missing_fonts)}"))
    elif fonts:
        checks.append(PrepressCheck("info", "fonts_embedded", f"Fontes incorporadas: {len(fonts)}"))

    stream = _page_stream(page)
    rgb_markers = bool(re.search(rb"/DeviceRGB|(?:^|\s)[0-9.]+\s+[0-9.]+\s+[0-9.]+\s+(?:rg|RG)(?:\s|$)", stream))
    cmyk_markers = bool(re.search(rb"/DeviceCMYK|(?:^|\s)[0-9.]+\s+[0-9.]+\s+[0-9.]+\s+[0-9.]+\s+(?:k|K)(?:\s|$)", stream))
    if rgb_markers and not cmyk_markers:
        checks.append(PrepressCheck("warning", "rgb_content", "Conteúdo RGB detectado e nenhum operador CMYK explícito encontrado"))

    profile = config.get("perfil_icc_saida")
    if not profile:
        checks.append(PrepressCheck("warning", "missing_icc_profile", "perfil_icc_saida não foi configurado; solicite o perfil à gráfica"))
    elif not Path(str(profile)).exists():
        checks.append(PrepressCheck("error", "icc_profile_not_found", f"Perfil ICC não encontrado: {profile}"))

    status = "failed" if any(item.severity == "error" for item in checks) else "passed_with_warnings" if any(item.severity == "warning" for item in checks) else "passed"
    return {
        "status": status,
        "pdf": str(pdf_path),
        "pdf_header": reader.pdf_header,
        "media_box_mm": {"width": round(width_mm, 3), "height": round(height_mm, 3)},
        "fonts": fonts,
        "color_markers": {"rgb": rgb_markers, "cmyk": cmyk_markers},
        "checks": [asdict(item) for item in checks],
    }


def save_prepress_report(report: Dict[str, Any], output: Path) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return output
