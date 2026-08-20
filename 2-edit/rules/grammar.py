#!/usr/bin/env python3
"""Revisão gramatical conservadora para português brasileiro.

O módulo cobre somente construções determinísticas ou de alta confiança. Casos
que exigem interpretação recebem alerta/observação e nunca são autocorrigidos.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import re
from typing import Any, Callable, Dict, List, Match, Pattern


Replacement = str | Callable[[Match[str]], str]


@dataclass(frozen=True)
class GrammarRule:
    code: str
    subcategory: str
    pattern: Pattern[str]
    explanation: str
    suggestion: str
    severity: str
    confidence: float
    auto_fixable: bool = False
    replacement: Replacement | None = None


@dataclass(frozen=True)
class GrammarIssue:
    rule: str
    subcategory: str
    severity: str
    confidence: float
    line: int
    chapter: str | None
    context: str
    excerpt: str
    explanation: str
    suggestion: str
    auto_fixable: bool
    replacement: str | None = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _word_rule(code: str, wrong: str, correct: str) -> GrammarRule:
    return GrammarRule(
        code=code,
        subcategory="ortografia",
        pattern=re.compile(rf"\b{re.escape(wrong)}\b", re.IGNORECASE),
        explanation=f"A forma '{wrong}' não corresponde à grafia-padrão.",
        suggestion=f"Usar '{correct}'.",
        severity="erro",
        confidence=0.99,
        auto_fixable=True,
        replacement=correct,
    )


RULES: List[GrammarRule] = [
    _word_rule("grammar.spelling.com_certeza", "concerteza", "com certeza"),
    _word_rule("grammar.spelling.de_repente", "derrepente", "de repente"),
    _word_rule("grammar.spelling.a_partir", "apartir", "a partir"),
    _word_rule("grammar.spelling.por_isso", "porisso", "por isso"),
    _word_rule("grammar.spelling.excecao", "excessão", "exceção"),
    _word_rule("grammar.spelling.privilegio", "previlégio", "privilégio"),
    _word_rule("grammar.spelling.empecilho", "impecilho", "empecilho"),
    _word_rule("grammar.spelling.menos", "menas", "menos"),
    _word_rule("grammar.spelling.seja", "seje", "seja"),
    _word_rule("grammar.spelling.esteja", "esteje", "esteja"),
    _word_rule("grammar.spelling.atraves", "atravez", "através"),
    _word_rule("grammar.spelling.enxergar", "enchergar", "enxergar"),
    _word_rule("grammar.spelling.mexer", "mecher", "mexer"),
    _word_rule("grammar.spelling.reivindicar", "reinvindicar", "reivindicar"),
    _word_rule("grammar.spelling.beneficente", "beneficiente", "beneficente"),
    _word_rule("grammar.spelling.sobrancelha", "sombrancelha", "sobrancelha"),
    _word_rule("grammar.spelling.cabeleireiro", "cabeleleiro", "cabeleireiro"),
    _word_rule("grammar.spelling.mortadela", "mortandela", "mortadela"),
    _word_rule("grammar.spelling.asterisco", "asterístico", "asterisco"),
    _word_rule("grammar.spelling.problema", "probrema", "problema"),
    _word_rule("grammar.spelling.ideia", "idéia", "ideia"),
    _word_rule("grammar.spelling.assembleia", "assembléia", "assembleia"),
    _word_rule("grammar.spelling.heroico", "heróico", "heroico"),
    _word_rule("grammar.spelling.voo", "vôo", "voo"),
    _word_rule("grammar.spelling.enjoo", "enjôo", "enjoo"),
    GrammarRule(
        code="grammar.agreement.possible_existential_houveram",
        subcategory="concordancia_verbal",
        pattern=re.compile(r"\bhouveram\b", re.IGNORECASE),
        explanation="Quando significa existir ou ocorrer, 'haver' é impessoal; em tempos compostos, o plural pode ser correto.",
        suggestion="Verificar o sentido: usar 'houve' se o verbo for existencial.",
        severity="observacao",
        confidence=0.65,
    ),
    GrammarRule(
        code="grammar.agreement.existential_haver_plural",
        subcategory="concordancia_verbal",
        pattern=re.compile(r"\bhaviam\s+(?:muitos?|muitas?|vários?|várias?)\b", re.IGNORECASE),
        explanation="No sentido de existir, 'haver' é impessoal e permanece no singular.",
        suggestion="Verificar o contexto e, se for existencial, usar 'havia'.",
        severity="alerta",
        confidence=0.9,
    ),
    GrammarRule(
        code="grammar.agreement.existir_plural_noun",
        subcategory="concordancia_verbal",
        pattern=re.compile(r"\b(?:existe|existia)\s+(?:muitos|muitas|vários|várias)\b", re.IGNORECASE),
        explanation="O verbo 'existir' é pessoal e deve concordar com o sujeito posposto no plural.",
        suggestion="Verificar o contexto e usar 'existem/existiam' quando o sujeito estiver no plural.",
        severity="alerta",
        confidence=0.92,
    ),
    GrammarRule(
        code="grammar.agreement.haver_auxiliary_plural",
        subcategory="concordancia_verbal",
        pattern=re.compile(r"\b(?:deve|pode|parece)\s+haverem\b", re.IGNORECASE),
        explanation="Em uma locução impessoal com sentido de existir, o infinitivo é 'haver'.",
        suggestion="Usar 'deve/pode/parece haver', conforme o contexto.",
        severity="erro",
        confidence=0.96,
    ),
    GrammarRule(
        code="grammar.agreement.elapsed_time_fazer",
        subcategory="concordancia_verbal",
        pattern=re.compile(r"\bfazem\s+(?:\d+|um|uma|dois|duas|três|quatro|cinco|seis|sete|oito|nove|dez)\s+(?:anos?|meses?|dias?|horas?)\b", re.IGNORECASE),
        explanation="Ao indicar tempo decorrido, o verbo 'fazer' é impessoal.",
        suggestion="Usar 'faz' no singular.",
        severity="erro",
        confidence=0.97,
    ),
    GrammarRule(
        code="grammar.agreement.a_gente_plural",
        subcategory="concordancia_verbal",
        pattern=re.compile(r"\ba\s+gente\s+(?:fomos|somos|vamos|temos|estamos)\b", re.IGNORECASE),
        explanation="Na norma-padrão, 'a gente' exige verbo na terceira pessoa do singular.",
        suggestion="Adequar o verbo ao singular ou substituir 'a gente' por 'nós'.",
        severity="observacao",
        confidence=0.9,
    ),
    GrammarRule(
        code="grammar.agreement.nos_singular",
        subcategory="concordancia_verbal",
        pattern=re.compile(r"\bnós\s+(?:vai|foi|era|tem|está)\b", re.IGNORECASE),
        explanation="O pronome 'nós' normalmente exige verbo na primeira pessoa do plural.",
        suggestion="Revisar a concordância, preservando fala caracterizada quando for deliberada.",
        severity="alerta",
        confidence=0.93,
    ),
    GrammarRule(
        code="grammar.agreement.eles_singular",
        subcategory="concordancia_verbal",
        pattern=re.compile(r"\b(?:eles|elas)\s+(?:vai|foi|era|tem|está)\b", re.IGNORECASE),
        explanation="O sujeito plural normalmente exige verbo no plural; 'ter' recebe acento: 'têm'.",
        suggestion="Revisar a concordância verbal.",
        severity="alerta",
        confidence=0.94,
    ),
    GrammarRule(
        code="grammar.agreement.simple_singular_subject_rangeram",
        subcategory="concordancia_verbal",
        pattern=re.compile(r"\b((?:o|a)\s+[A-Za-zÀ-úà-ÿ]+\s+)rangeram\b", re.IGNORECASE),
        explanation="Um sujeito simples introduzido por artigo singular exige o verbo no singular.",
        suggestion="Usar 'rangeu'.",
        severity="erro",
        confidence=0.98,
        auto_fixable=True,
        replacement=lambda match: f"{match.group(1)}rangeu",
    ),
    GrammarRule(
        code="grammar.regency.preferir_do_que",
        subcategory="regencia",
        pattern=re.compile(r"\b(?:prefiro|preferia|preferiu|preferem|preferimos)\b[^.!?\n]{1,80}\bdo\s+que\b", re.IGNORECASE),
        explanation="Na norma-padrão, a construção comparativa recomendada é 'preferir X a Y'.",
        suggestion="Reformular como 'preferir X a Y', preservando o sentido.",
        severity="observacao",
        confidence=0.8,
    ),
    GrammarRule(
        code="grammar.regency.obedecer_direct_article",
        subcategory="regencia",
        pattern=re.compile(r"\b(?:obedecer|obedeceu|obedecia|desobedecer|desobedeceu)\s+(?:o|a|os|as)\s+", re.IGNORECASE),
        explanation="Na norma-padrão, 'obedecer' e 'desobedecer' regem a preposição 'a'.",
        suggestion="Revisar a regência e a eventual ocorrência de crase.",
        severity="observacao",
        confidence=0.85,
    ),
    GrammarRule(
        code="grammar.pronoun.entre_eu",
        subcategory="pronomes",
        pattern=re.compile(r"\bentre\s+eu\s+e\b", re.IGNORECASE),
        explanation="Depois da preposição 'entre', a norma-padrão emprega o pronome oblíquo.",
        suggestion="Usar 'entre mim e ...'.",
        severity="erro",
        confidence=0.97,
    ),
    GrammarRule(
        code="grammar.pronoun.para_mim_infinitive",
        subcategory="pronomes",
        pattern=re.compile(r"\bpara\s+mim\s+([a-záàâãéêíóôõúç]+(?:ar|er|ir))\b", re.IGNORECASE),
        explanation="Quando o pronome é sujeito do infinitivo, a norma-padrão tende a exigir 'eu'.",
        suggestion="Verificar se o sentido pede 'para eu + infinitivo'.",
        severity="observacao",
        confidence=0.75,
    ),
    GrammarRule(
        code="grammar.crasis.invalid_before_fixed_expression",
        subcategory="crase",
        pattern=re.compile(r"\bà\s+(partir|pé|prazo|cavalo|respeito)\b", re.IGNORECASE),
        explanation="Nessa locução não ocorre artigo feminino que justifique a crase.",
        suggestion="Usar 'a' sem acento grave.",
        severity="erro",
        confidence=0.99,
        auto_fixable=True,
        replacement=lambda match: f"a {match.group(1)}",
    ),
    GrammarRule(
        code="grammar.crasis.a_medida_que",
        subcategory="crase",
        pattern=re.compile(r"\ba\s+medida\s+que\b", re.IGNORECASE),
        explanation="A locução conjuntiva consagrada é 'à medida que'.",
        suggestion="Usar 'à medida que'.",
        severity="erro",
        confidence=0.98,
        auto_fixable=True,
        replacement="à medida que",
    ),
    GrammarRule(
        code="grammar.crasis.as_vezes",
        subcategory="crase",
        pattern=re.compile(r"\bas\s+vezes\b", re.IGNORECASE),
        explanation="A locução adverbial de tempo 'às vezes' recebe crase.",
        suggestion="Usar 'às vezes'.",
        severity="erro",
        confidence=0.98,
        auto_fixable=True,
        replacement="às vezes",
    ),
    GrammarRule(
        code="grammar.crasis.daqui_a",
        subcategory="crase",
        pattern=re.compile(r"\bdaqui\s+à\s+(?=\d|um\b|uma\b|dois\b|duas\b|pouco\b)", re.IGNORECASE),
        explanation="Na indicação de tempo futuro iniciada por 'daqui', usa-se apenas a preposição 'a'.",
        suggestion="Usar 'daqui a'.",
        severity="erro",
        confidence=0.99,
        auto_fixable=True,
        replacement="daqui a ",
    ),
    GrammarRule(
        code="grammar.crasis.masculine_locution",
        subcategory="crase",
        pattern=re.compile(r"\bà\s+(?:longo|curto)\s+prazo\b|\bà\s+domicílio\b", re.IGNORECASE),
        explanation="Não ocorre crase antes do termo masculino nesta locução.",
        suggestion="Usar 'a longo/curto prazo' ou 'a/em domicílio', conforme a folha de estilo.",
        severity="erro",
        confidence=0.98,
    ),
    GrammarRule(
        code="grammar.punctuation.space_before_mark",
        subcategory="pontuacao",
        pattern=re.compile(r"\s+([,.;:!?])"),
        explanation="Não se usa espaço antes deste sinal de pontuação.",
        suggestion="Remover o espaço anterior.",
        severity="erro",
        confidence=0.99,
        auto_fixable=True,
        replacement=lambda match: match.group(1),
    ),
    GrammarRule(
        code="grammar.punctuation.missing_space_after_mark",
        subcategory="pontuacao",
        pattern=re.compile(r"([,;:])(?=[A-Za-zÀ-úà-ÿ])"),
        explanation="O sinal de pontuação deve ser seguido de espaço.",
        suggestion="Inserir um espaço depois do sinal.",
        severity="erro",
        confidence=0.98,
        auto_fixable=True,
        replacement=lambda match: f"{match.group(1)} ",
    ),
    GrammarRule(
        code="grammar.punctuation.repeated_separator",
        subcategory="pontuacao",
        pattern=re.compile(r"([,;])\1+"),
        explanation="A repetição deste sinal de pontuação parece acidental.",
        suggestion="Manter apenas um sinal.",
        severity="erro",
        confidence=0.99,
        auto_fixable=True,
        replacement=lambda match: match.group(1),
    ),
    GrammarRule(
        code="grammar.punctuation.space_after_open_parenthesis",
        subcategory="pontuacao",
        pattern=re.compile(r"\(\s+"),
        explanation="Não se usa espaço imediatamente depois do parêntese de abertura.",
        suggestion="Remover o espaço interno.",
        severity="erro",
        confidence=0.99,
        auto_fixable=True,
        replacement="(",
    ),
    GrammarRule(
        code="grammar.punctuation.space_before_close_parenthesis",
        subcategory="pontuacao",
        pattern=re.compile(r"\s+\)"),
        explanation="Não se usa espaço imediatamente antes do parêntese de fechamento.",
        suggestion="Remover o espaço interno.",
        severity="erro",
        confidence=0.99,
        auto_fixable=True,
        replacement=")",
    ),
]


DUPLICATE_WORD_PATTERN = re.compile(r"\b([A-Za-zÀ-úà-ÿ]{2,})\s+\1\b", re.IGNORECASE)
IGNORED_DUPLICATES = {"que"}


def _eligible_lines(text: str) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    in_frontmatter = False
    chapter: str | None = None
    for number, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if number == 1 and stripped == "---":
            in_frontmatter = True
            continue
        if in_frontmatter:
            if stripped == "---":
                in_frontmatter = False
            continue
        heading = re.match(r"^#{1,3}\s+(.+?)\s*$", stripped)
        if heading:
            if stripped.startswith("# "):
                chapter = heading.group(1)
            continue
        if not stripped or stripped == "---" or stripped.startswith((":::", "![", ">", "```")):
            continue
        records.append({
            "line": number,
            "chapter": chapter,
            "context": "dialogo" if stripped.startswith("—") else "prosa",
            "text": line,
        })
    return records


def _replacement_preview(match: Match[str], replacement: Replacement | None) -> str | None:
    if replacement is None:
        return None
    if callable(replacement):
        return replacement(match)
    if match.group(0)[:1].isupper():
        return replacement[:1].upper() + replacement[1:]
    return replacement


def _apply_replacement(match: Match[str], replacement: Replacement) -> str:
    preview = _replacement_preview(match, replacement)
    return preview if preview is not None else match.group(0)


def _balance_issues(text: str, records: List[Dict[str, Any]]) -> List[GrammarIssue]:
    issues: List[GrammarIssue] = []
    joined = "\n".join(record["text"] for record in records)
    checks = [
        ("grammar.punctuation.unbalanced_parentheses", "(", ")", "parênteses"),
        ("grammar.punctuation.unbalanced_smart_quotes", "“", "”", "aspas curvas"),
    ]
    for code, opening, closing, label in checks:
        if joined.count(opening) == joined.count(closing):
            continue
        first = next((record for record in records if opening in record["text"] or closing in record["text"]), None)
        if first:
            issues.append(GrammarIssue(
                rule=code,
                subcategory="pontuacao",
                severity="erro",
                confidence=0.95,
                line=first["line"],
                chapter=first["chapter"],
                context=first["context"],
                excerpt=first["text"].strip(),
                explanation=f"A quantidade de sinais de abertura e fechamento de {label} não coincide.",
                suggestion=f"Verificar o balanceamento de {label}.",
                auto_fixable=False,
            ))
    straight_quote_record = next((record for record in records if '"' in record["text"]), None)
    if joined.count('"') % 2 and straight_quote_record:
        issues.append(GrammarIssue(
            rule="grammar.punctuation.unbalanced_straight_quotes",
            subcategory="pontuacao",
            severity="erro",
            confidence=0.95,
            line=straight_quote_record["line"],
            chapter=straight_quote_record["chapter"],
            context=straight_quote_record["context"],
            excerpt=straight_quote_record["text"].strip(),
            explanation="A quantidade de aspas retas é ímpar no corpo do manuscrito.",
            suggestion="Verificar se alguma aspa de abertura ou fechamento está ausente.",
            auto_fixable=False,
        ))
    return issues


def analyze_grammar(text: str, book_config: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """Executa regras gramaticais locais e produz uma versão com correções seguras."""
    configured = (book_config or {}).get("revisao", {}).get("gramatica", {})
    ignored_rules = set(configured.get("ignorar_regras", []))
    preserve_dialogue = bool(configured.get("preservar_desvios_dialogo", True))
    max_items = int(configured.get("max_itens_relatorio", 100))
    records = _eligible_lines(text)
    corrected_lines = text.splitlines()
    issues: List[GrammarIssue] = []

    for record in records:
        original_line = record["text"]
        corrected_line = original_line
        for rule in RULES:
            if rule.code in ignored_rules:
                continue
            for match in rule.pattern.finditer(original_line):
                replacement = _replacement_preview(match, rule.replacement)
                contextual_dialogue = record["context"] == "dialogo" and preserve_dialogue
                dialogue_safe = rule.subcategory == "pontuacao"
                auto_fixable = rule.auto_fixable and (not contextual_dialogue or dialogue_safe)
                severity = rule.severity
                confidence = rule.confidence
                explanation = rule.explanation
                if contextual_dialogue and not dialogue_safe:
                    severity = "observacao" if severity in {"erro", "alerta"} else severity
                    confidence = round(confidence * 0.85, 2)
                    explanation += " Em diálogo, o desvio pode caracterizar a voz da personagem."
                issues.append(GrammarIssue(
                    rule=rule.code,
                    subcategory=rule.subcategory,
                    severity=severity,
                    confidence=confidence,
                    line=record["line"],
                    chapter=record["chapter"],
                    context=record["context"],
                    excerpt=match.group(0),
                    explanation=explanation,
                    suggestion=rule.suggestion,
                    auto_fixable=auto_fixable,
                    replacement=replacement,
                ))
            can_apply_to_line = not (
                record["context"] == "dialogo"
                and preserve_dialogue
                and rule.subcategory != "pontuacao"
            )
            if rule.auto_fixable and rule.replacement is not None and can_apply_to_line:
                corrected_line = rule.pattern.sub(
                    lambda current_match, value=rule.replacement: _apply_replacement(current_match, value),
                    corrected_line,
                )

        for match in DUPLICATE_WORD_PATTERN.finditer(original_line):
            if match.group(1).lower() in IGNORED_DUPLICATES:
                continue
            duplicate_in_dialogue = record["context"] == "dialogo" and preserve_dialogue
            issues.append(GrammarIssue(
                rule="grammar.duplication.adjacent_word",
                subcategory="duplicacao",
                severity="observacao" if duplicate_in_dialogue else "erro",
                confidence=0.8 if duplicate_in_dialogue else 0.98,
                line=record["line"],
                chapter=record["chapter"],
                context=record["context"],
                excerpt=match.group(0),
                explanation=(
                    "A mesma palavra aparece duas vezes consecutivas."
                    + (" Em diálogo, isso pode representar hesitação deliberada." if record["context"] == "dialogo" else "")
                ),
                suggestion="Remover uma ocorrência, salvo se a repetição for deliberada na fala.",
                auto_fixable=False,
            ))
        corrected_lines[record["line"] - 1] = corrected_line

    issues.extend(_balance_issues(text, records))
    issues.sort(key=lambda issue: (issue.line, issue.rule))
    summary: Dict[str, int] = {}
    for issue in issues:
        summary[issue.subcategory] = summary.get(issue.subcategory, 0) + 1
    auto_fix_count = sum(1 for issue in issues if issue.auto_fixable)
    return {
        "framework": "Gramática normativa do português brasileiro + regras editoriais conservadoras",
        "disclaimer": "A ausência de achados não certifica correção gramatical completa; regras contextuais exigem leitura humana.",
        "config": {
            "variant": configured.get("variante", "pt-BR"),
            "level": configured.get("nivel", "conservador"),
            "max_items": max_items,
            "ignored_rules": sorted(ignored_rules),
            "preserve_dialogue": preserve_dialogue,
        },
        "active_pattern_rules": len([rule for rule in RULES if rule.code not in ignored_rules]) + 1,
        "global_balance_checks": 3,
        "covered_subcategories": sorted({rule.subcategory for rule in RULES} | {"duplicacao"}),
        "total_issues": len(issues),
        "auto_fixable_count": auto_fix_count,
        "summary": summary,
        "issues": [issue.to_dict() for issue in issues],
        "display_issues": [issue.to_dict() for issue in issues[:max_items]],
        "corrected_text": "\n".join(corrected_lines),
    }
