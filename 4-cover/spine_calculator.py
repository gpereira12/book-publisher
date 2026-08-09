#!/usr/bin/env python3
"""
4-cover/spine_calculator.py
---------------------------
Calculador matemático da espessura da lombada baseado no PDF gerado no Layout (Projeto 3)
e no tipo de acabamento gráfico (Brochura, Capa Dura, Grampo, Espiral).
"""

import subprocess
import re
from pathlib import Path
from typing import Dict, Any


PAPER_FACTORS_MM = {
    "polen_soft_80g": 0.115,
    "polen_bold_90g": 0.135,
    "offset_75g": 0.095,
    "couche_115g": 0.090
}


def count_pdf_pages(pdf_path: Path) -> int:
    """Conta o número exato de páginas de um arquivo PDF."""
    if not pdf_path.exists():
        return 100  # Fallback

    try:
        res = subprocess.run(["pdfinfo", str(pdf_path)], capture_output=True, text=True)
        if res.returncode == 0:
            match = re.search(r'Pages:\s+(\d+)', res.stdout)
            if match:
                return int(match.group(1))
    except Exception:
        pass

    try:
        content = pdf_path.read_bytes()
        pages = len(re.findall(rb'/Type\s*/Page\b', content))
        return max(1, pages)
    except Exception:
        return 100


def calculate_spine_width_mm(
    page_count: int, paper_type: str = "polen_soft_80g", acabamento: str = "brochura"
) -> float:
    """
    Calcula a espessura da lombada em milímetros:
    - Grampo ou Espiral: Lombada = 0mm (não possuem texto na lombada).
    - Brochura ou Capa Dura: Lombada = (Páginas / 2) * Fator_Papel_mm.
    """
    if acabamento in ["grampo", "espiral"]:
        return 0.0

    factor = PAPER_FACTORS_MM.get(paper_type, 0.115)
    sheets = page_count / 2.0
    spine_mm = sheets * factor
    return round(max(3.0, spine_mm), 2)
