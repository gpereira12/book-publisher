#!/usr/bin/env python3
"""
4-cover/barcode_generator.py
----------------------------
Gerador oficial de código de barras EAN-13 / ISBN em vetor SVG para capas gráficas.
Gera um arquivo SVG autocontido com margem de segurança (quiet zone), barras pretas K=100%,
texto superior ISBN e texto inferior dos dígitos EAN-13 sem dependências externas.
"""

import re
from pathlib import Path

# Tabelas de codificação EAN-13
L_CODES = [
    "0001101", "0011001", "0010011", "0111101", "0100011",
    "0110001", "0101111", "0111011", "0110111", "0001011"
]
G_CODES = [
    "0100111", "0110011", "0011011", "0100001", "0011101",
    "0111001", "0000101", "0010001", "0001001", "0010111"
]
R_CODES = [
    "1110010", "1100110", "1101100", "1000010", "1011100",
    "1001110", "1010000", "1000100", "1001000", "1110100"
]
FIRST_DIGIT_PATTERNS = [
    "LLLLLL", "LLGLGG", "LLGGLG", "LLGGGL", "LGLLGG",
    "LGGLLG", "LGGGLL", "LGLGLG", "LGLGGL", "LGGLGL"
]


def clean_digits(isbn_str: str) -> str:
    """Extrai apenas os dígitos numéricos de um ISBN."""
    digits = re.sub(r'\D', '', isbn_str)
    if len(digits) == 10:
        digits = "978" + digits[:9]  # Converte ISBN-10 para 13 dígitos preliminares
    if len(digits) < 13:
        digits = digits.ljust(13, '0')[:13]
    return digits[:13]


def encode_ean13_binary(digits: str) -> str:
    """Converte 13 dígitos numéricos na sequência binária de barras do EAN-13."""
    first_digit = int(digits[0])
    pattern = FIRST_DIGIT_PATTERNS[first_digit]
    
    # 1. Guarda Inicial (101)
    binary = "101"
    
    # 2. Grupo Esquerdo (6 dígitos)
    left_digits = digits[1:7]
    for i, d in enumerate(left_digits):
        val = int(d)
        code_type = pattern[i]
        binary += L_CODES[val] if code_type == 'L' else G_CODES[val]
        
    # 3. Guarda Central (01010)
    binary += "01010"
    
    # 4. Grupo Direito (6 dígitos R-code)
    right_digits = digits[7:13]
    for d in right_digits:
        binary += R_CODES[int(d)]
        
    # 5. Guarda Final (101)
    binary += "101"
    
    return binary


def generate_ean13_svg(isbn_str: str, output_path: Path) -> Path:
    """Gera um arquivo SVG vetorial oficial EAN-13 com quiet zone e tipografia limpa."""
    digits = clean_digits(isbn_str)
    binary = encode_ean13_binary(digits)
    
    formatted_isbn = f"ISBN {isbn_str}" if "ISBN" not in isbn_str else isbn_str
    bottom_digits_fmt = f"{digits[0]} {digits[1:7]} {digits[7:13]}"

    # Dimensões do SVG (Quiet zone de 125px x 70px)
    svg_width = 130
    svg_height = 72
    bar_start_x = 18
    bar_width = 1.0
    normal_bar_y = 18
    normal_bar_h = 36
    guard_bar_h = 42

    rects_svg = []
    
    # Renderização das barras binárias
    for idx, bit in enumerate(binary):
        if bit == '1':
            x_pos = bar_start_x + (idx * bar_width)
            # Guardas iniciais (0..2), centrais (45..49) e finais (92..94) são mais longas
            is_guard = (idx in (0, 1, 2, 45, 46, 47, 48, 49, 92, 93, 94))
            bar_h = guard_bar_h if is_guard else normal_bar_h
            rects_svg.append(
                f'<rect x="{x_pos:.1f}" y="{normal_bar_y}" width="{bar_width:.1f}" height="{bar_h:.1f}" fill="#000000"/>'
            )

    rects_str = "\n    ".join(rects_svg)

    svg_content = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{svg_width}" height="{svg_height}" viewBox="0 0 {svg_width} {svg_height}">
  <!-- Fundo Fundo Fundo Branco Fundo Quiet Zone -->
  <rect width="{svg_width}" height="{svg_height}" fill="#ffffff" rx="4" ry="4" stroke="#cccccc" stroke-width="0.5"/>
  
  <!-- Texto Superior ISBN -->
  <text x="{svg_width/2:.1f}" y="13" font-family="Courier, monospace" font-size="7.5" font-weight="bold" fill="#000000" text-anchor="middle">{formatted_isbn}</text>
  
  <!-- Barras Vetoriais EAN-13 -->
  <g>
    {rects_str}
  </g>

  <!-- Texto Inferior Dígitos EAN-13 -->
  <text x="{svg_width/2:.1f}" y="66" font-family="Courier, monospace" font-size="7" font-weight="bold" fill="#000000" text-anchor="middle">{bottom_digits_fmt}</text>
</svg>
"""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(svg_content, encoding="utf-8")
    return output_path
