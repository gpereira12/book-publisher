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

# Fonte bitmap 5×7 mínima para manter o barcode 100% vetorial, sem fontes PDF.
BITMAP_GLYPHS = {
    "0": ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    "1": ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    "2": ("01110", "10001", "00001", "00010", "00100", "01000", "11111"),
    "3": ("11110", "00001", "00001", "01110", "00001", "00001", "11110"),
    "4": ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    "5": ("11111", "10000", "10000", "11110", "00001", "00001", "11110"),
    "6": ("01110", "10000", "10000", "11110", "10001", "10001", "01110"),
    "7": ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    "8": ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    "9": ("01110", "10001", "10001", "01111", "00001", "00001", "01110"),
    "I": ("11111", "00100", "00100", "00100", "00100", "00100", "11111"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "B": ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    "N": ("10001", "11001", "11001", "10101", "10011", "10011", "10001"),
    "X": ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    "-": ("00000", "00000", "00000", "11111", "00000", "00000", "00000"),
    " ": ("00000",) * 7,
}


def _vector_text(text: str, center_x: float, top_y: float, scale: float) -> str:
    glyph_w = 5 * scale
    advance = 6 * scale
    total_w = max(0.0, len(text) * advance - scale)
    start_x = center_x - total_w / 2
    rects = []
    for char_index, char in enumerate(text.upper()):
        glyph = BITMAP_GLYPHS.get(char, BITMAP_GLYPHS[" "])
        for row_index, row in enumerate(glyph):
            for column_index, bit in enumerate(row):
                if bit == "1":
                    rects.append(
                        f'<rect x="{start_x + char_index*advance + column_index*scale:.2f}" '
                        f'y="{top_y + row_index*scale:.2f}" width="{scale:.2f}" height="{scale:.2f}"/>'
                    )
    return f'<g fill="#000000">{"".join(rects)}</g>'


def clean_digits(isbn_str: str) -> str:
    """Normaliza ISBN-10/13 e rejeita valores que produziriam barras inválidas."""
    raw = re.sub(r"[^0-9Xx]", "", isbn_str)
    if len(raw) == 10:
        if not validate_isbn10(raw):
            raise ValueError(f"ISBN-10 inválido: {isbn_str!r}")
        base = "978" + raw[:9]
        return base + str(calculate_ean13_check_digit(base))
    if len(raw) != 13 or not raw.isdigit():
        raise ValueError(f"ISBN deve conter exatamente 10 ou 13 dígitos: {isbn_str!r}")
    if not validate_ean13(raw):
        raise ValueError(f"Dígito verificador EAN-13 inválido: {isbn_str!r}")
    return raw


def calculate_ean13_check_digit(first_twelve: str) -> int:
    if len(first_twelve) != 12 or not first_twelve.isdigit():
        raise ValueError("O cálculo do EAN-13 exige exatamente 12 dígitos")
    weighted = sum(int(d) * (1 if index % 2 == 0 else 3) for index, d in enumerate(first_twelve))
    return (10 - weighted % 10) % 10


def validate_ean13(digits: str) -> bool:
    return len(digits) == 13 and digits.isdigit() and calculate_ean13_check_digit(digits[:12]) == int(digits[-1])


def validate_isbn10(value: str) -> bool:
    if len(value) != 10 or not value[:9].isdigit() or not (value[-1].isdigit() or value[-1].upper() == "X"):
        return False
    values = [int(char) for char in value[:9]] + [10 if value[-1].upper() == "X" else int(value[-1])]
    return sum((10 - index) * digit for index, digit in enumerate(values)) % 11 == 0


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
    
    formatted_isbn = f"ISBN {digits}"
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
    top_text_svg = _vector_text(formatted_isbn, svg_width / 2, 4, 0.72)
    bottom_text_svg = _vector_text(bottom_digits_fmt, svg_width / 2, 59, 0.62)

    svg_content = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{svg_width}" height="{svg_height}" viewBox="0 0 {svg_width} {svg_height}">
  <!-- Fundo Fundo Fundo Branco Fundo Quiet Zone -->
  <rect width="{svg_width}" height="{svg_height}" fill="#ffffff" rx="4" ry="4" stroke="#cccccc" stroke-width="0.5"/>
  
  <!-- Texto Superior ISBN convertido em glifos vetoriais 5x7 -->
  {top_text_svg}
  
  <!-- Barras Vetoriais EAN-13 -->
  <g>
    {rects_str}
  </g>

  <!-- Dígitos inferiores convertidos em glifos vetoriais 5x7 -->
  {bottom_text_svg}
</svg>
"""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(svg_content, encoding="utf-8")
    return output_path
