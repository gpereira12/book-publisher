"""Planejamento de composição: regras explicáveis antes da renderização."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import math
from typing import Any, Dict, List

from design_engine.cover_spec import CoverSpec
from design_engine.editorial_brief import EditorialBrief


PHI = (1 + math.sqrt(5)) / 2


@dataclass(frozen=True)
class CompositionPlan:
    recommended_pattern: int
    title_lines: int
    type_base_pt: float
    type_heading_pt: float
    type_display_pt: float
    ornament_complexity: int
    ornament_density: str
    title_zone: str
    reasons: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def build_composition_plan(config: Dict[str, Any], brief: EditorialBrief, spec: CoverSpec, has_image: bool) -> CompositionPlan:
    title_length = len(brief.title)
    title_lines = 1 if title_length <= 22 else 2 if title_length <= 52 else 3
    base = float(config.get("tipo_base_pt", 10.5))
    display = base * PHI * PHI
    if title_lines == 1:
        display *= 1.16
    elif title_lines == 3:
        display *= 0.88
    display = round(min(36.0, max(23.0, display)), 1)
    heading = round(base * PHI, 1)

    reasons: List[str] = []
    if has_image and title_lines >= 2:
        pattern = 2
        title_zone = "tarja_superior"
        reasons.append("título longo e imagem pedem área tipográfica dedicada")
    elif has_image:
        pattern = 1
        title_zone = "terco_superior"
        reasons.append("título curto permite composição full-bleed")
    else:
        pattern = 3
        title_zone = "cabecalho_central"
        reasons.append("ausência de imagem favorece composição emoldurada/tipográfica")

    explicit_complexity = "ornamentos_complexidade" in config
    complexity = int(config.get("ornamentos_complexidade", 3))
    complexity = max(1, min(5, complexity))
    density = str(config.get("ornamentos_densidade", "moderada"))
    if spec.page_w_mm < 140 and complexity > 4 and not explicit_complexity:
        complexity = 4
        reasons.append("complexidade ornamental limitada pelo formato compacto")

    return CompositionPlan(pattern, title_lines, base, heading, display, complexity, density, title_zone, reasons)
