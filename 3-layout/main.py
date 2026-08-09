#!/usr/bin/env python3
"""
main.py
-------
Ponto de entrada principal para a Boutique de Livros (Engine 3.0).
Suporta múltiplos motores de diagramação (typst, html/pagedjs) e alvos de exportação (pdf_print, pdf_digital, epub).
"""

import os
import sys
import argparse
from pathlib import Path
from typing import Dict, List, Set, Any, Optional

from src.parser import process_markdown
from src.builder import build_html
from src.pdf_printer import print_pdf
from src.typst_exporter import export_typst_from_file
from src.epub_exporter import export_epub


VALID_ENGINES: Set[str] = {"typst", "html"}
VALID_TARGETS: Set[str] = {"pdf_print", "pdf_digital", "epub"}
DEFAULT_TARGETS: List[str] = ["pdf_print", "pdf_digital", "epub"]


def get_user_input(prompt_text: str, default_value: str = "") -> str:
    """Solicita entrada interativa do usuário com valor padrão opcional."""
    hint = f" [{default_value}]" if default_value else ""
    value = input(f"{prompt_text}{hint}: ").strip()
    return value if value else default_value


def parse_target_list(targets_arg: Optional[str]) -> List[str]:
    """Parseia a string delimitada por vírgulas de alvos de exportação."""
    if not targets_arg:
        return DEFAULT_TARGETS

    raw_targets = [t.strip().lower() for t in targets_arg.split(",") if t.strip()]
    invalid = set(raw_targets) - VALID_TARGETS
    if invalid:
        print(f"⚠️ Aviso: Alvos de exportação inválidos ignorados: {', '.join(invalid)}")

    valid_selected = [t for t in raw_targets if t in VALID_TARGETS]
    return valid_selected if valid_selected else DEFAULT_TARGETS


def collect_interactive_config(args: argparse.Namespace) -> Dict[str, Any]:
    """Coleta parâmetros interativamente caso não tenham sido passados via CLI."""
    book_dir = args.book_dir
    while not book_dir:
        book_dir = get_user_input("1. Qual o nome da pasta do livro? (ex: O_Olhar_Elevado)")

    input_path = Path("inputs") / book_dir
    
    # Prioriza texto_revisado.md do Edit (Projeto 2) se existir; senão texto_original.md
    md_file = input_path / "texto_revisado.md"
    if not md_file.exists():
        md_file = input_path / "texto_original.md"

    if not md_file.exists():
        print(f"\n❌ Erro: Nenhum manuscrito (texto_revisado.md ou texto_original.md) foi encontrado em {input_path}.")
        sys.exit(1)

    book_format = args.format or get_user_input("2. Qual o formato do livro?", "A5")
    theme = args.theme or get_user_input("3. Qual a cor do fundo/papel?", "Creme")
    author = args.author or get_user_input("4. Qual o nome do(a) Autor(a)?", "Carolina Cordaro")
    title = args.title or get_user_input("5. Qual o Título do livro?", "O Olhar Elevado")

    cover_image = args.cover
    if cover_image is None:
        default_cover = str(input_path / "assets" / "capa_olhar_elevado_v2.png")
        cover_image = get_user_input("6. Caminho da capa (Pressione Enter para usar o padrão)", default_cover)

    return {
        "book_id": book_dir,
        "format": book_format.upper(),
        "theme": theme.title(),
        "author": author,
        "title": title,
        "cover_image": cover_image,
        "input_dir": input_path,
        "md_file": md_file,
        "assets_dir": input_path / "assets"
    }


def execute_typst_engine(config: Dict[str, Any], targets: List[str], output_dir: Path) -> List[str]:
    """Executa a exportação utilizando o motor Typst com saídas organizadas em subpastas."""
    results: List[str] = []
    md_file: Path = config["md_file"]

    pdf_dir = output_dir / "pdf"
    epub_dir = output_dir / "epub"
    pdf_dir.mkdir(parents=True, exist_ok=True)
    epub_dir.mkdir(parents=True, exist_ok=True)

    if "pdf_print" in targets or "pdf_digital" in targets:
        out_pdf = pdf_dir / f"{config['book_id']}_impressao.pdf"
        print(f"📄 Compilando via Typst Exporter ({md_file} -> {out_pdf})...")
        success = export_typst_from_file(md_file, out_pdf)
        if success:
            results.append(f"PDF Impressão (Typst): {out_pdf}")

    if "epub" in targets:
        out_epub = epub_dir / f"{config['book_id']}.epub"
        print(f"📖 Exportando EPUB ({md_file} -> {out_epub})...")
        success = export_epub(md_file, out_epub, config)
        if success:
            results.append(f"E-book EPUB3: {out_epub}")

    return results


def execute_html_engine(config: Dict[str, Any], targets: List[str], output_dir: Path) -> List[str]:
    """Executa a exportação utilizando o motor HTML/Paged.js com saídas organizadas em subpastas."""
    results: List[str] = []
    md_file: Path = config["md_file"]

    pdf_dir = output_dir / "pdf"
    epub_dir = output_dir / "epub"
    pdf_dir.mkdir(parents=True, exist_ok=True)
    epub_dir.mkdir(parents=True, exist_ok=True)

    print("📝 Lendo e processando Markdown...")
    parsed_sections = process_markdown(str(md_file), config)

    gen_print = "pdf_print" in targets
    gen_digital = "pdf_digital" in targets

    if gen_print or gen_digital:
        print("🏗️ Construindo versões HTML com Paged.js...")
        html_print_path = build_html(parsed_sections, config, is_print=True) if gen_print else None
        html_digital_path = build_html(parsed_sections, config, is_print=False) if gen_digital else None

        print("🖨️ Exportando versões em PDF via Playwright...")
        if gen_print and html_print_path:
            pdf_print_path = print_pdf(html_print_path, config)
            if pdf_print_path:
                results.append(f"Versão Impressão (Paged.js): {pdf_print_path}")

        if gen_digital and html_digital_path:
            pdf_digital_path = print_pdf(html_digital_path, config)
            if pdf_digital_path:
                results.append(f"Versão Digital (Paged.js): {pdf_digital_path}")

    if "epub" in targets:
        out_epub = epub_dir / f"{config['book_id']}.epub"
        print(f"📖 Exportando EPUB ({md_file} -> {out_epub})...")
        success = export_epub(md_file, out_epub, config)
        if success:
            results.append(f"E-book EPUB3: {out_epub}")

    return results


def build_arg_parser() -> argparse.ArgumentParser:
    """Constrói a definição de argumentos da CLI."""
    parser = argparse.ArgumentParser(description="Boutique de Livros - Diagramação Profissional")
    parser.add_argument("--book-dir", help="Nome da pasta do livro dentro de 'inputs/'")
    parser.add_argument("--format", help="Formato (A5, A4, Pocket)")
    parser.add_argument("--theme", help="Tema/Cor do Papel (Creme, Branco)")
    parser.add_argument("--author", help="Nome do Autor")
    parser.add_argument("--title", help="Título do Livro")
    parser.add_argument("--cover", help="Caminho da imagem de capa")
    parser.add_argument(
        "--engine",
        default="typst",
        choices=list(VALID_ENGINES),
        help="Motor de diagramação a ser utilizado (padrão: typst)"
    )
    parser.add_argument(
        "--targets",
        default="pdf_print,pdf_digital,epub",
        help="Alvos de exportação separados por vírgula (ex: pdf_print,pdf_digital,epub)"
    )
    return parser


def main() -> None:
    print("========================================")
    print("      📚 BOUTIQUE DE LIVROS 3.0")
    print("========================================\n")

    parser = build_arg_parser()
    args = parser.parse_args()

    targets = parse_target_list(args.targets)
    config = collect_interactive_config(args)
    
    output_dir = Path("outputs") / config["book_id"]
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n--- INICIANDO DIAGRAMAÇÃO (Motor: {args.engine.upper()} | Alvos: {', '.join(targets)}) ---")

    if args.engine == "typst":
        generated_files = execute_typst_engine(config, targets, output_dir)
    else:
        generated_files = execute_html_engine(config, targets, output_dir)

    print("\n✨ Workflow concluído com sucesso!")
    if generated_files:
        for file_info in generated_files:
            print(f"📂 {file_info}")
    else:
        print("⚠️ Nenhum arquivo foi gerado ou ocorreu uma falha parcial durante o processo.")


if __name__ == "__main__":
    main()
