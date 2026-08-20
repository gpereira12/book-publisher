#!/usr/bin/env python3
"""Contrato comum para achados e execuções da revisão editorial."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha1
from typing import Any, Dict, List, Optional
import re


SCHEMA_VERSION = "1.0"
VALID_SEVERITIES = {"informacao", "observacao", "alerta", "erro", "bloqueador"}


@dataclass(frozen=True)
class Finding:
    id: str
    rule: str
    category: str
    severity: str
    confidence: float
    chapter: Optional[str]
    line: Optional[int]
    excerpt: str
    explanation: str
    suggestion: Optional[str]
    auto_fixable: bool = False

    def __post_init__(self) -> None:
        if self.severity not in VALID_SEVERITIES:
            raise ValueError(f"Severidade inválida: {self.severity}")
        if not 0 <= self.confidence <= 1:
            raise ValueError("A confiança deve estar entre 0 e 1")

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def stable_finding_id(rule: str, line: Optional[int], excerpt: str) -> str:
    """Cria um identificador estável enquanto regra, linha e trecho não mudarem."""
    normalized = re.sub(r"\s+", " ", excerpt.strip().lower())
    digest = sha1(f"{rule}|{line or 0}|{normalized}".encode("utf-8")).hexdigest()[:10]
    return f"REV-{digest.upper()}"


def locate_excerpt(text: str, excerpt: str) -> tuple[Optional[int], Optional[str]]:
    """Localiza a primeira ocorrência e o último título Markdown anterior."""
    needle = excerpt.strip()
    position = text.lower().find(needle.lower()) if needle else -1
    if position < 0:
        return None, None

    line_number = text.count("\n", 0, position) + 1
    chapter: Optional[str] = None
    for line in text[:position].splitlines():
        match = re.match(r"^#{1,3}\s+(.+?)\s*$", line)
        if match:
            chapter = match.group(1)
    return line_number, chapter


def make_finding(
    *,
    text: str,
    rule: str,
    category: str,
    severity: str,
    confidence: float,
    excerpt: str,
    explanation: str,
    suggestion: Optional[str] = None,
    auto_fixable: bool = False,
    line: Optional[int] = None,
    chapter: Optional[str] = None,
) -> Finding:
    if line is None:
        located_line, located_chapter = locate_excerpt(text, excerpt)
        line = located_line
        chapter = chapter or located_chapter
    return Finding(
        id=stable_finding_id(rule, line, excerpt),
        rule=rule,
        category=category,
        severity=severity,
        confidence=round(confidence, 2),
        chapter=chapter,
        line=line,
        excerpt=re.sub(r"\s+", " ", excerpt.strip())[:320],
        explanation=explanation,
        suggestion=suggestion,
        auto_fixable=auto_fixable,
    )


def summarize_findings(findings: List[Finding]) -> Dict[str, Dict[str, int]]:
    by_severity: Dict[str, int] = {}
    by_category: Dict[str, int] = {}
    for finding in findings:
        by_severity[finding.severity] = by_severity.get(finding.severity, 0) + 1
        by_category[finding.category] = by_category.get(finding.category, 0) + 1
    return {"by_severity": by_severity, "by_category": by_category}
