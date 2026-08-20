#!/usr/bin/env python3
"""Motor de revisão editorial com auditoria segura e achados estruturados."""

from __future__ import annotations

import argparse
import difflib
import json
import re
import shutil
import subprocess
import sys
import textwrap
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any, Dict, List, Tuple

from review_models import Finding, SCHEMA_VERSION, make_finding, summarize_findings
from rules.ai_patterns import analyze_ai_patterns
from rules.cohesion import analyze_cohesion
from rules.coherence import analyze_coherence
from rules.factuality import analyze_factuality
from rules.flesch_readability import analyze_readability
from rules.grammar import analyze_grammar
from rules.point_of_view import audit_point_of_view
from rules.structure import analyze_structure
from rules.style_dreyer import find_crutch_words, find_repeated_words
from rules.style_sheet import check_style_sheet_violations, load_style_sheet
from rules.typography import sanitize_typography


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def resolve_source_file(book_dir: Path, source: str) -> Path:
    original = book_dir / "texto_original.md"
    revised = book_dir / "texto_revisado.md"
    if source == "original":
        selected = original
    elif source == "revised":
        selected = revised
    else:
        selected = revised if revised.exists() else original
    if not selected.exists():
        raise FileNotFoundError(f"Manuscrito não encontrado: {selected}")
    return selected


def backup_file(path: Path, now: datetime | None = None) -> Path:
    """Preserva a versão anterior antes de qualquer escrita no manuscrito ativo."""
    timestamp = (now or utc_now()).strftime("%Y%m%dT%H%M%S%fZ")
    digest = sha256(path.read_bytes()).hexdigest()[:8]
    backup_dir = path.parent / "revisions" / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup = backup_dir / f"{path.stem}_{timestamp}_{digest}{path.suffix}"
    shutil.copy2(path, backup)
    return backup


def write_active_revision(book_dir: Path, content: str) -> Tuple[Path, Path | None]:
    target = book_dir / "texto_revisado.md"
    backup = backup_file(target) if target.exists() else None
    target.write_text(content, encoding="utf-8")
    return target, backup


def write_versioned_revision(book_dir: Path, content: str, now: datetime | None = None) -> Path:
    timestamp = (now or utc_now()).strftime("%Y%m%dT%H%M%S%fZ")
    revision_dir = book_dir / "revisions"
    revision_dir.mkdir(parents=True, exist_ok=True)
    target = revision_dir / f"texto_revisado_{timestamp}.md"
    target.write_text(content, encoding="utf-8")
    return target


def _style_finding(text: str, warning: str) -> Finding:
    term_match = re.search(r"Encontrado(?: termo)? '([^']+)'", warning)
    excerpt = term_match.group(1) if term_match else warning
    is_anachronism = "Anacronismo" in warning
    return make_finding(
        text=text,
        rule="style_sheet.anachronism" if is_anachronism else "style_sheet.spelling",
        category="consistencia_historica" if is_anachronism else "folha_de_estilo",
        severity="alerta" if is_anachronism else "erro",
        confidence=0.9 if is_anachronism else 0.99,
        excerpt=excerpt,
        explanation=warning,
        suggestion="Verificar o contexto histórico." if is_anachronism else "Aplicar a grafia definida na folha de estilo.",
    )


def build_findings(
    text: str,
    style_warnings: List[str],
    crutch_words: Dict[str, int],
    ai_patterns: Dict[str, Any],
    sanitized_content: str,
    readability: Dict[str, Any],
    grammar: Dict[str, Any],
    cohesion: Dict[str, Any],
    coherence: Dict[str, Any],
    factuality: Dict[str, Any],
    structure: Dict[str, Any],
    pov_findings: List[Finding] = None,
) -> List[Finding]:
    """Converte resultados heterogêneos no contrato editorial comum."""
    findings: List[Finding] = [_style_finding(text, warning) for warning in style_warnings]

    for issue in grammar["issues"]:
        suggestion = issue["suggestion"]
        if issue.get("replacement"):
            suggestion += f" Substituição segura proposta: '{issue['replacement']}'."
        findings.append(make_finding(
            text=text,
            rule=issue["rule"],
            category="gramatica",
            severity=issue["severity"],
            confidence=issue["confidence"],
            excerpt=issue["excerpt"],
            explanation=issue["explanation"],
            suggestion=suggestion,
            auto_fixable=issue["auto_fixable"],
            line=issue["line"],
            chapter=issue["chapter"],
        ))

    for issue in cohesion["issues"]:
        findings.append(make_finding(
            text=text,
            rule=issue["rule"],
            category="coesao",
            severity=issue["severity"],
            confidence=issue["confidence"],
            excerpt=issue["excerpt"],
            explanation=issue["explanation"],
            suggestion=issue["suggestion"],
            auto_fixable=False,
            line=issue["line"],
            chapter=issue["chapter"],
        ))

    for issue in coherence["issues"]:
        findings.append(make_finding(
            text=text,
            rule=issue["rule"],
            category="coerencia",
            severity=issue["severity"],
            confidence=issue["confidence"],
            excerpt=issue["excerpt"],
            explanation=issue["explanation"],
            suggestion=issue["suggestion"],
            auto_fixable=False,
            line=issue["line"],
            chapter=issue["chapter"],
        ))

    for issue in factuality["issues"]:
        source_note = f" Fontes registradas: {', '.join(issue['source_ids'])}." if issue["source_ids"] else ""
        findings.append(make_finding(
            text=text,
            rule=issue["rule"],
            category="factualidade",
            severity=issue["severity"],
            confidence=issue["confidence"],
            excerpt=issue["excerpt"],
            explanation=issue["explanation"] + source_note,
            suggestion=issue["suggestion"],
            auto_fixable=False,
            line=issue["line"],
            chapter=issue["chapter"],
        ))

    for issue in structure["issues"]:
        findings.append(make_finding(
            text=text,
            rule=issue["rule"],
            category="estrutura",
            severity=issue["severity"],
            confidence=issue["confidence"],
            excerpt=issue["excerpt"],
            explanation=issue["explanation"],
            suggestion=issue["suggestion"],
            auto_fixable=False,
            line=issue["line"],
            chapter=issue["chapter"],
        ))

    if pov_findings:
        findings.extend(pov_findings)

    for word, count in crutch_words.items():
        findings.append(make_finding(
            text=text,
            rule="style.crutch_word",
            category="estilo",
            severity="observacao",
            confidence=0.65,
            excerpt=word,
            explanation=f"O termo aparece {count} vez(es) no manuscrito.",
            suggestion="Avaliar cada ocorrência; manter quando acrescentar precisão ou caracterizar a voz.",
        ))

    readability_config = readability["config"]
    minimum_score = float(readability_config["min_flesch"])
    if not readability["target_met"]:
        overall_score = readability["overall"]["flesch_score"]
        findings.append(make_finding(
            text=text,
            rule="readability.global_target",
            category="legibilidade",
            severity="alerta",
            confidence=0.75,
            excerpt=f"Pontuação global: {overall_score}",
            explanation=f"A pontuação global ficou abaixo da meta editorial de {minimum_score}.",
            suggestion="Examinar as seções e os trechos mais densos; a métrica não exige simplificação automática.",
            line=1,
        ))
    for section in readability["sections"]:
        if (
            section["total_palavras"] < int(readability_config["min_palavras_secao"])
            or section["flesch_score"] >= minimum_score
        ):
            continue
        findings.append(make_finding(
            text=text,
            rule="readability.section_below_target",
            category="legibilidade",
            severity="observacao",
            confidence=0.7,
            excerpt=f"{section['chapter']} — {section['section']}",
            explanation=f"A seção marcou {section['flesch_score']}, abaixo da meta editorial de {minimum_score}.",
            suggestion="Revisar os trechos mais densos, preservando vocabulário e ritmo quando forem deliberados.",
            line=section["start_line"],
            chapter=section["chapter"],
        ))
    for sentence in readability["long_sentences"]:
        findings.append(make_finding(
            text=text,
            rule="readability.long_sentence",
            category="legibilidade",
            severity="observacao",
            confidence=0.85,
            excerpt=sentence["text"],
            explanation=f"A frase tem {sentence['word_count']} palavras; o limite editorial é {readability_config['max_palavras_frase']}.",
            suggestion="Ler em voz alta e considerar divisão apenas se houver perda de fôlego ou clareza.",
            line=sentence["line"],
            chapter=sentence["chapter"],
        ))
    for word in readability["difficult_words"]:
        findings.append(make_finding(
            text=text,
            rule="readability.potentially_difficult_word",
            category="legibilidade",
            severity="informacao",
            confidence=0.5,
            excerpt=word["word"],
            explanation=f"Palavra com aproximadamente {word['syllables_estimate']} sílabas, encontrada {word['count']} vez(es).",
            suggestion="Verificar se o contexto permite compreendê-la; não substituir automaticamente.",
            line=word["first_line"],
            chapter=word["first_chapter"],
        ))

    assessment = ai_patterns.get("assessment", {})
    formulaic_severity = "alerta" if assessment.get("review_recommended") else "informacao"
    formulaic_confidence = 0.8 if assessment.get("review_recommended") else 0.55
    formulaic_groups = {
        "antithesis": ("style.formulaic_antithesis", "Antítese espelhada"),
        "rhetorical_qa": ("style.formulaic_rhetorical_qa", "Pergunta retórica com resposta imediata"),
        "anaphora": ("style.formulaic_anaphora", "Três ou mais frases paralelas"),
        "dash_overuse": ("style.parenthetical_dash_overuse", "Travessões parentéticos em excesso"),
    }
    for key, (rule, explanation) in formulaic_groups.items():
        for excerpt in ai_patterns.get(key, []):
            findings.append(make_finding(
                text=text,
                rule=rule,
                category="prosa_formulaica",
                severity=formulaic_severity,
                confidence=formulaic_confidence,
                excerpt=excerpt,
                explanation=explanation,
                suggestion="Revisar apenas se o recurso estiver concentrado ou tornar a cadência previsível.",
            ))
    for phrase, count in ai_patterns.get("meta_announcements", {}).items():
        findings.append(make_finding(
            text=text,
            rule="style.meta_announcement",
            category="prosa_formulaica",
            severity=formulaic_severity,
            confidence=formulaic_confidence,
            excerpt=phrase,
            explanation=f"Anúncio metatextual encontrado {count} vez(es).",
            suggestion="Considerar apresentar a ideia diretamente.",
        ))

    original_lines = text.splitlines()
    sanitized_lines = sanitized_content.splitlines()
    for index, (before, after) in enumerate(zip(original_lines, sanitized_lines), start=1):
        if before == after:
            continue
        findings.append(make_finding(
            text=text,
            rule="typography.safe_normalization",
            category="tipografia",
            severity="erro",
            confidence=0.99,
            excerpt=before or after,
            explanation="A linha contém uma normalização tipográfica segura.",
            suggestion=after,
            auto_fixable=True,
            line=index,
        ))
    return findings


def derive_verdict(findings: List[Finding]) -> Tuple[str, str]:
    if any(f.severity in {"erro", "bloqueador"} for f in findings):
        return "revisao_necessaria", "O manuscrito requer **REVISÃO** antes do Layout; há correções objetivas pendentes."
    if any(f.severity == "alerta" for f in findings):
        return "revisao_recomendada", "O manuscrito está **EM REVISÃO**; existem alertas que pedem julgamento editorial."
    if findings:
        return "aprovado_com_observacoes", "O manuscrito está **APROVADO COM OBSERVAÇÕES**; não há impedimentos objetivos."
    return "aprovado", "O manuscrito está **APROVADO** para o Layout (Projeto 3 — Diagramação)."


def generate_review_report(
    *,
    book_id: str,
    mode: str,
    source_file: Path,
    grammar: Dict[str, Any],
    cohesion: Dict[str, Any],
    coherence: Dict[str, Any],
    factuality: Dict[str, Any],
    structure: Dict[str, Any],
    readability: Dict[str, Any],
    crutch_words: Dict[str, int],
    repeated_words: List[Any],
    corrections_count: int,
    style_warnings: List[str],
    ai_patterns: Dict[str, Any],
    findings: List[Finding],
    verdict_text: str,
) -> str:
    summary = summarize_findings(findings)
    assessment = ai_patterns.get("assessment", {})
    flesch_data = readability["overall"]
    readability_config = readability["config"]
    grammar_lines = [
        "---",
        "## 1. Gramática e correção linguística",
        f"- **Framework:** {grammar['framework']}",
        f"- **Variante:** `{grammar['config']['variant']}`",
        f"- **Nível:** `{grammar['config']['level']}`",
        f"- **Regras locais ativas:** `{grammar['active_pattern_rules']}`",
        f"- **Verificações globais de delimitadores:** `{grammar['global_balance_checks']}`",
        f"- **Categorias cobertas:** `{', '.join(grammar['covered_subcategories'])}`",
        f"- **Total de achados:** `{grammar['total_issues']}`",
        f"- **Autocorrigíveis com aplicação explícita:** `{grammar['auto_fixable_count']}`",
        f"- **Por categoria:** `{json.dumps(grammar['summary'], ensure_ascii=False)}`",
        f"- **Limitação:** {grammar['disclaimer']}",
    ]
    if grammar["display_issues"]:
        grammar_lines.extend([
            "",
            "| Linha | Contexto | Categoria | Gravidade | Regra | Trecho |",
            "|---:|---|---|---|---|---|",
        ])
        for issue in grammar["display_issues"]:
            excerpt = issue["excerpt"].replace("|", "\\|")
            grammar_lines.append(
                f"| {issue['line']} | {issue['context']} | {issue['subcategory']} | {issue['severity']} "
                f"| `{issue['rule']}` | {excerpt} |"
            )
    else:
        grammar_lines.append("✅ Nenhum caso coberto pelas regras conservadoras foi encontrado.")
    cohesion_lines = [
        "",
        "---",
        "## 2. Coesão e conexão de ideias",
        f"- **Framework:** {cohesion['framework']}",
        f"- **Entidades configuradas:** `{cohesion['config']['configured_entities']}`",
        f"- **Parágrafos analisados:** `{cohesion['metrics']['paragraphs']}`",
        f"- **Frases analisadas:** `{cohesion['metrics']['sentences']}`",
        f"- **Conectores iniciais por mil palavras:** `{cohesion['metrics']['leading_connectors_per_1000_words']}`",
        f"- **Total de achados:** `{cohesion['total_issues']}`",
        f"- **Por tipo:** `{json.dumps(cohesion['summary'], ensure_ascii=False)}`",
        f"- **Limitação:** {cohesion['disclaimer']}",
    ]
    if cohesion["display_issues"]:
        cohesion_lines.extend([
            "",
            "| Linha | Contexto | Tipo | Gravidade | Regra | Trecho |",
            "|---:|---|---|---|---|---|",
        ])
        for issue in cohesion["display_issues"]:
            excerpt = textwrap.shorten(issue["excerpt"].replace("|", "\\|"), width=120, placeholder="…")
            cohesion_lines.append(
                f"| {issue['line']} | {issue['context']} | {issue['subtype']} | {issue['severity']} "
                f"| `{issue['rule']}` | {excerpt} |"
            )
    else:
        cohesion_lines.append("✅ Nenhum caso coberto pelas heurísticas de coesão foi encontrado.")
    coherence_lines = [
        "",
        "---",
        "## 3. Coerência e continuidade interna",
        f"- **Framework:** {coherence['framework']}",
        f"- **Capítulos analisados:** `{coherence['metrics']['chapters']}`",
        f"- **Regras de estado:** `{coherence['config']['state_rules']}`",
        f"- **Regras de sequência:** `{coherence['config']['sequence_rules']}`",
        f"- **Regras de fatos numéricos:** `{coherence['config']['numeric_fact_rules']}`",
        f"- **Total de achados:** `{coherence['total_issues']}`",
        f"- **Por tipo:** `{json.dumps(coherence['summary'], ensure_ascii=False)}`",
        f"- **Cobertura das regras configuradas:** `{json.dumps(coherence['coverage'], ensure_ascii=False)}`",
        f"- **Limitação:** {coherence['disclaimer']}",
    ]
    if coherence["display_issues"]:
        coherence_lines.extend([
            "",
            "| Linha | Tipo | Gravidade | Regra | Trecho |",
            "|---:|---|---|---|---|",
        ])
        for issue in coherence["display_issues"]:
            excerpt = textwrap.shorten(issue["excerpt"].replace("|", "\\|"), width=120, placeholder="…")
            coherence_lines.append(
                f"| {issue['line']} | {issue['subtype']} | {issue['severity']} "
                f"| `{issue['rule']}` | {excerpt} |"
            )
    else:
        coherence_lines.append("✅ Nenhuma incompatibilidade coberta pelas regras configuradas foi encontrada.")
    coherence_lines.extend([
        "",
        "Dimensões que continuam exigindo leitura humana: "
        + ", ".join(coherence["manual_review_dimensions"]) + ".",
    ])
    factuality_lines = [
        "",
        "---",
        "## 4. Factualidade, fontes, anacronismos e sustentação",
        f"- **Framework:** {factuality['framework']}",
        f"- **Fontes registradas:** `{factuality['config']['sources']}`",
        f"- **Alegações registradas:** `{factuality['config']['claims']}`",
        f"- **Alegações localizadas:** `{factuality['metrics']['claims_found']}`",
        f"- **Regras temporais:** `{factuality['config']['temporal_rules']}`",
        f"- **Total de achados:** `{factuality['total_issues']}`",
        f"- **Por tipo:** `{json.dumps(factuality['summary'], ensure_ascii=False)}`",
        f"- **Limitação:** {factuality['disclaimer']}",
    ]
    if factuality["display_issues"]:
        factuality_lines.extend([
            "",
            "| Linha | Tipo | Gravidade | Regra | Fontes | Trecho |",
            "|---:|---|---|---|---|---|",
        ])
        for issue in factuality["display_issues"]:
            excerpt = textwrap.shorten(issue["excerpt"].replace("|", "\\|"), width=105, placeholder="…")
            source_ids = ", ".join(issue["source_ids"]) or "—"
            factuality_lines.append(
                f"| {issue['line']} | {issue['subtype']} | {issue['severity']} | `{issue['rule']}` "
                f"| {source_ids} | {excerpt} |"
            )
    else:
        factuality_lines.append("✅ Nenhuma lacuna coberta pelo registro factual foi encontrada.")
    factuality_lines.extend(["", "### Fontes cadastradas", ""])
    for source_id, source in factuality["sources"].items():
        source_title = source.get("titulo", source_id)
        source_url = source.get("url", "")
        source_type = source.get("tipo", "não informado")
        accessed = source.get("acesso", "não informado")
        label = f"[{source_title}]({source_url})" if source_url else source_title
        factuality_lines.append(
            f"- `{source_id}` — {label}; tipo: `{source_type}`; acesso: `{accessed}`."
        )
    structure_lines = [
        "",
        "---",
        "## 5. Estrutura conforme o framework do livro",
        f"- **Framework:** {structure['framework']}",
        f"- **Framework esperado:** `{structure['config']['framework_expected']}`",
        f"- **Capítulos de conteúdo:** `{structure['metrics']['content_chapters']}`",
        f"- **Seções obrigatórias deste livro:** `{', '.join(structure['config']['required_sections']) or 'nenhuma'}`",
        f"- **Elementos obrigatórios deste livro:** `{json.dumps(structure['config']['required_elements'], ensure_ascii=False)}`",
        f"- **Total de achados:** `{structure['total_issues']}`",
        f"- **Por tipo:** `{json.dumps(structure['summary'], ensure_ascii=False)}`",
        f"- **Limitação:** {structure['disclaimer']}",
    ]
    if structure["display_issues"]:
        structure_lines.extend([
            "",
            "| Linha | Capítulo | Tipo | Gravidade | Regra | Trecho |",
            "|---:|---|---|---|---|---|",
        ])
        for issue in structure["display_issues"]:
            excerpt = textwrap.shorten(issue["excerpt"].replace("|", "\\|"), width=90, placeholder="…")
            structure_lines.append(
                f"| {issue['line']} | {issue['chapter'] or '—'} | {issue['subtype']} | {issue['severity']} "
                f"| `{issue['rule']}` | {excerpt} |"
            )
    else:
        structure_lines.append("✅ Todos os requisitos estruturais configurados foram atendidos.")
    lines = [
        f"# Relatório de Revisão Editorial: {book_id}",
        "",
        f"- **Modo:** `{mode}`",
        f"- **Fonte auditada:** `{source_file}`",
        f"- **Versão do esquema:** `{SCHEMA_VERSION}`",
        f"- **Total de achados:** `{len(findings)}`",
        f"- **Por gravidade:** `{json.dumps(summary['by_severity'], ensure_ascii=False)}`",
        "",
        *grammar_lines,
        *cohesion_lines,
        *coherence_lines,
        *factuality_lines,
        *structure_lines,
        "",
        "---",
        "## 7. Legibilidade (linha de base; validação final adiada)",
        f"- **Pontuação:** `{flesch_data['flesch_score']}/100`",
        f"- **Classificação:** **{flesch_data['classificacao']}**",
        f"- **Total de palavras:** `{flesch_data['total_palavras']}`",
        f"- **Total de frases:** `{flesch_data['total_frases']}`",
        f"- **Média de palavras por frase:** `{flesch_data['media_palavras_por_frase']}`",
        f"- **Média de sílabas por palavra:** `{flesch_data['media_silabas_por_palavra']}`",
        f"- **Meta editorial:** `{readability_config['min_flesch']}`",
        f"- **Meta atingida:** `{'sim' if readability['target_met'] else 'não'}`",
        f"- **Faixa etária configurada:** `{readability_config.get('faixa_etaria') or 'não informada'}`",
        f"- **Nota:** {readability['disclaimer']}",
        "",
        "### Por capítulo/conto",
        "",
        "| Capítulo | Linha | Palavras | Flesch | Classificação |",
        "|---|---:|---:|---:|---|",
    ]
    for chapter in readability["chapters"]:
        lines.append(
            f"| {chapter['chapter']} | {chapter['start_line']} | {chapter['total_palavras']} "
            f"| {chapter['flesch_score']} | {chapter['classificacao']} |"
        )
    lines.extend([
        "",
        "### Por seção",
        "",
        "| Capítulo | Seção | Linha | Palavras | Flesch |",
        "|---|---|---:|---:|---:|",
    ])
    for section in readability["sections"]:
        lines.append(
            f"| {section['chapter']} | {section['section']} | {section['start_line']} "
            f"| {section['total_palavras']} | {section['flesch_score']} |"
        )
    lines.extend([
        "",
        "### Por tipo de conteúdo",
        "",
        "| Tipo | Palavras | Frases | Flesch |",
        "|---|---:|---:|---:|",
    ])
    for content_type in readability["content_types"]:
        lines.append(
            f"| {content_type['type']} | {content_type['total_palavras']} "
            f"| {content_type['total_frases']} | {content_type['flesch_score']} |"
        )
    lines.extend([
        "",
        "### Sinais locais",
        f"- **Frases acima de {readability_config['max_palavras_frase']} palavras:** `{readability['long_sentences_total']}` no total; `{len(readability['long_sentences'])}` exibida(s)",
        f"- **Palavras potencialmente difíceis:** `{readability['difficult_words_total']}` no total; `{len(readability['difficult_words'])}` exibida(s)",
        "- **Trechos mais densos:**",
    ])
    for excerpt in readability["hardest_excerpts"][:5]:
        compact = textwrap.shorten(excerpt["text"].replace("|", "\\|"), width=180, placeholder="…")
        lines.append(f"  - Linha {excerpt['line']} — Flesch `{excerpt['flesch_score']}`: “{compact}”")
    lines.extend([
        "",
        "---",
        "## Análise complementar — Folha de estilo e anacronismos",
    ])
    lines.extend([f"- ⚠️ {warning}" for warning in style_warnings] or ["✅ Nenhuma violação encontrada."])
    lines.extend(["", "---", "## Análise complementar — Palavras-muleta"])
    lines.extend(
        [f"- **{word}:** `{count}` ocorrência(s)" for word, count in crutch_words.items()]
        or ["✅ Nenhuma palavra-muleta cadastrada foi encontrada."]
    )
    lines.extend(["", "---", "## Análise complementar — Marcadores de prosa formulaica"])
    if assessment.get("total_flags", 0):
        lines.extend([
            f"- **Avaliação:** {assessment.get('label')}",
            f"- **Densidade:** `{assessment.get('flags_per_1000_words')}` por mil palavras",
            "- Marcadores estilísticos não determinam autoria.",
        ])
    else:
        lines.append("✅ Nenhum marcador relevante encontrado.")
    lines.extend(["", "---", "## Análise complementar — Frequência lexical"])
    lines.extend([f"- **{word}:** `{count}` ocorrências" for word, count in repeated_words])
    lines.extend([
        "",
        "---",
        "## Análise complementar — Sanitização tipográfica",
        f"- **Correções seguras detectadas:** `{corrections_count}`",
        f"- **Aplicadas ao manuscrito:** `{'sim' if mode == 'apply-safe-fixes' else 'não'}`",
        "",
        "---",
        "## Registro estruturado de achados",
    ])
    if not findings:
        lines.append("✅ Nenhum achado registrado.")
    for finding in findings:
        location = f"linha {finding.line}" if finding.line else "localização não determinada"
        if finding.chapter:
            location += f", {finding.chapter}"
        lines.extend([
            "",
            f"### {finding.id} — {finding.rule}",
            f"- **Categoria:** `{finding.category}`",
            f"- **Gravidade:** `{finding.severity}`",
            f"- **Confiança:** `{finding.confidence:.0%}`",
            f"- **Local:** {location}",
            f"- **Trecho:** “{finding.excerpt}”",
            f"- **Explicação:** {finding.explanation}",
            f"- **Sugestão:** {finding.suggestion or 'Revisão humana.'}",
            f"- **Autocorrigível:** `{'sim' if finding.auto_fixable else 'não'}`",
        ])
    lines.extend(["", "---", "## Veredito editorial", verdict_text])
    return "\n".join(lines) + "\n"


def create_comparison_report(original: Path, revised: Path) -> str:
    original_text = original.read_text(encoding="utf-8").splitlines()
    revised_text = revised.read_text(encoding="utf-8").splitlines()
    diff = list(difflib.unified_diff(
        original_text,
        revised_text,
        fromfile=str(original),
        tofile=str(revised),
        lineterm="",
    ))
    added = sum(1 for line in diff if line.startswith("+") and not line.startswith("+++"))
    removed = sum(1 for line in diff if line.startswith("-") and not line.startswith("---"))
    body = "\n".join(diff) if diff else "Sem diferenças."
    return (
        "# Comparação entre original e revisado\n\n"
        f"- **Linhas adicionadas:** `{added}`\n"
        f"- **Linhas removidas:** `{removed}`\n\n"
        "```diff\n"
        f"{body}\n"
        "```\n"
    )


def trigger_layout_diagramming(book_id: str) -> None:
    print(f"\n🚀 [--auto-approve] Disparando Layout para '{book_id}'...")
    config = load_style_sheet(Path("inputs") / book_id / "book_config.yaml")
    cmd = [
        sys.executable,
        "3-layout/main.py",
        "--book-dir", book_id,
        "--format", config.get("formato", "A5"),
        "--theme", config.get("tema", "Creme"),
        "--author", config.get("autor", "Autor"),
        "--title", config.get("titulo", book_id),
        "--cover", "none",
        "--targets", "pdf_print,pdf_digital,epub",
    ]
    subprocess.run(cmd, check=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Edit: revisão editorial segura e rastreável")
    parser.add_argument("--book-dir", required=True, help="Nome da pasta do livro em inputs/")
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--audit", dest="mode", action="store_const", const="audit", help="Somente audita; não altera manuscritos (padrão)")
    modes.add_argument("--apply-safe-fixes", dest="mode", action="store_const", const="apply-safe-fixes", help="Aplica correções mecânicas, criando backup antes da escrita")
    modes.add_argument("--create-revision", dest="mode", action="store_const", const="create-revision", help="Cria uma versão datada sem alterar o manuscrito ativo")
    modes.add_argument("--compare", dest="mode", action="store_const", const="compare", help="Compara texto_original.md e texto_revisado.md")
    parser.set_defaults(mode="audit")
    parser.add_argument("--source", choices=("auto", "original", "revised"), default="auto", help="Fonte da auditoria; auto prefere o revisado existente")
    parser.add_argument("--auto-approve", action="store_true", help="Dispara o Layout após --apply-safe-fixes")
    args = parser.parse_args()
    if args.auto_approve and args.mode != "apply-safe-fixes":
        parser.error("--auto-approve exige --apply-safe-fixes para impedir o uso de uma revisão desatualizada")
    return args


def main() -> None:
    args = parse_args()
    book_dir = Path("inputs") / args.book_dir
    report_dir = Path("outputs") / args.book_dir / "relatorios"
    report_dir.mkdir(parents=True, exist_ok=True)

    if args.mode == "compare":
        original = book_dir / "texto_original.md"
        revised = book_dir / "texto_revisado.md"
        if not original.exists() or not revised.exists():
            raise SystemExit("❌ A comparação exige texto_original.md e texto_revisado.md")
        comparison_file = report_dir / "comparacao_original_revisado.md"
        comparison_file.write_text(create_comparison_report(original, revised), encoding="utf-8")
        print(f"📊 [Edit] Comparação gerada em: {comparison_file}")
        return

    try:
        source_file = resolve_source_file(book_dir, args.source)
    except FileNotFoundError as error:
        raise SystemExit(f"❌ {error}") from error

    print(f"🔍 [Edit] Auditando manuscrito sem sobrescrita implícita: {source_file}...")
    raw_content = source_file.read_text(encoding="utf-8")
    style_sheet = load_style_sheet(book_dir / "style_sheet.yaml")
    book_config = load_style_sheet(book_dir / "book_config.yaml")
    style_warnings = check_style_sheet_violations(raw_content, style_sheet)
    grammar = analyze_grammar(raw_content, book_config)
    cohesion = analyze_cohesion(raw_content, book_config)
    coherence = analyze_coherence(raw_content, book_config)
    factuality = analyze_factuality(raw_content, book_config)
    structure = analyze_structure(raw_content, book_config, book_dir)
    pov_findings = audit_point_of_view(raw_content, book_config)
    readability = analyze_readability(raw_content, book_config)
    crutch_words = find_crutch_words(raw_content)
    repeated_words = find_repeated_words(raw_content)
    ai_patterns = analyze_ai_patterns(raw_content)
    typography_preview, _ = sanitize_typography(raw_content)
    sanitized_content, post_grammar_typography_count = sanitize_typography(grammar["corrected_text"])
    corrections_count = grammar["auto_fixable_count"] + post_grammar_typography_count
    findings = build_findings(
        raw_content,
        style_warnings,
        crutch_words,
        ai_patterns,
        typography_preview,
        readability,
        grammar,
        cohesion,
        coherence,
        factuality,
        structure,
        pov_findings=pov_findings,
    )
    verdict_code, verdict_text = derive_verdict(findings)

    if args.mode == "apply-safe-fixes":
        target = book_dir / "texto_revisado.md"
        if corrections_count or not target.exists():
            target, backup = write_active_revision(book_dir, sanitized_content)
            print(f"✨ [Edit] Revisão ativa salva em: {target}")
            if backup:
                print(f"🛡️ [Edit] Versão anterior preservada em: {backup}")
        else:
            print("✅ [Edit] Nenhuma correção segura pendente; manuscrito ativo preservado.")
    elif args.mode == "create-revision":
        revision_file = write_versioned_revision(book_dir, sanitized_content)
        print(f"✨ [Edit] Nova versão criada em: {revision_file}")

    generated_at = utc_now().isoformat()
    report_file = report_dir / "relatorio_revisao.md"
    findings_file = report_dir / "achados_revisao.json"
    report_file.write_text(generate_review_report(
        book_id=args.book_dir,
        mode=args.mode,
        source_file=source_file,
        grammar=grammar,
        cohesion=cohesion,
        coherence=coherence,
        factuality=factuality,
        structure=structure,
        readability=readability,
        crutch_words=crutch_words,
        repeated_words=repeated_words,
        corrections_count=corrections_count,
        style_warnings=style_warnings,
        ai_patterns=ai_patterns,
        findings=findings,
        verdict_text=verdict_text,
    ), encoding="utf-8")
    findings_payload = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": generated_at,
        "book_id": args.book_dir,
        "mode": args.mode,
        "source_file": str(source_file),
        "source_sha256": sha256(raw_content.encode("utf-8")).hexdigest(),
        "verdict": verdict_code,
        "summary": summarize_findings(findings),
        "metrics": {
            "grammar": {key: value for key, value in grammar.items() if key != "corrected_text"},
            "cohesion": cohesion,
            "coherence": coherence,
            "factuality": factuality,
            "structure": structure,
            "readability": readability,
            "formulaic_prose": ai_patterns.get("assessment", {}),
        },
        "findings": [finding.to_dict() for finding in findings],
    }
    findings_file.write_text(json.dumps(findings_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"📊 [Edit] Relatório gerado em: {report_file}")
    print(f"🧩 [Edit] Achados estruturados em: {findings_file}")

    if args.auto_approve:
        trigger_layout_diagramming(args.book_dir)


if __name__ == "__main__":
    main()
