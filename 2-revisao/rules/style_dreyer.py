#!/usr/bin/env python3
"""
2-revisao/rules/style_dreyer.py
--------------------------------
Módulo de revisão de estilo baseado no expurgo de palavras muleta de Benjamin Dreyer
e detecção de repetições excessivas no texto.
"""

import re
from collections import Counter
from typing import Dict, List, Tuple

# Palavras muleta em Português (Benjamin Dreyer Rule)
CRUTCH_WORDS_PTBR = [
    "realmente", "muito", "na verdade", "de fato", "simplesmente",
    "praticamente", "totalmente", "absolutamente", "certamente", "obviamente"
]


def find_crutch_words(text: str) -> Dict[str, int]:
    """Identifica e conta a ocorrência de palavras muleta no texto."""
    results: Dict[str, int] = {}
    lowered = text.lower()
    
    for word in CRUTCH_WORDS_PTBR:
        count = len(re.findall(r'\b' + re.escape(word) + r'\b', lowered))
        if count > 0:
            results[word] = count
            
    return results


def find_repeated_words(text: str, min_length: int = 5, top_n: int = 10) -> List[Tuple[str, int]]:
    """Identifica as palavras mais frequentes com comprimento maior que min_length."""
    words = re.findall(r'\b[a-zA-ZáàâãéèêíïóôõöúçñÁÀÂÃÉÈÊÍÏÓÔÕÖÚÇÑ]+\b', text.lower())
    
    # Palavras comuns a ignorar (stopwords em PT-BR)
    stopwords = {
        "para", "como", "com", "por", "que", "uma", "um", "dos", "das", "mais",
        "sobre", "quando", "eles", "elas", "este", "esta", "onde", "dele", "dela"
    }
    
    filtered = [w for w in words if len(w) >= min_length and w not in stopwords]
    counter = Counter(filtered)
    return counter.most_common(top_n)
