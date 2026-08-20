"""Modelo canônico de uma capa aberta e validação da configuração editorial."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import re
from typing import Any, Dict, List


FORMAT_DIMENSIONS_MM = {
    "pocket": (125.0, 180.0),
    "a5": (148.0, 210.0),
    "14x21": (140.0, 210.0),
    "trade": (152.0, 228.0),
    "executive": (170.0, 240.0),
}

VALID_FINISHES = {"brochura", "capadura", "grampo", "espiral"}
VALID_TITLE_MODES = {"nenhum", "imagem", "vetorial"}
HEX_COLOR_RE = re.compile(r"^#[0-9a-fA-F]{6}$")


@dataclass(frozen=True)
class CoverSpec:
    """Dimensões resolvidas, em milímetros, usadas por todos os renderizadores."""

    format_key: str
    finish: str
    page_w_mm: float
    page_h_mm: float
    bleed_mm: float
    flap_mm: float
    hinge_mm: float
    spine_mm: float
    safe_mm: float
    total_w_mm: float
    total_h_mm: float
    is_hardcover: bool
    has_flaps: bool

    @property
    def segments(self) -> List[Dict[str, float | str]]:
        """Painéis na ordem física da capa aberta, da esquerda para a direita."""
        raw = [
            ("bleed_left", self.bleed_mm),
            ("flap_left", self.flap_mm),
            ("back", self.page_w_mm),
            ("hinge_left", self.hinge_mm),
            ("spine", self.spine_mm),
            ("hinge_right", self.hinge_mm),
            ("front", self.page_w_mm),
            ("flap_right", self.flap_mm),
            ("bleed_right", self.bleed_mm),
        ]
        x = 0.0
        segments: List[Dict[str, float | str]] = []
        for name, width in raw:
            if width <= 0:
                continue
            segments.append({"name": name, "x_mm": round(x, 3), "width_mm": round(width, 3)})
            x += width
        return segments

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["segments"] = self.segments
        return data


def normalize_format(value: Any) -> str:
    return str(value or "Pocket").strip().lower()


def build_cover_spec(config: Dict[str, Any], spine_mm: float) -> CoverSpec:
    format_key = normalize_format(config.get("formato", "Pocket"))
    if format_key not in FORMAT_DIMENSIONS_MM:
        raise ValueError(
            f"formato inválido: {config.get('formato')!r}; use "
            f"{', '.join(FORMAT_DIMENSIONS_MM)}"
        )
    page_w_mm, page_h_mm = FORMAT_DIMENSIONS_MM[format_key]

    finish = str(config.get("acabamento", "brochura")).strip().lower()
    if finish not in VALID_FINISHES:
        raise ValueError(f"acabamento inválido: {finish!r}; use {', '.join(sorted(VALID_FINISHES))}")

    resolved_spine = max(0.0, float(spine_mm))
    if finish == "capadura":
        flap_mm = float(config.get("vira_mm", 35.0))
        bleed_mm = float(config.get("sangria_mm", 0.0))
        hinge_mm = float(config.get("calha_mm", 10.0))
    elif finish in {"grampo", "espiral"}:
        flap_mm = 0.0
        bleed_mm = float(config.get("sangria_mm", 5.0))
        hinge_mm = 0.0
        resolved_spine = 0.0
    else:
        has_flaps = bool(config.get("orelhas", False))
        flap_mm = float(config.get("orelha_mm", 70.0)) if has_flaps else 0.0
        bleed_mm = float(config.get("sangria_mm", 10.0))
        hinge_mm = 0.0

    safe_mm = float(config.get("area_segura_mm", 8.0))
    numeric = {
        "lombada": resolved_spine,
        "sangria": bleed_mm,
        "orelha/vira": flap_mm,
        "calha": hinge_mm,
        "área segura": safe_mm,
    }
    invalid = [name for name, value in numeric.items() if value < 0]
    if invalid:
        raise ValueError(f"dimensões negativas não são permitidas: {', '.join(invalid)}")

    total_w_mm = 2 * bleed_mm + 2 * flap_mm + 2 * page_w_mm + 2 * hinge_mm + resolved_spine
    total_h_mm = 2 * bleed_mm + page_h_mm
    return CoverSpec(
        format_key=format_key,
        finish=finish,
        page_w_mm=page_w_mm,
        page_h_mm=page_h_mm,
        bleed_mm=bleed_mm,
        flap_mm=flap_mm,
        hinge_mm=hinge_mm,
        spine_mm=resolved_spine,
        safe_mm=safe_mm,
        total_w_mm=round(total_w_mm, 3),
        total_h_mm=round(total_h_mm, 3),
        is_hardcover=finish == "capadura",
        has_flaps=flap_mm > 0,
    )


def validate_config(config: Dict[str, Any]) -> List[Dict[str, str]]:
    """Retorna problemas estruturais sem aplicar defaults silenciosos perigosos."""
    issues: List[Dict[str, str]] = []

    def add(severity: str, code: str, message: str) -> None:
        issues.append({"severity": severity, "code": code, "message": message})

    for field in ("titulo", "autor", "isbn"):
        if not str(config.get(field, "")).strip():
            add("error", f"missing_{field}", f"Campo obrigatório ausente: {field}")

    if not str(config.get("sinopse", "")).strip():
        add("warning", "missing_synopsis", "Sinopse ausente; a contracapa usará texto-placeholder")

    format_key = normalize_format(config.get("formato", "Pocket"))
    if format_key not in FORMAT_DIMENSIONS_MM:
        add("error", "invalid_format", f"Formato desconhecido: {config.get('formato')!r}")

    finish = str(config.get("acabamento", "brochura")).strip().lower()
    if finish not in VALID_FINISHES:
        add("error", "invalid_finish", f"Acabamento desconhecido: {finish!r}")

    title_mode = str(config.get("titulo_lettering_modo", "nenhum")).strip().lower()
    if title_mode not in VALID_TITLE_MODES:
        add("error", "invalid_title_mode", f"Modo de letreiro desconhecido: {title_mode!r}")

    pattern = config.get("padrao_capa", 1)
    if pattern not in (1, 2, 3):
        add("error", "invalid_pattern", f"padrao_capa deve ser 1, 2 ou 3; recebido {pattern!r}")

    if config.get("cor_capa") and not HEX_COLOR_RE.match(str(config["cor_capa"])):
        add("error", "invalid_cover_color", "cor_capa deve usar HEX #RRGGBB")

    for field in ("fade_start", "foco_x", "foco_y"):
        if field in config:
            try:
                value = float(config[field])
            except (TypeError, ValueError):
                add("error", f"invalid_{field}", f"{field} deve ser numérico entre 0 e 1")
                continue
            if not 0 <= value <= 1:
                add("error", f"invalid_{field}", f"{field} deve estar entre 0 e 1")

    return issues
