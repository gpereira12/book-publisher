#!/usr/bin/env python3
"""Factualidade, sustentação de alegações e anacronismos configuráveis."""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
import re
from typing import Any, Dict, Iterable, List


REVIEW_STATUSES = {
    "imprecisa", "contestada", "nao_verificada", "fonte_incompativel", "rotulo_enganoso",
}
SUPPORTED_NATURES = {"historica", "tradicao", "lenda"}


@dataclass(frozen=True)
class FactualityIssue:
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
    source_ids: List[str]
    auto_fixable: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


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
            "text": re.sub(r"[*_`]", "", stripped.lstrip("> ")),
        })
    return records


def _compile(patterns: Iterable[str]) -> List[re.Pattern[str]]:
    return [re.compile(pattern, re.IGNORECASE) for pattern in patterns]


def _matches(records: List[Dict[str, Any]], patterns: Iterable[str]) -> List[Dict[str, Any]]:
    compiled = _compile(patterns)
    return [record for record in records if any(pattern.search(record["text"]) for pattern in compiled)]


def _claim_issues(
    records: List[Dict[str, Any]],
    claims: List[Dict[str, Any]],
    sources: Dict[str, Dict[str, Any]],
) -> tuple[List[FactualityIssue], List[Dict[str, Any]]]:
    issues: List[FactualityIssue] = []
    coverage: List[Dict[str, Any]] = []
    for claim in claims:
        matches = _matches(records, claim.get("padroes", []))
        source_ids = list(claim.get("fontes", []))
        missing_source_ids = [source_id for source_id in source_ids if source_id not in sources]
        incomplete_source_ids = [
            source_id for source_id in source_ids
            if source_id in sources and not all(sources[source_id].get(field) for field in ("titulo", "url"))
        ]
        status = claim.get("status", "nao_verificada")
        nature = claim.get("natureza", "historica")
        coverage.append({
            "id": claim.get("id", "alegacao"),
            "nature": nature,
            "status": status,
            "matches": len(matches),
            "source_count": len(source_ids),
        })
        if not matches:
            continue
        first = matches[0]
        if missing_source_ids:
            issues.append(FactualityIssue(
                rule="factuality.source.unknown_reference",
                subtype="fonte",
                severity="erro",
                confidence=1.0,
                line=first["line"], chapter=first["chapter"], section=first["section"],
                excerpt=first["text"][:320],
                explanation=f"A alegação '{claim.get('id', 'alegacao')}' referencia fontes inexistentes na configuração: {', '.join(missing_source_ids)}.",
                suggestion="Cadastrar as fontes ou corrigir seus identificadores.",
                source_ids=source_ids,
            ))
            continue
        if incomplete_source_ids:
            issues.append(FactualityIssue(
                rule="factuality.source.incomplete_metadata",
                subtype="fonte",
                severity="erro",
                confidence=1.0,
                line=first["line"], chapter=first["chapter"], section=first["section"],
                excerpt=first["text"][:320],
                explanation=f"As fontes da alegação '{claim.get('id', 'alegacao')}' não possuem título e URL completos: {', '.join(incomplete_source_ids)}.",
                suggestion="Completar os metadados bibliográficos antes de considerar a alegação sustentada.",
                source_ids=source_ids,
            ))
            continue
        if nature in SUPPORTED_NATURES and not source_ids:
            issues.append(FactualityIssue(
                rule="factuality.source.missing_support",
                subtype="sustentacao",
                severity="alerta",
                confidence=float(claim.get("confianca", 0.85)),
                line=first["line"], chapter=first["chapter"], section=first["section"],
                excerpt=first["text"][:320],
                explanation=f"A alegação '{claim.get('id', 'alegacao')}' é apresentada como {nature}, mas não possui fonte registrada.",
                suggestion=claim.get("sugestao", "Adicionar fonte confiável ou rotular explicitamente como adaptação ficcional."),
                source_ids=[],
            ))
        elif status in REVIEW_STATUSES:
            issues.append(FactualityIssue(
                rule="factuality.claim.review_status",
                subtype="alegacao",
                severity="alerta",
                confidence=float(claim.get("confianca", 0.85)),
                line=first["line"], chapter=first["chapter"], section=first["section"],
                excerpt=first["text"][:320],
                explanation=claim.get("nota", f"A alegação está marcada como '{status}'."),
                suggestion=claim.get("sugestao", "Reformular a alegação ou fortalecer sua sustentação."),
                source_ids=source_ids,
            ))
    return issues, coverage


def _temporal_issues(
    records: List[Dict[str, Any]], rules: List[Dict[str, Any]], sources: Dict[str, Dict[str, Any]],
) -> tuple[List[FactualityIssue], List[Dict[str, Any]]]:
    issues: List[FactualityIssue] = []
    coverage: List[Dict[str, Any]] = []
    for rule in rules:
        ignored_sections = {value.casefold() for value in rule.get("ignorar_secoes", ["Reflexão"])}
        all_matches = _matches(records, rule.get("padroes", []))
        applicable = [
            record for record in all_matches
            if (record["section"] or "").casefold() not in ignored_sections
        ]
        source_ids = list(rule.get("fontes", []))
        coverage.append({
            "id": rule.get("id", "termo_temporal"),
            "matches": len(all_matches),
            "applicable_matches": len(applicable),
        })
        for record in applicable:
            issues.append(FactualityIssue(
                rule="factuality.anachronism.temporal_term",
                subtype="anacronismo",
                severity="alerta",
                confidence=float(rule.get("confianca", 0.95)),
                line=record["line"], chapter=record["chapter"], section=record["section"],
                excerpt=record["text"][:320],
                explanation=rule.get("nota", "O termo não é compatível com o período narrativo configurado."),
                suggestion=rule.get("sugestao", "Substituir por imagem compatível com o universo narrativo."),
                source_ids=[source_id for source_id in source_ids if source_id in sources],
            ))
    return issues, coverage


def analyze_factuality(text: str, book_config: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """Cruza alegações declaradas, fontes e restrições temporais sem consultar a web."""
    book_config = book_config or {}
    config = book_config.get("revisao", {}).get("factualidade", {})
    sources = config.get("fontes", {})
    claims = config.get("alegacoes", [])
    temporal_rules = config.get("termos_temporais", [])
    ignored = set(config.get("ignorar_regras", []))
    max_items = int(config.get("max_itens_relatorio", 100))
    records = _records(text)
    claim_issues, claim_coverage = _claim_issues(records, claims, sources)
    temporal_issues, temporal_coverage = _temporal_issues(records, temporal_rules, sources)
    issues = [issue for issue in claim_issues + temporal_issues if issue.rule not in ignored]
    issues.sort(key=lambda issue: (issue.line, issue.rule))
    summary = Counter(issue.subtype for issue in issues)
    source_types = Counter(source.get("tipo", "nao_informado") for source in sources.values())
    return {
        "framework": "Registro de alegações + proveniência de fontes + restrições temporais",
        "disclaimer": "O motor audita evidência cadastrada e sinais explícitos; não prova verdade histórica nem substitui pesquisa especializada.",
        "config": {
            "max_items": max_items,
            "ignored_rules": sorted(ignored),
            "sources": len(sources),
            "claims": len(claims),
            "temporal_rules": len(temporal_rules),
        },
        "metrics": {
            "records": len(records),
            "source_types": dict(source_types),
            "claims_found": sum(1 for item in claim_coverage if item["matches"]),
        },
        "coverage": {"claims": claim_coverage, "temporal_terms": temporal_coverage},
        "sources": sources,
        "total_issues": len(issues),
        "summary": dict(summary),
        "issues": [issue.to_dict() for issue in issues],
        "display_issues": [issue.to_dict() for issue in issues[:max_items]],
    }
