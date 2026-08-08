"""
4-capas/design_engine/geometry_engine.py
----------------------------------------
Bloco 1: Geometria Gráfica Absoluta.
Calcula com precisão milimétrica as dimensões da folha aberta da capa (Capa, Contracapa, Lombada, Orelhas e Sangria).
"""

from typing import Dict, Any

FORMAT_DIMENSIONS_MM = {
    "Pocket": (125.0, 180.0),
    "A5": (148.0, 210.0),
    "14x21": (140.0, 210.0),
    "Trade": (152.0, 228.0),
    "Executive": (170.0, 240.0)
}


def calculate_cover_geometry(config: Dict[str, Any], spine_mm: float) -> Dict[str, float]:
    fmt = config.get("formato", "Pocket")
    page_w_mm, page_h_mm = FORMAT_DIMENSIONS_MM.get(fmt, FORMAT_DIMENSIONS_MM["Pocket"])

    acabamento = config.get("acabamento", "brochura").lower()
    has_flaps = config.get("orelhas", False)
    
    # Cálculo da largura das orelhas / vira
    if acabamento == "capadura":
        flap_mm = 35.0  # Vira colada no papelão holandês
        bleed_mm = 0.0
        hinge_mm = 10.0 # Calhas de dobra da capa dura
    elif acabamento in ("grampo", "espiral"):
        flap_mm = 0.0
        bleed_mm = 5.0
        hinge_mm = 0.0
        spine_mm = 0.0
    else:  # brochura
        flap_mm = float(config.get("orelha_mm", 70.0)) if has_flaps else 0.0
        bleed_mm = 10.0
        hinge_mm = 0.0

    total_w_mm = (bleed_mm * 2) + (flap_mm * 2) + (page_w_mm * 2) + (hinge_mm * 2) + spine_mm
    total_h_mm = (bleed_mm * 2) + page_h_mm

    return {
        "page_w_mm": page_w_mm,
        "page_h_mm": page_h_mm,
        "bleed_mm": bleed_mm,
        "flap_mm": flap_mm,
        "hinge_mm": hinge_mm,
        "spine_mm": spine_mm,
        "total_w_mm": total_w_mm,
        "total_h_mm": total_h_mm,
        "is_hardcover": (acabamento == "capadura"),
        "has_flaps": (flap_mm > 0.0)
    }
