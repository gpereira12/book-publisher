#!/usr/bin/env python3
"""Detecta marcadores de prosa formulaica para revisão humana.

Os marcadores abaixo também aparecem em prosa humana. Por isso, o módulo considera
contexto e densidade, não tenta determinar autoria e nunca corrige o texto sozinho.
"""

import math
import re
from typing import Any, Dict, List

# Frases de anúncio metatextual (a IA se anunciando antes de dizer algo)
META_ANNOUNCEMENT_PHRASES = [
    "é importante dizer",
    "é importante destacar",
    "é importante ressaltar",
    "é importante notar",
    "vale destacar",
    "vale ressaltar",
    "cabe destacar",
    "cabe ressaltar",
    "convém destacar",
    "convém ressaltar",
    "não podemos esquecer",
    "é fundamental notar",
    "é preciso dizer",
    "importante mencionar",
]

# Construções formulaicas. O pretérito ("não foi de X, mas de Y") fica de
# fora porque costuma indicar contraste narrativo, não uma tese abstrata.
ANTITHESIS_PATTERNS = [
    re.compile(
        r"não\s+(?:é|são)\s+(?:apenas\s+|só\s+|somente\s+)?"
        r"[^,.;!?—\n]{1,80}[,;]\s*(?:mas(?:\s+sim)?|e\s+sim)\b"
        r"[^.;!?—\n]{1,240}",
        re.IGNORECASE,
    ),
    re.compile(
        r"não\s+(?:apenas|só|somente)\s+[^,.;!?—\n]{1,80}"
        r"[,;]?\s*mas\s+também\b[^.;!?—\n]{1,240}",
        re.IGNORECASE,
    ),
    re.compile(r"\bo que\b[^.\n]{1,80};\s*o que\b", re.IGNORECASE),
]

# Pergunta retórica imediatamente respondida com "Porque..." (estrutura de redação de IA)
RHETORICAL_QA_PATTERN = re.compile(r"[^.!?\n]{5,120}\?\s*Porque\b", re.IGNORECASE)

# Palavras de abertura que, repetidas, indicam "bênção paralela" (tique de fechamento de IA).
# Pronomes e verbos de ação comuns (Ele, Você, Olhou, Quando...) ficam de fora de propósito:
# repetí-los em sequência é um recurso narrativo legítimo, não um tique de IA.
ANAPHORA_TRIGGER_WORDS = {"que", "não", "seja", "sejam", "assim"}


def find_meta_announcements(text: str) -> Dict[str, int]:
    """Conta frases de anúncio metatextual no texto."""
    results: Dict[str, int] = {}
    lowered = text.lower()
    for phrase in META_ANNOUNCEMENT_PHRASES:
        count = lowered.count(phrase)
        if count > 0:
            results[phrase] = count
    return results


def find_antithesis_patterns(text: str) -> List[str]:
    """Encontra trechos com antítese espelhada ('não é X, é Y')."""
    matches: List[str] = []
    for pattern in ANTITHESIS_PATTERNS:
        matches.extend(m.group(0).strip() for m in pattern.finditer(text))
    return matches


def find_rhetorical_question_answer(text: str) -> List[str]:
    """Encontra perguntas retóricas respondidas de imediato com 'Porque...'."""
    return [m.group(0).strip() for m in RHETORICAL_QA_PATTERN.finditer(text)]


def find_anaphora_repetition(text: str, min_repeats: int = 3) -> List[str]:
    """Encontra paralelismo insistente fora de diálogos.

    A análise é feita parágrafo a parágrafo para não criar sequências
    artificiais entre blocos. Duas repetições são aceitas como ênfase normal.
    """
    flagged: List[str] = []
    paragraphs = re.split(r"\n\s*\n", text)

    for paragraph in paragraphs:
        stripped = paragraph.strip()
        if not stripped or stripped.startswith(("—", "#")):
            continue

        sentences = re.split(r"(?<=[.!?])\s+", stripped)
        first_words: List[str | None] = []
        for sentence in sentences:
            words = re.findall(r"[A-Za-zÀ-úà-ÿ]+", sentence)
            first_words.append(words[0].lower() if words else None)

        i = 0
        while i < len(sentences):
            j = i
            while (
                j + 1 < len(sentences)
                and first_words[j + 1] == first_words[i]
                and first_words[i] in ANAPHORA_TRIGGER_WORDS
            ):
                j += 1
            if first_words[i] in ANAPHORA_TRIGGER_WORDS and j - i + 1 >= min_repeats:
                flagged.append(" / ".join(s.strip() for s in sentences[i:j + 1]))
            i = j + 1

    return flagged


def find_dash_parenthetical_overuse(text: str, max_per_paragraph: int = 1) -> List[str]:
    """Encontra frases com 2+ travessões parentéticos (' — aside — ') fora do início de linha (diálogo)."""
    flagged: List[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("—"):
            continue
        if stripped.count(" — ") >= max_per_paragraph + 1:
            flagged.append(stripped)
    return flagged


def assess_pattern_density(text: str, results: Dict[str, Any]) -> Dict[str, Any]:
    """Classifica a concentração dos marcadores, sem inferir autoria."""
    word_count = len(re.findall(r"\b[A-Za-zÀ-úà-ÿ]+\b", text))
    total_flags = (
        sum(results["meta_announcements"].values())
        + len(results["antithesis"])
        + len(results["rhetorical_qa"])
        + len(results["anaphora"])
        + len(results["dash_overuse"])
    )
    flags_per_1000 = round(total_flags * 1000 / max(word_count, 1), 2)
    review_threshold = max(4, math.ceil(word_count / 1000))

    if total_flags == 0:
        level = "sem_marcadores"
        label = "Nenhum marcador relevante"
    elif total_flags < review_threshold:
        level = "ocorrencias_isoladas"
        label = "Ocorrências isoladas; sem concentração relevante"
    elif flags_per_1000 < 2:
        level = "revisao_recomendada"
        label = "Concentração moderada; revisão humana recomendada"
    else:
        level = "excesso"
        label = "Concentração alta; revisar estilo"

    return {
        "level": level,
        "label": label,
        "total_flags": total_flags,
        "word_count": word_count,
        "flags_per_1000_words": flags_per_1000,
        "review_threshold": review_threshold,
        "review_recommended": level in {"revisao_recomendada", "excesso"},
    }


def analyze_ai_patterns(text: str) -> Dict[str, Any]:
    """Retorna ocorrências e uma avaliação de densidade consolidada."""
    results = {
        "meta_announcements": find_meta_announcements(text),
        "antithesis": find_antithesis_patterns(text),
        "rhetorical_qa": find_rhetorical_question_answer(text),
        "anaphora": find_anaphora_repetition(text),
        "dash_overuse": find_dash_parenthetical_overuse(text),
    }
    results["assessment"] = assess_pattern_density(text, results)
    return results
