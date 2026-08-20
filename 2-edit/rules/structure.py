#!/usr/bin/env python3
"""Validação estrutural declarativa, sem impor um formato universal aos livros."""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
import math
import re
from pathlib import Path
from typing import Any, Dict, List

import yaml


WORD_PATTERN = re.compile(r"\b[A-Za-zÀ-úà-ÿ]+\b")
HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
IMAGE_PATTERN = re.compile(r"!\[(.*?)\]\((.*?)\)")


@dataclass(frozen=True)
class StructureIssue:
    rule: str
    subtype: str
    severity: str
    confidence: float
    line: int
    chapter: str | None
    excerpt: str
    explanation: str
    suggestion: str
    auto_fixable: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _frontmatter(text: str) -> Dict[str, Any]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    try:
        end = next(index for index, line in enumerate(lines[1:], start=1) if line.strip() == "---")
    except StopIteration:
        return {}
    loaded = yaml.safe_load("\n".join(lines[1:end]))
    return loaded if isinstance(loaded, dict) else {}


def _clean_words(lines: List[str]) -> int:
    clean: List[str] = []
    for line in lines:
        stripped = line.strip()
        if not stripped or HEADING_PATTERN.match(stripped) or stripped.startswith(("![", ":::", "```", ">")):
            continue
        clean.append(re.sub(r"[*_`]", "", stripped))
    return len(WORD_PATTERN.findall(" ".join(clean)))


def _parse_chapters(text: str) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    lines = text.splitlines()
    headings: List[Dict[str, Any]] = []
    in_frontmatter = False
    for index, raw in enumerate(lines, start=1):
        stripped = raw.strip()
        if index == 1 and stripped == "---":
            in_frontmatter = True
            continue
        if in_frontmatter:
            if stripped == "---":
                in_frontmatter = False
            continue
        match = HEADING_PATTERN.match(stripped)
        if match:
            headings.append({"level": len(match.group(1)), "title": match.group(2), "line": index})

    chapter_headings = [heading for heading in headings if heading["level"] == 1]
    chapters: List[Dict[str, Any]] = []
    for chapter_index, heading in enumerate(chapter_headings):
        start = heading["line"]
        end = chapter_headings[chapter_index + 1]["line"] - 1 if chapter_index + 1 < len(chapter_headings) else len(lines)
        chapter_lines = lines[start:end]
        section_headings = [
            item for item in headings
            if item["level"] == 2 and start < item["line"] <= end
        ]
        sections: List[Dict[str, Any]] = []
        for section_index, section_heading in enumerate(section_headings):
            section_start = section_heading["line"]
            section_end = (
                section_headings[section_index + 1]["line"] - 1
                if section_index + 1 < len(section_headings) else end
            )
            sections.append({
                **section_heading,
                "word_count": _clean_words(lines[section_start:section_end]),
            })
        images = []
        for relative_index, line in enumerate(chapter_lines, start=start + 1):
            for match in IMAGE_PATTERN.finditer(line):
                images.append({"line": relative_index, "alt": match.group(1).strip(), "target": match.group(2)})
        chapters.append({
            "title": heading["title"],
            "line": start,
            "end_line": end,
            "word_count": _clean_words(chapter_lines),
            "sections": sections,
            "images": images,
            "has_attribution": any(line.strip().startswith(">") for line in chapter_lines),
        })
    return headings, chapters


def _issue(*, rule: str, subtype: str, line: int, chapter: str | None, excerpt: str,
           explanation: str, suggestion: str, severity: str = "alerta",
           confidence: float = 0.95) -> StructureIssue:
    return StructureIssue(
        rule=rule, subtype=subtype, severity=severity, confidence=confidence,
        line=line, chapter=chapter, excerpt=excerpt[:320], explanation=explanation,
        suggestion=suggestion,
    )


def _illustration_plan_review(
    plan_config: Dict[str, Any], content_chapters: List[Dict[str, Any]], book_dir: Path | None,
) -> tuple[List[StructureIssue], Dict[str, Any]]:
    """Valida paginação e completude de um plano visual externo configurado pelo livro."""
    issues: List[StructureIssue] = []
    mode = str(plan_config.get("modo", "totalmente_ilustrado")) if plan_config else "nao_configurado"
    metrics: Dict[str, Any] = {"configured": bool(plan_config), "validated": False, "mode": mode}
    valid_modes = {"sem_imagens", "abertura_pagina_par", "totalmente_ilustrado"}
    if not plan_config:
        return issues, metrics
    if mode not in valid_modes:
        issues.append(_issue(
            rule="structure.illustration_plan.invalid_mode", subtype="plano_ilustracoes",
            line=1, chapter=None, excerpt=mode,
            explanation="O modo de ilustração configurado não é reconhecido.",
            suggestion="Usar sem_imagens, abertura_pagina_par ou totalmente_ilustrado.",
            severity="erro", confidence=1.0,
        ))
        return issues, metrics
    if mode == "sem_imagens":
        metrics.update({"validated": True, "skipped": True, "reason": "Este livro não usa ilustrações."})
        return issues, metrics
    if book_dir is None:
        return issues, metrics

    plan_file = book_dir / str(plan_config.get("arquivo", "plano_ilustracoes.yaml"))
    metrics["file"] = str(plan_file)
    if not plan_file.is_file():
        issues.append(_issue(
            rule="structure.illustration_plan.missing_file", subtype="plano_ilustracoes",
            line=1, chapter=None, excerpt=str(plan_file),
            explanation="O arquivo configurado para o plano de ilustrações não existe.",
            suggestion="Criar o plano visual ou corrigir o caminho em book_config.yaml.",
            severity="erro", confidence=1.0,
        ))
        return issues, metrics

    try:
        loaded = yaml.safe_load(plan_file.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        issues.append(_issue(
            rule="structure.illustration_plan.invalid_yaml", subtype="plano_ilustracoes",
            line=1, chapter=None, excerpt=str(exc),
            explanation="O plano de ilustrações não pôde ser interpretado como YAML.",
            suggestion="Corrigir a sintaxe do arquivo do plano visual.", severity="erro", confidence=1.0,
        ))
        return issues, metrics
    if not isinstance(loaded, dict):
        issues.append(_issue(
            rule="structure.illustration_plan.invalid_document", subtype="plano_ilustracoes",
            line=1, chapter=None, excerpt=str(plan_file),
            explanation="O plano de ilustrações precisa ser um objeto YAML.",
            suggestion="Declarar miolo, direção visual e capítulos no plano.", severity="erro", confidence=1.0,
        ))
        return issues, metrics

    planned_chapters = loaded.get("capitulos", [])
    adaptive_spreads = str(plan_config.get("quantidade_spreads", "fixa")).casefold() == "adaptativa"
    pages_per_chapter = int(plan_config.get("paginas_por_capitulo", 0))
    scenes_per_chapter = int(plan_config.get("cenas_por_capitulo", 0))
    minimum_spreads = int(plan_config.get("min_spreads_por_capitulo", 3))
    reference_words_per_spread = int(plan_config.get("palavras_por_spread_referencia", 210))
    density_tolerance = float(plan_config.get("tolerancia_superior_densidade", 1.25))
    front_pages = int(plan_config.get("paginas_iniciais", 0))
    back_pages = int(plan_config.get("paginas_finais", 0))
    if adaptive_spreads:
        expected_total = front_pages + sum(
            int(item.get("paginas", [0, -1])[1]) - int(item.get("paginas", [0, -1])[0]) + 1
            for item in planned_chapters
        ) + back_pages
    else:
        expected_total = front_pages + len(content_chapters) * pages_per_chapter + back_pages
    actual_total = int(loaded.get("miolo", {}).get("total_paginas", 0))
    if actual_total != expected_total:
        issues.append(_issue(
            rule="structure.illustration_plan.total_pages", subtype="plano_ilustracoes",
            line=1, chapter=None, excerpt=f"plano={actual_total}; esperado={expected_total}",
            explanation="O total do miolo não corresponde às páginas iniciais, capítulos e páginas finais configuradas.",
            suggestion="Recalcular o mapa de páginas do plano visual.", severity="erro", confidence=1.0,
        ))

    visual_direction = loaded.get("direcao_visual", {})
    required_direction = {"estilo_ilustracao", "fotografia", "cinematografia", "cenografia", "cor_e_luz"}
    missing_direction = sorted(required_direction - set(visual_direction))
    if missing_direction:
        issues.append(_issue(
            rule="structure.illustration_plan.missing_art_direction", subtype="plano_ilustracoes",
            line=1, chapter=None, excerpt=", ".join(missing_direction),
            explanation="A bíblia visual não cobre todas as disciplinas necessárias aos prompts.",
            suggestion="Definir estilo de ilustração, fotografia, cinema, cenografia, cor e luz.",
            severity="erro", confidence=1.0,
        ))

    if len(planned_chapters) != len(content_chapters):
        issues.append(_issue(
            rule="structure.illustration_plan.chapter_count", subtype="plano_ilustracoes",
            line=1, chapter=None, excerpt=f"plano={len(planned_chapters)}; manuscrito={len(content_chapters)}",
            explanation="A quantidade de capítulos do plano visual difere do manuscrito.",
            suggestion="Adicionar, remover ou reconciliar capítulos no plano.", severity="erro", confidence=1.0,
        ))

    scene_ids: List[str] = []
    asset_paths: List[str] = []
    asset_count = 0
    phase = str(plan_config.get("fase", loaded.get("status", "planejamento"))).casefold()
    for index, chapter in enumerate(content_chapters):
        if index >= len(planned_chapters):
            break
        planned = planned_chapters[index]
        title = str(planned.get("titulo", ""))
        if title != chapter["title"]:
            issues.append(_issue(
                rule="structure.illustration_plan.chapter_mismatch", subtype="plano_ilustracoes",
                line=chapter["line"], chapter=chapter["title"], excerpt=title,
                explanation=f"O plano visual esperava o capítulo '{chapter['title']}' nesta posição.",
                suggestion="Alinhar título e ordem entre manuscrito e plano.", severity="erro", confidence=1.0,
            ))
        if adaptive_spreads:
            start = front_pages + 1 if index == 0 else int(planned_chapters[index - 1]["paginas"][1]) + 1
            scene_count = len(planned.get("cenas", []))
            end = start + (2 + 2 * max(0, scene_count - 1)) - 1
        else:
            start = front_pages + index * pages_per_chapter + 1
            end = start + pages_per_chapter - 1
        pages = planned.get("paginas", [])
        if pages != [start, end] or (plan_config.get("inicio_capitulo_impar") and start % 2 != 1):
            issues.append(_issue(
                rule="structure.illustration_plan.page_geometry", subtype="plano_ilustracoes",
                line=chapter["line"], chapter=chapter["title"], excerpt=str(pages),
                explanation=f"O capítulo deveria ocupar as páginas {start}–{end} e começar em página ímpar.",
                suggestion="Corrigir a faixa de páginas do capítulo.", severity="erro", confidence=1.0,
            ))
        if planned.get("pagina_reflexao") != end:
            issues.append(_issue(
                rule="structure.illustration_plan.reflection_page", subtype="plano_ilustracoes",
                line=chapter["line"], chapter=chapter["title"], excerpt=str(planned.get("pagina_reflexao")),
                explanation=f"Neste preset, a reflexão deve encerrar o capítulo na página {end}.",
                suggestion="Corrigir a página da reflexão ou alterar o preset deste livro.",
                severity="erro", confidence=1.0,
            ))
        scenes = planned.get("cenas", [])
        spread_count = max(0, len(scenes) - 1)
        invalid_scene_count = (
            spread_count < minimum_spreads if adaptive_spreads
            else len(scenes) != scenes_per_chapter
        )
        if invalid_scene_count:
            issues.append(_issue(
                rule="structure.illustration_plan.scene_count", subtype="plano_ilustracoes",
                line=chapter["line"], chapter=chapter["title"], excerpt=str(len(scenes)),
                explanation=(
                    f"O capítulo precisa de uma abertura e no mínimo {minimum_spreads} spreads."
                    if adaptive_spreads else
                    f"O capítulo deveria ter {scenes_per_chapter} cenas planejadas."
                ),
                suggestion="Completar ou ajustar o mapa de cenas antes de gerar as imagens.",
                severity="erro", confidence=1.0,
            ))
        if adaptive_spreads and reference_words_per_spread > 0 and density_tolerance > 0:
            reflection_words = sum(
                int(section.get("word_count", 0))
                for section in chapter.get("sections", [])
                if str(section.get("title", "")).casefold() == "reflexão"
            )
            narrative_words = max(0, int(chapter.get("word_count", 0)) - reflection_words)
            recommended_spreads = max(
                minimum_spreads,
                math.ceil(narrative_words / (reference_words_per_spread * density_tolerance)),
            )
            if spread_count < recommended_spreads:
                issues.append(_issue(
                    rule="structure.illustration_plan.spread_density",
                    subtype="plano_ilustracoes",
                    line=chapter["line"], chapter=chapter["title"],
                    excerpt=(
                        f"narrativa={narrative_words} palavras; planejado={spread_count}; "
                        f"recomendado={recommended_spreads}"
                    ),
                    explanation=(
                        "A densidade narrativa supera a referência configurada para os spreads "
                        "atuais. Isso pode comprimir texto, imagens e momentos narrativos."
                    ),
                    suggestion=(
                        f"Avaliar {recommended_spreads} spreads antes de gerar as artes. "
                        "A ampliação exige aprovação editorial e novo mapa de páginas."
                    ),
                    severity="alerta", confidence=0.9,
                ))
        if mode == "abertura_pagina_par":
            expected_scene_pages = [[start - 1]]
        else:
            expected_scene_pages = []
            next_page = start
            if plan_config.get("abertura_pagina_unica"):
                expected_scene_pages.append([next_page])
                next_page += 1
            configured_spreads = (
                spread_count if adaptive_spreads
                else int(plan_config.get("cenas_internas_em_spread", 0))
            )
            for _ in range(configured_spreads):
                expected_scene_pages.append([next_page, next_page + 1])
                next_page += 2
        for scene_index, scene in enumerate(scenes):
            required = {"id", "tipo", "paginas", "funcao", "ancora_textual", "descricao", "zona_texto",
                        "personagens", "elementos_continuidade", "alt_texto", "arquivo", "status"}
            missing = sorted(key for key in required if not scene.get(key))
            if missing:
                issues.append(_issue(
                    rule="structure.illustration_plan.incomplete_scene", subtype="plano_ilustracoes",
                    line=chapter["line"], chapter=chapter["title"], excerpt=f"{scene.get('id', '?')}: {', '.join(missing)}",
                    explanation="A ficha da cena não contém todos os componentes necessários para compilar um prompt editorial.",
                    suggestion="Preencher os campos ausentes da cena.", severity="erro", confidence=1.0,
                ))
            if scene_index < len(expected_scene_pages) and scene.get("paginas") != expected_scene_pages[scene_index]:
                issues.append(_issue(
                    rule="structure.illustration_plan.scene_pages", subtype="plano_ilustracoes",
                    line=chapter["line"], chapter=chapter["title"], excerpt=f"{scene.get('id', '?')}: {scene.get('paginas')}",
                    explanation=f"A cena deveria ocupar {expected_scene_pages[scene_index]} neste modelo editorial.",
                    suggestion="Corrigir o suporte da abertura ou do spread.", severity="erro", confidence=1.0,
                ))
            scene_id = str(scene.get("id", ""))
            asset = str(scene.get("arquivo", ""))
            if scene_id:
                scene_ids.append(scene_id)
            if asset:
                asset_paths.append(asset)
                resolved = Path(asset) if Path(asset).is_absolute() else book_dir / asset
                if resolved.is_file():
                    asset_count += 1
                elif phase in {"producao", "produção", "final"}:
                    issues.append(_issue(
                        rule="structure.illustration_plan.missing_asset", subtype="plano_ilustracoes",
                        line=chapter["line"], chapter=chapter["title"], excerpt=asset,
                        explanation="O plano está em produção, mas o ativo visual ainda não existe.",
                        suggestion="Gerar, aprovar e armazenar a arte no caminho previsto.", severity="erro", confidence=1.0,
                    ))

    for value, count in Counter(scene_ids).items():
        if count > 1:
            issues.append(_issue(
                rule="structure.illustration_plan.duplicate_scene_id", subtype="plano_ilustracoes",
                line=1, chapter=None, excerpt=value, explanation="O identificador de cena não é único.",
                suggestion="Usar um ID exclusivo para cada prompt.", severity="erro", confidence=1.0,
            ))
    for value, count in Counter(asset_paths).items():
        if count > 1:
            issues.append(_issue(
                rule="structure.illustration_plan.duplicate_asset", subtype="plano_ilustracoes",
                line=1, chapter=None, excerpt=value, explanation="Mais de uma cena aponta para o mesmo arquivo de arte.",
                suggestion="Reservar um caminho exclusivo para cada cena.", severity="erro", confidence=1.0,
            ))

    metrics.update({
        "validated": True, "phase": phase, "chapters": len(planned_chapters),
        "scenes": len(scene_ids), "planned_assets": len(asset_paths), "existing_assets": asset_count,
        "total_pages": actual_total,
    })
    return issues, metrics


def analyze_structure(
    text: str,
    book_config: Dict[str, Any] | None = None,
    book_dir: Path | None = None,
) -> Dict[str, Any]:
    """Aplica apenas as restrições estruturais declaradas na configuração do livro."""
    book_config = book_config or {}
    config = book_config.get("revisao", {}).get("estrutura", {})
    ignored_rules = set(config.get("ignorar_regras", []))
    max_items = int(config.get("max_itens_relatorio", 100))
    headings, chapters = _parse_chapters(text)
    frontmatter = _frontmatter(text)
    ignored_chapters = {title.casefold() for title in config.get("capitulos_ignorados", [])}
    content_chapters = [chapter for chapter in chapters if chapter["title"].casefold() not in ignored_chapters]
    issues: List[StructureIssue] = []

    max_jump = int(config.get("hierarquia_titulos", {}).get("salto_maximo", 1))
    for previous, current in zip(headings, headings[1:]):
        if current["level"] - previous["level"] > max_jump:
            issues.append(_issue(
                rule="structure.heading.level_jump", subtype="hierarquia",
                line=current["line"], chapter=current["title"], excerpt=current["title"],
                explanation=f"O título salta do nível {previous['level']} para o nível {current['level']}.",
                suggestion="Usar níveis Markdown consecutivos ou configurar um salto maior.",
            ))

    title_counts = Counter(chapter["title"].casefold() for chapter in chapters)
    for normalized, count in title_counts.items():
        if count > 1:
            chapter = next(item for item in chapters if item["title"].casefold() == normalized)
            issues.append(_issue(
                rule="structure.chapter.duplicate_title", subtype="capitulos",
                line=chapter["line"], chapter=chapter["title"], excerpt=chapter["title"],
                explanation=f"O título de capítulo aparece {count} vezes.",
                suggestion="Distinguir os títulos ou confirmar se a repetição é deliberada.",
            ))

    expected_framework = config.get("framework_esperado") or book_config.get("framework")
    used_framework = frontmatter.get("framework_used")
    if expected_framework and used_framework != expected_framework:
        issues.append(_issue(
            rule="structure.framework.mismatch", subtype="framework",
            line=1, chapter=None, excerpt=f"framework_used: {used_framework}",
            explanation=f"O manuscrito declara '{used_framework}', mas o livro está configurado para '{expected_framework}'.",
            suggestion="Alinhar o frontmatter e o book_config.yaml.", confidence=0.99,
        ))

    registry_field = config.get("registro_capitulos", {}).get("campo")
    title_field = config.get("registro_capitulos", {}).get("campo_titulo", "titulo")
    pending_values = {
        value.casefold() for value in config.get("registro_capitulos", {}).get("valores_pendentes", ["Pendente"])
    }
    registry = book_config.get(registry_field, []) if registry_field else []
    if registry:
        expected_count = len(registry)
        if len(content_chapters) != expected_count:
            issues.append(_issue(
                rule="structure.registry.count_mismatch", subtype="registro",
                line=1, chapter=None, excerpt=f"registro={expected_count}; manuscrito={len(content_chapters)}",
                explanation="A quantidade de capítulos do manuscrito difere do registro configurado.",
                suggestion="Atualizar o registro ou incluir/remover capítulos conforme o projeto.", confidence=0.99,
            ))
        pending_positions = []
        for index, entry in enumerate(registry):
            expected_title = str(entry.get(title_field, ""))
            if expected_title.casefold() in pending_values:
                pending_positions.append(index + 1)
                continue
            if index >= len(content_chapters):
                continue
            actual = content_chapters[index]
            if actual["title"] != expected_title:
                issues.append(_issue(
                    rule="structure.registry.title_or_order_mismatch", subtype="registro",
                    line=actual["line"], chapter=actual["title"], excerpt=actual["title"],
                    explanation=f"Na posição {index + 1}, o registro espera '{expected_title}'.",
                    suggestion="Corrigir o título, a ordem ou o registro do livro.", confidence=0.99,
                ))
        if pending_positions and not config.get("registro_capitulos", {}).get("permitir_pendentes", False):
            issues.append(_issue(
                rule="structure.registry.pending_entries", subtype="registro",
                line=1, chapter=None, excerpt=f"Posições pendentes: {', '.join(map(str, pending_positions))}",
                explanation="O registro estrutural ainda contém títulos pendentes para capítulos já presentes.",
                suggestion="Preencher os títulos reais no registro de capítulos.", confidence=0.99,
            ))

    required_sections = config.get("secoes_obrigatorias", [])
    unique_sections = set(config.get("secoes_unicas", required_sections))
    required_elements = config.get("elementos_obrigatorios", {})
    min_words = int(config.get("min_palavras_capitulo", 0))
    proportions = config.get("proporcoes_secoes", {})
    for chapter in content_chapters:
        section_counts = Counter(section["title"] for section in chapter["sections"])
        for section_name in required_sections:
            if not section_counts[section_name]:
                issues.append(_issue(
                    rule="structure.section.missing", subtype="secoes",
                    line=chapter["line"], chapter=chapter["title"], excerpt=chapter["title"],
                    explanation=f"A seção configurada como obrigatória, '{section_name}', está ausente.",
                    suggestion="Adicionar a seção ou removê-la dos requisitos deste framework.",
                ))

        for section_name in unique_sections:
            if section_counts[section_name] > 1:
                issues.append(_issue(
                    rule="structure.section.duplicate", subtype="secoes",
                    line=chapter["line"], chapter=chapter["title"], excerpt=section_name,
                    explanation=f"A seção única '{section_name}' aparece {section_counts[section_name]} vezes.",
                    suggestion="Manter uma seção ou alterar a configuração.",
                ))
        if required_elements.get("atribuicao") and not chapter["has_attribution"]:
            issues.append(_issue(
                rule="structure.element.missing_attribution", subtype="elementos",
                line=chapter["line"], chapter=chapter["title"], excerpt=chapter["title"],
                explanation="O framework deste livro exige uma linha de atribuição no capítulo.",
                suggestion="Adicionar a atribuição ou desativar o requisito para este livro.",
            ))
        if required_elements.get("imagem") and not chapter["images"]:
            issues.append(_issue(
                rule="structure.element.missing_image", subtype="elementos",
                line=chapter["line"], chapter=chapter["title"], excerpt=chapter["title"],
                explanation="O framework deste livro exige ao menos uma imagem no capítulo.",
                suggestion="Adicionar a imagem ou desativar o requisito.",
            ))
        if required_elements.get("texto_alternativo_imagem"):
            for image in chapter["images"]:
                if not image["alt"]:
                    issues.append(_issue(
                        rule="structure.image.missing_alt", subtype="elementos",
                        line=image["line"], chapter=chapter["title"], excerpt=f"![]({image['target']})",
                        explanation="A imagem não possui texto alternativo.",
                        suggestion="Descrever brevemente a função ou o conteúdo da imagem.",
                        severity="observacao", confidence=0.99,
                    ))
        if required_elements.get("arquivo_imagem") and book_dir is not None:
            for image in chapter["images"]:
                target = image["target"].strip()
                if re.match(r"^(?:https?:|data:)", target, re.IGNORECASE):
                    continue
                target_path = Path(target)
                resolved = target_path if target_path.is_absolute() else book_dir / target_path
                if not resolved.is_file():
                    issues.append(_issue(
                        rule="structure.image.missing_file", subtype="elementos",
                        line=image["line"], chapter=chapter["title"], excerpt=target,
                        explanation="O arquivo de imagem referenciado pelo manuscrito não existe.",
                        suggestion="Adicionar o ativo no caminho declarado ou corrigir a referência.",
                        severity="alerta", confidence=1.0,
                    ))
        if min_words and chapter["word_count"] < min_words:
            issues.append(_issue(
                rule="structure.chapter.below_min_words", subtype="proporcao",
                line=chapter["line"], chapter=chapter["title"], excerpt=chapter["title"],
                explanation=f"O capítulo tem {chapter['word_count']} palavras; a meta mínima configurada é {min_words}.",
                suggestion="Verificar se o capítulo está completo; não ampliar automaticamente.",
                severity="observacao", confidence=0.85,
            ))
        for section_name, limits in proportions.items():
            section = next((item for item in chapter["sections"] if item["title"] == section_name), None)
            if not section or not chapter["word_count"]:
                continue
            ratio = section["word_count"] / chapter["word_count"]
            minimum = float(limits.get("min", 0))
            maximum = float(limits.get("max", 1))
            if ratio < minimum or ratio > maximum:
                issues.append(_issue(
                    rule="structure.section.proportion_outside_range", subtype="proporcao",
                    line=section["line"], chapter=chapter["title"], excerpt=section_name,
                    explanation=f"A seção ocupa {ratio:.1%} do capítulo; a faixa configurada é {minimum:.0%}–{maximum:.0%}.",
                    suggestion="Revisar o equilíbrio apenas se a diferença prejudicar a proposta do capítulo.",
                    severity="observacao", confidence=0.8,
                ))

    illustration_issues, illustration_metrics = _illustration_plan_review(
        config.get("plano_ilustracoes", {}), content_chapters, book_dir,
    )
    issues.extend(illustration_issues)

    issues = [issue for issue in issues if issue.rule not in ignored_rules]
    issues.sort(key=lambda issue: (issue.line, issue.rule, issue.chapter or ""))
    summary = Counter(issue.subtype for issue in issues)
    return {
        "framework": "Restrições estruturais declarativas + integridade Markdown",
        "disclaimer": "O motor valida somente requisitos configurados; não existe estrutura narrativa universal nem obrigação implícita de introdução, conflito ou reflexão.",
        "config": {
            "framework_expected": expected_framework,
            "ignored_chapters": sorted(ignored_chapters),
            "required_sections": required_sections,
            "required_elements": required_elements,
            "max_items": max_items,
            "ignored_rules": sorted(ignored_rules),
        },
        "metrics": {
            "headings": len(headings), "chapters": len(chapters),
            "content_chapters": len(content_chapters),
            "chapter_words": {chapter["title"]: chapter["word_count"] for chapter in content_chapters},
            "illustration_plan": illustration_metrics,
        },
        "total_issues": len(issues),
        "summary": dict(summary),
        "issues": [issue.to_dict() for issue in issues],
        "display_issues": [issue.to_dict() for issue in issues[:max_items]],
    }
