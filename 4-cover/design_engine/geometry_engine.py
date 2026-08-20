"""
4-cover/design_engine/geometry_engine.py
----------------------------------------
Bloco 1: Geometria Gráfica Absoluta.
Calcula com precisão milimétrica as dimensões da folha aberta da capa (Capa, Contracapa, Lombada, Orelhas e Sangria).
"""

from typing import Dict, Any

from design_engine.cover_spec import FORMAT_DIMENSIONS_MM, build_cover_spec


def calculate_cover_geometry(config: Dict[str, Any], spine_mm: float) -> Dict[str, float]:
    """Compatibilidade legada; novos consumidores devem usar CoverSpec."""
    return build_cover_spec(config, spine_mm).to_dict()
