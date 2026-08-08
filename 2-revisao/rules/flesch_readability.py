#!/usr/bin/env python3
"""
2-revisao/rules/flesch_readability.py
--------------------------------------
Calculador de Índice de Legibilidade Flesch-Siqueira adaptado para Português (pt-BR).
"""

import re
from typing import Dict, Any


def count_syllables_ptbr(word: str) -> int:
    """Estimativa simples de contagem de sílabas para palavras em Português."""
    word = word.lower().strip()
    if not word:
        return 0
        
    vowels = "aeiouáàâãéèêíïóôõöú"
    # Grupos de vogais/vogais contadas como núcleos silábicos
    matches = re.findall(r'[' + vowels + ']+', word)
    return max(1, len(matches))


def calculate_flesch_siqueira(text: str) -> Dict[str, Any]:
    """
    Calcula o Índice Flesch-Siqueira para Português:
    Flesch = 248.835 - (1.015 * PalavrasPorFrase) - (84.6 * SilabasPorPalavra)
    """
    # Limpa código de marcação Markdown antes do cálculo
    clean_text = re.sub(r'#+|>\s*|:::.*|!\[.*?\]\(.*?\)', '', text)
    
    sentences = [s.strip() for s in re.split(r'[.!?]+', clean_text) if s.strip()]
    words = re.findall(r'\b[a-zA-ZáàâãéèêíïóôõöúçñÁÀÂÃÉÈÊÍÏÓÔÕÖÚÇÑ]+\b', clean_text)
    
    num_sentences = max(1, len(sentences))
    num_words = max(1, len(words))
    num_syllables = sum(count_syllables_ptbr(w) for w in words)
    
    words_per_sentence = num_words / num_sentences
    syllables_per_word = num_syllables / num_words
    
    flesch_score = 248.835 - (1.015 * words_per_sentence) - (84.6 * syllables_per_word)
    flesch_score = round(max(0.0, min(100.0, flesch_score)), 1)
    
    # Classificação por Faixa Etária
    if flesch_score >= 80:
        classification = "Muito Fácil (5 a 8 anos / Leitura Infantil)"
    elif flesch_score >= 60:
        classification = "Fácil (9 a 12 anos / Leitura Infantojuvenil)"
    elif flesch_score >= 50:
        classification = "Médio (13 a 15 anos / Jovens Adultos)"
    else:
        classification = "Difícil (Adultos / Texto Técnico ou Acadêmico)"
        
    return {
        "flesch_score": flesch_score,
        "classificacao": classification,
        "total_palavras": num_words,
        "total_frases": num_sentences,
        "media_palavras_por_frase": round(words_per_sentence, 1),
        "media_silabas_por_palavra": round(syllables_per_word, 2)
    }
