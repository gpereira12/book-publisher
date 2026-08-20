#!/usr/bin/env python3
"""Coesão referencial e sequencial com heurísticas conservadoras."""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
import re
import unicodedata
from typing import Any, Dict, Iterable, List


CONNECTOR_GROUPS: Dict[str, List[str]] = {
    "adversidade": ["mas", "porém", "contudo", "todavia", "entretanto", "no entanto"],
    "causa": ["porque", "pois", "já que", "uma vez que", "visto que"],
    "conclusao": ["portanto", "por isso", "assim", "logo", "desse modo", "dessa forma"],
    "adicao": ["além disso", "também", "ainda", "bem como"],
    "tempo": ["então", "depois", "em seguida", "finalmente", "enquanto isso"],
    "condicao": ["se", "caso", "desde que", "contanto que"],
    "concessao": ["embora", "ainda que", "mesmo que", "apesar disso"],
    "explicacao": ["ou seja", "isto é", "em outras palavras"],
}
CONNECTOR_TO_GROUP = {
    connector: group
    for group, connectors in CONNECTOR_GROUPS.items()
    for connector in connectors
}
LEADING_CONNECTORS = sorted(CONNECTOR_TO_GROUP, key=len, reverse=True)

GENERIC_ENTITIES = {
    "homem": "masculino", "menino": "masculino", "mestre": "masculino",
    "general": "masculino", "imperador": "masculino", "filho": "masculino",
    "pai": "masculino", "velho": "masculino", "guerreiro": "masculino",
    "açougueiro": "masculino", "rapaz": "masculino", "irmão": "masculino",
    "professor": "masculino", "aluno": "masculino", "jovem": "comum",
    "mulher": "feminino", "menina": "feminino", "mestra": "feminino",
    "imperatriz": "feminino", "filha": "feminino", "mãe": "feminino",
    "velha": "feminino", "guerreira": "feminino", "irmã": "feminino",
    "professora": "feminino", "aluna": "feminino",
    "homens": "masculino_plural", "meninos": "masculino_plural",
    "filhos": "masculino_plural", "irmãos": "masculino_plural",
    "mulheres": "feminino_plural", "meninas": "feminino_plural",
    "filhas": "feminino_plural", "irmãs": "feminino_plural",
}
PRONOUN_GENDER = {
    "ele": "masculino", "ela": "feminino",
    "eles": "masculino_plural", "elas": "feminino_plural",
}


@dataclass(frozen=True)
class CohesionIssue:
    rule: str
    subtype: str
    severity: str
    confidence: float
    line: int
    chapter: str | None
    context: str
    excerpt: str
    explanation: str
    suggestion: str
    auto_fixable: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _normalize(value: str) -> str:
    decomposed = unicodedata.normalize("NFD", value.casefold())
    return "".join(char for char in decomposed if unicodedata.category(char) != "Mn")


def _paragraphs(text: str) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    in_frontmatter = False
    chapter: str | None = None
    section: str | None = None
    for number, raw_line in enumerate(text.splitlines(), start=1):
        stripped = raw_line.strip()
        if number == 1 and stripped == "---":
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
        if not stripped or stripped == "---" or stripped.startswith((":::", "![", ">", "```")):
            continue
        records.append({
            "paragraph": len(records),
            "line": number,
            "chapter": chapter,
            "section": section,
            "context": "dialogo" if stripped.startswith("—") else "prosa",
            "text": re.sub(r"[*_`]", "", stripped),
        })
    return records


def _sentences(paragraphs: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    sentences: List[Dict[str, Any]] = []
    for paragraph in paragraphs:
        for sentence_index, match in enumerate(re.finditer(r"[^.!?]+(?:[.!?]+|$)", paragraph["text"])):
            sentence = match.group(0).strip()
            if not re.search(r"[A-Za-zÀ-úà-ÿ]", sentence):
                continue
            sentences.append({**paragraph, "sentence_index": sentence_index, "text": sentence})
    return sentences


def _leading_connector(sentence: str) -> str | None:
    cleaned = re.sub(r"^[—\s\"'“”]+", "", sentence).casefold()
    for connector in LEADING_CONNECTORS:
        if re.match(rf"{re.escape(connector)}\b", cleaned, flags=re.IGNORECASE):
            return connector
    return None


def _entity_config(book_config: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    configured = book_config.get("revisao", {}).get("coesao", {}).get("entidades", {})
    entities: Dict[str, Dict[str, Any]] = {}
    for canonical, data in configured.items():
        if isinstance(data, str):
            entities[canonical] = {"gender": data, "aliases": [canonical]}
        else:
            entities[canonical] = {
                "gender": data.get("genero", "comum"),
                "aliases": data.get("aliases", [canonical]),
            }
    return entities


def _entities_in(sentence: str, configured: Dict[str, Dict[str, Any]]) -> Dict[str, str]:
    found: Dict[str, str] = {}
    lowered = sentence.casefold()
    configured_mentions: List[Dict[str, Any]] = []
    for canonical, data in configured.items():
        for alias in data["aliases"]:
            for match in re.finditer(rf"\b{re.escape(alias.casefold())}\b", lowered):
                found[f"entity:{canonical}"] = data["gender"]
                configured_mentions.append({
                    "key": f"entity:{canonical}",
                    "start": match.start(),
                    "end": match.end(),
                })
    generic_mentions: List[Dict[str, Any]] = []
    for noun, gender in GENERIC_ENTITIES.items():
        for match in re.finditer(rf"\b{re.escape(noun)}\b", lowered):
            generic_mentions.append({
                "noun": noun,
                "gender": gender,
                "start": match.start(),
                "end": match.end(),
            })

    remaining: List[Dict[str, Any]] = []
    for generic in sorted(generic_mentions, key=lambda item: item["start"]):
        merged = False
        for entity in configured_mentions:
            if generic["start"] < entity["end"] and entity["start"] < generic["end"]:
                merged = True
                break
            left = min(generic["end"], entity["end"])
            right = max(generic["start"], entity["start"])
            between = lowered[left:right]
            distance = max(0, right - left)
            apposition = (
                bool(re.search(r"\b(?:chamad[oa]|conhecid[oa]\s+como)\b", between))
                or ("," in between and distance <= 45)
                or ("—" in between and distance <= 45)
                or (bool(re.search(r"\b(?:era|foi|é)\s+(?:um|uma|o|a)\b", between)) and distance <= 45)
            )
            if apposition:
                merged = True
                break
        if not merged:
            remaining.append(generic)

    clusters: List[List[Dict[str, Any]]] = []
    for mention in remaining:
        if not clusters:
            clusters.append([mention])
            continue
        previous = clusters[-1][-1]
        between = lowered[previous["end"]:mention["start"]]
        if mention["start"] - previous["end"] <= 16 and not re.search(r"[,;.!?]", between):
            clusters[-1].append(mention)
        else:
            clusters.append([mention])
    for cluster in clusters:
        label = " ".join(item["noun"] for item in cluster)
        genders = {item["gender"] for item in cluster}
        gender = next(iter(genders)) if len(genders) == 1 else "comum"
        found[f"noun:{label}"] = gender
    return found


def _gender_matches(candidate: str, pronoun_gender: str) -> bool:
    if candidate == "comum":
        return pronoun_gender in {"masculino", "feminino"}
    return candidate == pronoun_gender


def _connector_issues(sentences: List[Dict[str, Any]], min_repeat: int) -> List[CohesionIssue]:
    issues: List[CohesionIssue] = []
    redundant_patterns = [
        re.compile(r"\bmas\s+(?:porém|contudo|todavia|entretanto|no\s+entanto)\b", re.IGNORECASE),
        re.compile(r"\bporém\s+(?:contudo|todavia|entretanto)\b", re.IGNORECASE),
        re.compile(r"\bcontudo\s+(?:porém|todavia|entretanto)\b", re.IGNORECASE),
        re.compile(r"\bportanto\s+(?:logo|por\s+isso)\b", re.IGNORECASE),
    ]
    correlation_patterns = [
        re.compile(r"\bembora\b[^.!?\n]{1,180},?\s+mas\b", re.IGNORECASE),
        re.compile(r"\bapesar\s+de\b[^.!?\n]{1,180},?\s+mas\b", re.IGNORECASE),
    ]
    for sentence in sentences:
        for pattern in redundant_patterns:
            for match in pattern.finditer(sentence["text"]):
                issues.append(CohesionIssue(
                    rule="cohesion.connector.redundant_pair",
                    subtype="conector_redundante",
                    severity="observacao",
                    confidence=0.92,
                    line=sentence["line"],
                    chapter=sentence["chapter"],
                    context=sentence["context"],
                    excerpt=match.group(0),
                    explanation="Dois conectores exercem praticamente a mesma função no mesmo ponto.",
                    suggestion="Manter o conector que expressar melhor a relação entre as ideias.",
                ))
        for pattern in correlation_patterns:
            for match in pattern.finditer(sentence["text"]):
                issues.append(CohesionIssue(
                    rule="cohesion.connector.concessive_adversative_overlap",
                    subtype="correlacao",
                    severity="observacao",
                    confidence=0.88,
                    line=sentence["line"],
                    chapter=sentence["chapter"],
                    context=sentence["context"],
                    excerpt=match.group(0),
                    explanation="A concessão iniciada por 'embora/apesar de' já estabelece contraste; o 'mas' pode ser redundante.",
                    suggestion="Reformular com apenas uma estrutura de contraste.",
                ))

    index = 0
    while index < len(sentences):
        connector = _leading_connector(sentences[index]["text"])
        if not connector:
            index += 1
            continue
        end = index + 1
        while (
            end < len(sentences)
            and sentences[end]["chapter"] == sentences[index]["chapter"]
            and _leading_connector(sentences[end]["text"]) == connector
        ):
            end += 1
        if end - index >= min_repeat:
            excerpt = " / ".join(item["text"] for item in sentences[index:end])
            context = sentences[index]["context"]
            issues.append(CohesionIssue(
                rule="cohesion.connector.repeated_opening",
                subtype="repeticao_de_conector",
                severity="informacao" if context == "dialogo" else "observacao",
                confidence=0.7 if context == "dialogo" else 0.82,
                line=sentences[index]["line"],
                chapter=sentences[index]["chapter"],
                context=context,
                excerpt=excerpt[:320],
                explanation=f"{end - index} frases consecutivas começam com '{connector}'.",
                suggestion="Verificar se a repetição cria progressão deliberada ou cadência mecânica.",
            ))
        index = end
    return issues


def _reference_issues(
    sentences: List[Dict[str, Any]],
    configured_entities: Dict[str, Dict[str, Any]],
) -> List[CohesionIssue]:
    issues: List[CohesionIssue] = []
    for index in range(1, len(sentences)):
        current = sentences[index]
        previous = sentences[index - 1]
        if current["context"] == "dialogo" or current["chapter"] != previous["chapter"]:
            continue
        start = re.match(r"^[—\s\"'“”]*(Ele|Ela|Eles|Elas)\b", current["text"], re.IGNORECASE)
        if not start:
            continue
        pronoun = start.group(1).casefold()
        expected_gender = PRONOUN_GENDER[pronoun]
        candidates = {
            name: gender
            for name, gender in _entities_in(previous["text"], configured_entities).items()
            if _gender_matches(gender, expected_gender)
        }
        if len(candidates) < 2:
            continue
        labels = [name.split(":", 1)[1] for name in candidates]
        issues.append(CohesionIssue(
            rule="cohesion.reference.ambiguous_pronoun",
            subtype="referencia_pronominal",
            severity="observacao",
            confidence=0.65,
            line=current["line"],
            chapter=current["chapter"],
            context=current["context"],
            excerpt=f"{previous['text']} {current['text']}"[:320],
            explanation=f"O pronome '{pronoun}' pode retomar mais de um referente recente: {', '.join(labels)}.",
            suggestion="Confirmar se o referente está inequívoco; repetir o nome apenas se houver ambiguidade real.",
        ))
    return issues


def analyze_cohesion(text: str, book_config: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """Analisa coesão local sem reescrever relações semânticas automaticamente."""
    book_config = book_config or {}
    configured = book_config.get("revisao", {}).get("coesao", {})
    ignored_rules = set(configured.get("ignorar_regras", []))
    max_items = int(configured.get("max_itens_relatorio", 100))
    min_repeat = int(configured.get("min_repeticoes_conector", 3))
    paragraphs = _paragraphs(text)
    sentences = _sentences(paragraphs)
    entities = _entity_config(book_config)
    issues = _connector_issues(sentences, min_repeat) + _reference_issues(sentences, entities)
    issues = [issue for issue in issues if issue.rule not in ignored_rules]
    issues.sort(key=lambda issue: (issue.line, issue.rule))

    leading = [_leading_connector(sentence["text"]) for sentence in sentences]
    leading_counts = Counter(connector for connector in leading if connector)
    group_counts = Counter(CONNECTOR_TO_GROUP[connector] for connector in leading if connector)
    word_count = sum(len(re.findall(r"\b[A-Za-zÀ-úà-ÿ]+\b", item["text"])) for item in paragraphs)
    summary = Counter(issue.subtype for issue in issues)
    return {
        "framework": "Coesão referencial e sequencial + heurísticas editoriais locais",
        "disclaimer": "Coesão depende de sentido e contexto; os achados são perguntas editoriais, não correções automáticas.",
        "config": {
            "min_connector_repetitions": min_repeat,
            "max_items": max_items,
            "ignored_rules": sorted(ignored_rules),
            "configured_entities": len(entities),
        },
        "metrics": {
            "paragraphs": len(paragraphs),
            "sentences": len(sentences),
            "words": word_count,
            "leading_connectors": dict(leading_counts.most_common()),
            "connector_groups": dict(group_counts.most_common()),
            "leading_connectors_per_1000_words": round(sum(leading_counts.values()) * 1000 / max(word_count, 1), 2),
        },
        "total_issues": len(issues),
        "summary": dict(summary),
        "issues": [issue.to_dict() for issue in issues],
        "display_issues": [issue.to_dict() for issue in issues[:max_items]],
    }
