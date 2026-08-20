"""Plano cromático editorial baseado em papéis 70/20/10."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import re
from typing import Any, Dict, List


HEX_RE = re.compile(r"^#[0-9a-fA-F]{6}$")


@dataclass(frozen=True)
class ColorRole:
    name: str
    color: str
    ratio: float
    purpose: str


@dataclass(frozen=True)
class ColorPlan:
    dominant: ColorRole
    secondary: ColorRole
    accent: ColorRole

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _shade(color: str, factor: float) -> str:
    value = color.lstrip("#")
    if len(value) != 6:
        return color
    channels = [round(int(value[index:index + 2], 16) * factor) for index in (0, 2, 4)]
    return "#" + "".join(f"{max(0, min(255, channel)):02x}" for channel in channels)


def _ratios(config: Dict[str, Any]) -> Dict[str, float]:
    raw = config.get("proporcao_cores") or {}
    values = {
        "dominante": float(raw.get("dominante", 70)),
        "secundaria": float(raw.get("secundaria", 20)),
        "destaque": float(raw.get("destaque", 10)),
    }
    total = sum(values.values())
    if total <= 0:
        raise ValueError("proporcao_cores precisa ter soma positiva")
    return {name: value / total for name, value in values.items()}


def build_color_plan(config: Dict[str, Any], palette: Dict[str, Any]) -> ColorPlan:
    ratios = _ratios(config)
    dominant = str(config.get("cor_capa") or palette["bg_color"])
    secondary = str(config.get("cor_secundaria") or _shade(dominant, 1.35))
    accent = str(config.get("cor_destaque") or palette["gold_color"])
    return ColorPlan(
        dominant=ColorRole("dominante", dominant, ratios["dominante"], "grandes campos, atmosfera e continuidade"),
        secondary=ColorRole("secundaria", secondary, ratios["secundaria"], "tarjas, molduras, profundidade e apoio"),
        accent=ColorRole("destaque", accent, ratios["destaque"], "título, ornamentos, filetes e pontos focais"),
    )


def validate_color_plan(config: Dict[str, Any], palette: Dict[str, Any]) -> List[Dict[str, str]]:
    issues: List[Dict[str, str]] = []
    try:
        plan = build_color_plan(config, palette)
    except (TypeError, ValueError) as exc:
        return [{"severity": "error", "code": "invalid_color_ratio", "message": str(exc)}]
    for role in (plan.dominant, plan.secondary, plan.accent):
        if not HEX_RE.match(role.color):
            issues.append({"severity": "error", "code": f"invalid_{role.name}_color", "message": f"Cor {role.name} deve usar HEX #RRGGBB"})
    raw = config.get("proporcao_cores") or {"dominante": 70, "secundaria": 20, "destaque": 10}
    total = sum(float(raw.get(name, 0)) for name in ("dominante", "secundaria", "destaque"))
    if abs(total - 100) > 0.01:
        issues.append({"severity": "warning", "code": "normalized_color_ratio", "message": f"Proporção cromática soma {total:g}; o motor normalizará para 100"})
    return issues
