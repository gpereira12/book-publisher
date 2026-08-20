#!/usr/bin/env python3
"""Coerência e continuidade interna por registros narrativos configuráveis."""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
import re
import unicodedata
from typing import Any, Dict, Iterable, List


NUMBER_WORDS = {
    "zero": 0, "um": 1, "uma": 1, "dois": 2, "duas": 2, "tres": 3,
    "quatro": 4, "cinco": 5, "seis": 6, "sete": 7, "oito": 8, "nove": 9,
    "dez": 10, "onze": 11, "doze": 12, "treze": 13, "catorze": 14,
    "quatorze": 14, "quinze": 15, "dezesseis": 16, "dezessete": 17,
    "dezoito": 18, "dezenove": 19, "vinte": 20, "trinta": 30,
    "quarenta": 40, "cinquenta": 50, "sessenta": 60, "setenta": 70,
    "oitenta": 80, "noventa": 90, "cem": 100, "cento": 100,
}


@dataclass(frozen=True)
class CoherenceIssue:
    rule: str
    subtype: str
    severity: str
    confidence: float
    line: int
    chapter: str | None
    section: str | None
    excerpt: str
    explanation: str
    suggestion: str
    auto_fixable: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _normalize(value: str) -> str:
    decomposed = unicodedata.normalize("NFD", value.casefold())
    return "".join(char for char in decomposed if unicodedata.category(char) != "Mn")


def _records(text: str) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    chapter: str | None = None
    section: str | None = None
    in_frontmatter = False
    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        stripped = raw_line.strip()
        if line_number == 1 and stripped == "---":
            in_frontmatter = True
            continue
        if in_frontmatter:
            if stripped == "---":
                in_frontmatter = False
            continue
        heading = re.match(r"^(#{1,3})\s+(.+?)\s*$", stripped)
        if heading:
            if len(heading.group(1)) == 1:
                chapter = heading.group(2)
                section = None
            else:
                section = heading.group(2)
            continue
        if not stripped or stripped == "---" or stripped.startswith(("![", "```", ":::")):
            continue
        records.append({
            "line": line_number,
            "chapter": chapter,
            "section": section,
            "text": re.sub(r"[*_`]", "", stripped),
        })
    return records


def _scope_key(record: Dict[str, Any], scope: str) -> tuple[Any, ...]:
    if scope == "livro":
        return ("livro",)
    if scope == "secao":
        return (record["chapter"], record["section"])
    return (record["chapter"],)


def _compile_patterns(values: Iterable[str]) -> List[re.Pattern[str]]:
    return [re.compile(value, re.IGNORECASE) for value in values]


def _matching_records(records: List[Dict[str, Any]], patterns: Iterable[str]) -> List[Dict[str, Any]]:
    compiled = _compile_patterns(patterns)
    return [record for record in records if any(pattern.search(record["text"]) for pattern in compiled)]


def _terminal_state_issues(records: List[Dict[str, Any]], rules: List[Dict[str, Any]]) -> List[CoherenceIssue]:
    issues: List[CoherenceIssue] = []
    for rule in rules:
        terminal_patterns = _compile_patterns(rule.get("padroes_terminais", []))
        incompatible_patterns = _compile_patterns(
            rule.get("padroes_incompativeis", rule.get("padroes_atividade", []))
        )
        scope = rule.get("escopo", "capitulo")
        terminal_by_scope: Dict[tuple[Any, ...], Dict[str, Any]] = {}
        reported_terminal_lines: set[int] = set()
        for record in records:
            key = _scope_key(record, scope)
            terminal = terminal_by_scope.get(key)
            if (
                terminal
                and terminal["line"] not in reported_terminal_lines
                and any(pattern.search(record["text"]) for pattern in incompatible_patterns)
            ):
                issues.append(CoherenceIssue(
                    rule="coherence.state.incompatible_after_terminal",
                    subtype="continuidade_de_estado",
                    severity="alerta",
                    confidence=float(rule.get("confianca", 0.9)),
                    line=record["line"], chapter=record["chapter"], section=record["section"],
                    excerpt=f"{terminal['text']} / {record['text']}"[:320],
                    explanation=f"A regra '{rule.get('id', 'estado')}' encontrou uma afirmação incompatível após uma mudança definida como terminal.",
                    suggestion="Confirmar se há reparo, reposição, lembrança, salto temporal ou contradição de continuidade.",
                ))
                reported_terminal_lines.add(terminal["line"])
            if any(pattern.search(record["text"]) for pattern in terminal_patterns):
                terminal_by_scope[key] = record
    return issues


def _sequence_issues(records: List[Dict[str, Any]], rules: List[Dict[str, Any]]) -> List[CoherenceIssue]:
    issues: List[CoherenceIssue] = []
    for rule in rules:
        scope = rule.get("escopo", "capitulo")
        positions: List[tuple[int, Dict[str, Any], str]] = []
        for expected_index, milestone in enumerate(rule.get("marcos", [])):
            matches = _matching_records(records, milestone.get("padroes", []))
            for match in matches:
                positions.append((expected_index, match, milestone.get("id", str(expected_index + 1))))
        positions.sort(key=lambda item: item[1]["line"])
        previous: tuple[int, Dict[str, Any], str] | None = None
        for current in positions:
            if previous and _scope_key(previous[1], scope) == _scope_key(current[1], scope) and current[0] < previous[0]:
                issues.append(CoherenceIssue(
                    rule="coherence.timeline.milestone_order",
                    subtype="cronologia",
                    severity="alerta",
                    confidence=float(rule.get("confianca", 0.9)),
                    line=current[1]["line"], chapter=current[1]["chapter"], section=current[1]["section"],
                    excerpt=f"{previous[1]['text']} / {current[1]['text']}"[:320],
                    explanation=f"O marco '{current[2]}' aparece depois de '{previous[2]}', contrariando a ordem declarada em '{rule.get('id', 'sequencia')}'.",
                    suggestion="Verificar a cronologia ou ajustar a ordem esperada na configuração do livro.",
                ))
            previous = current
    return issues


def _number_value(raw: str) -> int | None:
    normalized = _normalize(raw.strip())
    if normalized.isdigit():
        return int(normalized)
    parts = re.split(r"[\s-]+e?[\s-]*", normalized)
    values = [NUMBER_WORDS[part] for part in parts if part in NUMBER_WORDS]
    return sum(values) if values else None


def _numeric_fact_issues(records: List[Dict[str, Any]], rules: List[Dict[str, Any]]) -> List[CoherenceIssue]:
    issues: List[CoherenceIssue] = []
    for rule in rules:
        patterns = _compile_patterns(rule.get("padroes", []))
        scope = rule.get("escopo", "livro")
        claims: Dict[tuple[Any, ...], tuple[int, Dict[str, Any], str]] = {}
        for record in records:
            for pattern in patterns:
                match = pattern.search(record["text"])
                if not match:
                    continue
                raw_value = match.groupdict().get("valor")
                if raw_value is None:
                    continue
                value = _number_value(raw_value)
                if value is None:
                    continue
                key = _scope_key(record, scope)
                previous = claims.get(key)
                if previous and previous[0] != value:
                    issues.append(CoherenceIssue(
                        rule="coherence.fact.conflicting_quantity",
                        subtype="fato_quantificado",
                        severity="alerta",
                        confidence=float(rule.get("confianca", 0.95)),
                        line=record["line"], chapter=record["chapter"], section=record["section"],
                        excerpt=f"{previous[1]['text']} / {record['text']}"[:320],
                        explanation=f"O fato '{rule.get('id', 'quantidade')}' aparece com os valores {previous[0]} e {value} no mesmo escopo.",
                        suggestion="Confirmar o valor correto e uniformizar as afirmações, salvo se a mudança for explicada pela narrativa.",
                    ))
                else:
                    claims[key] = (value, record, raw_value)
    return issues


def analyze_coherence(text: str, book_config: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """Audita contradições explícitas declaradas sem inferir o sentido completo da obra."""
    book_config = book_config or {}
    config = book_config.get("revisao", {}).get("coerencia", {})
    ignored = set(config.get("ignorar_regras", []))
    max_items = int(config.get("max_itens_relatorio", 100))
    records = _records(text)
    state_rules = config.get("estados", [])
    sequence_rules = config.get("sequencias", [])
    fact_rules = config.get("fatos_numericos", [])
    issues = (
        _terminal_state_issues(records, state_rules)
        + _sequence_issues(records, sequence_rules)
        + _numeric_fact_issues(records, fact_rules)
    )
    issues = [issue for issue in issues if issue.rule not in ignored]
    issues.sort(key=lambda issue: (issue.line, issue.rule))
    summary = Counter(issue.subtype for issue in issues)
    chapters = {record["chapter"] for record in records if record["chapter"]}
    coverage = {
        "states": [
            {
                "id": rule.get("id", "estado"),
                "terminal_matches": len(_matching_records(records, rule.get("padroes_terminais", []))),
                "incompatible_matches": len(_matching_records(
                    records,
                    rule.get("padroes_incompativeis", rule.get("padroes_atividade", [])),
                )),
            }
            for rule in state_rules
        ],
        "sequences": [
            {
                "id": rule.get("id", "sequencia"),
                "milestones": {
                    milestone.get("id", str(index + 1)): len(
                        _matching_records(records, milestone.get("padroes", []))
                    )
                    for index, milestone in enumerate(rule.get("marcos", []))
                },
            }
            for rule in sequence_rules
        ],
        "numeric_facts": [
            {
                "id": rule.get("id", "quantidade"),
                "matches": len(_matching_records(records, rule.get("padroes", []))),
            }
            for rule in fact_rules
        ],
    }
    return {
        "framework": "Registro de continuidade narrativa + restrições declarativas por livro",
        "disclaimer": "O módulo confirma incompatibilidades explícitas configuradas; motivação, causalidade implícita e plausibilidade ainda exigem leitura humana.",
        "config": {
            "max_items": max_items,
            "ignored_rules": sorted(ignored),
            "state_rules": len(state_rules),
            "sequence_rules": len(sequence_rules),
            "numeric_fact_rules": len(fact_rules),
        },
        "metrics": {"records": len(records), "chapters": len(chapters)},
        "coverage": coverage,
        "manual_review_dimensions": [
            "motivacao e causalidade", "objetivos e decisões das personagens",
            "cronologia implícita", "geografia e deslocamentos", "objetos e ferimentos",
            "regras do mundo narrativo", "promessas e resoluções",
        ],
        "total_issues": len(issues),
        "summary": dict(summary),
        "issues": [issue.to_dict() for issue in issues],
        "display_issues": [issue.to_dict() for issue in issues[:max_items]],
    }
