#!/usr/bin/env python3
"""
src/typst_exporter.py
---------------------
Compilador e exportador Typst para a Boutique de Livros.
Converte Markdown para sintaxe Typst com baixa complexidade ciclomática e Clean Code/SOLID.
"""

import os
import sys
import argparse
import subprocess
from pathlib import Path
from typing import Dict, Tuple, Any, List, Optional
import yaml


def parse_markdown_with_frontmatter(file_path: Path) -> Tuple[Dict[str, Any], str]:
    """Lê um arquivo Markdown e separa o YAML frontmatter do corpo de texto."""
    if not file_path.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {file_path}")

    content = file_path.read_text(encoding="utf-8")
    if not content.startswith("---"):
        return {}, content

    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}, content

    raw_yaml, markdown_body = parts[1], parts[2].strip()
    try:
        metadata = yaml.safe_load(raw_yaml) or {}
    except yaml.YAMLError as exc:
        print(f"[Aviso] Falha ao processar YAML frontmatter: {exc}", file=sys.stderr)
        metadata = {}

    return metadata, markdown_body


def _convert_heading(stripped_line: str) -> Optional[str]:
    """Mapeia títulos Markdown (#, ##, ###) para sintaxe Typst (=, ==, ===)."""
    if stripped_line.startswith("# "):
        return f"= {stripped_line[2:]}\n"
    if stripped_line.startswith("## "):
        return f"== {stripped_line[3:]}\n"
    if stripped_line.startswith("### "):
        return f"=== {stripped_line[4:]}\n"
    return None


def _convert_blockquote(stripped_line: str) -> Optional[str]:
    """Mapeia citação Markdown (> texto) para sintaxe #quote[...] Typst."""
    if stripped_line.startswith("> "):
        quote_text = stripped_line[2:]
        return f"#quote[{quote_text}]\n"
    return None


import re

def _clean_raw_html_and_urls(text: str) -> str:
    """Remove tags HTML brutas (ex: <div>, <p>) e converte links/handles para evitar conflitos no Typst."""
    # Remove HTML tags como <div...>, </div>, <p...>, </p>, <span>, etc.
    cleaned = re.sub(r'</?(?:div|p|span|section|header|footer|article|strong|em|a|img|br|hr)[^>]*>', '', text, flags=re.IGNORECASE)
    # Converte links <https://...> para https://...
    cleaned = re.sub(r'<(https?://[^>]+)>', r'\1', cleaned)
    # Escapa @ para evitar sintaxe de referência a label no Typst (ex: @carolinacordaropereira -> \@carolinacordaropereira)
    cleaned = re.sub(r'@([a-zA-Z0-9_\.]+)', r'\\@\1', cleaned)
    return cleaned


def convert_line_to_typst(line: str) -> str:
    """Converte uma única linha de Markdown para Typst usando regras funcionais limpas."""
    sanitized = _clean_raw_html_and_urls(line)
    stripped = sanitized.strip()
    
    heading = _convert_heading(stripped)
    if heading is not None:
        return heading

    quote = _convert_blockquote(stripped)
    if quote is not None:
        return quote

    # Converte marcadores de lista Markdown com asterisco '* item' ou '* [ ]' para '- item' do Typst
    if stripped.startswith("* "):
        sanitized = line.replace("* ", "- ", 1)

    return sanitized


def convert_markdown_to_typst(markdown_text: str) -> str:
    """Converte texto Markdown em sintaxe Typst de forma modular."""
    lines = markdown_text.splitlines()
    typst_lines = [convert_line_to_typst(line) for line in lines]
    return "\n".join(typst_lines)


def build_typst_document(
    metadata: Dict[str, Any], typst_body: str, input_dir: Path, preset: str = "romance"
) -> str:
    """Gera a estrutura do documento Typst injetando o template e metadados."""
    title = metadata.get("title", "Título do Livro")
    author = metadata.get("author", "Nome do Autor")
    isbn = metadata.get("isbn", "978-0-00000-000-0")
    publisher = metadata.get("publisher", "Editora Boutique")
    year = str(metadata.get("year", "2026"))
    fmt = metadata.get("format", "A5")
    acabamento = metadata.get("acabamento", "brochura")
    theme = str(metadata.get("theme", "Creme")).title()
    paper_hex = "fdf5e6" if theme == "Creme" else "ffffff"

    template_file = (Path(__file__).resolve().parent / "templates_typst" / f"{preset}.typ")
    try:
        rel_template = os.path.relpath(template_file, input_dir)
    except ValueError:
        rel_template = str(template_file)

    rel_template_posix = Path(rel_template).as_posix()

    return f"""#import "{rel_template_posix}": romance-theme, moldura, full-bleed, double-spread, svg-divider, illustrated-chapter-opener

#show: doc => romance-theme(
  title: "{title}",
  author: "{author}",
  isbn: "{isbn}",
  publisher: "{publisher}",
  year: "{year}",
  format: "{fmt}",
  acabamento: "{acabamento}",
  paper-color: rgb("{paper_hex}"),
  doc
)

{typst_body}
"""


# Alias para retrocompatibilidade
generate_typst_document = build_typst_document


def compile_typst(typst_file: Path, output_pdf: Path) -> bool:
    """Executa o compilador `typst` via subprocess para gerar o PDF final."""
    project_root = Path.cwd().resolve()
    cmd = ["typst", "compile", "--root", str(project_root), str(typst_file), str(output_pdf)]
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(f"[Sucesso] PDF gerado com Typst: {output_pdf}")
        return True
    except FileNotFoundError:
        print("[Erro] O executável `typst` não foi encontrado no PATH do sistema.", file=sys.stderr)
        print("Instale o Typst com `brew install typst` ou via https://github.com/typst/typst", file=sys.stderr)
        return False
    except subprocess.CalledProcessError as err:
        print(f"[Erro] Falha ao compilar com Typst:\n{err.stderr}", file=sys.stderr)
        return False


def export_typst_from_file(input_path: Path, output_pdf: Path, preset: str = "romance") -> bool:
    """Pipeline completo de exportação Typst a partir de um arquivo Markdown."""
    metadata, md_body = parse_markdown_with_frontmatter(input_path)
    typst_body = convert_markdown_to_typst(md_body)
    typst_code = generate_typst_document(metadata, typst_body, input_path.parent, preset=preset)

    temp_typst_file = input_path.with_suffix(".typ")
    temp_typst_file.write_text(typst_code, encoding="utf-8")
    print(f"--> Código Typst intermediário gerado: {temp_typst_file}")

    return compile_typst(temp_typst_file, output_pdf)


def build_parser() -> argparse.ArgumentParser:
    """Cria e configura o leitor de argumentos CLI."""
    parser = argparse.ArgumentParser(description="Boutique de Livros - Typst Exporter")
    parser.add_argument("--input", "-i", required=True, help="Caminho do arquivo Markdown de entrada")
    parser.add_argument("--output", "-o", help="Caminho de saída para o PDF gerado")
    parser.add_argument("--preset", default="romance", choices=["romance", "components"], help="Preset de estilo Typst")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    input_path = Path(args.input).resolve()
    output_pdf = Path(args.output).resolve() if args.output else input_path.with_suffix(".pdf")

    print(f"--> Processando {input_path} via Typst Exporter...")
    success = export_typst_from_file(input_path, output_pdf, preset=args.preset)
    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()
