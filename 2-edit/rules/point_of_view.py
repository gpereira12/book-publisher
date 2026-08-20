#!/usr/bin/env python3
"""
rules/point_of_view.py
----------------------
Módulo de auditoria do Ponto 6 — Ponto de Vista e Voz Narrativa.
Verifica a consistência da perspectiva narrativa, identifica deslizes de 1ª pessoa em narração de 3ª pessoa,
endereçamento indevido ao leitor e transições não justificadas, respeitando exceções por seção (Prefácio, Reflexão)
e ignorando falas em diálogos.
"""

from typing import Dict, List, Any, Set, Tuple
import re

from review_models import Finding, make_finding


# Termos e pronomes característicos de 1ª pessoa no singular e plural
FIRST_PERSON_PRONOUNS = {
    "eu", "me", "mim", "comigo", "meu", "minha", "meus", "minhas",
    "nós", "nos", "conosco", "nosso", "nossa", "nossos", "nossas"
}

FIRST_PERSON_VERB_PATTERNS = [
    r"\b(?:eu\s+)?(?:vi|percebi|senti|notei|pensei|decidi|caminhei|olhei|observei)\b",
    r"\b(?:nós\s+)?(?:vimos|percebemos|sentimos|notamos|pensamos|decidimos|caminhamos|olhamos|observamos)\b",
]

READER_ADDRESS_PATTERNS = [
    r"\bcomo\s+você\s+(?:verá|sabe|percebeu|aprenderá)\b",
    r"\bcaro\s+leitor\b",
    r"\bleitora?\b",
    r"\bveja\s+bem\b",
    r"\bobserve\s+que\b",
]


def _is_dialogue_line(line: str) -> bool:
    """Verifica se a linha é um diálogo (iniciada por travessão ou entre aspas)."""
    stripped = line.strip()
    if stripped.startswith("—") or stripped.startswith("- ") or stripped.startswith("–"):
        return True
    if (stripped.startswith('"') and stripped.endswith('"')) or (stripped.startswith('“') and stripped.endswith('”')):
        return True
    return False


def audit_point_of_view(
    markdown_text: str, config: Dict[str, Any]
) -> List[Finding]:
    """
    Audita o texto em busca de inconsistências de ponto de vista e voz narrativa.
    """
    findings: List[Finding] = []
    
    pov_config = config.get("revisao", {}).get("ponto_de_vista", {})
    expected_pov = pov_config.get("voz_esperada", "3a_pessoa") # '3a_pessoa' ou '1a_pessoa'
    allowed_1st_person_sections = set(pov_config.get("secoes_permitidas_1a_pessoa", ["Prefácio", "Reflexão"]))
    allowed_reader_address_sections = set(pov_config.get("secoes_permitidas_endereçamento", ["Prefácio", "Reflexão"]))

    lines = markdown_text.splitlines()
    current_section = "Introdução"
    
    for idx, line in enumerate(lines, start=1):
        stripped = line.strip()
        if not stripped:
            continue
            
        # Atualiza título da seção/capítulo
        heading_match = re.match(r"^#{1,3}\s+(.+?)\s*$", stripped)
        if heading_match:
            current_section = heading_match.group(1).strip()
            continue

        # Ignora linhas de diálogo na prosa
        if _is_dialogue_line(stripped):
            continue

        # Check 1: Inconsistência de 1ª pessoa quando se espera 3ª pessoa na narração
        if expected_pov == "3a_pessoa" and current_section not in allowed_1st_person_sections:
            for pattern in FIRST_PERSON_VERB_PATTERNS:
                match = re.search(pattern, stripped, re.IGNORECASE)
                if match:
                    excerpt = match.group(0)
                    findings.append(
                        make_finding(
                            text=markdown_text,
                            rule="ponto_de_vista.deslize_1a_pessoa",
                            category="ponto_de_vista",
                            severity="observacao",
                            confidence=0.85,
                            excerpt=stripped,
                            explanation=(
                                f"Uso de 1ª pessoa ('{excerpt}') identificado na seção de narração em 3ª pessoa '{current_section}'."
                            ),
                            suggestion="Confirmar se o narrador é estritamente em 3ª pessoa ou ajustar para manter a distância narrativa.",
                            line=idx,
                            chapter=current_section,
                        )
                    )
                    break

        # Check 2: Endereçamento direto ao leitor fora de seções permitidas
        if current_section not in allowed_reader_address_sections:
            for pattern in READER_ADDRESS_PATTERNS:
                match = re.search(pattern, stripped, re.IGNORECASE)
                if match:
                    excerpt = match.group(0)
                    findings.append(
                        make_finding(
                            text=markdown_text,
                            rule="ponto_de_vista.enderecamento_leitor",
                            category="ponto_de_vista",
                            severity="observacao",
                            confidence=0.90,
                            excerpt=stripped,
                            explanation=(
                                f"Endereçamento direto ao leitor ('{excerpt}') identificado fora de seções dedicadas (como Prefácio ou Reflexão)."
                            ),
                            suggestion="Avaliar se o recurso de quebrar a 4ª parede é intencional ou se deve ser mantido na voz da história.",
                            line=idx,
                            chapter=current_section,
                        )
                    )
                    break

    return findings
