#!/usr/bin/env python3
"""
2-revisao/rules/typography.py
------------------------------
Sanitização tipográfica: conversão de hífens soltos em travessões (—),
correção de verba dicendi em diálogos e limpeza de espaços duplos.
Preserva o bloco de YAML Frontmatter intacto.
"""

import re
from typing import Tuple

VERBA_DICENDI = [
    "disse", "falou", "respondeu", "gritou", "perguntou", "murmurou",
    "afirmou", "acrescentou", "protestou", "explicou", "resmungou",
    "rosnou", "exclamou", "retrucou", "concordou", "anunciou", "chamou"
]


def _fix_verba_dicendi_capitalization(line: str) -> Tuple[str, int]:
    """Corrige maiúsculas indevidas em verbos de dizer após o travessão de fechamento."""
    count = 0
    new_line = line
    for verb in VERBA_DICENDI:
        capitalized = verb.capitalize()
        pattern = r'—\s+' + capitalized + r'\b'
        replacement = f'— {verb}'
        if re.search(pattern, new_line):
            new_line, num_sub = re.subn(pattern, replacement, new_line)
            count += num_sub
    return new_line, count


def sanitize_typography(text: str) -> Tuple[str, int]:
    """
    Sanitiza a tipografia do texto aplicando padrões editoriais profissionais:
    - Hífen no início de linha ou diálogo com espaço -> Travessão (—)
    - Verba dicendi com maiúscula após travessão -> minúscula (— disse)
    - Espaços duplos -> Espaço único
    Ignora o bloco de YAML Frontmatter inicial.
    """
    corrections_count = 0
    lines = text.splitlines()
    sanitized_lines = []
    
    in_frontmatter = False
    frontmatter_delimiters = 0

    for i, line in enumerate(lines):
        new_line = line

        # Checa delimitadores do YAML Frontmatter
        if line.strip() == "---":
            frontmatter_delimiters += 1
            in_frontmatter = (frontmatter_delimiters == 1)
            sanitized_lines.append(new_line)
            continue

        # Se estiver dentro do YAML Frontmatter, não altera listas com hífen
        if in_frontmatter and frontmatter_delimiters == 1:
            sanitized_lines.append(new_line)
            continue

        # 1. Converte traço inicial de diálogo '- ' ou '-- ' em travessão '— '
        if re.match(r'^\s*(?:--|-)\s+', new_line):
            new_line = re.sub(r'^\s*(?:--|-)\s+', '— ', new_line)
            corrections_count += 1
            
        # 2. Converte traços de fala no meio da linha ' - ' ou ' -- ' em ' — '
        if ' - ' in new_line or ' -- ' in new_line:
            new_line = re.sub(r'\s+--?\s+', ' — ', new_line)
            corrections_count += 1

        # 3. Correção de Verba Dicendi
        new_line, dicendi_fixes = _fix_verba_dicendi_capitalization(new_line)
        corrections_count += dicendi_fixes
            
        # 4. Remove espaços duplos
        while '  ' in new_line:
            new_line = new_line.replace('  ', ' ')
            corrections_count += 1
            
        sanitized_lines.append(new_line)

    return "\n".join(sanitized_lines), corrections_count
