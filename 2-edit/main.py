#!/usr/bin/env python3
"""
2-edit/main.py
-----------------
Motor do Edit (Projeto 2 — Revisão): Auditador e Lapidador Editorial Profissional.
Aplica as 4 Camadas de Revisão + Folha de Estilo + Verba Dicendi + Auto-Disparo do Layout (Projeto 3).
"""

import os
import sys
import argparse
import subprocess
from pathlib import Path
from typing import Dict, Any, List

from rules.style_dreyer import find_crutch_words, find_repeated_words
from rules.flesch_readability import calculate_flesch_siqueira
from rules.typography import sanitize_typography
from rules.style_sheet import load_style_sheet, check_style_sheet_violations


def generate_review_report(
    book_id: str,
    flesch_data: Dict[str, Any],
    crutch_words: Dict[str, int],
    repeated_words: List[Any],
    corrections_count: int,
    style_warnings: List[str]
) -> str:
    """Gera o relatório de revisão detalhado em Markdown."""
    lines = [
        f"# 📝 Relatório de Revisão Editorial: {book_id}",
        "\n---",
        "## 1.📊 Índice de Legibilidade (Flesch-Siqueira PT-BR)",
        f"- **Pontuação:** `{flesch_data['flesch_score']}/100`",
        f"- **Classificação:** **{flesch_data['classificacao']}**",
        f"- **Total de Palavras:** `{flesch_data['total_palavras']}`",
        f"- **Total de Frases:** `{flesch_data['total_frases']}`",
        f"- **Média de Palavras por Frase:** `{flesch_data['media_palavras_por_frase']} palavras`",
        f"- **Média de Sílabas por Palavra:** `{flesch_data['media_silabas_por_palavra']} sílabas`",
        "\n---",
        "## 2. 📋 Auditoria de Folha de Estilo & Anacronismos",
    ]

    if style_warnings:
        for warn in style_warnings:
            lines.append(f"- ⚠️ {warn}")
    else:
        lines.append("✅ Nenhuma violação de folha de estilo ou anacronismo encontrado.")

    lines.extend([
        "\n---",
        "## 3. ✂️ Expurgo de Palavras Muleta (Benjamin Dreyer Rule)",
    ])

    if crutch_words:
        for word, count in crutch_words.items():
            lines.append(f"- Termo **'{word}'**: `{count} ocorrência(s)` (Avaliar redução)")
    else:
        lines.append("✅ Nenhuma palavra muleta em excesso foi encontrada no texto.")

    lines.extend([
        "\n---",
        "## 4. 🔄 Detecção de Termos Mais Frequentes (Análise de Eco)",
    ])

    for word, count in repeated_words:
        lines.append(f"- Palavra **'{word}'**: `{count} vezes`")

    lines.extend([
        "\n---",
        "## 5. ✍️ Sanitização Tipográfica & Verba Dicendi",
        f"- **Ajustes Efetuados (Travessões, Verbos de Dizer e Espaços):** `{corrections_count} correções registradas`",
        "\n---",
        "## 6. ✅ Veredito Editorial",
        "O manuscrito passou por todas as Camadas de Revisão e está **APROVADO** para o Layout (Projeto 3 — Diagramação)."
    ])

    return "\n".join(lines)


def trigger_layout_diagramming(book_id: str) -> None:
    """[Sugestão 3] Dispara a execução automática do Layout (Projeto 3 — Diagramação)."""
    print(f"\n🚀 [--auto-approve] Disparando Layout (Projeto 3) para '{book_id}'...")
    python_bin = sys.executable
    
    config_file = Path("inputs") / book_id / "book_config.yaml"
    config = load_style_sheet(config_file)  # Reaproveita o leitor yaml

    fmt = config.get("formato", "A5")
    theme = config.get("tema", "Creme")
    author = config.get("autor", "Autor")
    title = config.get("titulo", book_id)

    cmd = [
        python_bin, "3-layout/main.py",
        "--book-dir", book_id,
        "--format", fmt,
        "--theme", theme,
        "--author", author,
        "--title", title,
        "--cover", "none",
        "--targets", "pdf_print,pdf_digital,epub"
    ]
    try:
        subprocess.run(cmd, check=True)
        print("✨ [Layout] Diagramação executada automaticamente com sucesso!")
    except subprocess.CalledProcessError as err:
        print(f"❌ [Erro] Falha ao executar o Layout automaticamente: {err}", file=sys.stderr)


def main() -> None:
    parser = argparse.ArgumentParser(description="Edit (Projeto 2): Revisão Editorial")
    parser.add_argument("--book-dir", required=True, help="Nome da pasta do livro em inputs/")
    parser.add_argument("--auto-approve", action="store_true", help="Dispara o Layout (Projeto 3 — Diagramação) automaticamente após revisão")
    args = parser.parse_args()

    book_dir = Path("inputs") / args.book_dir
    md_file = book_dir / "texto_original.md"

    if not md_file.exists():
        print(f"❌ Erro: Arquivo {md_file} não encontrado.", file=sys.stderr)
        sys.exit(1)

    print(f"🔍 [Edit] Auditando manuscrito: {md_file}...")
    raw_content = md_file.read_text(encoding="utf-8")

    # 1. Carregar e Checar Folha de Estilo (Sugestão 1)
    style_sheet_path = book_dir / "style_sheet.yaml"
    style_sheet = load_style_sheet(style_sheet_path)
    style_warnings = check_style_sheet_violations(raw_content, style_sheet)

    # 2. Análise Flesch
    flesch_data = calculate_flesch_siqueira(raw_content)
    
    # 3. Análise Dreyer e Repetições
    crutch_words = find_crutch_words(raw_content)
    repeated_words = find_repeated_words(raw_content)

    # 4. Sanitização Tipográfica + Verba Dicendi (Sugestão 2)
    sanitized_content, corrections_count = sanitize_typography(raw_content)

    # 5. Gravar arquivo texto_revisado.md
    revisado_file = book_dir / "texto_revisado.md"
    revisado_file.write_text(sanitized_content, encoding="utf-8")
    print(f"✨ [Edit] Manuscrito lapidado salvo em: {revisado_file}")

    # 6. Gerar Relatório em outputs/<livro>/relatorios/
    out_relatorios_dir = Path("outputs") / args.book_dir / "relatorios"
    out_relatorios_dir.mkdir(parents=True, exist_ok=True)
    report_file = out_relatorios_dir / "relatorio_revisao.md"
    
    report_md = generate_review_report(
        args.book_dir, flesch_data, crutch_words, repeated_words, corrections_count, style_warnings
    )
    report_file.write_text(report_md, encoding="utf-8")
    print(f"📊 [Edit] Relatório de revisão gerado em: {report_file}")

    # 7. Disparo Automático do Layout se ativado (Sugestão 3)
    if args.auto_approve:
        trigger_layout_diagramming(args.book_dir)


if __name__ == "__main__":
    main()
