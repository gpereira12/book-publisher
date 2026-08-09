#!/usr/bin/env python3
"""
2-edit/rules/style_sheet.py
------------------------------
Validador de Folha de Estilo Editorial e detecção de termos anacrônicos ou incorretos.
"""

import re
from pathlib import Path
from typing import Dict, List, Tuple, Any
import yaml


def load_style_sheet(style_sheet_path: Path) -> Dict[str, Any]:
    """Carrega o arquivo style_sheet.yaml do livro se existir."""
    if not style_sheet_path.exists():
        return {}
    with open(style_sheet_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def check_style_sheet_violations(text: str, style_sheet: Dict[str, Any]) -> List[str]:
    """Verifica violações de grafia estrita e presença de termos anacrônicos proibidos."""
    warnings: List[str] = []
    
    # 1. Checagem de Grafia Estrita
    strict_spelling: Dict[str, List[str]] = style_sheet.get("grafia_estrita", {})
    for correct_form, wrong_forms in strict_spelling.items():
        for wrong in wrong_forms:
            pattern = r'\b' + re.escape(wrong) + r'\b'
            matches = re.findall(pattern, text)
            if matches:
                warnings.append(
                    f"Grafia Incorreta: Encontrado '{wrong}' {len(matches)} vez(es). Substituir por '{correct_form}'."
                )

    # 2. Checagem de Termos Anacrônicos Proibidos
    prohibited_terms: List[str] = style_sheet.get("termos_anacronicos_proibidos", [])
    for term in prohibited_terms:
        pattern = r'\b' + re.escape(term) + r'\b'
        matches = re.findall(pattern, text, flags=re.IGNORECASE)
        if matches:
            warnings.append(
                f"Alerta de Anacronismo/Termo Proibido: Encontrado termo '{term}' {len(matches)} vez(es)."
            )

    return warnings
