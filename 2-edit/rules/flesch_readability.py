#!/usr/bin/env python3
"""Legibilidade em português: Flesch, segmentos e sinais locais de dificuldade."""

from __future__ import annotations

import re
import unicodedata
from typing import Any, Dict, Iterable, List


WORD_PATTERN = re.compile(r"\b[A-Za-zÀ-úà-ÿ]+\b")
DEFAULT_CONFIG: Dict[str, Any] = {
    "min_flesch": 60.0,
    "max_palavras_frase": 24,
    "silabas_palavra_dificil": 4,
    "min_letras_palavra_dificil": 8,
    "max_itens_relatorio": 10,
    "min_palavras_secao": 40,
    "ignorar_palavras": [],
}


def _normalize(value: str) -> str:
    decomposed = unicodedata.normalize("NFD", value.lower())
    return "".join(char for char in decomposed if unicodedata.category(char) != "Mn")


def count_syllables_ptbr(word: str) -> int:
    """Estima sílabas por grupos vocálicos; é uma aproximação, não separação fonética."""
    word = word.lower().strip()
    if not word:
        return 0
    vowels = "aeiouáàâãéèêíïóôõöúü"
    return max(1, len(re.findall(r"[" + vowels + r"]+", word)))


def clean_markdown(text: str) -> str:
    """Remove marcação que não pertence à prosa antes do cálculo."""
    text = re.sub(r"\A---\s*\n.*?\n---\s*\n", "", text, flags=re.DOTALL)
    text = re.sub(r"!\[[^]]*]\([^)]*\)", "", text)
    text = re.sub(r"^\s*:::[^\n]*$", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*#{1,6}\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*>\s*", "", text, flags=re.MULTILINE)
    return re.sub(r"[*_`]", "", text)


def calculate_flesch_siqueira(text: str) -> Dict[str, Any]:
    """Calcula Flesch adaptado: 248,835 - 1,015 CPF - 84,6 SP."""
    clean_text = clean_markdown(text)
    sentences = [part.strip() for part in re.split(r"[.!?]+", clean_text) if WORD_PATTERN.search(part)]
    words = WORD_PATTERN.findall(clean_text)
    if not words:
        return {
            "flesch_score": 0.0,
            "classificacao": "Sem texto suficiente",
            "total_palavras": 0,
            "total_frases": 0,
            "media_palavras_por_frase": 0.0,
            "media_silabas_por_palavra": 0.0,
        }

    num_sentences = max(1, len(sentences))
    num_syllables = sum(count_syllables_ptbr(word) for word in words)
    words_per_sentence = len(words) / num_sentences
    syllables_per_word = num_syllables / len(words)
    score = 248.835 - (1.015 * words_per_sentence) - (84.6 * syllables_per_word)
    score = round(max(0.0, min(100.0, score)), 1)
    if score >= 80:
        classification = "Muito fácil (referência aproximada: 5 a 8 anos)"
    elif score >= 60:
        classification = "Fácil (referência aproximada: 9 a 12 anos)"
    elif score >= 50:
        classification = "Média (referência aproximada: 13 a 15 anos)"
    else:
        classification = "Difícil (referência aproximada: adulto/técnico)"
    return {
        "flesch_score": score,
        "classificacao": classification,
        "total_palavras": len(words),
        "total_frases": num_sentences,
        "media_palavras_por_frase": round(words_per_sentence, 1),
        "media_silabas_por_palavra": round(syllables_per_word, 2),
    }


def resolve_readability_config(book_config: Dict[str, Any]) -> Dict[str, Any]:
    """Combina padrões, faixa etária do livro e ajustes editoriais explícitos."""
    configured = book_config.get("revisao", {}).get("legibilidade", {})
    result = dict(DEFAULT_CONFIG)
    result.update(configured)
    age_match = re.search(r"\d+", str(book_config.get("faixa_etaria", "")))
    result["faixa_etaria"] = int(age_match.group()) if age_match else None
    result["ignorar_palavras"] = [str(word).lower() for word in result.get("ignorar_palavras", [])]
    return result


def _content_lines(text: str) -> List[Dict[str, Any]]:
    """Extrai prosa com linha, capítulo, seção e tipo de conteúdo."""
    records: List[Dict[str, Any]] = []
    in_frontmatter = False
    frontmatter_closed = False
    chapter = "Sem capítulo"
    section = "Narração"

    for number, raw_line in enumerate(text.splitlines(), start=1):
        stripped = raw_line.strip()
        if number == 1 and stripped == "---":
            in_frontmatter = True
            continue
        if in_frontmatter:
            if stripped == "---":
                in_frontmatter = False
                frontmatter_closed = True
            continue
        if not frontmatter_closed and not records and stripped == "---":
            continue
        heading = re.match(r"^(#{1,3})\s+(.+?)\s*$", stripped)
        if heading:
            if len(heading.group(1)) == 1:
                chapter = heading.group(2)
                section = "Narração"
            else:
                section = heading.group(2)
            continue
        if (
            not stripped
            or stripped == "---"
            or stripped.startswith((":::", "![", ">"))
        ):
            continue
        cleaned = re.sub(r"[*_`]", "", stripped)
        if not WORD_PATTERN.search(cleaned):
            continue
        normalized_section = _normalize(section)
        content_type = "dialogo" if cleaned.startswith("—") else (
            "reflexao" if "reflexao" in normalized_section else "narracao"
        )
        records.append({
            "line": number,
            "chapter": chapter,
            "section": section,
            "type": content_type,
            "text": cleaned,
        })
    return records


def _group_metrics(records: Iterable[Dict[str, Any]], keys: List[str]) -> List[Dict[str, Any]]:
    groups: Dict[tuple[str, ...], List[Dict[str, Any]]] = {}
    for record in records:
        key = tuple(str(record[name]) for name in keys)
        groups.setdefault(key, []).append(record)
    results: List[Dict[str, Any]] = []
    for key, items in groups.items():
        metrics = calculate_flesch_siqueira("\n".join(item["text"] for item in items))
        results.append({
            **{name: value for name, value in zip(keys, key)},
            "start_line": items[0]["line"],
            **metrics,
        })
    return results


def _sentence_records(records: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    sentences: List[Dict[str, Any]] = []
    for record in records:
        for match in re.finditer(r"[^.!?]+(?:[.!?]+|$)", record["text"]):
            sentence = match.group(0).strip()
            words = WORD_PATTERN.findall(sentence)
            if words:
                sentences.append({**record, "text": sentence, "word_count": len(words)})
    return sentences


def _difficult_words(records: Iterable[Dict[str, Any]], config: Dict[str, Any]) -> List[Dict[str, Any]]:
    ignored = set(config["ignorar_palavras"])
    occurrences: Dict[str, List[int]] = {}
    display: Dict[str, str] = {}
    first_chapter: Dict[str, str] = {}
    for record in records:
        for word in WORD_PATTERN.findall(record["text"]):
            lowered = word.lower()
            if (
                lowered in ignored
                or len(lowered) < int(config["min_letras_palavra_dificil"])
                or count_syllables_ptbr(lowered) < int(config["silabas_palavra_dificil"])
            ):
                continue
            display.setdefault(lowered, word)
            first_chapter.setdefault(lowered, record["chapter"])
            occurrences.setdefault(lowered, []).append(record["line"])
    ranked = sorted(occurrences, key=lambda word: (-len(occurrences[word]), word))
    return [
        {
            "word": display[word],
            "count": len(occurrences[word]),
            "syllables_estimate": count_syllables_ptbr(word),
            "first_line": occurrences[word][0],
            "first_chapter": first_chapter[word],
        }
        for word in ranked
    ]


def analyze_readability(text: str, book_config: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """Produz métricas globais e locais sem confundir legibilidade com qualidade."""
    config = resolve_readability_config(book_config or {})
    records = _content_lines(text)
    sentences = _sentence_records(records)
    chapters = _group_metrics(records, ["chapter"])
    sections = _group_metrics(records, ["chapter", "section"])
    content_types = _group_metrics(records, ["type"])
    all_long_sentences = [
        sentence for sentence in sentences
        if sentence["word_count"] > int(config["max_palavras_frase"])
    ]
    paragraphs = []
    for record in records:
        if len(WORD_PATTERN.findall(record["text"])) < 12:
            continue
        metrics = calculate_flesch_siqueira(record["text"])
        paragraphs.append({**record, **metrics})
    hardest = sorted(paragraphs, key=lambda item: item["flesch_score"])[: int(config["max_itens_relatorio"])]
    overall = calculate_flesch_siqueira("\n".join(record["text"] for record in records))
    all_difficult_words = _difficult_words(records, config)
    report_limit = int(config["max_itens_relatorio"])
    return {
        "framework": "Flesch adaptado ao português + heurísticas editoriais locais",
        "disclaimer": "Legibilidade estima esforço de leitura; não mede qualidade literária nem adequação temática.",
        "config": config,
        "overall": overall,
        "target_met": overall["flesch_score"] >= float(config["min_flesch"]),
        "chapters": chapters,
        "sections": sections,
        "content_types": content_types,
        "long_sentences_total": len(all_long_sentences),
        "long_sentences": all_long_sentences[:report_limit],
        "difficult_words_total": len(all_difficult_words),
        "difficult_words": all_difficult_words[:report_limit],
        "hardest_excerpts": hardest,
    }
